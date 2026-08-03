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
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa
from s3c1.shield import Shield, HOLD, REFUSE  # noqa
from expert.expert import HoverExpert  # noqa
from env.scene_builder import drone_camera  # noqa
from env.scene_attr import bbox_from_mask, COLORS as SA_COLORS, SHAPE_GEOM as SA_SHAPES  # noqa
from s3c1.traps import relocate_designated_beyond_geofence  # noqa
from demo.record import save_jpg, draw_bbox256  # noqa
from demo_proof.authz import Authorizer  # noqa
from demo_proof.memory import SemanticMemory  # noqa

SAVE_EVERY = 2                                  # rider 4: klatki paneli na niższym fps (wszystkie zdarzenia w trace)
OUT = os.path.join(_ROOT, "results", "demo_proof", "mission")

Z_HOVER = 0.5
R_GOAL = 0.25
HOME = np.array([-0.9, 0.0, Z_HOVER])          # środek regionu spawnu (in-distribution start)
# Obwiednia (stałe zamrożone: config/env_f3.json aneks_1 — spawn_azymut_deg=25, spawn_dystans_m=[1,2])
ENV_AZ_DEG = 25.0
ENV_DIST = (1.0, 2.0)
LAUNCH_R = 1.5                                  # środek [1,2] m; reguła deterministyczna
LAUNCH_CLAMP = 1.6                              # launch musi zostać w arenie (|xy|<=1.6)


def launch_for(target_xy):
    """Reguła launch (deterministyczna, funkcja celu+obwiedni): L = cel − LAUNCH_R·(+x),
    cel dokładnie +x-przed (azymut 0 ⊂ ±25°), dystans 1.5 m ⊂ [1,2]. Clamp do areny."""
    lx = float(np.clip(target_xy[0] - LAUNCH_R, -LAUNCH_CLAMP, LAUNCH_CLAMP))
    ly = float(np.clip(target_xy[1], -LAUNCH_CLAMP, LAUNCH_CLAMP))
    return np.array([lx, ly, Z_HOVER])


