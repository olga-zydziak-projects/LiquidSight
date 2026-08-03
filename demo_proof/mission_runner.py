"""demo_proof/mission_runner.py — runner misji ciągłej (faza MC B2).

JEDEN ciągły sim (bez teleportów, rider 1): env.reset RAZ; między nogami tylko SOFT RE-ARM
liczników epizodu (ctick/done/in_goal/pos_hist/_pk/_sem_now) — self.env (dron+fizyka) NIETKNIĘTE,
dron leci nieprzerwanie. Segmenty:
  LEARNED-LEG   — lot polityki gc5 z home (in-distribution) do celu, osłona APPLIED.
  SCRIPTED-TRANSIT — egzekutor (setpoint→DSL-PID) leci dronem do home; BEZ polityki (przelot w kadrze).
Trace globalny (ciągły k), typ segmentu per odcinek. Zero pomiaru, nagranie≠pomiar.

Smoke: .venv/bin/python -m demo_proof.mission_runner smoke   (waliduje lot z home = in-distribution)
"""
from __future__ import annotations
import os
import sys
import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa
from env.scene_attr import scene_params  # noqa
from models.policy_gc5 import PolicyGC5  # noqa
from train.common import get_device, load_cfg, make_env  # noqa
from task import split_state  # noqa
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5, CKPT  # noqa
from s3b3.live_grounder import TICK_EVERY, GrounderClient  # noqa
from s3c1.shield import Shield, HOLD, REFUSE  # noqa
from expert.expert import HoverExpert  # noqa

Z_HOVER = 0.5
R_GOAL = 0.25
HOME = np.array([-0.9, 0.0, Z_HOVER])          # środek regionu spawnu (in-distribution start)


