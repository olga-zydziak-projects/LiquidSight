"""s3d/precond.py — Precondition P-3D (PRE_3D0 §5): RMSE boxa < RMSE ducha ZOH (offline).

Na wstrzymanym zbiorze walidacyjnym (48300–48399), RMSE liczone na tickach z etykietą GT
ORAZ aktywnym lockiem (mask = M * has_lock, ten sam skrypt dla wszystkich ramion).
Ramię bije ZOH (A0) ⇒ PASS; A2/A3 per seed, próg zamrożony = MEDIANA seedów bije ZOH.
FAIL obu uczonych ⇒ eskalacja (STOP). Precondition NIE jest tezą.

CLI: .venv/bin/python -m s3d.precond
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from train.common import get_device  # noqa: E402
from s3d.filters import KalmanCV, MicroGRU, MicroCfC  # noqa: E402
from s3d.offline import replay, rmse_vs_gt, zoh_pred  # noqa: E402
from s3d.train_filter import load, SEEDS, CKDIR  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3d")


def arm_rmse(make_filt, X, Y, M):
    pred = np.zeros_like(Y)
    for i in range(X.shape[0]):
        pred[i] = replay(make_filt(), X[i])
    return rmse_vs_gt(pred, Y, M)


def main():
    device = get_device()
    Xva, Yva, Mva = load("val")                        # M już = etykieta ∧ lock
    zoh = rmse_vs_gt(zoh_pred(Xva), Yva, Mva)
    res = {"n_val": int(Xva.shape[0]), "mask_coverage": float(Mva.mean()),
           "zoh_rmse": round(float(zoh), 6), "arms": {}}

    # A1 Kalman
    qr = json.load(open(os.path.join(OUT, "kalman_qr.json")))
    a1 = arm_rmse(lambda: KalmanCV(q=qr["q"], r=qr["r"]), Xva, Yva, Mva)
    res["arms"]["A1"] = {"rmse": round(float(a1), 6), "beats_zoh": bool(a1 < zoh),
                         "status": "PASS" if a1 < zoh else "FAIL-PRECOND"}

    # A2/A3 per seed + mediana
    for arm, Cls in (("A2", MicroGRU), ("A3", MicroCfC)):
        per = []
        for seed in SEEDS:
            m = Cls().to(device)
            m.load_state_dict(torch.load(os.path.join(CKDIR, f"{arm}_s{seed}.pt"),
                                         map_location=device)); m.eval()
            r = arm_rmse(lambda mm=m: _Frozen(mm), Xva, Yva, Mva)
            per.append({"seed": seed, "rmse": round(float(r), 6), "beats_zoh": bool(r < zoh)})
        med = float(np.median([p["rmse"] for p in per]))
        res["arms"][arm] = {"per_seed": per, "median_rmse": round(med, 6),
                            "beats_zoh": bool(med < zoh),
                            "status": "PASS" if med < zoh else "FAIL-PRECOND"}

    learned_fail = all(res["arms"][a]["status"] == "FAIL-PRECOND" for a in ("A2", "A3"))
    res["escalation"] = ("STOP: oba ramiona uczone FAIL-PRECOND" if learned_fail else None)
    json.dump(res, open(os.path.join(OUT, "precond_p3d.json"), "w"), indent=2)
    print(f"ZOH rmse={zoh:.5f}")
    for a in ("A1", "A2", "A3"):
        d = res["arms"][a]
        key = "rmse" if a == "A1" else "median_rmse"
        print(f"  {a}: {d[key]:.5f}  {d['status']}")
    if learned_fail:
        print("!! ESKALACJA: oba ramiona uczone nie biją ZOH — STOP (PRE §5)")
    return res


class _Frozen:
    """Adapter: filtr uczony jako make_filt() jednorazowego użytku (reset per epizod)."""
    def __init__(self, model):
        self.m = model; self.m.reset()

    def reset(self):
        self.m.reset()

    def step(self, box4, has_lock, has_delivery, age_n):
        return self.m.step(box4, has_lock, has_delivery, age_n)


if __name__ == "__main__":
    main()