def in_envelope(target_xy):
    """Czy cel jest flyable regułą launch: po launchu azymut ⊂ ±25° i dystans ⊂ [1,2]."""
    L = launch_for(target_xy)
    d = target_xy[:2] - L[:2]
    dist = float(np.linalg.norm(d))
    az = abs(np.degrees(np.arctan2(d[1], d[0])))     # względem +x
    return (ENV_DIST[0] - 0.05 <= dist <= ENV_DIST[1] + 0.05) and (az <= ENV_AZ_DEG + 1e-6), dist, az


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
        self.events = []                           # zdarzenia pod napisy (subtitles.vtt)
        self.save = False; self.fidx = 0; self.frame_at = {}
        self.last256 = None; self.last_box = None; self.last_color = "#22c55e"
        self.az = Authorizer(); self.mem = SemanticMemory(); self.admissions = []

    def event(self, kind, text):
        self.events.append({"t": round(self.gk * DT, 2), "g": self.gk, "kind": kind, "text": text})

    def _save_frame(self):
        if not self.save:
            return
        st = self.env.env._getDroneStateVector(0); s = split_state(st)
        rgb64, _ = drone_camera(self.env.env.CLIENT, s["pos"], s["quat"], 64)
        os.makedirs(os.path.join(OUT, "cam256"), exist_ok=True)
        os.makedirs(os.path.join(OUT, "cam64"), exist_ok=True)
        f256 = self.last256 if self.last256 is not None else np.zeros((256, 256, 3), np.uint8)
        save_jpg(draw_bbox256(f256, self.last_box, self.last_color),
                 os.path.join(OUT, "cam256", f"f{self.fidx:04d}.jpg"))
        save_jpg(np.asarray(rgb64, np.uint8), os.path.join(OUT, "cam64", f"f{self.fidx:04d}.jpg"), size=(192, 192))
        self.frame_at[self.gk] = self.fidx; self.fidx += 1

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

    def transit_home(self, home=HOME, max_ticks=80, tol=0.15):
        """SCRIPTED-TRANSIT: egzekutor + gładka rampa eksperta (HoverExpert) leci dronem do home;
        BEZ polityki (przelot w kadrze, deterministyczny). Rider 1: zero teleportu."""
        self._rearm(home)
        self.event("TRANSIT", "reposition to launch (executor) — not the learned pilot")
        expert = HoverExpert(self._pos(), home, v_max=1.0, t_ramp_min=2.0)
        for k in range(max_ticks):
            sp = expert.setpoint(k * DT).astype(np.float32)          # [pos, vel] gładka rampa
            self._log("SCRIPTED-TRANSIT", {"state": "TRANSIT", "decision": "TRANSIT",
                      "_link": "n/a", "_age": None, "_conf": None})
            if k % SAVE_EVERY == 0:
                self._save_frame()
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
                self._log("LEARNED-LEG", dec, {"cmd": cmd}); self._save_frame()
                self.event("REFUSE", f"REFUSE({dec['reason']}) — rule {dec['rule']}"); break
            self._log("LEARNED-LEG", dec, {"cmd": cmd})
            if k % SAVE_EVERY == 0:
                self._save_frame()
            obs, info, done = self.env.step(applied)
            mind = min(mind, float(np.linalg.norm(self._pos()[:2] - hover[:2])))
            if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                self.last256 = info["rgb256"]; t = k // TICK_EVERY
                box, cf, _ = self.client.query(info["rgb256"], cmd)
                if cf is not None:
                    conf = cf
                if drop_mode == "burst" and first_lock is None and box is not None:
                    first_lock = t
                    Lt = int(round(drop_param / (TICK_EVERY * DT)))
                    start = (first_lock + burst_offset) if burst_offset is not None else first_lock + 1
                    window = (start, start + Lt)
                dropped = False
                if drop_mode == "burst":
                    dropped = window is not None and window[0] <= t < window[1]
                    if dropped:
                        self.event("FROZEN", "LINK FROZEN — burst gap, bbox held as ghost, age climbing")
                if box is not None and not dropped:
                    tr.observe(k, box); self.last_box = box
                    st2 = self.env.env._getDroneStateVector(0); s2 = split_state(st2)
                    _, seg = drone_camera(self.env.env.CLIENT, s2["pos"], s2["quat"], 256, want_seg=True)
                    gtb = bbox_from_mask(seg, target_obj["id"])
                    self.last_color = "#22c55e" if (gtb and iou(box, gtb) >= 0.5) else "#eab308"
                    self.event("DELIVERY", f"delivery: '{cmd}' · conf {conf:.3f}" if conf else "delivery")
            if done:
                break
        return {"cmd": cmd, "min_dist": round(mind, 3),
                "arrived": mind <= R_GOAL, "near": mind <= 0.5}


def smoke():
    """Sweep offsetu burstu (L2): szuka offsetu dającego ARRIVED bez REFUSE (bridging w dwell)."""
    m = Mission(49502)
    print(f"scena {m.seed} K{m.K}/{m.A}", flush=True)
    try:
        bs = next(o for o in m.objects if o["color"] == "blue" and o["shape"] == "sphere")
        for off in (3, 4, 5, 6):
            m.transit_home(home=launch_for(np.asarray(bs["pos"], float)))
            n0 = sum(1 for d in m.trace if d["decision"] == "REFUSE")
            rb = m.fly_leg(bs, drop_mode="burst", drop_param=5.0, burst_offset=off)
            refused = sum(1 for d in m.trace if d["decision"] == "REFUSE") > n0
            tag = "ARRIVED" if rb['arrived'] else "NEAR" if rb['near'] else "MISS"
            print(f"  BURST L5 off={off} -> min={rb['min_dist']} {tag} refused={refused} "
                  f"{'<<< CLEAN BRIDGE' if (rb['arrived'] and not refused) else ''}", flush=True)
        print(f"trace tików={len(m.trace)} (ciągły, bez teleportu)", flush=True)
    finally:
        m.client.close(); m.env.close()


