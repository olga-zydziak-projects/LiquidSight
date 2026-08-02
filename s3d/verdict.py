"""s3d/verdict.py — agregacja pomiaru 3d i WERDYKT (PRE_3D0 §6, zamrożony).

Czyta eval_{arm}[_s{seed}]_{leg}.json z results/s3d/. Liczy:
  metryka pierwotna: sukces na nodze p50 (A0/A1 jeden bieg; A2/A3 średnia po 5 seedach);
  pooled_std = sqrt((sd_s(A2)² + sd_s(A3)²)/2), sd po 5 seedach (F3-GATE §5);
  Δ = succ(A3) − max(succ(A0), succ(A1), succ(A2));
  WERDYKT: Δ>+pooled_std POZYTYWNY / Δ<−pooled_std NEGATYWNY / inaczej NULL;
  constraint transparencji (clean): succ(ramię) ≥ succ(A0) − 3 pp, inaczej NIETRANSPARENTNE;
  metryki wtórne: wrong-lock per noga, L5, rmse-online, age hist.

CLI: .venv/bin/python -m s3d.verdict
"""
from __future__ import annotations
import glob
import json
import os
import sys

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(_ROOT, "results", "s3d")
SEEDS = [45040, 45041, 45042, 45043, 45044]
LEGS = ["clean", "p50", "L5"]
TRANSP_TOL = 3.0        # pp


def _load(arm, leg, seed=None):
    tag = f"{arm}" + (f"_s{seed}" if seed is not None else "") + f"_{leg}"
    p = os.path.join(OUT, f"eval_{tag}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def arm_leg_succ(arm, leg):
    """Zwraca (mean_pct, sd_pct|None, per_seed|None, raw_list)."""
    if arm in ("A0", "A1"):
        r = _load(arm, leg)
        return (r["sukces_pct"] if r else None), None, None, ([r] if r else [])
    per = [_load(arm, leg, s) for s in SEEDS]
    per = [p for p in per if p is not None]
    if not per:
        return None, None, None, []
    vals = [p["sukces_pct"] for p in per]
    return float(np.mean(vals)), float(np.std(vals)), \
        {p["filter_seed"]: p["sukces_pct"] for p in per}, per


def wrong_lock(arm, leg):
    if arm in ("A0", "A1"):
        r = _load(arm, leg); return (r["wrong_lock_pct"] if r else None,
                                     r["wrong_lock_decomp"] if r else None)
    per = [_load(arm, leg, s) for s in SEEDS]; per = [p for p in per if p]
    if not per:
        return None, None
    wl = float(np.mean([p["wrong_lock_pct"] for p in per]))
    kr = int(sum(p["wrong_lock_decomp"].get("kradziez", 0) for p in per))
    return round(wl, 1), {"kradziez_total_over_seeds": kr}


def rmse_online(arm, leg):
    if arm in ("A0", "A1"):
        r = _load(arm, leg); return r["rmse_online_mean"] if r else None
    per = [_load(arm, leg, s) for s in SEEDS]; per = [p for p in per if p]
    vals = [p["rmse_online_mean"] for p in per if p.get("rmse_online_mean") is not None]
    return round(float(np.mean(vals)), 5) if vals else None


def main():
    summary = {"legs": {}, "primary": {}, "verdict": {}, "transparency": {}, "secondary": {}}
    # sukces per arm per noga
    for leg in LEGS:
        summary["legs"][leg] = {a: arm_leg_succ(a, leg)[0] for a in ("A0", "A1", "A2", "A3")}

    # metryka pierwotna: p50
    prim = {}
    for a in ("A0", "A1", "A2", "A3"):
        m, sd, per, _ = arm_leg_succ(a, "p50")
        prim[a] = {"succ_p50": m, "sd_p50": sd, "per_seed": per}
    summary["primary"] = prim

    sd_a2 = prim["A2"]["sd_p50"]; sd_a3 = prim["A3"]["sd_p50"]
    pooled_std = None
    if sd_a2 is not None and sd_a3 is not None:
        pooled_std = float(np.sqrt((sd_a2 ** 2 + sd_a3 ** 2) / 2))

    s0, s1 = prim["A0"]["succ_p50"], prim["A1"]["succ_p50"]
    s2, s3 = prim["A2"]["succ_p50"], prim["A3"]["succ_p50"]
    verdict = {"pooled_std": pooled_std}
    if None not in (s0, s1, s2, s3, pooled_std):
        best_other = max(s0, s1, s2)
        delta = s3 - best_other
        if delta > pooled_std:
            v = "POZYTYWNY"
        elif delta < -pooled_std:
            v = "NEGATYWNY"
        else:
            v = "NULL"
        verdict.update({"succ_A3": s3, "max_A0_A1_A2": best_other, "delta": round(delta, 2),
                        "verdict": v, "formula": "Δ=succ(A3)-max(A0,A1,A2) vs ±pooled_std"})
    summary["verdict"] = verdict

    # transparencja (clean): succ >= A0_clean - 3pp
    a0c = arm_leg_succ("A0", "clean")[0]
    for a in ("A1", "A2", "A3"):
        sc = arm_leg_succ(a, "clean")[0]
        if sc is None or a0c is None:
            summary["transparency"][a] = None
        else:
            ok = sc >= a0c - TRANSP_TOL
            summary["transparency"][a] = {"clean_succ": sc, "a0_clean": a0c,
                                          "transparent": bool(ok),
                                          "status": "OK" if ok else "NIETRANSPARENTNE"}

    # wtorne: wrong-lock per noga, rmse-online
    for leg in LEGS:
        summary["secondary"][leg] = {
            a: {"wrong_lock_pct": wrong_lock(a, leg)[0],
                "wl_decomp": wrong_lock(a, leg)[1],
                "rmse_online": rmse_online(a, leg)}
            for a in ("A0", "A1", "A2", "A3")}

    json.dump(summary, open(os.path.join(OUT, "verdict_3d.json"), "w"), indent=2)
    print(json.dumps({"legs": summary["legs"], "verdict": summary["verdict"],
                      "transparency": summary["transparency"]}, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    main()
