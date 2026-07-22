"""core_cfc — rdzen ramienia A_CFC (dense CfC, ncps).

Ramie OPISOWE (F3_GATE par.1): izoluje wklad dynamiki ciaglej od wiringu.
Dense CfC z biblioteki ncps (continuous-time cell; ciaglosc dynamiki z
komorkami P0/C1). Wejscie rdzenia 78, wyjscie = units (do glowy Linear->6).

Parytet (I3a): units=53, backbone_layers=0 -> 27 984 param rdzenia (+1.22%
wzgledem 27 648 GRU; w pasmie +-2% [27095, 28201]).

Native ts: dt zadania jest STALE (12 Hz, regularne probkowanie) -> timespans
podawane jako None (jednostkowy krok czasu = stala bramka czasu; kanal dt
jest i tak obecny jako cecha w wejsciu 78). Regularne dt czyni native-ts
inertnym; os OOD jest percepcyjna, nie czasowa.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from ncps.torch import CfC

IN_DIM = 78
CFC_UNITS = 53          # dowod parytetu I3a: 27 984 param (+1.22%)


class CoreCfC(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units: int = CFC_UNITS):
        super().__init__()
        self.units = units
        self.OUT_DIM = units
        self.state_size = units
        self.cfc = CfC(IN_DIM, units, batch_first=True, backbone_layers=0)

    def init_hidden(self, batch: int, device) -> torch.Tensor:
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x: torch.Tensor, h: torch.Tensor):
        """x:(B,78), h:(B,units) -> (out(B,units), h(B,units)). timespans=None (dt stale)."""
        out, h = self.cfc(x.unsqueeze(1), h)     # (B,1,units), (B,units)
        return out.squeeze(1), h

    def core_params(self) -> int:
        return sum(p.numel() for p in self.cfc.parameters())
