"""policy_gc — polityka GOAL-CONDITIONED fazy 3b (S3b2).

Rozszerzenie polityki P-SANITY (models/policy.py) o **kanał celu** (D3):
wejście rdzenia 78 -> **84** (+6 = cx,cy,w,h,conf,age_s znormalizowane). Enkoder
i głowa BEZ ZMIAN (te same klasy). Kanał celu wchodzi do wektora wejściowego
rdzenia przez concat z feat+kin+dt. Parytet NIE obowiązuje (brak twin w 3b).

Rdzen = GRU (jak ramię P-SANITY; CfC był GRANICĄ w 3a). Skalowanie głowy i
kontrakt setpointu — dziedziczone z models.policy (te same zakresy areny/v_max).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from models.encoder import Encoder
from models.policy import _scale_setpoint

FEAT_DIM = Encoder.OUT_DIM      # 64
KIN_DIM = 13
DT_DIM = 1
TARGET_DIM = 6                  # (cx,cy,w,h,conf,age_s) znormalizowane — D3
IN_DIM = FEAT_DIM + KIN_DIM + DT_DIM + TARGET_DIM   # 84
HIDDEN = 64


class PolicyGC(nn.Module):
    IN_DIM = IN_DIM
    HIDDEN = HIDDEN
    TARGET_DIM = TARGET_DIM

    def __init__(self):
        super().__init__()
        self.encoder = Encoder()                     # bez zmian
        self.core = nn.GRUCell(IN_DIM, HIDDEN)       # 84 -> 64
        self.head = nn.Linear(HIDDEN, 6)             # bez zmian

    def init_hidden(self, batch: int, device):
        return torch.zeros(batch, HIDDEN, device=device)

    def _tick(self, rgb, kin, dt, target, h):
        feat = self.encoder(rgb)                              # (B,64)
        x = torch.cat([feat, kin, dt, target], dim=-1)       # (B,84)
        h = self.core(x, h)
        return _scale_setpoint(self.head(h)), h

    def forward(self, rgb_seq, kin_seq, dt_seq, target_seq, mask=None):
        """Sekwencyjnie po epizodzie. rgb (B,T,64,64,3), kin (B,T,13), dt (B,T,1),
        target (B,T,6) -> pred setpoint (B,T,6)."""
        B, T = rgb_seq.shape[0], rgb_seq.shape[1]
        h = self.init_hidden(B, rgb_seq.device)
        outs = []
        for t in range(T):
            sp, h = self._tick(rgb_seq[:, t], kin_seq[:, t], dt_seq[:, t],
                               target_seq[:, t], h)
            outs.append(sp)
        return torch.stack(outs, dim=1)              # (B,T,6)

    @torch.no_grad()
    def act(self, obs: dict, target: np.ndarray, h, device):
        rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).unsqueeze(0)
        kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
        dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
        tg = torch.as_tensor(np.asarray(target, np.float32), device=device).unsqueeze(0)
        sp, h = self._tick(rgb, kin, dt, tg, h)
        return sp.squeeze(0).cpu().numpy(), h


def param_report(policy: PolicyGC) -> dict:
    c = lambda m: sum(p.numel() for p in m.parameters())
    return {"encoder": c(policy.encoder), "rdzen_gru_gc": c(policy.core),
            "glowa": c(policy.head), "razem": c(policy),
            "in_dim": IN_DIM, "target_dim": TARGET_DIM}


if __name__ == "__main__":
    import json
    from models.policy import Policy
    p_gc = PolicyGC()
    p_base = Policy()
    rep = param_report(p_gc)
    rep["rdzen_3a_gru_78"] = sum(x.numel() for x in p_base.core.parameters())
    rep["delta_rdzen"] = rep["rdzen_gru_gc"] - rep["rdzen_3a_gru_78"]
    print(json.dumps(rep, indent=2))
