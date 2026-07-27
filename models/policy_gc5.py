"""policy_gc5 — polityka goal-conditioned BEZ conf (ANEKS-3B Z1).

Kanał celu 5-dim: (cx, cy, w, h, age_s) znormalizowany — conf USUNIETY z wejscia
(DIAG-3B: conf-shift = 88 pp). Wejscie rdzenia 78 + 5 = 83. Enkoder i glowa BEZ ZMIAN.
conf nie wchodzi do tensora wejsciowego (assert w treningu). Rdzen = GRU.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from models.encoder import Encoder
from models.policy import _scale_setpoint

FEAT_DIM = Encoder.OUT_DIM      # 64
KIN_DIM, DT_DIM = 13, 1
TARGET_DIM = 5                  # (cx,cy,w,h,age_s) — BEZ conf (ANEKS-3B)
IN_DIM = FEAT_DIM + KIN_DIM + DT_DIM + TARGET_DIM   # 83
HIDDEN = 64


class PolicyGC5(nn.Module):
    IN_DIM = IN_DIM
    HIDDEN = HIDDEN
    TARGET_DIM = TARGET_DIM

    def __init__(self):
        super().__init__()
        self.encoder = Encoder()
        self.core = nn.GRUCell(IN_DIM, HIDDEN)       # 83 -> 64
        self.head = nn.Linear(HIDDEN, 6)

    def init_hidden(self, batch: int, device):
        return torch.zeros(batch, HIDDEN, device=device)

    def _tick(self, rgb, kin, dt, target, h):
        feat = self.encoder(rgb)
        x = torch.cat([feat, kin, dt, target], dim=-1)   # (B,83)
        h = self.core(x, h)
        return _scale_setpoint(self.head(h)), h

    def forward(self, rgb_seq, kin_seq, dt_seq, target_seq, mask=None):
        B, T = rgb_seq.shape[0], rgb_seq.shape[1]
        h = self.init_hidden(B, rgb_seq.device)
        outs = []
        for t in range(T):
            sp, h = self._tick(rgb_seq[:, t], kin_seq[:, t], dt_seq[:, t],
                               target_seq[:, t], h)
            outs.append(sp)
        return torch.stack(outs, dim=1)

    @torch.no_grad()
    def act(self, obs: dict, target: np.ndarray, h, device):
        rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).unsqueeze(0)
        kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
        dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
        tg = torch.as_tensor(np.asarray(target, np.float32), device=device).unsqueeze(0)
        sp, h = self._tick(rgb, kin, dt, tg, h)
        return sp.squeeze(0).cpu().numpy(), h


def param_report(policy: PolicyGC5) -> dict:
    c = lambda m: sum(p.numel() for p in m.parameters())
    return {"encoder": c(policy.encoder), "rdzen_gru5": c(policy.core),
            "glowa": c(policy.head), "razem": c(policy),
            "in_dim": IN_DIM, "target_dim": TARGET_DIM}


if __name__ == "__main__":
    import json
    print(json.dumps(param_report(PolicyGC5()), indent=2))
