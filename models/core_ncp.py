"""core_ncp — rdzen ramienia A_NCP (CfC + okablowanie AutoNCP, ncps).

Ramie ORZEKAJACE (F3_GATE par.1) — wiernosc [4]: Chahine uzywal wiringu NCP;
realizuje "CfC" z zapisu P_SANITY. CfC na rzadkim grafie AutoNCP z ncps
(neurony motoryczne = odczyt). Wejscie rdzenia 78; wyjscie = neurony
motoryczne (out=6) -> glowa Linear(6->6).

Parytet (I3a): AutoNCP(units=64, out=6, seed=0) -> 27 571 param rdzenia
(-0.28% wzgledem 27 648 GRU; w pasmie +-2%). Stan ukryty = units (64).

Native ts: jak w A_CFC — timespans=None (dt zadania stale, native-ts inertny);
dt obecne jako cecha wejscia 78.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from ncps.torch import CfC
from ncps.wirings import AutoNCP

IN_DIM = 78
NCP_UNITS = 64          # dowod parytetu I3a: 27 571 param (-0.28%)
NCP_OUT = 6             # neurony motoryczne = wymiar akcji (jak frozen C1PolicyAutoNCP)
NCP_SEED = 0            # wiring seed (F3_GATE: AutoNCP(units, 6, seed=0))


class CoreNCP(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units: int = NCP_UNITS, out: int = NCP_OUT, seed: int = NCP_SEED):
        super().__init__()
        self.units = units
        self.OUT_DIM = out
        self.state_size = units
        self.wiring = AutoNCP(units, out, seed=seed)
        self.cfc = CfC(IN_DIM, self.wiring, batch_first=True)

    def init_hidden(self, batch: int, device) -> torch.Tensor:
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x: torch.Tensor, h: torch.Tensor):
        """x:(B,78), h:(B,units) -> (out(B,6), h(B,units)). timespans=None (dt stale)."""
        out, h = self.cfc(x.unsqueeze(1), h)     # (B,1,6), (B,units)
        return out.squeeze(1), h

    def core_params(self) -> int:
        return sum(p.numel() for p in self.cfc.parameters())
