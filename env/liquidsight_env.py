"""liquidsight_env — srodowisko zadaniowe fazy 3 (D1/D1b/D2/D3).

Warstwa wykonawcza (setpoint->DSL-PID, klif v1.0) IMPORTOWANA z frozen_v1/
(kopia bit-w-bit z liquidflight-v1.0). Tutaj wylacznie ADAPTACJE zadaniowe:
- scena fly-to-target + kamera z pozy drona (env/scene_builder.py),
- takt policy@12Hz / kontrola@48Hz / fizyka@240Hz z ZOH setpointu miedzy klatkami,
- sukces/dwell D1 + rozszerzenie klifu o geofence areny i kontakt (D1b).

CtrlAviary konstruowany bezposrednio (potrzebny losowy yaw startowy -> initial_rpys),
klasa pochodzi z gym_pybullet_drones (external/), NIE z frozen.

API:
  reset(scene_seed, level) -> obs, info
  step(setpoint6, want_seg=False) -> obs, info, done
  obs  = {"rgb": uint8 (res,res,3), "kin": float32 (13), "dt": float32 (1,)}
  info = {"success", "fail_type", "gt_target_pos", "seg_mask"?}
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile

import numpy as np
import pybullet as p
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from gym_pybullet_drones.utils.enums import DroneModel, Physics

# --- import warstwy wykonawczej z frozen_v1/ (kopia z liquidflight-v1.0) -----
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FROZEN = os.path.join(_ROOT, "frozen_v1")
for _pth in (_ROOT, _FROZEN):
    if _pth not in sys.path:
        sys.path.insert(0, _pth)
# WYLACZNIE prymitywy warstwy wykonawczej z frozen_v1/task.py (verbatim v1.0);
# logiki zadania okregu (reference/episode_init/CIRCLE_*) celowo NIE importujemy.
from task import (CTRL_DT, CTRL_FREQ, FAIL_TILT_DEG, FAIL_Z_MIN, make_expert,
                  obs_kin, split_state)

from env.scene_builder import build_task_scene, drone_camera  # noqa: E402

# --- takt (D3) --------------------------------------------------------------
PYB_FREQ = 240
CAM_EVERY = 4                            # render co 4. tik kontroli -> 12 Hz
EPISODE_S = 10.0
CONTROL_STEPS = int(EPISODE_S * CTRL_FREQ)      # 480
POLICY_STEPS = CONTROL_STEPS // CAM_EVERY       # 120
DT_OBS = CAM_EVERY * CTRL_DT                     # 1/12 s (dt miedzy klatkami)

# --- parametry zadania D1 (start: strojone na ekspercie w I1) ---------------
DEFAULTS = {
    "res": 64,
    "r_goal": 0.25,
    "z_hover": 0.5,
    "t_dwell": 2.0,
    "arena_half": 2.0,      # geofence xy: |x|,|y| <= 2.0 (arena 4x4)
    "arena_z": 2.5,         # geofence z:  z <= 2.5
    "start_half": 1.5,      # start w centralnych 3x3 m
    "start_z": 0.5,
    "min_target_dist": 1.0,
}


class LiquidSightEnv:
    def __init__(self, **kw):
        self.cfg = {**DEFAULTS, **kw}
        self.res = int(self.cfg["res"])
        self.env: CtrlAviary | None = None
        self.ctrl = None
        self._tmpdir = None

    # -- reset ---------------------------------------------------------------
    def reset(self, scene_seed: int, level="T0"):
        self.close()
        rng = np.random.default_rng(scene_seed)
        sh = self.cfg["start_half"]
        start_xy = rng.uniform(-sh, sh, size=2)
        start_yaw = float(rng.uniform(0.0, 2 * np.pi))
        self.p0 = np.array([start_xy[0], start_xy[1], self.cfg["start_z"]])
        self.start_yaw = start_yaw

        self._tmpdir = tempfile.mkdtemp(prefix="liquidsight_tex_")
        with contextlib.redirect_stdout(io.StringIO()):
            self.env = CtrlAviary(
                drone_model=DroneModel.CF2X, num_drones=1,
                initial_xyzs=self.p0.reshape(1, 3),
                initial_rpys=np.array([[0.0, 0.0, start_yaw]]),
                physics=Physics.PYB, pyb_freq=PYB_FREQ, ctrl_freq=CTRL_FREQ,
                gui=False,
            )
            self.env.reset(seed=int(scene_seed))

        self.scene = build_task_scene(
            client=self.env.CLIENT, plane_id=self.env.PLANE_ID,
            scene_seed=int(scene_seed), level=level, start_xy=start_xy,
            tmpdir=self._tmpdir, arena_half=self.cfg["arena_half"],
            min_target_dist=self.cfg["min_target_dist"])
        self.target_pos = self.scene["target_pos"]
        self.hover = np.array([self.scene["hover_xy"][0], self.scene["hover_xy"][1],
                               self.cfg["z_hover"]])

        self.ctrl = make_expert()
        self.ctrl.reset()

        self.ctick = 0
        self.in_goal: list[bool] = []
        self.fail_type = None
        self.done = False

        state = self.env._getDroneStateVector(0)
        return self._obs(state), self._info(None)

    # -- step ----------------------------------------------------------------
    def step(self, setpoint6, want_seg: bool = False):
        if self.done:
            state = self.env._getDroneStateVector(0)
            return self._obs(state, want_seg), self._info(want_seg), True
        sp = np.asarray(setpoint6, dtype=np.float64).reshape(6)
        tgt_pos, tgt_vel = sp[:3], sp[3:6]

        for _ in range(CAM_EVERY):                      # setpoint ZOH przez 4 tiki
            state = self.env._getDroneStateVector(0)
            rpm, _, _ = self.ctrl.computeControlFromState(
                control_timestep=CTRL_DT, state=state,
                target_pos=tgt_pos, target_vel=tgt_vel)
            self.env.step(np.clip(rpm, 0.0, self.env.MAX_RPM).reshape(1, 4))
            self.ctick += 1
            state = self.env._getDroneStateVector(0)
            dist = float(np.linalg.norm(split_state(state)["pos"] - self.hover))
            self.in_goal.append(dist <= self.cfg["r_goal"])
            ft = self._check_cliff(state)
            if ft is not None:
                self.fail_type, self.done = ft, True
                break
            if self.ctick >= CONTROL_STEPS:
                self.done = True
                break

        state = self.env._getDroneStateVector(0)
        if self.done and self.fail_type is None:        # dojechalo bez katastrofy -> dwell
            if not self._eval_dwell():
                self.fail_type = "dwell"
        return self._obs(state, want_seg), self._info(want_seg), self.done

    # -- klif D1b: v1.0 (z, tilt) z frozen + geofence areny + kontakt --------
    def _check_cliff(self, state) -> str | None:
        s = split_state(state)
        pos, rpy = s["pos"], s["rpy"]
        if pos[2] < FAIL_Z_MIN:
            return "crash"
        if max(abs(rpy[0]), abs(rpy[1])) > np.deg2rad(FAIL_TILT_DEG):
            return "tilt"
        if (abs(pos[0]) > self.cfg["arena_half"] or abs(pos[1]) > self.cfg["arena_half"]
                or pos[2] > self.cfg["arena_z"]):
            return "geofence"
        cps = p.getContactPoints(bodyA=int(self.env.DRONE_IDS[0]),
                                 physicsClientId=self.env.CLIENT)
        if len(cps) > 0:
            return "contact"
        return None

    def _eval_dwell(self) -> bool:
        dwell_ticks = int(round(self.cfg["t_dwell"] * CTRL_FREQ))
        w0 = CONTROL_STEPS - dwell_ticks
        if len(self.in_goal) < CONTROL_STEPS:
            return False
        return all(self.in_goal[w0:CONTROL_STEPS])

    # -- kategoryzacja porazki (D1b): katastrofa vs brak-dolotu/dwell --------
    @staticmethod
    def is_catastrophe(fail_type) -> bool:
        return fail_type in ("tilt", "crash", "geofence", "contact")

    # -- obs / info ----------------------------------------------------------
    def _obs(self, state, want_seg: bool = False):
        rgb, _ = drone_camera(self.env.CLIENT, split_state(state)["pos"],
                              split_state(state)["quat"], self.res, want_seg=False)
        return {"rgb": rgb, "kin": obs_kin(state).astype(np.float32),
                "dt": np.array([DT_OBS], dtype=np.float32)}

    def _info(self, want_seg):
        info = {"success": (self.done and self.fail_type is None),
                "fail_type": self.fail_type,
                "gt_target_pos": self.target_pos.copy()}
        if want_seg and self.env is not None:
            state = self.env._getDroneStateVector(0)
            _, seg = drone_camera(self.env.CLIENT, split_state(state)["pos"],
                                  split_state(state)["quat"], self.res, want_seg=True)
            info["seg_mask"] = (seg == self.scene["target_id"])
        return info

    def close(self):
        if self.env is not None:
            with contextlib.redirect_stdout(io.StringIO()):
                self.env.close()
            self.env = None
        if self._tmpdir and os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
