"""arms — fabryka ramion pojedynku F3_GATE + rachunek parametrow rdzenia.

A_GRU: models.policy.Policy (GRU 64, referencja P-SANITY).
A_CFC: TwinPolicy(CoreCfC) — dense CfC (opisowe).
A_NCP: TwinPolicy(CoreNCP) — CfC+AutoNCP (orzekajace).
Enkoder i glowa: definicje identyczne (nowe instancje; zero wspoldzielenia wag).
"""
from __future__ import annotations

from models.core_cfc import CoreCfC
from models.core_ncp import CoreNCP
from models.policy import Policy
from models.twin import TwinPolicy

ARMS = ["A_GRU", "A_NCP", "A_CFC"]
CORE_REF = 27648                 # GRU rdzen (referencja parytetu)
BAND = (27095, 28201)            # +-2%


def build_arm(name: str):
    if name == "A_GRU":
        return Policy()
    if name == "A_CFC":
        return TwinPolicy(CoreCfC())
    if name == "A_NCP":
        return TwinPolicy(CoreNCP())
    raise ValueError(f"nieznane ramie: {name}")


def core_params(policy) -> int:
    return sum(p.numel() for p in policy.core.parameters())


def part_params(policy) -> dict:
    enc = sum(p.numel() for p in policy.encoder.parameters())
    core = core_params(policy)
    head = sum(p.numel() for p in policy.head.parameters())
    return {"encoder": enc, "rdzen": core, "glowa": head,
            "razem": sum(p.numel() for p in policy.parameters())}
