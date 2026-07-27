"""diag_b4 — DIAG-B4: dlaczego B4 (lock poprawny, epizod przegrany).

Deterministyczny REPLAY zamrozonego PolicyGC5 na 100 scenach eval (eval-only, zero
treningu; kontrakt/env/ekspert/config bez zmian). Loguje per-tick (in-FOV): box live
vs GT bbox (256), poza drona (do back-projekcji); per-epizod: pozycje (min dystans,
dwell). Analiza wg T1:
  a) profil koncowy: min dystans, blad dwell; near-miss (<=0.5 m) vs lost.
  b) jakosc boxow: J = mediana bledu centroidu (px@256) po tikach in-FOV;
     J_last = blad OSTATNIEGO dostarczonego boxa przed martwym polem (dist>=0.5).
  c) test przyczynowy: korelacja offsetu hoveru (dwell_xy - GT) z bledem
     back-projektowanego boxa (box_xy - GT) — czy polityka wisi gdzie wskazal box.

Uruchomienie: .venv/bin/python -m s3b3.diag_b4
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pybullet as p
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_attr import bbox_from_mask  # noqa: E402
from env.scene_builder import CAM_LOOK_DZ, drone_camera  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, EVAL_SEEDS, Tracker5  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3b2r")
CKPT = os.path.join(_ROOT, "ckpt", "s3b2r", "policy_gc5.pt")
NEAR_MISS = 0.5          # min dystans <=0.5 m => near-miss
BLIND = 0.5              # J_last: ostatni box przed dist<0.5
Z_OBJ = 0.08             # wysokosc srodka obiektu (back-proj plane)
DWELL_STEPS = 24         # ~2 s okna dwell (policy steps)


def view_proj(client, pos, quat, res=256):
    R = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
    eye = np.asarray(pos) + R @ np.array([0.10, 0.0, 0.02])
    look = eye + R @ np.array([1.0, 0.0, CAM_LOOK_DZ])
    up = R @ np.array([0.0, 0.0, 1.0])
    view = np.array(p.computeViewMatrix(eye.tolist(), look.tolist(), up.tolist())).reshape(4, 4, order="F")
    proj = np.array(p.computeProjectionMatrixFOV(60, 1.0, 0.05, 6.0)).reshape(4, 4, order="F")
    return view, proj


def backproject(px, py, view, proj, res=256, zp=Z_OBJ):
    Minv = np.linalg.inv(proj @ view)
    def un(nz):
        v = Minv @ np.array([2 * (px + 0.5) / res - 1, 1 - 2 * (py + 0.5) / res, nz, 1.0])
        return v[:3] / v[3]
    a, b = un(-1.0), un(1.0)
    d = b - a
    if abs(d[2]) < 1e-9:
        return None
    t = (zp - a[2]) / d[2]
    w = a + t * d
    return np.array([w[0], w[1]])


def centroid(bb):
    return np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2])


def main():
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    bucket = {e["seed"]: e["bucket"] for e in json.load(open(os.path.join(OUT, "diag_lite_episodes.json")))}
    client = GrounderClient()
    rows = []
    try:
        for seed in EVAL_SEEDS:
            obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
            command, did = info["command"], info["designated_id"]
            hover_xy = np.asarray(env.hover[:2], float)
            h = model.init_hidden(1, device); tr = Tracker5()
            positions = []; jitters = []; last_box = None; last_pose = None
            for k in range(POLICY_STEPS):
                tgt = tr.vector(k)
                action, h = model.act(obs, tgt, h, device)
                obs, info, done = env.step(action)
                st = env.env._getDroneStateVector(0); s = split_state(st)
                pos = np.asarray(s["pos"], float); positions.append(pos)
                dist = float(np.linalg.norm(pos - env.hover))
                if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                    box, conf, _ = client.query(info["rgb256"], command)
                    tr.observe(k, box)
                    _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
                    gtb = bbox_from_mask(seg, did)
                    if box is not None and gtb is not None and (seg == did).sum() >= 3:
                        jit = float(np.linalg.norm(centroid(box) - centroid(gtb)))
                        jitters.append(jit)
                        if dist >= BLIND:                    # ostatni dostarczony w dolocie
                            last_box = list(box); last_pose = (s["pos"], s["quat"]); last_gt = list(gtb)
                if done:
                    break
            positions = np.array(positions)
            min_dist = float(np.min(np.linalg.norm(positions - env.hover, axis=1)))
            dwell_xy = positions[-DWELL_STEPS:, :2].mean(axis=0)
            row = {"seed": seed, "bucket": bucket.get(seed, "?"),
                   "min_dist": round(min_dist, 3), "near_miss": min_dist <= NEAR_MISS,
                   "J": (round(float(np.median(jitters)), 2) if jitters else None),
                   "J_last": None, "dhover": (dwell_xy - hover_xy).tolist(), "dbox": None}
            if last_box is not None:
                row["J_last"] = round(float(np.linalg.norm(centroid(last_box) - centroid(last_gt))), 2)
                vw, pr = view_proj(env.env.CLIENT, last_pose[0], last_pose[1])
                bxy = backproject(*centroid(last_box), vw, pr)
                if bxy is not None:
                    row["dbox"] = (bxy - hover_xy).tolist()
            rows.append(row)
    finally:
        client.close()
    env.close()

    B4 = [r for r in rows if r["bucket"] == "B4"]
    OK = [r for r in rows if r["bucket"] == "OK"]
    def med(rs, key):
        vs = [r[key] for r in rs if r[key] is not None]
        return round(float(np.median(vs)), 2) if vs else None
    nm_b4 = round(100 * sum(r["near_miss"] for r in B4) / len(B4), 1)
    # korelacja c) na B4 (skladowe dbox vs dhover, gdzie oba dostepne)
    dbx, dhv = [], []
    for r in B4:
        if r["dbox"] is not None:
            dbx += r["dbox"]; dhv += r["dhover"]
    corr = round(float(np.corrcoef(dbx, dhv)[0, 1]), 3) if len(dbx) >= 4 else None
    tab = {"n_B4": len(B4), "n_OK": len(OK),
           "near_miss_pct_B4": nm_b4,
           "lost_pct_B4": round(100 - nm_b4, 1),
           "J_med_B4": med(B4, "J"), "J_med_OK": med(OK, "J"),
           "J_last_med_B4": med(B4, "J_last"), "J_last_med_OK": med(OK, "J_last"),
           "J_last_ratio_B4_vs_OK": (round(med(B4, "J_last") / med(OK, "J_last"), 2)
                                     if med(OK, "J_last") else None),
           "korelacja_dbox_dhover_B4": corr, "n_corr_points": len(dbx)}
    json.dump({"tabela": tab, "rows": rows}, open(os.path.join(OUT, "diag_b4.json"), "w"), indent=2)
    print("DIAG-B4:")
    for k, v in tab.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
