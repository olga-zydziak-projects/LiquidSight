"""s3b2r6 — ANEKS-3B-6: hover-rich BC. Przepis S3b2-R + Z1 (stratyfikowany val) + ROUNDS=3.

JEDNA zmiana: BC = 400 ep = 300 std (46000-46299, ekspert std) + 100 hover-rich
(47200-47299, ekspert szybki najazd v_max=2/t_ramp=0.5 — ta sama klasa HoverExpert —
+ trzyma zawis). F2 OFF. Cel: kubelek B4 (precyzja dwell).

CLI: python -m train.s3b2r6 {train|precond|g1r}
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
# ROUNDS=3 i DAGGER_SEEDS oryginalne (S3b2-R) — swiezy proces, bez kontaminacji z r5
s.CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r6")
s.OUT = os.path.join(_ROOT, "results", "s3b2r6")
s.CKPT = os.path.join(s.CKDIR, "policy_gc5.pt")
SPLIT_SEED, VAL_FRAC = 45021, 0.08
BC_STD = range(46000, 46300)
BC_HOVER = range(47200, 47300)
HOVER_TR = 0.25          # age_n > 0.25 <=> age_s > 2.0 s


def cmd_train6():
    os.makedirs(s.CKDIR, exist_ok=True); os.makedirs(s.OUT, exist_ok=True)
    device = s.get_device(); cfg = s.load_cfg(); env = s.make_env(cfg)
    hover_cfg = {**cfg, "v_max": 2.0, "t_ramp_min": 0.5}      # szybki najazd (augmentacja)
    print(f"S3b2-R6 hover-rich | ROUNDS={s.ROUNDS} | {json.dumps(param_report(PolicyGC5()))}", flush=True)
    client = s.GrounderClient()
    conf_log, alog = [], []
    rng = np.random.default_rng(SPLIT_SEED)
    train_store, val_store = s.Store5(), s.Store5()
    val_src = collections.Counter()
    age_frac = collections.defaultdict(list)

    def collect_split(seeds, controller, ep_cfg, model=None, tag=""):
        seeds = list(seeds); eps = []
        for sd in seeds:
            ep = s.episode_live(env, client, sd, ep_cfg, controller, model, device, conf_log)
            eps.append(ep); alog.append(ep["assert_log"])
            if "target" in ep:                              # udzial stanow age>2.0
                t = ep["target"][:ep["length"], 4]
                age_frac[tag].append(float((t > HOVER_TR).mean()))
        n_val = max(1, int(round(VAL_FRAC * len(seeds))))
        vidx = set(rng.permutation(len(seeds))[:n_val].tolist())
        for i, ep in enumerate(eps):
            (val_store if i in vidx else train_store).add(ep)
            if i in vidx:
                val_src[tag] += 1
        return (sum(e["success"] for e in eps) if controller == "dagger" else None)

    t0 = time.perf_counter()
    collect_split(BC_STD, "expert", cfg, tag="BC_std")
    collect_split(BC_HOVER, "expert", hover_cfg, tag="BC_hover")
    t_bc = time.perf_counter() - t0
    print(f"BC 400 (std+hover): train={len(train_store)} val={len(val_store)} ({t_bc:.0f}s) | "
          f"age>2.0 frac: std={np.mean(age_frac['BC_std']):.3f} "
          f"hover={np.mean(age_frac['BC_hover']):.3f}", flush=True)

    stages, model = [], None
    for rnd in range(s.ROUNDS + 1):
        n_succ, t_roll = None, 0.0
        if rnd > 0:
            t1 = time.perf_counter(); model.eval()
            n_succ = collect_split(s.DAGGER_SEEDS[rnd - 1], "dagger", cfg, model, tag=f"r{rnd}")
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
           "age_frac_gt2s": {k: round(float(np.mean(v)), 3) for k, v in age_frac.items()},
           "best_epochs": [x["best_epoch"] for x in stages], "stages": stages,
           "total_cycle_s": total, "total_cycle_h": round(total / 3600, 2),
           "contract_asserts": asserts, "hover_cfg": {"v_max": 2.0, "t_ramp_min": 0.5}}
    json.dump(log, open(os.path.join(s.OUT, "train_log.json"), "w"), indent=2)
    with open(os.path.join(s.OUT, "conf_log.jsonl"), "w") as f:
        for r in conf_log:
            f.write(json.dumps(r) + "\n")
    print(f"ZAPIS -> {s.CKPT} ; cykl {total:.0f}s ({total/3600:.2f}h)", flush=True)
    print(f"  best_epochs: {[x['best_epoch'] for x in stages]} | val zrodla: {dict(val_src)}", flush=True)
    print(f"  age>2.0 frac per zrodlo: {log['age_frac_gt2s']} | asserty {json.dumps(asserts)}", flush=True)


if __name__ == "__main__":
    os.makedirs(s.OUT, exist_ok=True)
    {"train": cmd_train6, "precond": s.cmd_precond, "g1r": s.cmd_g1r}[sys.argv[1]]()
