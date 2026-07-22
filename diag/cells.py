"""diag/cells — warianty rdzeni CfC do sond diagnostycznych (NIE dla biegu wiazacego).

Warianty jednej zmiennej:
- CoreCfCFrozen: komorka closed-form w stylu frozen v1.0 (models.CfCCell): backbone
  Linear(in+h->bb)+lecun_tanh, potem ff1/ff2/time_a/time_b; ts przekazywane jawnie
  (custom cell -> brak buga batch>1 z ncps). Sonda "co jesli poprawna komorka".
- CoreCfCncps: ncps.torch.CfC (jak bieg wiazacy), backbone_layers konfigurowalne,
  ts wylacznie None (ncps odrzuca jawne timespans przy batch>1).
- CoreNCPreadout: ncps CfC(AutoNCP) z wyborem readoutu (motor-6 vs stan pelny).
Interfejs jak models.core_*: OUT_DIM, init_hidden, step(x,h)->(out,h).
"""
from __future__ import annotations

import torch
import torch.nn as nn
from ncps.torch import CfC
from ncps.wirings import AutoNCP

IN_DIM = 78
DT_OBS = 1.0 / 12.0


def lecun_tanh(x):
    return 1.7159 * torch.tanh(0.666 * x)


class CfCCellFrozen(nn.Module):
    """Closed-form CfC (Hasani 'default') — reimplementacja frozen models.CfCCell.
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


def _ts_value(mode, B, device):
    if mode == "sec":
        v = DT_OBS
    elif mode == "tick4":
        v = 4.0
    else:                      # 'tick1'
        v = 1.0
    return torch.full((B, 1), v, device=device)


class CoreCfCFrozen(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units=70, backbone=64, ts_mode="tick1"):
        super().__init__()
        self.OUT_DIM = units
        self.state_size = units
        self.ts_mode = ts_mode
        self.cell = CfCCellFrozen(IN_DIM, units, backbone)

    def init_hidden(self, batch, device):
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x, h):
        ts = _ts_value(self.ts_mode, x.shape[0], x.device)
        h = self.cell(x, h, ts)
        return h, h

    def core_params(self):
        return sum(p.numel() for p in self.cell.parameters())


class CoreCfCncps(nn.Module):
    IN_DIM = IN_DIM

    def __init__(self, units=53, backbone_layers=0):
        super().__init__()
        self.OUT_DIM = units
        self.state_size = units
        self.cfc = CfC(IN_DIM, units, batch_first=True, backbone_layers=backbone_layers)

    def init_hidden(self, batch, device):
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x, h):
        out, h = self.cfc(x.unsqueeze(1), h)     # timespans=None (ncps bug batch>1)
        return out.squeeze(1), h

    def core_params(self):
        return sum(p.numel() for p in self.cfc.parameters())


class CoreNCPreadout(nn.Module):
    """A_NCP z wyborem readoutu: 'motor' (6 neuronow -> OUT_DIM=6) lub 'state' (stan 64)."""
    IN_DIM = IN_DIM

    def __init__(self, units=64, out=6, seed=0, readout="motor"):
        super().__init__()
        self.readout = readout
        self.state_size = units
        self.OUT_DIM = out if readout == "motor" else units
        self.wiring = AutoNCP(units, out, seed=seed)
        self.cfc = CfC(IN_DIM, self.wiring, batch_first=True)

    def init_hidden(self, batch, device):
        return torch.zeros(batch, self.state_size, device=device)

    def step(self, x, h):
        out, h = self.cfc(x.unsqueeze(1), h)     # out=(B,6) motor, h=(B,units) stan
        return (out.squeeze(1) if self.readout == "motor" else h), h

    def core_params(self):
        return sum(p.numel() for p in self.cfc.parameters())
