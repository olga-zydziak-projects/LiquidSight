"""s3d/train_filter.py — trening filtrów uczonych A2/A3 + strojenie A1 (PRE_3D0 §4).

OFFLINE nadzorowane: X (kanał ZOH pod degradacją) -> Y (GT box), strata MSE na tickach z
etykietą ORAZ aktywnym lockiem (mask = M * has_lock). Selekcja = best-val (min masked MSE
na val 48300–48399). 5 seedów PAROWANE A2↔A3 (45040–45044).

Hiperparametry PRE-REJESTROWANE, IDENTYCZNE dla A2 i A3 (parytet §2 „identyczna procedura"):
  lr = 1e-3, epoki = 300, batch = 32 epizodów, Adam, grad-clip = 1.0, best-val.
A1 Kalman: Q/R z siatki, min RMSE na zbiorze TRENINGOWYM (bez uczenia grad).

CLI: .venv/bin/python -m s3d.train_filter {all|A2|A3|kalman}
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
from s3d.filters import MicroGRU, MicroCfC, KalmanCV, param_count  # noqa: E402
from s3d.offline import replay_all, rmse_vs_gt, zoh_pred  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3d")
CKDIR = os.path.join(_ROOT, "ckpt", "s3d")
SEEDS = [45040, 45041, 45042, 45043, 45044]          # parowane A2<->A3
LR, EPOCHS, BATCH, CLIP = 1e-3, 300, 32, 1.0         # identyczne A2/A3 (parytet)
Q_GRID = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2]
R_GRID = [1e-3, 3e-3, 1e-2, 3e-2, 1e-1]


def load(tag):
    d = np.load(os.path.join(OUT, f"data_{tag}.npz"))
    X, Y, M = d["X"].astype(np.float32), d["Y"].astype(np.float32), d["M"].astype(np.float32)
    has_lock = ((X[..., 2] > 0) | (X[..., 3] > 0)).astype(np.float32)
    return X, Y, M * has_lock                         # maska efektywna = etykieta ∧ lock


def masked_mse(pred, Y, mask):
    err = ((pred - Y) ** 2).mean(dim=-1)              # (B,T)
    return (err * mask).sum() / mask.sum().clamp_min(1.0)


def train_arm(arm, Xtr, Ytr, Mtr, Xva, Yva, Mva, device):
    Cls = {"A2": MicroGRU, "A3": MicroCfC}[arm]
    os.makedirs(CKDIR, exist_ok=True)
    Xtr_t = torch.from_numpy(Xtr).to(device); Ytr_t = torch.from_numpy(Ytr).to(device)
    Mtr_t = torch.from_numpy(Mtr).to(device)
    Xva_t = torch.from_numpy(Xva).to(device); Yva_t = torch.from_numpy(Yva).to(device)
    Mva_t = torch.from_numpy(Mva).to(device)
    Ntr = Xtr.shape[0]
    logs = []
    for seed in SEEDS:
        torch.manual_seed(seed)
        m = Cls().to(device)
        opt = torch.optim.Adam(m.parameters(), lr=LR)
        g = torch.Generator().manual_seed(seed)
        best_val, best_state, best_ep = float("inf"), None, -1
        for ep in range(EPOCHS):
            m.train()
            perm = torch.randperm(Ntr, generator=g)
            for i in range(0, Ntr, BATCH):
                idx = perm[i:i + BATCH]
                pred = m(Xtr_t[idx])
                loss = masked_mse(pred, Ytr_t[idx], Mtr_t[idx])
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(m.parameters(), CLIP); opt.step()
            m.eval()
            with torch.no_grad():
                vpred = m(Xva_t)
                vloss = float(masked_mse(vpred, Yva_t, Mva_t))
            if vloss < best_val:
                best_val = vloss; best_ep = ep
                best_state = {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}
        torch.save(best_state, os.path.join(CKDIR, f"{arm}_s{seed}.pt"))
        # RMSE walidacyjny wybranego checkpointu (do precondition/logu)
        m.load_state_dict(best_state); m.eval()
        with torch.no_grad():
            vp = m(Xva_t).cpu().numpy()
        val_rmse = rmse_vs_gt(vp, Yva, Mva)
        logs.append({"arm": arm, "seed": seed, "best_epoch": best_ep,
                     "best_val_mse": round(best_val, 7), "val_rmse": round(val_rmse, 6),
                     "params": param_count(m)})
        print(f"  [{arm} s{seed}] best@{best_ep} val_mse={best_val:.6f} "
              f"val_rmse={val_rmse:.5f} params={param_count(m)}", flush=True)
    return logs


def tune_kalman(Xtr, Ytr, Mtr):
    best = None
    for q in Q_GRID:
        for r in R_GRID:
            rmse, _ = replay_all(lambda: KalmanCV(q=q, r=r), Xtr, Ytr, Mtr)
            if best is None or rmse < best["rmse"]:
                best = {"q": q, "r": r, "rmse": float(rmse)}
    zoh = rmse_vs_gt(zoh_pred(Xtr), Ytr, Mtr)
    best["zoh_rmse_train"] = float(zoh)
    json.dump(best, open(os.path.join(OUT, "kalman_qr.json"), "w"), indent=2)
    print(f"  [A1 Kalman] q={best['q']} r={best['r']} train_rmse={best['rmse']:.5f} "
          f"(ZOH {zoh:.5f})", flush=True)
    return best


def main(which):
    device = get_device()
    Xtr, Ytr, Mtr = load("train"); Xva, Yva, Mva = load("val")
    print(f"train {Xtr.shape} val {Xva.shape} | eff-mask cov tr={Mtr.mean():.3f} va={Mva.mean():.3f}",
          flush=True)
    log = {"hparams": {"lr": LR, "epochs": EPOCHS, "batch": BATCH, "clip": CLIP, "seeds": SEEDS},
           "arms": {}}
    if which in ("all", "kalman"):
        log["A1_kalman"] = tune_kalman(Xtr, Ytr, Mtr)
    if which in ("all", "A2"):
        log["arms"]["A2"] = train_arm("A2", Xtr, Ytr, Mtr, Xva, Yva, Mva, device)
    if which in ("all", "A3"):
        log["arms"]["A3"] = train_arm("A3", Xtr, Ytr, Mtr, Xva, Yva, Mva, device)
    json.dump(log, open(os.path.join(OUT, f"train_log_{which}.json"), "w"), indent=2)
    print(f"zapisano train_log_{which}.json", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
