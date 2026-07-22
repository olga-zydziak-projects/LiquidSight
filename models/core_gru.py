"""core_gru — rdzen rekurencyjny ramienia P-SANITY (GRU).

Ramie P-SANITY = GRU (P_SANITY.md, wynik rzutu moneta = 0). Rdzen tyka na
KAZDEJ klatce kamery (12 Hz), stan h utrzymywany przez caly epizod.
Wejscie rdzenia: concat(feat 64, kin 13, dt 1) = 78. Hidden 64.

Parytet parametrow rdzenia liczony WZGLEDEM tej klasy (przyszly CfC: +-2%).
"""
from __future__ import annotations

import torch
import torch.nn as nn

IN_DIM = 78          # feat(64) + kin(13) + dt(1)
HIDDEN = 64


class CoreGRU(nn.Module):
    IN_DIM = IN_DIM
    HIDDEN = HIDDEN

    def __init__(self):
        super().__init__()
        self.cell = nn.GRUCell(IN_DIM, HIDDEN)

    def init_hidden(self, batch: int, device) -> torch.Tensor:
        return torch.zeros(batch, HIDDEN, device=device)

    def step(self, x: torch.Tensor, h: torch.Tensor) -> torch.Tensor:
        """x: (B,78), h: (B,64) -> h': (B,64)."""
        return self.cell(x, h)
