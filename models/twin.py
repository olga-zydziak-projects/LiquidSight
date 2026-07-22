"""twin — wspolna polityka ramion pojedynku (F3_GATE): enkoder + rdzen + glowa.

Enkoder identyczny z P-SANITY (nowa instancja, zero wspoldzielenia wag).
Glowa Linear(rdzen.OUT_DIM -> 6) z TYM SAMYM skalowaniem co P-SANITY
(_scale_setpoint). Interfejs identyczny z models.policy.Policy (forward/act/
init_hidden) -> ten sam pipeline BC/DAgger/ewaluacji dla wszystkich ramion.

A_GRU realizuje models.policy.Policy (referencja P-SANITY). A_CFC/A_NCP:
TwinPolicy(CoreCfC/CoreNCP).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from models.encoder import Encoder
from models.policy import _scale_setpoint


class TwinPolicy(nn.Module):
    def __init__(self, core):
        super().__init__()
        self.encoder = Encoder()
        self.core = core
        self.head = nn.Linear(core.OUT_DIM, 6)

    def init_hidden(self, batch: int, device):
        return self.core.init_hidden(batch, device)

    def _tick(self, rgb, kin, dt, h):
        feat = self.encoder(rgb)                          # (B,64)
        x = torch.cat([feat, kin, dt], dim=-1)            # (B,78)
        out, h = self.core.step(x, h)
        return _scale_setpoint(self.head(out)), h

    def forward(self, rgb_seq, kin_seq, dt_seq, mask=None):
        B, T = rgb_seq.shape[0], rgb_seq.shape[1]
        h = self.init_hidden(B, rgb_seq.device)
        outs = []
        for t in range(T):
            sp, h = self._tick(rgb_seq[:, t], kin_seq[:, t], dt_seq[:, t], h)
            outs.append(sp)
        return torch.stack(outs, dim=1)                   # (B,T,6)

    @torch.no_grad()
    def act(self, obs: dict, h, device):
        rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).unsqueeze(0)
        kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
        dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
        sp, h = self._tick(rgb, kin, dt, h)
        return sp.squeeze(0).cpu().numpy(), h
