"""smoke_arm — smoke nominalny pipeline'u dla ramienia CfC (I3a T3).

Pelny cykl BC + DAgger x3 dla jednego ramienia (seed 45010, hiperparametry
F3_GATE par.3), ewaluacja WYLACZNIE nominal (43000-43099). Checkpointy smoke
NIE wchodza do biegu wiazacego (I3b trenuje wszystkie seedy od zera).
Patologie (NaN, brak spadku straty, ~0% nominal) -> STOP z diagnoza.

Uzycie: python -m train.smoke_arm A_NCP|A_CFC [--lr 3e-4] [--seed 45010]
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
from train.common import (EpisodeStore, collect_dagger_episode, eval_policy_episode,
                          get_device, load_cfg, make_env, masked_mse)  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
DGDIR = os.path.join(_ROOT, "data", "dagger_smoke")
NOMINAL = list(range(43000, 43100))
ROUND_SEEDS = [range(44300, 44400), range(44400, 44500), range(44500, 44600)]
BATCH, CLIP, BC_EPOCHS, DG_EPOCHS = 16, 1.0, 15, 10


def train_epochs(model, store, val_store, device, rng, opt, epochs):
    curve = []
    for _ in range(epochs):
        order = rng.permutation(len(store))
        tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt), sp, mask)
            if torch.isnan(loss):
                raise RuntimeError("NaN w stracie -> STOP (patologia)")
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            tl += float(loss); nb += 1
        curve.append(round(tl / nb, 6))
    model.eval()
    vtot, vn = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(val_store), BATCH):
            idx = list(range(i, min(i + BATCH, len(val_store))))
            rgb, kin, dt, sp, mask = val_store.batch(idx, device)
            vtot += float(masked_mse(model(rgb, kin, dt), sp, mask)) * len(idx); vn += len(idx)
    model.train()
    return curve, vtot / max(vn, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["A_NCP", "A_CFC", "A_GRU"])
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=45010)
    args = ap.parse_args()

    cfg = load_cfg()
    device = get_device()
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    val_store = EpisodeStore()
    for s in split["val"]:
        val_store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))

    model = build_arm(args.arm).to(device)
    print(f"{args.arm} | rdzen {core_params(model)} param | lr {args.lr} | device {device}")

    # --- BC ---
    t0 = time.perf_counter()
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    bc_curve, bc_val = train_epochs(model, store, val_store, device, rng, opt, BC_EPOCHS)
    t_bc = time.perf_counter() - t0
    if bc_curve[-1] >= bc_curve[0]:
        raise RuntimeError(f"BC bez spadku straty {bc_curve[0]}->{bc_curve[-1]} -> STOP")
    print(f"  BC {BC_EPOCHS} epok: train_mse {bc_curve[0]:.4f}->{bc_curve[-1]:.4f} val {bc_val:.4f} | {t_bc:.0f}s")

    # --- DAgger x3 ---
    env = make_env(cfg)
    dg = []
    for r, seeds in enumerate(ROUND_SEEDS, 1):
        seeds = list(seeds)
        rdir = os.path.join(DGDIR, args.arm, f"round{r}")
        os.makedirs(rdir, exist_ok=True)
        tr = time.perf_counter()
        model.eval(); n_succ = 0
        for s in seeds:
            ep = collect_dagger_episode(env, model, s, "T0", cfg, device)
            n_succ += int(ep["success"])
            np.savez_compressed(os.path.join(rdir, f"ep_{s}.npz"), rgb=ep["rgb"], kin=ep["kin"],
                                dt=ep["dt"], setpoint=ep["setpoint"], length=ep["length"], success=ep["success"])
            store.add_npz(os.path.join(rdir, f"ep_{s}.npz"))
        model.train()
        tr = time.perf_counter() - tr
        tt = time.perf_counter()
        opt = torch.optim.Adam(model.parameters(), lr=args.lr)
        _, vl = train_epochs(model, store, val_store, device, rng, opt, DG_EPOCHS)
        tt = time.perf_counter() - tt
        dg.append({"round": r, "rollout_succ_pct": round(100 * n_succ / len(seeds), 1),
                   "val_mse": round(vl, 6), "sec_rollout": round(tr, 1), "sec_train": round(tt, 1)})
        print(f"  DAgger r{r}: rollout {dg[-1]['rollout_succ_pct']}% | val {vl:.4f} | "
              f"{tr:.0f}+{tt:.0f}s")

    # --- ewaluacja NOMINAL (43000-43099) ---
    te = time.perf_counter()
    model.eval(); succ = 0; fails = collections.Counter()
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

    total = t_bc + sum(x["sec_rollout"] + x["sec_train"] for x in dg)
    out = {"arm": args.arm, "lr": args.lr, "seed": args.seed,
           "rdzen_param": core_params(model),
           "nominal_sukces": succ, "nominal_pct": nom_pct, "nominal_porazki": dict(fails),
           "bc_curve": bc_curve, "bc_val": round(bc_val, 6), "sec_bc": round(t_bc, 1),
           "dagger": dg, "sec_eval_nominal": round(te, 1),
           "sec_cykl_treningu": round(total, 1)}
    with open(os.path.join(_ROOT, "results", f"smoke_{args.arm}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"{args.arm} NOMINAL: {succ}/{len(NOMINAL)} = {nom_pct}% | cykl treningu {total:.0f}s | "
          f"porazki={dict(fails)}")


if __name__ == "__main__":
    main()