def scene_search(start=49500, limit=30):
    """ANEKS_MC1 §C: ascending K8 z red box + blue sphere w obwiedni + relokowalny. Log odrzuconych."""
    cfg = load_cfg(); env = make_env(cfg)
    rejects = []
    try:
        for seed in range(start, start + 400):
            K, A = scene_params(seed)
            if K != 8:
                rejects.append({"seed": seed, "why": "K!=8"}); continue
            env.reset(scene_seed=seed, level="T0", scene_type="3b")
            objs = env.scene["objects"]
            def find(color, shape):
                for o in objs:
                    if o["color"] == color and o["shape"] == shape:
                        ok, d, az = in_envelope(np.asarray(o["pos"], float))
                        if ok:
                            return o
                return None
            rb = find("red", "box"); bs = find("blue", "sphere")
            if rb is None:
                rejects.append({"seed": seed, "why": "brak red box w obwiedni"}); continue
            if bs is None:
                rejects.append({"seed": seed, "why": "brak blue sphere w obwiedni"}); continue
            reloc = next((o for o in objs if o["id"] not in (rb["id"], bs["id"])), None)
            if reloc is None:
                rejects.append({"seed": seed, "why": "brak obiektu do relokacji"}); continue
            print(f"WINNER seed={seed} K8/{A}  red box@{[round(x,2) for x in rb['pos'][:2]]}  "
                  f"blue sphere@{[round(x,2) for x in bs['pos'][:2]]}  reloc={reloc['color']} {reloc['shape']}", flush=True)
            print(f"odrzuconych: {len(rejects)}", flush=True)
            for r in rejects[-8:]:
                print(f"  reject {r['seed']}: {r['why']}", flush=True)
            return seed, rejects
    finally:
        env.close()
    print("SCENE-SEARCH FAIL — STOP"); return None, rejects


import pybullet as p  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402


def _relocate(m, obj_id, pos, coord=2.2):
    tx, ty = float(pos[0]), float(pos[1]); mm = max(abs(tx), abs(ty), 1e-6); s = coord / mm
    nx, ny = tx * s, ty * s
    p.resetBasePositionAndOrientation(int(obj_id), [nx, ny, 0.08], [0, 0, 0, 1],
                                      physicsClientId=m.env.env.CLIENT)
    return np.array([nx, ny])


def _land(m, ticks=28):
    start = m._pos()
    exp = HoverExpert(start, np.array([HOME[0], HOME[1], 0.06]), v_max=0.6, t_ramp_min=2.0)
    m._rearm(np.array([HOME[0], HOME[1], 0.06]))
    for k in range(ticks):
        m._log("SCRIPTED-TRANSIT", {"state": "LANDING", "decision": "LAND", "_link": "n/a", "_age": None, "_conf": None})
        if k % SAVE_EVERY == 0:
            m._save_frame()
        m.env.step(exp.setpoint(k * DT).astype(np.float32))


