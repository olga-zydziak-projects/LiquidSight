"""smoke_arm — smoke nominalny pelnocyklowy (I3a-R2 / ANEKS-4).

Pelny cykl treningu wg ZUNIFIKOWANEJ procedury C1 (train/procedure.run_cycle):
4 etapy OD ZERA (BC=runda0 + DAgger 1..3), best-val, 120 epok/etap. Jeden kod
dla wszystkich ramion. Ewaluacja WYLACZNIE nominal (43000-43099). Checkpointy
smoke NIE wchodza do biegu wiazacego (I3b trenuje wszystkie seedy od zera).
Patologie (NaN, ~0% nominal) -> STOP z diagnoza. Warunek T4: A_GRU<90% ->
FLAGA STOP (aneks nie moze pogarszac referencji).

Uzycie: python -m train.smoke_arm A_NCP|A_CFC|A_GRU [--lr 3e-4] [--seed 45010]
Wynik: results/smoke_<arm>.json
"""
import argparse
import collections
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.arms import build_arm, core_params  # noqa: E402
from train.common import (EpisodeStore, eval_policy_episode, get_device,  # noqa: E402
                          load_cfg, make_env)
from train.procedure import run_cycle  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
DGDIR = os.path.join(_ROOT, "data", "dagger_smoke")
NOMINAL = list(range(43000, 43100))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["A_NCP", "A_CFC", "A_GRU"])
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=45010)
    args = ap.parse_args()

    cfg = load_cfg()
    device = get_device()

    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    val_store = EpisodeStore()
    for s in split["val"]:
        val_store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))

    print(f"{args.arm} | rdzen {core_params(build_arm(args.arm))} param | lr {args.lr} | "
          f"seed {args.seed} | device {device} | store {len(store)}tr/{len(val_store)}val")

    # --- pelny cykl wg procedury C1 (Z1-Z3) ---
    env = make_env(cfg)
    t0 = time.perf_counter()
    model, stages = run_cycle(args.arm, args.lr, args.seed, cfg, env, store,
                              val_store, device, DGDIR)
    sec_cykl = time.perf_counter() - t0

    # --- ewaluacja NOMINAL (43000-43099) ---
    te = time.perf_counter()
    model.eval()
    succ = 0
    fails = collections.Counter()
    for s in NOMINAL:
        r = eval_policy_episode(env, model, s, "T0", cfg, device)
        if r["success"]:
            succ += 1
        else:
            fails[r["fail_type"]] += 1
    env.close()
    te = time.perf_counter() - te
    nom_pct = round(100 * succ / len(NOMINAL), 1)
    if nom_pct < 1.0:
        raise RuntimeError(f"nominal ~0% ({nom_pct}) -> STOP (patologia)")

    bc = stages[0]
    dagger = [{"round": s["round"], "rollout_succ_pct": s["rollout_succ_pct"],
               "best_val": s["best_val"], "best_epoch": s["best_epoch"],
               "sec_rollout": s["sec_rollout"], "sec_train": s["sec_train"]}
              for s in stages if s["round"] > 0]
    out = {"arm": args.arm, "lr": args.lr, "seed": args.seed,
           "procedura": "C1/ANEKS-4 (od-zera x4 etapy, best-val, 120 epok)",
           "rdzen_param": core_params(model),
           "nominal_sukces": succ, "nominal_pct": nom_pct,
           "nominal_porazki": dict(fails),
           "bc": {"best_val": bc["best_val"], "best_epoch": bc["best_epoch"],
                  "train_mse_start_end": bc["train_mse_start_end"],
                  "sec_train": bc["sec_train"]},
           "dagger": dagger,
           "sec_cykl_treningu": round(sec_cykl, 1),
           "sec_eval_nominal": round(te, 1)}
    if args.arm == "A_GRU" and nom_pct < 90.0:
        out["FLAGA"] = f"A_GRU<90% ({nom_pct}) -> STOP par.T4 (aneks pogarsza referencje)"
    with open(os.path.join(_ROOT, "results", f"smoke_{args.arm}.json"), "w") as f:
        json.dump(out, f, indent=2)
    traj = "->".join(str(d["rollout_succ_pct"]) for d in dagger)
    print(f"{args.arm} NOMINAL: {succ}/{len(NOMINAL)} = {nom_pct}% | DAgger {traj} | "
          f"cykl {sec_cykl:.0f}s | porazki={dict(fails)}")


if __name__ == "__main__":
    main()
