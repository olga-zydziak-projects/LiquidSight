"""s3b2r7 — ANEKS-3B-7: kurikulum GT+live. Przepis S3b2-R + Z1 (stratyfikowany val) + ROUNDS=3.

BC 400 = 300 live-fed (46000-46299, box=zywy YOLO) + 100 GT-fed (47300-47399,
box=gt_bbox_256). Ekspert STANDARDOWY w OBU + DAgger (lekcja F-3b-4: profile predkosci
zgodne). F2 OFF. Assert: mediany/p95 predkosci eksperta zgodne miedzy zrodlami.

CLI: python -m train.s3b2r7 {train|precond|g1r}
"""
from __future__ import annotations

import collections
import json
import os
import sys
import time

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
import train.s3b2r as s  # noqa: E402
from models.policy_gc5 import PolicyGC5, param_report  # noqa: E402

assert not hasattr(s.Tracker5, "total_rejected"), "F2 musi byc OFF"
s.CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r7")
s.OUT = os.path.join(_ROOT, "results", "s3b2r7")
s.CKPT = os.path.join(s.CKDIR, "policy_gc5.pt")
SPLIT_SEED, VAL_FRAC = 45021, 0.08


def cmd_train7():
    os.makedirs(s.CKDIR, exist_ok=True); os.makedirs(s.OUT, exist_ok=True)
    device = s.get_device(); cfg = s.load_cfg(); env = s.make_env(cfg)
    print(f"S3b2-R7 kurikulum GT+live | ROUNDS={s.ROUNDS} | {json.dumps(param_report(PolicyGC5()))}", flush=True)
    client = s.GrounderClient()
    conf_log, alog = [], []
    rng = np.random.default_rng(SPLIT_SEED)
    train_store, val_store = s.Store5(), s.Store5()
    val_src = collections.Counter()
    vel = collections.defaultdict(list)          # predkosci eksperta per zrodlo

    def collect_split(seeds, controller, tag, box_source="live", model=None):
        seeds = list(seeds); eps = []
        for sd in seeds:
            ep = s.episode_live(env, client, sd, cfg, controller, model, device, conf_log, box_source)
            eps.append(ep); alog.append(ep["assert_log"])
            if "setpoint" in ep:
                v = np.linalg.norm(ep["setpoint"][:ep["length"], 3:6], axis=1)
                vel[tag].extend(v.tolist())
        n_val = max(1, int(round(VAL_FRAC * len(seeds))))
        vidx = set(rng.permutation(len(seeds))[:n_val].tolist())
        for i, ep in enumerate(eps):
            (val_store if i in vidx else train_store).add(ep)
            if i in vidx:
                val_src[tag] += 1
        return (sum(e["success"] for e in eps) if controller == "dagger" else None)

    t0 = time.perf_counter()
    collect_split(range(46000, 46300), "expert", "BC_live", box_source="live")
    collect_split(range(47300, 47400), "expert", "BC_gt", box_source="gt")
    t_bc = time.perf_counter() - t0
    print(f"BC 400 (300 live + 100 GT): train={len(train_store)} val={len(val_store)} ({t_bc:.0f}s)", flush=True)

    stages, model = [], None
    for rnd in range(s.ROUNDS + 1):
        n_succ, t_roll = None, 0.0
        if rnd > 0:
            t1 = time.perf_counter(); model.eval()
            n_succ = collect_split(s.DAGGER_SEEDS[rnd - 1], "dagger", f"r{rnd}", "live", model)
            t_roll = time.perf_counter() - t1
        t2 = time.perf_counter(); model, m = s.train_from_scratch(train_store, val_store, device)
        t_tr = time.perf_counter() - t2
        pct = round(100 * n_succ / len(s.DAGGER_SEEDS[rnd - 1]), 1) if rnd > 0 else None
        stages.append({"round": rnd, "train": len(train_store), "val": len(val_store),
                       "rollout_succ_pct": pct, "best_val": m["best_val"], "best_epoch": m["best_epoch"],
                       "sec_rollout": round(t_roll, 1), "sec_train": round(t_tr, 1)})
        print(f"[r{rnd}] train={len(train_store)} val={len(val_store)} "
              f"best_val={m['best_val']:.5f}@{m['best_epoch']} rollout={pct} ({t_roll:.0f}+{t_tr:.0f}s)", flush=True)
    client.close(); env.close()
    torch.save(model.state_dict(), s.CKPT)

    def stats(vs):
        a = np.array(vs); return {"median": round(float(np.median(a)), 3), "p95": round(float(np.percentile(a, 95)), 3)}
    vel_stats = {k: stats(v) for k, v in vel.items()}
    # zgodnosc profili: mediana i p95 BC_live vs BC_gt vs DAgger (r1..r3) w waskim pasmie
    meds = [vel_stats[k]["median"] for k in vel_stats]
    p95s = [vel_stats[k]["p95"] for k in vel_stats]
    profil_zgodny = (max(meds) - min(meds) < 0.05) and (max(p95s) - min(p95s) < 0.1)
    asserts = {"n_frames": sum(a["n_frames"] for a in alog),
               "delivery_frame_ok": all(a["delivery_frame_ok"] for a in alog),
               "age_monotonic_ok": all(a["age_monotonic_ok"] for a in alog),
               "conf_nie_w_wejsciu": PolicyGC5.TARGET_DIM == 5,
               "F2_off_0_odrzucen": not hasattr(s.Tracker5, "total_rejected"),
               "profil_predkosci_zgodny": bool(profil_zgodny)}
    total = round(t_bc + sum(x["sec_rollout"] + x["sec_train"] for x in stages), 1)
    log = {"params": param_report(PolicyGC5()), "val_zrodla": dict(val_src),
           "vel_profil": vel_stats, "best_epochs": [x["best_epoch"] for x in stages],
           "stages": stages, "total_cycle_s": total, "total_cycle_h": round(total / 3600, 2),
           "contract_asserts": asserts}
    json.dump(log, open(os.path.join(s.OUT, "train_log.json"), "w"), indent=2)
    with open(os.path.join(s.OUT, "conf_log.jsonl"), "w") as f:
        for r in conf_log:
            f.write(json.dumps(r) + "\n")
    print(f"ZAPIS -> {s.CKPT} ; cykl {total:.0f}s ({total/3600:.2f}h)", flush=True)
    print(f"  best_epochs: {[x['best_epoch'] for x in stages]} | val zrodla: {dict(val_src)}", flush=True)
    print(f"  vel profil (median/p95): {vel_stats} | zgodny={profil_zgodny}", flush=True)
    print(f"  asserty {json.dumps(asserts)}", flush=True)


if __name__ == "__main__":
    os.makedirs(s.OUT, exist_ok=True)
    {"train": cmd_train7, "precond": s.cmd_precond, "g1r": s.cmd_g1r}[sys.argv[1]]()