def _static_refuse(m, reason, ticks=20):
    for _ in range(ticks):
        m._log("ADMISSION-REFUSE", {"state": "DONE", "decision": "REFUSE", "reason": reason,
               "rule": "R-C", "_link": "seeking", "_age": None, "_conf": None})
        if m.gk % SAVE_EVERY == 0:
            m._save_frame()


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def mission():
    """Pełna misja MC na scenie 49508 (ANEKS_MC1). L1-L5, APPLIED, ciągły sim, klatki+trace+events."""
    m = Mission(49508); m.save = True
    try:
        rb = next(o for o in m.objects if o["color"] == "red" and o["shape"] == "box")
        bs = next(o for o in m.objects if o["color"] == "blue" and o["shape"] == "sphere")
        rs = next(o for o in m.objects if o["color"] == "red" and o["shape"] == "sphere")
        reloc = _relocate(m, rs["id"], rs["pos"], 2.2); rs["pos"] = [float(reloc[0]), float(reloc[1]), 0.08]
        m.event("MISSION", "mission start · one continuous recording · shield APPLIED")
        results = {}
        # L1
        r = m.az.admit("fly to the red box"); m.admissions.append({"leg": "L1", **r})
        m.event("ADMIT", f"admit: 'fly to the red box' → ALLOW · sig {r['sig'][:12]}")
        m.transit_home(home=launch_for(np.asarray(rb["pos"], float)))
        m.event("FRAME", "midcourse by executor; terminal flight by the learned pilot within its "
                         "measured envelope (±25° frontal cone, 1–2 m — RAPORT_3B)")
        r1 = m.fly_leg(rb, max_ticks=125); results["L1"] = r1
        m.event("DWELL", f"L1 {'dwell at' if r1['arrived'] else 'approach to (near)'} red box · min {r1['min_dist']} m")
        # L2 (burst L5 offset=4)
        r = m.az.admit("fly to the blue sphere"); m.admissions.append({"leg": "L2", **r})
        m.event("ADMIT", "admit: 'fly to the blue sphere' → ALLOW")
        m.transit_home(home=launch_for(np.asarray(bs["pos"], float)))
        r2 = m.fly_leg(bs, max_ticks=130, drop_mode="burst", drop_param=5.0, burst_offset=4); results["L2"] = r2
        m.event("DWELL", f"L2 burst bridged from memory · {'dwell holds' if r2['arrived'] else 'approach (near)'} · min {r2['min_dist']} m")
        # L3 geofence refuse (admission)
        rg = m.az.admit("fly to the red sphere", target_xy=reloc); m.admissions.append({"leg": "L3", **rg})
        m.event("REFUSE", "admit: 'fly to the red sphere' → REFUSE(GEOFENCE) · proved P2 (drone never leaves 2.0 m)")
        _static_refuse(m, "GEOFENCE"); results["L3"] = {"decision": rg["decision"], "reason": rg["reason"]}
        # L4 correction (crimson→red)
        raw = "fly to the crimson box"
        r0 = m.az.admit(m.mem.resolve(raw)); m.admissions.append({"leg": "L4a", **r0})
        m.event("NO_MATCH", "admit: 'fly to the crimson box' → REFUSE(NO_MATCH) · unknown word")
        lr = m.mem.learn("crimson", "red")
        m.event("CORRECTION", f"operator maps crimson→red · signed record {lr['sig'][:12]}")
        r1c = m.az.admit(m.mem.resolve(raw)); m.admissions.append({"leg": "L4b", **r1c})
        m.event("ADMIT", "admit: 'fly to the red box' (canonical) → ALLOW")
        m.transit_home(home=launch_for(np.asarray(rb["pos"], float)))
        r4 = m.fly_leg(rb, max_ticks=130); results["L4"] = r4
        m.event("DWELL", f"L4 {'dwell at' if r4['arrived'] else 'approach to (near)'} red box · min {r4['min_dist']} m")
        # L5 return home + land
        m.event("ADMIT", "command: 'return home'")
        m.transit_home(home=HOME); _land(m); m.event("LANDED", "landed · mission complete")
        _save_mission(m, results)
    finally:
        m.client.close(); m.env.close()


def _save_mission(m, results):
    os.makedirs(OUT, exist_ok=True)
    scene = {"seed": m.seed, "K": m.K, "A": m.A, "arena_half": 2.0, "geo_lim": 1.8, "margin": 0.2,
             "objects": [{"id": o["id"], "color": o["color"], "shape": o["shape"],
                          "pos": [round(float(x), 4) for x in o["pos"]], "designated": bool(o["designated"])}
                         for o in m.objects],
             "render": {"colors": {k: list(v) for k, v in SA_COLORS.items()}, "shapes": SA_SHAPES}}
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=2)
    mission = {"seed": m.seed, "scene_sha256": _sha(os.path.join(OUT, "scene.json")),
               "n_ticks": len(m.trace), "n_frames": m.fidx, "save_every": SAVE_EVERY,
               "results": {k: {"min_dist": v.get("min_dist"), "arrived": v.get("arrived"),
                               "decision": v.get("decision"), "reason": v.get("reason")} for k, v in results.items()},
               "admissions": m.admissions, "authz_ok": m.az.verify_chain() and m.mem.verify_chain(),
               "burst_L2": {"mask_seed": 45105, "offset": 4}, "envelope": {"az_deg": 25.0, "dist_m": [1.0, 2.0]},
               "trace": m.trace, "events": m.events, "frame_at": m.frame_at}
    json.dump(mission, open(os.path.join(OUT, "mission.json"), "w"), indent=2, ensure_ascii=False)
    print(f"MISSION seed={m.seed} ticks={len(m.trace)} frames={m.fidx} events={len(m.events)}", flush=True)
    for k, v in results.items():
        print(f"  {k}: {v}", flush=True)
    print(f"authz_ok={mission['authz_ok']}  scene_sha={mission['scene_sha256'][:12]}", flush=True)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    {"smoke": smoke, "scene-search": scene_search, "mission": mission}[a]()
