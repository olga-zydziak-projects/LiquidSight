"""core_ncp — rdzen ramienia A_NCP (CfC + AutoNCP, po ANEKS-3: bug-fix).

Ramie ORZEKAJACE — wiernosc [4] (Chahine: wiring NCP). Okablowanie AutoNCP z ncps
BEZ ZMIAN (rdzen 27 571 param, parytet v1 zachowany). Naprawa (RAPORT_DIAG_CFC):
- readout z PELNEGO stanu (64) zamiast 6 neuronow motorycznych (dolot 8->26/50);
- jawny ts w SEKUNDACH przez MANUALNE krokowanie wewnetrznej komorki ncps
  (WiredCfCCell przyjmuje ts poprawnie; bug jest tylko we wrapperze CfC.forward).

Wyjscie rdzenia = pelny stan (64) -> glowa Linear(64->6)=390 (symetria z A_GRU/A_CFC).
"""
from __future__ import annotations

import torch
import torch.nn as nn
from ncps.torch import CfC
from ncps.wirings import AutoNCP

IN_DIM = 78
NCP_UNITS = 64          # stan/wyjscie rdzenia = 64 (readout pelnego stanu; glowa 64->6)
NCP_OUT = 6             # neurony motoryczne wiringu (nieuzywane jako readout po ANEKS-3)
NCP_SEED = 0            # AutoNCP(units, 6, seed=0) — bez zmian wzgledem v1
TS_SEC = 1.0 / 12.0     # jawny ts w sekundach (ANEKS-3 Z2)


class CoreNCP(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units: int = NCP_UNITS, out: int = NCP_OUT, seed: int = NCP_SEED):
        super().__init__()
        self.OUT_DIM = units            # readout PELNEGO stanu
        self.state_size = units
        self.wiring = AutoNCP(units, out, seed=seed)
        self.cfc = CfC(IN_DIM, self.wiring, batch_first=True)   # buduje wewnetrzna WiredCfCCell

    def init_hidden(self, batch: int, device) -> torch.Tensor:
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x: torch.Tensor, h: torch.Tensor):
        ts = torch.full((x.shape[0], 1), TS_SEC, device=x.device, dtype=x.dtype)
        _motor, h = self.cfc.rnn_cell(x, h, ts)   # komorka przyjmuje ts (obejscie buga wrappera)
        return h, h                                # readout = pelny stan (64)

    def core_params(self) -> int:
        return sum(p.numel() for p in self.cfc.parameters())
