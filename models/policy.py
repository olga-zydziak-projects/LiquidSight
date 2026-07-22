"""policy — instrument fazy 3: enkoder + rdzen GRU + glowa setpointu.

Glowa: Linear(64->6). Skalowanie (spojne z arena D1b i v_max eksperta):
  pos_xy = 2.0*tanh   -> +-2.0 m
  pos_z  = tanh->[0.1, 2.4] m
  vel    = 1.0*tanh   -> +-1.0 m/s
Wyjscie = setpoint6 (target_pos(3), target_vel(3)) w jednostkach fizycznych,
podawany wprost do env.step.

Rdzen wymienny (D4): tu GRU (ramie P-SANITY). CfC NIE powstaje przed F3_GATE.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from models.core_gru import CoreGRU
from models.encoder import Encoder

# zakresy skalowania glowy
XY_LIM = 2.0
Z_LO, Z_HI = 0.1, 2.4
VEL_LIM = 1.0


def _scale_setpoint(raw: torch.Tensor) -> torch.Tensor:
    """raw (…,6) -> setpoint (…,6) w jednostkach fizycznych."""
    t = torch.tanh(raw)
    pos_xy = XY_LIM * t[..., 0:2]
    pos_z = Z_LO + (Z_HI - Z_LO) * (t[..., 2:3] + 1.0) * 0.5
    vel = VEL_LIM * t[..., 3:6]
    return torch.cat([pos_xy, pos_z, vel], dim=-1)


class Policy(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = Encoder()
        self.core = CoreGRU()
        self.head = nn.Linear(CoreGRU.HIDDEN, 6)

    # -- czesc rdzeniowa: feat+kin+dt -> setpoint (dla treningu sekwencyjnego) --
    def _tick(self, rgb, kin, dt, h):
        feat = self.encoder(rgb)                         # (B,64)
        x = torch.cat([feat, kin, dt], dim=-1)           # (B,78)
        h = self.core.step(x, h)
        return _scale_setpoint(self.head(h)), h

    def init_hidden(self, batch: int, device):
        return self.core.init_hidden(batch, device)

    def forward(self, rgb_seq, kin_seq, dt_seq, mask=None):
        """Sekwencyjnie po epizodzie. rgb_seq (B,T,64,64,3), kin_seq (B,T,13),
        dt_seq (B,T,1) -> pred setpoint (B,T,6). GRU stan przez T."""
        B, T = rgb_seq.shape[0], rgb_seq.shape[1]
        device = rgb_seq.device
        h = self.init_hidden(B, device)
        outs = []
        for t in range(T):
            sp, h = self._tick(rgb_seq[:, t], kin_seq[:, t], dt_seq[:, t], h)
            outs.append(sp)
        return torch.stack(outs, dim=1)                  # (B,T,6)

    # -- inference online (eval / DAgger): jeden tik, numpy in/out ------------
    @torch.no_grad()
    def act(self, obs: dict, h, device):
        rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).unsqueeze(0)
        kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
        dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
        sp, h = self._tick(rgb, kin, dt, h)
        return sp.squeeze(0).cpu().numpy(), h


def count_params(module) -> int:
    return sum(p.numel() for p in module.parameters())


def param_report(policy: Policy) -> dict:
    return {
        "encoder": count_params(policy.encoder),
        "rdzen_gru": count_params(policy.core),
        "glowa": count_params(policy.head),
        "razem": count_params(policy),
    }
