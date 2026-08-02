"""s3d/measure.py — POMIAR zamkniętej pętli 3d (parowany, BEZ osłony; PRE_3D0 §6).

Frozen polityka `ckpt/s3b2r/policy_gc5.pt` + drop-in filtra na target5[0:4] (age nietknięte).
Metryka pierwotna = czysty sukces env. Nogi: clean / Bernoulli p=0.5 (maska 45102) /
burst L=5 (maska 45105). N=100 na 46500–46599. Parowanie = te same seedy/maski dla ramion.
Metryki wtórne: wrong-lock (+dekompozycja), RMSE-online (na dostarczeniach), age-at-dwell hist.

CLI: .venv/bin/python -m s3d.measure <arm> <leg> [filter_seed]
  arm ∈ {A0,A1,A2,A3}; leg ∈ {clean,p50,L5,all}; filter_seed dla A2/A3 (jeden bieg).
"""
from __future__ import annotations
import collections
import hashlib
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from train.s3b2r import CKPT  # noqa: E402  (frozen policy)
from s3b3.live_grounder import GrounderClient  # noqa: E402
from s3d.rollout import run_episode  # noqa: E402
from s3d.filters import NoFilter, KalmanCV, MicroGRU, MicroCfC  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3d")
CKDIR = os.path.join(_ROOT, "ckpt", "s3d")
EVAL_SEEDS = list(range(46500, 46600))        # N=100
AGE_BINS = [0, .1, .25, .5, .75, 1.01]
LEGS = {"clean": ("clean", 0.0, 45200), "p50": ("bernoulli", 0.5, 45102),
        "L5": ("burst", 5.0, 45105)}          # clean: mask nieużywana


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def build_filter(arm, filter_seed, device):
    if arm == "A0":
        return NoFilter()
    if arm == "A1":
        qr = json.load(open(os.path.join(OUT, "kalman_qr.json")))
        return KalmanCV(q=qr["q"], r=qr["r"])
    cls = {"A2": MicroGRU, "A3": MicroCfC}[arm]
    m = cls().to(device)
    ck = os.path.join(CKDIR, f"{arm}_s{filter_seed}.pt")
    m.load_state_dict(torch.load(ck, map_location=device)); m.eval()
    return m


def decomp_wrong_lock(src_matched):
    if not src_matched:
        return "inne"
    if src_matched[0] == "other":
        return "pierwszy_zly"
    if "designated" in src_matched and "other" in src_matched[src_matched.index("designated"):]:
        return "kradziez"
    return "inne"


def run_leg(env, client, model, device, arm, leg, filter_seed, seeds=None):
    mode, param, mseed = LEGS[leg]
    filt = build_filter(arm, filter_seed, device)
    seeds = seeds if seeds is not None else EVAL_SEEDS
    succ = 0; wl = 0; near_fail = 0
    decomp = collections.Counter(); fails = collections.Counter()
    ages = []; rmses = []; eps = []
    for seed in seeds:
        r = run_episode(env, client, seed, controller="policy", mode=mode, param=param,
                        mask_seed=mseed, model=model, device=device, filt=filt)
        ok = r["success"]; ft = r["fail_type"]
        succ += int(ok)
        if not ok:
            fails[ft] += 1
        if ft == "wrong_lock":
            wl += 1; decomp[decomp_wrong_lock(r["src_matched"])] += 1
        if r["age_at_dwell_entry"] is not None:
            ages.append(r["age_at_dwell_entry"])
        if "rmse_online" in r:
            rmses.append(r["rmse_online"])
        eps.append({"seed": seed, "success": ok, "fail_type": ft,
                    "age_at_dwell_entry": r["age_at_dwell_entry"],
                    "rmse_online": r.get("rmse_online")})
    n = len(seeds)
    hist = np.histogram(ages, bins=AGE_BINS)[0].tolist() if ages else [0] * (len(AGE_BINS) - 1)
    return {
        "arm": arm, "leg": leg, "filter_seed": filter_seed, "mode": mode, "param": param,
        "mask_seed": (mseed if mode != "clean" else None), "n": n,
        "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
        "sd_binom_pp": round(100 * (succ / n * (1 - succ / n) / n) ** 0.5, 1),
        "wrong_lock": wl, "wrong_lock_pct": round(100 * wl / n, 1),
        "wrong_lock_decomp": dict(decomp),
        "fail_types": dict(fails),
        "rmse_online_mean": round(float(np.mean(rmses)), 5) if rmses else None,
        "age_at_dwell_hist": {"bins": AGE_BINS, "counts": hist},
        "episodes": eps,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    arm = sys.argv[1]; leg_arg = sys.argv[2] if len(sys.argv) > 2 else "all"
    fseed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    smoke_seeds = None
    if leg_arg == "smoke":
        legs = ["clean"]; smoke_seeds = EVAL_SEEDS[:3]
    else:
        legs = list(LEGS) if leg_arg == "all" else [leg_arg]
    try:
        for leg in legs:
            r = run_leg(env, client, model, device, arm, leg, fseed, seeds=smoke_seeds)
            tag = f"{arm}" + (f"_s{fseed}" if fseed is not None else "") + f"_{leg}"
            path = os.path.join(OUT, f"eval_{tag}.json")
            json.dump(r, open(path, "w"), indent=2)
            print(f"[{tag}] sukces={r['sukces_pct']}%±{r['sd_binom_pp']} "
                  f"wl={r['wrong_lock_pct']}% rmse={r['rmse_online_mean']} "
                  f"age={r['age_at_dwell_hist']['counts']}  sha={sha256(path)[:12]}", flush=True)
    finally:
        client.close(); env.close()


if __name__ == "__main__":
    main()
