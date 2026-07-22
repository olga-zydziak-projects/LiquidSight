"""encoder — enkoder percepcji fazy 3 (D2/D4 primary: wlasny enkoder per ramie).

rgb uint8/float (B,64,64,3) -> /255 -> 4x [conv k3 s2 + ReLU] kanaly 16/32/64/64
(64->32->16->8->4) -> flatten (4*4*64=1024) -> Linear 1024->64.

FLATTEN, nie global pooling: polityka musi wiedziec GDZIE w kadrze jest cel
(setpoint zalezy od kierunku do celu), a pooling zabija informacje polozenia.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class Encoder(nn.Module):
    OUT_DIM = 64

    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1), nn.ReLU(),   # 64->32
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1), nn.ReLU(),  # 32->16
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1), nn.ReLU(),  # 16->8
            nn.Conv2d(64, 64, kernel_size=3, stride=2, padding=1), nn.ReLU(),  # 8->4
        )
        self.fc = nn.Linear(4 * 4 * 64, self.OUT_DIM)                          # flatten->64

    def forward(self, rgb: torch.Tensor) -> torch.Tensor:
        """rgb: (B,64,64,3) uint8/float -> feat (B,64)."""
        x = rgb.float() / 255.0
        x = x.permute(0, 3, 1, 2).contiguous()          # (B,3,64,64)
        x = self.conv(x)                                # (B,64,4,4)
        x = x.flatten(1)                                # (B,1024)
        return self.fc(x)                               # (B,64)
