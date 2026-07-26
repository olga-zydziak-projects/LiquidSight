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
from env.scene_attr import bbox_from_mask, build_attr_scene    # noqa: E402  (3b)

# --- takt (D3) --------------------------------------------------------------
PYB_FREQ = 240
CAM_EVERY = 4                            # render co 4. tik kontroli -> 12 Hz
EPISODE_S = 10.0
CONTROL_STEPS = int(EPISODE_S * CTRL_FREQ)      # 480
POLICY_STEPS = CONTROL_STEPS // CAM_EVERY       # 120
DT_OBS = CAM_EVERY * CTRL_DT                     # 1/12 s (dt miedzy klatkami)

# --- kamera semantyczna 3b (D2): 256^2 z tej samej pozy, tick 1 Hz ----------
SEM_RES = 256
SEM_EVERY = 12                           # co 12. klatke polityki (12 Hz / 12 = 1 Hz)

# --- parametry zadania D1 (r_goal/z_hover/t_dwell zamrozone w I1) -----------
# ANEKS-1 (2026-07-23): dron patrzy na +x (yaw=0), cel w stozku czolowym +x
# (scene_builder Z2). Region startu ograniczony do polowy -x tak, by cel 1-2 m
# w przod zawsze miescil sie w arenie (lim=arena_half-0.3=1.7; d_max=2.0,
# az=25 st. -> start_x<=-0.3, |start_y|<=1.7-2.0*sin25=0.855). Konieczna
# realizacja rewizji D1/D2: "azymut wzgledem +x" wymaga headingu +x od t=0.
DEFAULTS = {
    "res": 64,
    "r_goal": 0.25,
    "z_hover": 0.5,
    "t_dwell": 2.0,
    "arena_half": 2.0,      # geofence xy: |x|,|y| <= 2.0 (arena 4x4)
    "arena_z": 2.5,         # geofence z:  z <= 2.5
    "start_x_lo": -1.5,     # ANEKS-1: start w polowie -x
    "start_x_hi": -0.3,
    "start_y_half": 0.85,   # ANEKS-1: |start_y| <= 0.85
    "start_z": 0.5,
    "start_yaw": 0.0,       # ANEKS-1: heading +x (kamera na +x od t=0)
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
    def reset(self, scene_seed: int, level="T0", scene_type: str = "3a"):
        self.scene_type = scene_type
        self.close()
        rng = np.random.default_rng(scene_seed)
        start_x = float(rng.uniform(self.cfg["start_x_lo"], self.cfg["start_x_hi"]))
        yh = self.cfg["start_y_half"]
        start_y = float(rng.uniform(-yh, yh))
        start_xy = np.array([start_x, start_y])
        start_yaw = float(self.cfg["start_yaw"])       # ANEKS-1: heading +x
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

        builder = build_attr_scene if scene_type == "3b" else build_task_scene
        self.scene = builder(
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
        self._pk = 0                     # licznik krokow polityki (kadencja 3b)
        self._sem_now = None             # ostatnia klatka semantyczna (3b) lub None
        self.pos_hist: list = []         # historia xy drona (3b: wrong-lock)

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
            pos = split_state(state)["pos"]
            self.in_goal.append(float(np.linalg.norm(pos - self.hover)) <= self.cfg["r_goal"])
            if self.scene_type == "3b":                 # historia xy (wrong-lock)
                self.pos_hist.append(np.asarray(pos[:2], dtype=np.float64))
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
                if self.scene_type == "3b":             # D5: wrong-lock vs no-arrival vs dwell
                    self.fail_type = ("wrong_lock" if self._wrong_lock()
                                      else ("no_arrival" if not any(self.in_goal) else "dwell"))
                else:
                    self.fail_type = "dwell"

        # kamera semantyczna 256^2 (D2): co SEM_EVERY krok polityki, ta sama poza
        self._sem_now = None
        if self.scene_type == "3b" and (self._pk % SEM_EVERY == 0):
            self._sem_now = self._render_semantic(state)
        self._pk += 1
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

    def _wrong_lock(self) -> bool:
        """3b (D5): czy dron utrzymal zawis (dwell) w r_goal WOKOL innego obiektu."""
        dwell_ticks = int(round(self.cfg["t_dwell"] * CTRL_FREQ))
        w0 = CONTROL_STEPS - dwell_ticks
        if len(self.pos_hist) < CONTROL_STEPS:
            return False
        window = self.pos_hist[w0:CONTROL_STEPS]
        rg = self.cfg["r_goal"]
        for obj in self.scene["objects"]:
            if obj["designated"]:
                continue
            oxy = np.asarray(obj["pos"][:2], dtype=np.float64)
            if all(np.linalg.norm(pxy - oxy) <= rg for pxy in window):
                return True
        return False

    def _render_semantic(self, state) -> dict:
        """Kamera semantyczna 256^2 z tej samej pozy (D2) + GT bbox wskazanego."""
        s = split_state(state)
        rgb256, seg256 = drone_camera(self.env.CLIENT, s["pos"], s["quat"],
                                      SEM_RES, want_seg=True)
        _, seg64 = drone_camera(self.env.CLIENT, s["pos"], s["quat"],
                                self.res, want_seg=True)
        did = self.scene["designated_id"]
        return {"rgb256": rgb256, "gt_bbox_256": bbox_from_mask(seg256, did),
                "gt_bbox_64": bbox_from_mask(seg64, did), "pk": self._pk}

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
        if self.scene_type == "3b":                     # rozszerzenia 3b (T2)
            info["designated_id"] = self.scene["designated_id"]
            info["command"] = self.scene["command"]
            info["objects"] = self.scene["objects"]
            sem = self._sem_now
            info["rgb256"] = sem["rgb256"] if sem else None
            info["gt_bbox_256"] = sem["gt_bbox_256"] if sem else None
            info["gt_bbox_64"] = sem["gt_bbox_64"] if sem else None
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
