"""s3d/offline.py — replay filtrów na zebranych danych (bez env) + RMSE.

Wejście danych: X (Nep,T,6)=[bx,by,bw,bh,has_delivery,age_n], Y (Nep,T,4)=GT box,
M (Nep,T)=maska etykiety (1 gdy GT on-frame). has_lock wyprowadzany z X: box ma w,h>0.
Używane do: strojenia Kalmana (A1), precondition P-3D (RMSE<ZOH), diagnostyki.
"""
from __future__ import annotations

import numpy as np


def has_lock_row(x6):
    return bool(x6[2] > 0.0 or x6[3] > 0.0)     # w>0 lub h>0 => aktywny lock (no-lock=0)


def replay(filt, X_ep):
    """filt (reset/step) na jednym epizodzie X (T,6) -> pred (T,4)."""
    filt.reset()
    T = X_ep.shape[0]
    out = np.zeros((T, 4), np.float32)
    for t in range(T):
        x = X_ep[t]
        out[t] = filt.step(x[:4].astype(np.float32), has_lock_row(x),
                           bool(x[4] > 0.5), float(x[5]))
    return out


def rmse_vs_gt(pred, Y, M):
    """RMSE boxa na tickach z etykietą (M=1). pred/Y (Nep,T,4), M (Nep,T)."""
    m = M[..., None]                              # (Nep,T,1)
    num = float((((pred - Y) ** 2) * m).sum())
    den = float(m.sum() * 4)
    return (num / den) ** 0.5 if den > 0 else float("nan")


def replay_all(make_filt, X, Y, M):
    """make_filt: () -> świeży filtr. Zwraca (rmse, pred_all)."""
    pred = np.zeros_like(Y)
    for i in range(X.shape[0]):
        pred[i] = replay(make_filt(), X[i])
    return rmse_vs_gt(pred, Y, M), pred


def zoh_pred(X):
    """Duch ZOH = box4 z kanału (A0). pred (Nep,T,4) = X[...,:4]."""
    return X[..., :4].copy()
