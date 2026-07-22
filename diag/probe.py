"""diag/probe — sonda diagnostyczna (nominal only): BC-N (bez DAgger) + eval z traj.

NIE dla biegu wiazacego. Checkpointy -> results/diag/. Analizuje mechanizm porazki:
klasyfikacja (dwell/brak-dolotu/inne), wariancja setpointu w fazie zawisu (jitter),
przejscia przez r_goal. Uzycie:
  python -m diag.probe --core <name> --epochs 8 --eval 50 --label <lbl>
core: gru | cfc_ncps | cfc_ncps_bb | cfc_frozen[:ts] | ncp_motor | ncp_state
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
from diag.cells import (CoreCfCFrozen, CoreCfCncps, CoreNCPreadout)  # noqa: E402
from models.policy import Policy  # noqa: E402
from models.twin import TwinPolicy  # noqa: E402
from train.common import (EpisodeStore, DT_OBS, POLICY_STEPS, get_device, load_cfg,  # noqa: E402
                          make_env, masked_mse)
from expert.expert import make_expert_for  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
NOMINAL0 = 43000
BATCH = 16


def build(core_name):
    if core_name == "gru":
        return Policy()
    if core_name == "cfc_ncps":
        return TwinPolicy(CoreCfCncps(units=53, backbone_layers=0))
    if core_name == "cfc_ncps_bb":
        return TwinPolicy(CoreCfCncps(units=32, backbone_layers=1))   # z backbone (ncps)
    if core_name.startswith("cfc_frozen"):
        ts = core_name.split(":")[1] if ":" in core_name else "tick1"
        return TwinPolicy(CoreCfCFrozen(units=70, backbone=64, ts_mode=ts))
    if core_name == "ncp_motor":
        return TwinPolicy(CoreNCPreadout(units=64, out=6, readout="motor"))
    if core_name == "ncp_state":
        return TwinPolicy(CoreNCPreadout(units=64, out=6, readout="state"))
    raise ValueError(core_name)


def bc_train(model, device, epochs, seed=45010):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    curve = []
    for _ in range(epochs):
        order = rng.permutation(len(store))
        tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt), sp, mask)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tl += float(loss); nb += 1
        curve.append(round(tl / nb, 5))
    return curve


@torch.no_grad()
def eval_traj(model, env, cfg, device, n_scenes):
    r_goal = cfg["r_goal"]
    dwell_w = 24                         # ostatnie ~2 s (24 tiki @12Hz)
    recs = []
    succ = 0
    fails = collections.Counter()
    for s in range(NOMINAL0, NOMINAL0 + n_scenes):
        obs, info = env.reset(scene_seed=s, level="T0")
        h = model.init_hidden(1, device)
        hover = env.hover.copy()
        sp_pos, dists, in_goal = [], [], []
        done = False
        for _ in range(POLICY_STEPS):
            act, h = model.act(obs, h, device)
            sp_pos.append(act[:3].copy())
            obs, info, done = env.step(act)
            d = float(np.linalg.norm(obs["kin"][:3] - hover))
            dists.append(d); in_goal.append(d <= r_goal)
            if done:
                break
        if info["success"]:
            succ += 1
        else:
            fails[info["fail_type"]] += 1
        sp_pos = np.array(sp_pos)
        w = sp_pos[-dwell_w:] if len(sp_pos) >= dwell_w else sp_pos
        hover_sp_var = float(np.mean(np.var(w, axis=0)))      # jitter setpointu w zawisie
        crossings = int(np.sum(np.abs(np.diff(np.array(in_goal, int)))))
        recs.append({"seed": s, "success": bool(info["success"]), "fail": info["fail_type"],
                     "min_dist": round(min(dists), 3), "final_dist": round(dists[-1], 3),
                     "hover_sp_var": hover_sp_var, "rgoal_crossings": crossings,
                     "reached_rgoal": bool(any(in_goal))})
    return succ, dict(fails), recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--eval", type=int, default=50)
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    label = args.label or args.core

    cfg = load_cfg(); device = get_device()
    model = build(args.core).to(device)
    ncore = sum(p.numel() for p in model.core.parameters())
    t0 = time.perf_counter()
    curve = bc_train(model, device, args.epochs)
    t_bc = time.perf_counter() - t0

    env = make_env(cfg)
    succ, fails, recs = eval_traj(model, env, cfg, device, args.eval)
    env.close()

    reached = sum(r["reached_rgoal"] for r in recs)
    var_all = float(np.mean([r["hover_sp_var"] for r in recs]))
    var_fail = float(np.mean([r["hover_sp_var"] for r in recs if not r["success"]] or [0]))
    cross = float(np.mean([r["rgoal_crossings"] for r in recs]))
    out = {"core": args.core, "label": label, "epochs": args.epochs,
           "rdzen_param": ncore, "bc_curve": curve, "sec_bc": round(t_bc, 1),
           "nominal_n": args.eval, "nominal_sukces": succ,
           "nominal_pct": round(100 * succ / args.eval, 1), "porazki": fails,
           "dolecialo_do_rgoal": reached, "hover_sp_var_mean": round(var_all, 4),
           "hover_sp_var_fail": round(var_fail, 4), "rgoal_crossings_mean": round(cross, 2)}
    os.makedirs(os.path.join(_ROOT, "results", "diag"), exist_ok=True)
    with open(os.path.join(_ROOT, "results", "diag", f"{label}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[{label}] rdzen {ncore} | BC{args.epochs} {curve[0]}->{curve[-1]} | "
          f"nominal {out['nominal_pct']}% ({succ}/{args.eval}) | dolot->rgoal {reached}/{args.eval} | "
          f"hover_sp_var {var_all:.4f} (fail {var_fail:.4f}) | rgoal_cross {cross:.1f} | porazki {fails}")


if __name__ == "__main__":
    main()
