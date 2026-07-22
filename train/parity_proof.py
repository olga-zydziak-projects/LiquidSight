"""parity_proof — dowod parytetu rdzeni ramion F3_GATE (I3a T2).

Automatyczne wyszukanie rozmiarow tak, by liczba parametrow rdzenia byla
w pasmie 27 648 +-2% = [27095, 28201]; tabela dowodu -> stdout; sekcja
"gate_arms" -> MANIFEST_F3.json. Sanity forward kazdego ramienia.
"""
import json
import os
import sys

import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ncps.torch import CfC  # noqa: E402
from ncps.wirings import AutoNCP  # noqa: E402

from models.arms import ARMS, BAND, CORE_REF, build_arm, core_params, part_params  # noqa: E402
from models.core_cfc import CFC_UNITS  # noqa: E402
from models.core_ncp import NCP_OUT, NCP_SEED, NCP_UNITS  # noqa: E402

MANIFEST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "MANIFEST_F3.json"))
LO, HI = BAND


def _cp(m):
    return sum(p.numel() for p in m.parameters())


def search_cfc():
    """dense CfC (bl=0): units najblizszy CORE_REF w pasmie."""
    best = None
    for u in range(40, 70):
        p = _cp(CfC(78, u, batch_first=True, backbone_layers=0))
        if LO <= p <= HI and (best is None or abs(p - CORE_REF) < abs(best[1] - CORE_REF)):
            best = (u, p)
    return best


def search_ncp():
    """CfC(AutoNCP(units,6,seed=0)): units najblizszy CORE_REF w pasmie."""
    best = None
    for u in range(56, 72):
        p = _cp(CfC(78, AutoNCP(u, NCP_OUT, seed=NCP_SEED), batch_first=True))
        if LO <= p <= HI and (best is None or abs(p - CORE_REF) < abs(best[1] - CORE_REF)):
            best = (u, p)
    return best


def main():
    cfc_u, cfc_p = search_cfc()
    ncp_u, ncp_p = search_ncp()
    assert cfc_u == CFC_UNITS, f"A_CFC search {cfc_u} != modul {CFC_UNITS}"
    assert ncp_u == NCP_UNITS, f"A_NCP search {ncp_u} != modul {NCP_UNITS}"

    configs = {
        "A_GRU": "GRUCell(78->64)",
        "A_NCP": f"CfC(78, AutoNCP(units={ncp_u}, out={NCP_OUT}, seed={NCP_SEED}))",
        "A_CFC": f"CfC(78, units={cfc_u}, backbone_layers=0)",
    }
    print("=== DOWOD PARYTETU RDZENI (referencja 27648, pasmo [27095,28201]) ===")
    print(f"{'RAMIE':7} {'KONFIGURACJA':46} {'RDZEN':>7} {'DELTA%':>8} {'PASMO':>6}")
    rows = {}
    ok = True
    for name in ARMS:
        pol = build_arm(name)
        cp = core_params(pol)
        parts = part_params(pol)
        delta = (cp - CORE_REF) / CORE_REF * 100
        inb = LO <= cp <= HI
        ok = ok and inb
        rows[name] = {"konfiguracja": configs[name], "rdzen_param": cp,
                      "delta_pct": round(delta, 2), "w_pasmie": inb,
                      "enkoder_param": parts["encoder"], "glowa_param": parts["glowa"],
                      "razem_param": parts["razem"]}
        print(f"{name:7} {configs[name]:46} {cp:>7} {delta:>+7.2f}% {'OK' if inb else 'POZA':>6}")
        # sanity forward
        dev = "cpu"
        rgb = torch.randint(0, 256, (2, 5, 64, 64, 3), dtype=torch.uint8)
        kin = torch.randn(2, 5, 13); dt = torch.full((2, 5, 1), 1 / 12)
        out = pol(rgb, kin, dt)
        assert out.shape == (2, 5, 6), f"{name} forward {out.shape}"
    print(f"\nPARYTET: {'PASS (wszystkie w pasmie)' if ok else 'FAIL'}")

    # dopisz gate_arms do MANIFEST_F3.json
    with open(MANIFEST) as f:
        man = json.load(f)
    man["gate_arms"] = {
        "opis": "Dowod parytetu rdzeni ramion F3_GATE (I3a). Referencja = rdzen GRU 27648; pasmo +-2% [27095,28201]. Enkoder i glowa: definicje identyczne, nowe instancje (zero wspoldzielenia wag). Native ts=None (dt zadania stale).",
        "referencja_rdzen": CORE_REF, "pasmo": [LO, HI],
        "ncps_wersja": "1.0.1",
        "ramiona": rows,
    }
    with open(MANIFEST, "w") as f:
        json.dump(man, f, indent=2)
    print("gate_arms dopisane ->", MANIFEST)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
