"""diag_r6 — DIAG R6: kubelki B1-B4 + DEKOMPOZYCJA wrong-lock (jeden replay, frozen).

Wrong-lock: pierwszy-lock-zly (pierwszy dostarczony lock = other, polityka przykleja
sie) vs kradziez-w-locie (pierwszy = designated, potem nadpisany other). Zasila decyzje
o scianie drugiej. Eval-only, zero treningu.
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

OUT = os.path.join(_ROOT, "results", "s3b2r6")
CKPT = os.path.join(_ROOT, "ckpt", "s3b2r6", "policy_gc5.pt")
BLIND, LATE_S, NEAR = 0.7, 3.0, 0.5


def main():
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    eps = []
    try:
        for seed in EVAL_SEEDS:
            K, A = scene_params(seed)
            obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
            command, did, objects = info["command"], info["designated_id"], info["objects"]
            h = model.init_hidden(1, device); tr = Tracker5()
            ticks, src_matched = [], []           # src_matched: matched dostarczonych zrodel
            positions = []
            for k in range(POLICY_STEPS):
                tgt = tr.vector(k)
                action, h = model.act(obs, tgt, h, device)
                obs, info, done = env.step(action)
                st = env.env._getDroneStateVector(0); sp = split_state(st)
                positions.append(np.asarray(sp["pos"], float))
                if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                    box, conf, _ = client.query(info["rgb256"], command)
                    tr.observe(k, box)
                    _, seg = drone_camera(env.env.CLIENT, sp["pos"], sp["quat"], 256, want_seg=True)
                    gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                    dist = float(np.linalg.norm(np.asarray(sp["pos"]) - env.hover))
                    if box is None:
                        m = "no_detection"
                    elif gtb.get(did) and iou(box, gtb[did]) >= 0.5:
                        m = "designated"
                    else:
                        m = "other" if any(i != did and b and iou(box, b) >= 0.5 for i, b in gtb.items()) else "background"
                    ticks.append({"k": k, "t": round(k * DT, 3), "matched": m, "dist": round(dist, 3)})
                    if box is not None:
                        src_matched.append(m)
                if done:
                    break
            positions = np.array(positions)
            min_dist = float(np.min(np.linalg.norm(positions - env.hover, axis=1)))
            eps.append({"seed": seed, "K": K, "A": A, "success": bool(info["success"]),
                        "fail_type": info["fail_type"], "min_dist": min_dist,
                        "ticks": ticks, "src_matched": src_matched})
    finally:
        client.close()
    env.close()

    # kubelki B1-B4
    def bucket(e):
        des = [t for t in e["ticks"] if t["matched"] == "designated"]
        if not des: return "B1"
        if des[0]["t"] > LATE_S: return "B2"
        theft = any(t["dist"] >= BLIND for t in des) and any(t["matched"] == "other" and t["dist"] < BLIND for t in e["ticks"])
        if e["fail_type"] == "wrong_lock" and theft: return "B3"
        return "B4"
    fails = [e for e in eps if not e["success"]]
    buckets = collections.Counter(bucket(e) for e in fails)
    n = len(eps)
    kub = {b: {"ep": buckets.get(b, 0), "pp": round(100 * buckets.get(b, 0) / n, 1)} for b in ("B1", "B2", "B3", "B4")}

    # dekompozycja wrong-lock: pierwszy-zly vs kradziez
    wl = [e for e in eps if e["fail_type"] == "wrong_lock"]
    first_bad, theft, other = 0, 0, 0
    for e in wl:
        sm = e["src_matched"]
        if not sm:
            other += 1; continue
        if sm[0] == "other":
            first_bad += 1
        elif "designated" in sm and "other" in sm[sm.index("designated"):]:
            theft += 1
        else:
            other += 1
    other_dists = [t["dist"] for e in eps for t in e["ticks"] if t["matched"] == "other"]
    out = {"n_ep": n, "n_fail": len(fails), "kubelki": kub,
           "wrong_lock": {"total": len(wl), "pierwszy_lock_zly": first_bad, "kradziez_w_locie": theft, "inne": other,
                          "pierwszy_zly_pp": round(100 * first_bad / n, 1), "kradziez_pp": round(100 * theft / n, 1)},
           "other_tick_dist_median": round(float(np.median(other_dists)), 3) if other_dists else None,
           "near_miss_B4_pct": round(100 * sum(1 for e in fails if bucket(e) == "B4" and e["min_dist"] <= NEAR) / max(1, buckets.get("B4", 0)), 1)}
    json.dump(out, open(os.path.join(OUT, "diag_r6.json"), "w"), indent=2)
    print("DIAG R6:")
    for b in ("B1", "B2", "B3", "B4"): print(f"  {b}: {kub[b]['ep']} ep = {kub[b]['pp']} pp")
    print(f"  wrong-lock total={len(wl)}: pierwszy-zly={first_bad} ({out['wrong_lock']['pierwszy_zly_pp']}pp) "
          f"kradziez={theft} ({out['wrong_lock']['kradziez_pp']}pp) inne={other}")
    print(f"  B4 near-miss%={out['near_miss_B4_pct']} | other-tick dist median={out['other_tick_dist_median']}m")


if __name__ == "__main__":
    main()
