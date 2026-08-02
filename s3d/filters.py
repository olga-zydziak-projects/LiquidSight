"""s3d/filters.py — mikro-filtry temporalne kanału celu (faza 3d).

Filtr = DROP-IN na `target5` tuż przed `model.act` (RECON_3D §A.2). Podmienia wyłącznie
`target5[0:4]` (cx,cy,w,h); `target5[4]` (age_n) pozostaje PRAWDZIWYM wiekiem (PRE_3D0 §3).
Przestrzeń image-space (D-1 ratyfikowane). Przy no-lock (`[0,0,0,0,1.0]`) — pass-through.

Wspólny interfejs online:
    f.reset(); box4_out = f.step(box4, has_lock, has_delivery, age_n)
gdzie box4 = target5[0:4] (ZOH), has_delivery = 1 na tiku świeżego dostarczenia, age_n = target5[4].

Ramiona:
  A0 NoFilter   — zwraca box4 bit-w-bit (duch ZOH; kontrola).
  A1 KalmanCV   — 4 rozłączne 1D KF constant-velocity (image-space), realny Δt, predykcja
                  co tik + update na dostarczeniu; Q/R strojone offline (A0 nie ma param).
  A2 MicroGRU   — GRUCell, Δt jako cecha wejścia (has_delivery + age_n); uczony.
  A3 MicroCfC   — CfCCell (przepis frozen models/core_cfc, ts w SEKUNDACH = DT_OBS,
                  krokowanie ręczne); uczony. Wejście/wyjście identyczne z A2 (parytet §2).

Wejście learned per tik (6-dim): [bx, by, bw, bh, has_delivery, age_n].  Wyjście: [cx,cy,w,h].
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from models.core_cfc import CfCCell

DT_OBS = 1.0 / 12.0
AGE_MAX = 8.0
IN_DIM = 6          # [bx,by,bw,bh, has_delivery, age_n]
OUT_DIM = 4         # [cx,cy,w,h]


# ---------------------------------------------------------------------------
# A0 — no-filter (duch ZOH bit-w-bit)
# ---------------------------------------------------------------------------
class NoFilter:
    name = "A0_nofilter"
    trained = False

    def reset(self):
        pass

    def step(self, box4, has_lock, has_delivery, age_n):
        return np.asarray(box4, np.float32)


# ---------------------------------------------------------------------------
# A1 — Kalman constant-velocity (4 rozłączne 1D KF), image-space, realny Δt
# ---------------------------------------------------------------------------
class KalmanCV:
    """4 niezależne 1D KF stanu [pos, vel]. Predykcja co tik (dt=DT_OBS); update z pomiaru
    tylko na tiku świeżego dostarczenia. Q/R skalarne (strojone offline). Bez uczenia grad."""
    name = "A1_kalman"
    trained = False

    def __init__(self, q=1e-3, r=1e-2, dt=DT_OBS):
        self.q = float(q); self.r = float(r); self.dt = float(dt)
        self.reset()

    def reset(self):
        self._init = False
        self.p = np.zeros(4, np.float32)      # pozycja (cx,cy,w,h)
        self.v = np.zeros(4, np.float32)      # prędkość
        # kowariancje 2x2 per współrzędna: [[Ppp,Ppv],[Pvp,Pvv]]
        self.P = np.tile(np.array([[1.0, 0.0], [0.0, 1.0]], np.float32), (4, 1, 1))

    def _predict(self):
        dt = self.dt
        self.p = self.p + dt * self.v
        # F = [[1,dt],[0,1]]; Q = q * [[dt^3/3, dt^2/2],[dt^2/2, dt]]
        q = self.q
        Q = np.array([[dt**3 / 3, dt**2 / 2], [dt**2 / 2, dt]], np.float32)
        for i in range(4):
            F = np.array([[1.0, dt], [0.0, 1.0]], np.float32)
            self.P[i] = F @ self.P[i] @ F.T + q * Q

    def _update(self, z):
        # H = [1,0]; R = r; K = [P00/S, P10/S]; P <- (I-KH) P  (pre-update P na prawej)
        for i in range(4):
            P00, P01 = self.P[i, 0, 0], self.P[i, 0, 1]
            P10, P11 = self.P[i, 1, 0], self.P[i, 1, 1]
            S = P00 + self.r
            k0 = P00 / S
            k1 = P10 / S
            y = z[i] - self.p[i]
            self.p[i] += k0 * y
            self.v[i] += k1 * y
            # (I-KH) = [[1-k0,0],[-k1,1]]  ->  P_new = (I-KH) @ P_pre
            self.P[i, 0, 0] = (1 - k0) * P00
            self.P[i, 0, 1] = (1 - k0) * P01
            self.P[i, 1, 0] = -k1 * P00 + P10
            self.P[i, 1, 1] = -k1 * P01 + P11

    def step(self, box4, has_lock, has_delivery, age_n):
        box4 = np.asarray(box4, np.float32)
        if not has_lock:
            self.reset()
            return box4                        # pass-through no-lock
        if not self._init:
            self.p = box4.copy(); self.v = np.zeros(4, np.float32)
            self.P = np.tile(np.array([[1.0, 0.0], [0.0, 1.0]], np.float32), (4, 1, 1))
            self._init = True
            return self.p.astype(np.float32)
        self._predict()
        if has_delivery:
            self._update(box4)
        return self.p.astype(np.float32)


# ---------------------------------------------------------------------------
# Rdzenie uczone — wspólny wrapper online + trening batched
# ---------------------------------------------------------------------------
class _LearnedFilter(nn.Module):
    trained = True

    def reset(self):
        self._h = None

    @torch.no_grad()
    def step(self, box4, has_lock, has_delivery, age_n):
        box4 = np.asarray(box4, np.float32)
        if not has_lock:
            self.reset()
            return box4                        # pass-through no-lock
        dev = next(self.parameters()).device
        x = torch.tensor([[box4[0], box4[1], box4[2], box4[3],
                           1.0 if has_delivery else 0.0, float(age_n)]],
                         dtype=torch.float32, device=dev)
        if self._h is None:
            self._h = self.init_hidden(1, dev)
        out, self._h = self._tick(x, self._h)
        return out.squeeze(0).cpu().numpy().astype(np.float32)


class MicroGRU(_LearnedFilter):
    name = "A2_microgru"

    def __init__(self, hidden=28):
        super().__init__()
        self.hidden = hidden
        self.core = nn.GRUCell(IN_DIM, hidden)
        self.head = nn.Linear(hidden, OUT_DIM)

    def init_hidden(self, batch, device):
        return torch.zeros(batch, self.hidden, device=device)

    def _tick(self, x, h):
        h = self.core(x, h)
        return self.head(h), h

    def forward(self, seq):                    # seq (B,T,6) -> (B,T,4)
        B, T, _ = seq.shape
        h = self.init_hidden(B, seq.device)
        outs = []
        for t in range(T):
            h = self.core(seq[:, t], h)
            outs.append(self.head(h))
        return torch.stack(outs, dim=1)


class MicroCfC(_LearnedFilter):
    name = "A3_microcfc"

    def __init__(self, hidden=16, backbone=35, ts_sec=DT_OBS):
        super().__init__()
        self.hidden = hidden
        self.ts_sec = float(ts_sec)
        self.cell = CfCCell(IN_DIM, hidden, backbone)      # przepis frozen (ANEKS-3)
        self.head = nn.Linear(hidden, OUT_DIM)

    def init_hidden(self, batch, device):
        return torch.zeros(batch, self.hidden, device=device)

    def _ts(self, batch, device, dtype):
        return torch.full((batch, 1), self.ts_sec, device=device, dtype=dtype)

    def _tick(self, x, h):
        h = self.cell(x, h, self._ts(x.shape[0], x.device, x.dtype))
        return self.head(h), h

    def forward(self, seq):                    # seq (B,T,6) -> (B,T,4)
        B, T, _ = seq.shape
        h = self.init_hidden(B, seq.device)
        ts = self._ts(B, seq.device, seq.dtype)
        outs = []
        for t in range(T):
            h = self.cell(seq[:, t], h, ts)
            outs.append(self.head(h))
        return torch.stack(outs, dim=1)


def param_count(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


def make_filter(name: str, **kw):
    return {"A0": NoFilter, "A1": KalmanCV, "A2": MicroGRU, "A3": MicroCfC}[name](**kw) \
        if name != "A0" else NoFilter()
