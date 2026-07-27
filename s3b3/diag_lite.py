"""diag_lite — DIAG-lite: dekompozycja porazek PRECONDITION-R na kubelki B1-B4.

UWAGA (jawnie): istniejacy precond_R_audit_tick_audit.jsonl NIE zawiera dystansu
drona ani per-epizod fail_type — niezbednych dla B3 (dist<0.7 m) i B4 (wynik).
Dlatego DIAG-lite wykonuje JEDEN wzbogacony przebieg audytowy na ZAMROZONYM modelu
(zero treningu, zero strojenia — czysty pomiar), logujac per-tick {matched, dist}
i per-epizod {fail_type, success}. Model, config, kanal, env, ekspert — bez zmian.

Kubelki (przypisanie priorytetowe, partycja porazek):
  B1 nigdy-nie-zlockowane : brak designated-ticku w epizodzie
  B2 pozno-zlockowane     : pierwszy designated-tick > 3 s (k>36)
  B3 kradziez w martwym polu: wrong_lock; poprawny lock w dolocie (dist>=0.7)
     nadpisany other-tickiem przy dist<0.7
  B4 lock poprawny do konca a epizod przegrany (dwell/no-arrival, kanal poprawny)

Uruchomienie: .venv/bin/python -m s3b3.diag_lite
"""
from __future__ import annotations

import collections
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, EVAL_SEEDS, Tracker5  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3b2r")
CKPT = os.path.join(_ROOT, "ckpt", "s3b2r", "policy_gc5.pt")
BLIND = 0.7          # martwe pole: dystans do celu < 0.7 m
LATE_S = 3.0


def bucket(ep):
    """Przypisz porazke do jednego kubelka (B1>B2>B3>B4)."""
    des = [t for t in ep["ticks"] if t["matched"] == "designated"]
    if not des:
        return "B1"
    if des[0]["t"] > LATE_S:
        return "B2"
    # kradziez: poprawny lock w dolocie (dist>=BLIND) potem other przy dist<BLIND
    correct_approach = any(t["dist"] >= BLIND for t in des)
    theft = correct_approach and any(t["matched"] == "other" and t["dist"] < BLIND
                                     for t in ep["ticks"])
    if ep["fail_type"] == "wrong_lock" and theft:
        return "B3"
    return "B4"


def main():
    # opcjonalny tag (np. 's3b2r4') przekierowuje CKPT/OUT — reszta bez zmian
    global OUT, CKPT
    if len(sys.argv) > 1:
        tag = sys.argv[1]
        OUT = os.path.join(_ROOT, "results", tag)
        CKPT = os.path.join(_ROOT, "ckpt", tag, "policy_gc5.pt")
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    episodes = []
    other_dists = []
    try:
        for seed in EVAL_SEEDS:
            K, A = scene_params(seed)
            obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
            command, did, objects = info["command"], info["designated_id"], info["objects"]
            h = model.init_hidden(1, device); tr = Tracker5(); ticks = []
            for k in range(POLICY_STEPS):
                tgt = tr.vector(k)
                action, h = model.act(obs, tgt, h, device)
                obs, info, done = env.step(action)
                st = env.env._getDroneStateVector(0); s = split_state(st)
                dist = float(np.linalg.norm(s["pos"] - env.hover))
                if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                    box, conf, _ = client.query(info["rgb256"], command)
                    tr.observe(k, box)
                    _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
                    gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                    if box is None:
                        m = "no_detection"
                    elif gtb.get(did) and iou(box, gtb[did]) >= 0.5:
                        m = "designated"
                    else:
                        m = "other" if any(i != did and b and iou(box, b) >= 0.5
                                           for i, b in gtb.items()) else "background"
                    ticks.append({"k": k, "t": round(k * DT, 3), "matched": m, "dist": round(dist, 3)})
                    if m == "other":
                        other_dists.append(dist)
                if done:
                    break
            episodes.append({"seed": seed, "K": K, "A": A, "success": bool(info["success"]),
                             "fail_type": info["fail_type"], "ticks": ticks})
    finally:
        client.close()
    env.close()

    fails = [e for e in episodes if not e["success"]]
    buckets = collections.Counter(bucket(e) for e in fails)
    n = len(episodes)
    tab = {b: {"epizody": buckets.get(b, 0), "pp": round(100 * buckets.get(b, 0) / n, 1)}
           for b in ("B1", "B2", "B3", "B4")}
    # rozklad dystansu other-tickow
    od = np.array(other_dists) if other_dists else np.array([])
    dist_bins = [0, 0.35, 0.5, 0.7, 1.0, 1.5, 3.0]
    dist_hist = np.histogram(od, bins=dist_bins)[0].tolist() if len(od) else []
    out = {"n_ep": n, "n_fail": len(fails), "kubelki": tab,
           "other_tick_dist": {"n": len(od), "median": round(float(np.median(od)), 3) if len(od) else None,
                               "frac_w_martwym_polu_<0.7": round(float((od < BLIND).mean()), 3) if len(od) else None,
                               "hist": dist_hist, "bins": dist_bins},
           "uwaga": "wzbogacony audyt (1 przebieg, frozen model) — oryginalny log bez dist/wyniku"}
    json.dump(out, open(os.path.join(OUT, "diag_lite.json"), "w"), indent=2)
    json.dump([{k: e[k] for k in ("seed", "K", "A", "success", "fail_type")} | {"bucket": bucket(e) if not e["success"] else "OK"}
               for e in episodes], open(os.path.join(OUT, "diag_lite_episodes.json"), "w"), indent=2)
    print(f"DIAG-lite: {len(fails)}/{n} porazek")
    for b in ("B1", "B2", "B3", "B4"):
        print(f"  {b}: {tab[b]['epizody']} ep = {tab[b]['pp']} pp")
    print(f"  other-tick dist: median {out['other_tick_dist']['median']}m, "
          f"frac<0.7m {out['other_tick_dist']['frac_w_martwym_polu_<0.7']} "
          f"(hist {dist_hist} bins {dist_bins})")


if __name__ == "__main__":
    main()
