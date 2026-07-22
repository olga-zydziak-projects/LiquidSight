"""parity_proof_v2 — dowod parytetu rdzeni po ANEKS-3 (I3a-R T2).

Ramiona po naprawie konstrukcji (models/core_cfc, core_ncp). Wymog: rdzenie w
[27 095, 28 201]; glowy identyczne 390 (symetria twin). Tabela -> stdout;
MANIFEST_F3.json: dotychczasowe gate_arms -> gate_arms_v1, nowe -> gate_arms_v2.
"""
import json
import os
import sys

import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.arms import ARMS, BAND, CORE_REF, build_arm, core_params, part_params  # noqa: E402

MANIFEST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "MANIFEST_F3.json"))
LO, HI = BAND
CONFIGS = {
    "A_GRU": "GRUCell(78->64)",
    "A_NCP": "CfC(78, AutoNCP(units=64, out=6, seed=0)); readout stan pelny(64); ts=0.0833s manual",
    "A_CFC": "CfCCell(78, hidden=64, backbone=69); ts=0.0833s manual",
}


def main():
    print("=== DOWOD PARYTETU v2 (po ANEKS-3) — ref 27648, pasmo [27095,28201] ===")
    print(f"{'RAMIE':7} {'RDZEN':>7} {'DELTA%':>8} {'PASMO':>6} {'GLOWA':>6} {'RAZEM':>8}")
    rows = {}
    ok = True
    heads = set()
    for name in ARMS:
        pol = build_arm(name)
        parts = part_params(pol)
        cp = parts["rdzen"]
        delta = (cp - CORE_REF) / CORE_REF * 100
        inb = LO <= cp <= HI
        ok = ok and inb
        heads.add(parts["glowa"])
        rows[name] = {"konfiguracja": CONFIGS[name], "rdzen_param": cp,
                      "delta_pct": round(delta, 2), "w_pasmie": inb,
                      "glowa_param": parts["glowa"], "razem_param": parts["razem"]}
        print(f"{name:7} {cp:>7} {delta:>+7.2f}% {'OK' if inb else 'POZA':>6} "
              f"{parts['glowa']:>6} {parts['razem']:>8}")
        rgb = torch.randint(0, 256, (2, 5, 64, 64, 3), dtype=torch.uint8)
        out = pol(rgb, torch.randn(2, 5, 13), torch.full((2, 5, 1), 1 / 12))
        assert out.shape == (2, 5, 6)
        assert not torch.isnan(out).any()
    heads_ok = heads == {390}
    print(f"\nRDZENIE w pasmie: {'PASS' if ok else 'FAIL'} | GLOWY identyczne 390: "
          f"{'PASS' if heads_ok else 'FAIL ' + str(heads)}")

    with open(MANIFEST) as f:
        man = json.load(f)
    if "gate_arms" in man and "gate_arms_v1" not in man:
        man["gate_arms_v1"] = man.pop("gate_arms")   # zachowaj poprzednia jako v1
    man["gate_arms_v2"] = {
        "opis": "Parytet rdzeni po ANEKS-3 (naprawa konstrukcji CfC). Glowy identyczne Linear(64->6)=390 (symetria twin). A_CFC: CfCCell z backbone, hidden=64/bb=69 (aneks Z1 proponowal 70/64 -> glowa 426; realizacja 64/69 zachowuje parytet ORAZ symetrie glow z Z3/T2). A_NCP: AutoNCP bez zmian (27571), readout stan pelny + ts=sekundy. ncps 1.0.1 (bug wrappera timespans batch>1 obchodzony manualnym krokowaniem komorki).",
        "referencja_rdzen": CORE_REF, "pasmo": [LO, HI],
        "ts_sekundy": round(1 / 12, 5),
        "ramiona": rows,
    }
    with open(MANIFEST, "w") as f:
        json.dump(man, f, indent=2)
    print("gate_arms_v2 dopisane (gate_arms -> gate_arms_v1) ->", MANIFEST)
    sys.exit(0 if (ok and heads_ok) else 1)


if __name__ == "__main__":
    main()
