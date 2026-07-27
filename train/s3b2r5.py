"""s3b2r5 — ANEKS-3B-5: naprawa selekcji checkpointu (stratyfikowany val-agregat).

JEDNA zmiana vs R4: walidacja selekcyjna = held-out 8% KAZDEJ rundy (BC, r1..r4),
seed splitu 45021 — reprezentuje pelny agregat (nie tylko BC). F2 OFF, ROUNDS=4,
reszta jak S3b2-R. Bezposredni test F-3b-3: best-epoki pozne takze w r4?

CLI: python -m train.s3b2r5 {train|precond|g1r}
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

# F2 OFF (plain Tracker5), F3 (ROUNDS=4)
assert not hasattr(s.Tracker5, "total_rejected"), "F2 musi byc OFF"
s.ROUNDS = 4
s.DAGGER_SEEDS = s.DAGGER_SEEDS + [list(range(47100, 47200))]
s.CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r5")
s.OUT = os.path.join(_ROOT, "results", "s3b2r5")
s.CKPT = os.path.join(s.CKDIR, "policy_gc5.pt")
SPLIT_SEED = 45021
VAL_FRAC = 0.08


def cmd_train5():
    os.makedirs(s.CKDIR, exist_ok=True); os.makedirs(s.OUT, exist_ok=True)
    device = s.get_device(); cfg = s.load_cfg(); env = s.make_env(cfg)
    print(f"S3b2-R5 (stratyfikowany val) | device={device} | {json.dumps(param_report(PolicyGC5()))}", flush=True)
    client = s.GrounderClient()
    conf_log, alog = [], []
    rng = np.random.default_rng(SPLIT_SEED)
    train_store, val_store = s.Store5(), s.Store5()
    val_src = collections.Counter()

    def collect_split(seeds, controller, model=None, tag=""):
        eps = []
        for sd in seeds:
            ep = s.episode_live(env, client, sd, cfg, controller, model, device, conf_log)
            eps.append(ep); alog.append(ep["assert_log"])
        n_val = max(1, int(round(VAL_FRAC * len(seeds))))
        vidx = set(rng.permutation(len(seeds))[:n_val].tolist())
        for i, ep in enumerate(eps):
            if i in vidx:
                val_store.add(ep); val_src[tag] += 1
            else:
                train_store.add(ep)
        return (sum(e["success"] for e in eps) if controller == "dagger" else None)

    t0 = time.perf_counter()
    collect_split(range(46000, 46300), "expert", tag="BC")     # 300 -> 24 val
    t_bc = time.perf_counter() - t0
    print(f"BC live-fed: train={len(train_store)} val={len(val_store)} ({t_bc:.0f}s)", flush=True)

    stages, model = [], None
    for rnd in range(s.ROUNDS + 1):
        n_succ, t_roll = None, 0.0
        if rnd > 0:
            t1 = time.perf_counter(); model.eval()
            n_succ = collect_split(s.DAGGER_SEEDS[rnd - 1], "dagger", model, tag=f"r{rnd}")
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

    asserts = {"n_frames": sum(a["n_frames"] for a in alog),
               "delivery_frame_ok": all(a["delivery_frame_ok"] for a in alog),
               "age_monotonic_ok": all(a["age_monotonic_ok"] for a in alog),
               "conf_nie_w_wejsciu": PolicyGC5.TARGET_DIM == 5,
               "F2_off_0_odrzucen": not hasattr(s.Tracker5, "total_rejected")}
    total = round(t_bc + sum(x["sec_rollout"] + x["sec_train"] for x in stages), 1)
    log = {"params": param_report(PolicyGC5()), "val_zrodla": dict(val_src),
           "best_epochs": [x["best_epoch"] for x in stages], "stages": stages,
           "total_cycle_s": total, "total_cycle_h": round(total / 3600, 2),
           "contract_asserts": asserts, "split_seed": SPLIT_SEED, "val_frac": VAL_FRAC}
    json.dump(log, open(os.path.join(s.OUT, "train_log.json"), "w"), indent=2)
    with open(os.path.join(s.OUT, "conf_log.jsonl"), "w") as f:
        for r in conf_log:
            f.write(json.dumps(r) + "\n")
    print(f"ZAPIS -> {s.CKPT} ; cykl {total:.0f}s ({total/3600:.2f}h)", flush=True)
    print(f"  best_epochs per etap: {[x['best_epoch'] for x in stages]} (test F-3b-3: r4 pozna?)", flush=True)
    print(f"  val zrodla: {dict(val_src)} | asserty {json.dumps(asserts)}", flush=True)


if __name__ == "__main__":
    os.makedirs(s.OUT, exist_ok=True)
    {"train": cmd_train5, "precond": s.cmd_precond, "g1r": s.cmd_g1r}[sys.argv[1]]()
