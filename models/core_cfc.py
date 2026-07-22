"""core_cfc — rdzen ramienia A_CFC (dense CfC, po ANEKS-3: bug-fix do przepisu frozen C1).

Ramie OPISOWE. Komorka closed-form stylu frozen v1.0/models.CfCCell (Hasani 'default')
z BACKBONE (naprawa: ncps.torch.CfC bez backbone nie dosiegal celu — RAPORT_DIAG_CFC).
Krokowanie MANUALNE z jawnym ts w SEKUNDACH (0.0833 = 1/12 s), obchodzac bug wrappera
ncps (odrzuca timespans przy batch>1).

Parytet v2 (ANEKS-3 Z1): hidden=64, backbone=69 -> rdzen ~27 787 (+0.5%, pasmo +-2%).
Uwaga: aneks Z1 proponowal units=70/backbone=64 (rdzen 27 736), ale Z3+T2 wymagaja
glowy Linear(64->6)=390 identycznej we wszystkich ramionach -> hidden=64 (wyjscie 64),
backbone dobrany pod parytet. Zachowany rdzen w pasmie ORAZ symetria glow.
"""
from __future__ import annotations

import torch
import torch.nn as nn

IN_DIM = 78
CFC_UNITS = 64          # wyjscie rdzenia = 64 (glowa 64->6=390, symetria twin)
CFC_BACKBONE = 69       # dobrany pod parytet: rdzen ~27 787 (+0.5%)
TS_SEC = 1.0 / 12.0     # jawny ts w sekundach na tik kamery (ANEKS-3 Z2)


def lecun_tanh(x):
    return 1.7159 * torch.tanh(0.666 * x)


class CfCCell(nn.Module):
    """Closed-form CfC ('default', Hasani 2022) — przepis frozen v1.0/models.CfCCell.
    h' = ff1(z)*(1-g) + ff2(z)*g, g=sigmoid(time_a(z)*ts + time_b(z)), z=lecun_tanh(bb([x,h]))."""

    def __init__(self, input_size, hidden_size, backbone_units):
        super().__init__()
        self.backbone = nn.Linear(input_size + hidden_size, backbone_units)
        self.ff1 = nn.Linear(backbone_units, hidden_size)
        self.ff2 = nn.Linear(backbone_units, hidden_size)
        self.time_a = nn.Linear(backbone_units, hidden_size)
        self.time_b = nn.Linear(backbone_units, hidden_size)

    def forward(self, x, h, ts):
        z = lecun_tanh(self.backbone(torch.cat([x, h], dim=-1)))
        ff1 = torch.tanh(self.ff1(z))
        ff2 = torch.tanh(self.ff2(z))
        g = torch.sigmoid(self.time_a(z) * ts + self.time_b(z))
        return ff1 * (1.0 - g) + ff2 * g


class CoreCfC(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units: int = CFC_UNITS, backbone: int = CFC_BACKBONE):
        super().__init__()
        self.OUT_DIM = units
        self.state_size = units
        self.cell = CfCCell(IN_DIM, units, backbone)

    def init_hidden(self, batch: int, device) -> torch.Tensor:
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x: torch.Tensor, h: torch.Tensor):
        ts = torch.full((x.shape[0], 1), TS_SEC, device=x.device, dtype=x.dtype)
        h = self.cell(x, h, ts)
        return h, h

    def core_params(self) -> int:
        return sum(p.numel() for p in self.cell.parameters())