class Mission:
    def __init__(self, seed):
        self.cfg = load_cfg(); self.env = make_env(self.cfg)
        self.device = get_device()
        self.model = PolicyGC5().to(self.device)
        self.model.load_state_dict(torch.load(CKPT, map_location=self.device)); self.model.eval()
        self.client = GrounderClient()
        self.env.reset(scene_seed=seed, level="T0", scene_type="3b")   # RAZ (spawn)
        self.seed = seed; self.K, self.A = scene_params(seed)
        self.objects = [dict(o) for o in self.env.scene["objects"]]
        self.gk = 0                                # globalny licznik tików
        self.trace = []

    def _rearm(self, hover):
        e = self.env
        e.ctick = 0; e.done = False; e.fail_type = None
        e.in_goal = []; e.pos_hist = []; e._pk = 0; e._sem_now = None
        e.hover = np.asarray(hover, float)         # cel nogi (self.env/dron NIETKNIETE — bez teleportu)

    def _pos(self):
        return np.asarray(split_state(self.env.env._getDroneStateVector(0))["pos"], float)

    def _log(self, seg, dec, extra=None):
        d = {"g": self.gk, "seg": seg, "pos": [round(float(x), 3) for x in self._pos()],
             "state": dec.get("state"), "decision": dec.get("decision"), "reason": dec.get("reason"),
             "rule": dec.get("rule"), "age_s": dec.get("_age"), "link": dec.get("_link"),
             "conf": dec.get("_conf")}
        if extra:
            d.update(extra)
        self.trace.append(d); self.gk += 1

    def transit_home(self, home=HOME, max_ticks=60, tol=0.15):
        """SCRIPTED-TRANSIT: egzekutor + gładka rampa eksperta (HoverExpert) leci dronem do home;
        BEZ polityki (przelot w kadrze, deterministyczny). Rider 1: zero teleportu."""
        self._rearm(home)
        expert = HoverExpert(self._pos(), home, v_max=1.0, t_ramp_min=2.0)
        for k in range(max_ticks):
            sp = expert.setpoint(k * DT).astype(np.float32)          # [pos, vel] gładka rampa
            self._log("SCRIPTED-TRANSIT", {"state": "TRANSIT", "decision": "TRANSIT",
                      "_link": "n/a", "_age": None, "_conf": None})
            self.env.step(sp)
            if k > 20 and float(np.linalg.norm(self._pos()[:2] - home[:2])) <= tol:
                break
        return self._pos()

    def fly_leg(self, target_obj, max_ticks=140, drop_mode=None, drop_param=None,
                mask_seed=45105, burst_offset=None):
        """LEARNED-LEG: lot polityki do celu (osłona APPLIED). drop: None|('bernoulli',p)|('burst',L)."""
        cmd = f"fly to the {target_obj['color']} {target_obj['shape']}"
        hover = np.array([target_obj['pos'][0], target_obj['pos'][1], Z_HOVER])
        self._rearm(hover)
        h = self.model.init_hidden(1, self.device); tr = Tracker5()
        sh = Shield(arena_half=self.env.cfg["arena_half"], margin=0.2, near=0.5, theta_age_s=2.0,
                    t_acq_s=3.0, t_hold_s=3.0, dt=DT); sh.reset(hover_xy=(hover[0], hover[1]))
        obs = self.env._obs(self.env.env._getDroneStateVector(0)); info = self.env._info(False)
        conf = None; mind = 9.9; window = None; first_lock = None
        n_ticks = max_ticks // TICK_EVERY
        for k in range(max_ticks):
            tgt = tr.vector(k)
            action, h = self.model.act(obs, tgt, h, self.device)
            pos = self._pos()
            has_lock = any(ks + K_DEL <= k for (ks, _) in tr.sources)
            age = float(tgt[4]) * AGE_MAX
            dec = sh.step(k, pos, has_lock, age if has_lock else None, conf,
                          float(np.linalg.norm(pos - hover)))
            dec["_age"] = round(age, 2) if has_lock else None
            dec["_conf"] = round(conf, 4) if conf is not None else None
            dec["_link"] = ("frozen" if (has_lock and age > 6) else "stale" if (has_lock and age > 2)
                            else "live" if has_lock else "seeking")
            applied = action
            if dec["decision"] == HOLD:
                applied = np.array([pos[0], pos[1], pos[2], 0, 0, 0], np.float32)
            elif dec["decision"] == REFUSE:
                self._log("LEARNED-LEG", dec, {"cmd": cmd}); break
            self._log("LEARNED-LEG", dec, {"cmd": cmd})
            obs, info, done = self.env.step(applied)
            mind = min(mind, float(np.linalg.norm(self._pos()[:2] - hover[:2])))
            if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                t = k // TICK_EVERY
                box, cf, _ = self.client.query(info["rgb256"], cmd)
                if cf is not None:
                    conf = cf
                if drop_mode == "burst" and first_lock is None and box is not None:
                    first_lock = t
                    Lt = int(round(drop_param / (TICK_EVERY * DT)))
                    start = (first_lock + burst_offset) if burst_offset is not None else first_lock + 1
                    window = (start, start + Lt)
                dropped = False
                if drop_mode == "bernoulli":
                    rng = np.random.default_rng([mask_seed, self.seed, k]); dropped = rng.random() < drop_param
                elif drop_mode == "burst":
                    dropped = window is not None and window[0] <= t < window[1]
                if box is not None and not dropped:
                    tr.observe(k, box)
            if done:
                break
        return {"cmd": cmd, "min_dist": round(mind, 3),
                "arrived": mind <= R_GOAL, "near": mind <= 0.5}


def smoke():
    m = Mission(49502)
    print(f"scena {m.seed} K{m.K}/{m.A}", flush=True)
    try:
        t0 = m.objects[0]
        r1 = m.fly_leg(t0)                                    # z SPAWN
        print(f"LEG1 spawn '{r1['cmd']}' min={r1['min_dist']} arrived={r1['arrived']}", flush=True)
        m.transit_home()                                     # SCRIPTED-TRANSIT do home
        hp = m._pos(); print(f"transit -> home end={[round(float(x),2) for x in hp[:2]]}", flush=True)
        r2 = m.fly_leg(m.objects[1])                          # z HOME (in-distribution)
        print(f"LEG2 home '{r2['cmd']}' min={r2['min_dist']} arrived={r2['arrived']} near={r2['near']}", flush=True)
        m.transit_home()
        r3 = m.fly_leg(m.objects[3])
        print(f"LEG3 home '{r3['cmd']}' min={r3['min_dist']} arrived={r3['arrived']} near={r3['near']}", flush=True)
        print(f"trace tików={len(m.trace)} (ciągły, bez teleportu)", flush=True)
    finally:
        m.client.close(); m.env.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        smoke()
