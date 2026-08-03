"""proofs/net_ibp.py — P3: sound numpy-IBP na rdzeniu liquid (A_CFC z I3b) (DP moduł 6).

Obiekt (P3 opcja B, hierarchia (1)): ISTNIEJĄCY checkpoint A_CFC z I3b — złota recepta CfCCell
(dense, rdzeń 27787 param), pełna prowieniencja `results/i3b/ckpt/A_CFC|0.001|45011.pt`.
Metoda: interval bound propagation (IBP), czysto-numpy, SOUND (auto_LiRPA NIE — F-D3).
Twierdzenie = ZAKRES AKCJI (nie poprawność zadaniowa):
  (1) STAN liquid ograniczony: h' ∈ (−1,1)^64 dla DOWOLNEGO wejścia (h'=ff1(1−g)+ff2·g,
      kombinacja wypukła tanh — bezwarunkowe);
  (2) KOPERTA AKCJI: przy stanie ∈ [−1,1]^64 wyjście pilota ∈ [action box] (bezwarunkowe);
  (3) ROBUSTNOŚĆ LOKALNA: dla kostki wejść ±ε wokół nominału — sound przedział akcji.
Param-count = fakt strukturalny z checkpointu; przedziały = wyłącznie z IBP (F-D2).

CLI: .venv/bin/python -m proofs.net_ibp
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

import numpy as np
import torch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)

CKPT = os.path.join(_ROOT, "results", "i3b", "ckpt", "A_CFC|0.001|45011.pt")
CERT = os.path.join(_HERE, "certs", "P3.json")
TS = 1.0 / 12.0
XY_LIM, Z_LO, Z_HI, VEL_LIM = 2.0, 0.1, 2.4, 1.0     # _scale_setpoint (models/policy.py:22-24)


# --- IBP prymitywy (interval = (lo, hi), sound) -----------------------------
def lin(W, b, lo, hi):
    c = (lo + hi) / 2; r = (hi - lo) / 2
    oc = W @ c + b; orad = np.abs(W) @ r
    return oc - orad, oc + orad


def mono(f, lo, hi):                                  # f monotonicznie rosnąca
    return f(lo), f(hi)


def lecun(v):
    return 1.7159 * np.tanh(0.666 * v)


def cfc_step(w, xlo, xhi, hlo, hhi):
    """IBP jednego kroku CfCCell -> przedział h' (64). Zwraca (h'lo, h'hi)."""
    zlo = np.concatenate([xlo, hlo]); zhi = np.concatenate([xhi, hhi])
    blo, bhi = lin(w["bb_W"], w["bb_b"], zlo, zhi)
    zlo, zhi = mono(lecun, blo, bhi)                  # z
    f1lo, f1hi = mono(np.tanh, *lin(w["f1_W"], w["f1_b"], zlo, zhi))
    f2lo, f2hi = mono(np.tanh, *lin(w["f2_W"], w["f2_b"], zlo, zhi))
    talo, tahi = lin(w["ta_W"], w["ta_b"], zlo, zhi)
    tblo, tbhi = lin(w["tb_W"], w["tb_b"], zlo, zhi)
    glo, ghi = mono(lambda v: 1 / (1 + np.exp(-v)), talo * TS + tblo, tahi * TS + tbhi)  # g∈(0,1)
    # h' = ff1*(1-g) + ff2*g  — kombinacja wypukła (g∈[0,1]): sound = [min los, max his]
    hp_lo = np.minimum(f1lo, f2lo)
    hp_hi = np.maximum(f1hi, f2hi)
    return hp_lo, hp_hi


def scale_setpoint(rlo, rhi):
    """_scale_setpoint IBP: pos_xy=2·tanh, pos_z=0.1+2.3·(tanh+1)/2, vel=tanh (monotoniczne)."""
    out_lo = np.zeros(6); out_hi = np.zeros(6)
    tl, th = np.tanh(rlo), np.tanh(rhi)
    out_lo[0:2], out_hi[0:2] = XY_LIM * tl[0:2], XY_LIM * th[0:2]
    out_lo[2] = Z_LO + (Z_HI - Z_LO) * (tl[2] + 1) / 2
    out_hi[2] = Z_LO + (Z_HI - Z_LO) * (th[2] + 1) / 2
    out_lo[3:6], out_hi[3:6] = VEL_LIM * tl[3:6], VEL_LIM * th[3:6]
    return out_lo, out_hi


def action_range(w, hlo, hhi):
    rlo, rhi = lin(w["hd_W"], w["hd_b"], hlo, hhi)
    return scale_setpoint(rlo, rhi)


def load_weights():
    sd = torch.load(CKPT, map_location="cpu")
    g = lambda k: sd[k].numpy().astype(np.float64)
    return {"bb_W": g("core.cell.backbone.weight"), "bb_b": g("core.cell.backbone.bias"),
            "f1_W": g("core.cell.ff1.weight"), "f1_b": g("core.cell.ff1.bias"),
            "f2_W": g("core.cell.ff2.weight"), "f2_b": g("core.cell.ff2.bias"),
            "ta_W": g("core.cell.time_a.weight"), "ta_b": g("core.cell.time_a.bias"),
            "tb_W": g("core.cell.time_b.weight"), "tb_b": g("core.cell.time_b.bias"),
            "hd_W": g("head.weight"), "hd_b": g("head.bias")}


def main():
    if not os.path.exists(CKPT):
        print(f"!! ESKALACJA: brak checkpointu A_CFC ({CKPT}) — nie buduję (ratyfikacja P3 (1)).")
        raise SystemExit(2)
    w = load_weights()
    param_count = int(sum(v.size for k, v in w.items()))  # rdzeń CfCCell + głowa (fakt strukturalny)
    core_only = int(sum(w[k].size for k in ("bb_W", "bb_b", "f1_W", "f1_b", "f2_W", "f2_b",
                                            "ta_W", "ta_b", "tb_W", "tb_b")))

    # (1) STAN ograniczony: wejście NIEOGRANICZONE -> h' ⊆ [−1,1]^64 (bezwarunkowe)
    BIG = 1e6
    xlo, xhi = -BIG * np.ones(78), BIG * np.ones(78)
    hlo0, hhi0 = -BIG * np.ones(64), BIG * np.ones(64)
    hp_lo, hp_hi = cfc_step(w, xlo, xhi, hlo0, hhi0)
    state_bound = float(max(np.max(np.abs(hp_lo)), np.max(np.abs(hp_hi))))
    state_ok = state_bound <= 1.0 + 1e-9

    # (2) KOPERTA AKCJI: stan ∈ [−1,1]^64 (zbiór osiągalny) -> zakres akcji (bezwarunkowe)
    env_lo, env_hi = action_range(w, -np.ones(64), np.ones(64))

    # (3) ROBUSTNOŚĆ LOKALNA: kostka ±ε wokół nominału (x0=0, h0=0)
    local = {}
    for eps in (0.01, 0.05, 0.1):
        alo, ahi = action_range(w, *cfc_step(w, -eps * np.ones(78), eps * np.ones(78),
                                             -eps * np.ones(64), eps * np.ones(64)))
        width = (ahi - alo)
        local[str(eps)] = {"action_lo": [round(x, 4) for x in alo],
                           "action_hi": [round(x, 4) for x in ahi],
                           "max_width": round(float(np.max(width)), 4)}
    # informatywność: koperta akcji (2) ściślejsza niż pełna skala setpointu?
    full_w = np.array([2 * XY_LIM, 2 * XY_LIM, Z_HI - Z_LO, 2 * VEL_LIM, 2 * VEL_LIM, 2 * VEL_LIM])
    env_w = env_hi - env_lo
    informative = bool(np.all(env_w <= full_w + 1e-9) and np.any(env_w < full_w - 1e-3))

    print("=== P3 numpy-IBP na A_CFC (I3b, złota recepta) ===")
    print(f"  obiekt: {os.path.relpath(CKPT, _ROOT)}  | rdzeń CfCCell={core_only} +głowa -> {param_count} param")
    print(f"  (1) stan liquid ⊆ [−1,1]^64: max|h'|={state_bound:.6f}  -> {'OK' if state_ok else 'FAIL'}")
    print(f"  (2) koperta akcji (stan∈[−1,1]): width={[round(x,3) for x in env_w]}  vs pełna {list(full_w)}")
    print(f"      informatywne (ściślej niż skala): {informative}")
    for e, d in local.items():
        print(f"  (3) ε={e}: max szerokość akcji = {d['max_width']}")

    # ROZDZIAŁ werdyktu (zasada 6: nie zmiękczamy): (1)+(2) PROVED bezwarunkowo; (3) UNPROVEN-tą-metodą
    local_informative = all(d["max_width"] < float(np.max(full_w)) - 0.05 for d in local.values())
    print(f"  (1)+(2) zakres akcji: {'PROVED' if state_ok else 'FAIL'}   "
          f"(3) robustność lokalna: {'informatywna' if local_informative else 'UNPROVEN-tą-metodą (IBP luźny ≈ pełna skala)'}")
    verdict = "PROVED" if state_ok else "UNPROVEN"
    print(f"WERDYKT P3: {verdict} dla zakresu akcji (stan-bound + koperta); robustność lokalna "
          f"{'PROVED' if local_informative else 'UNPROVEN-tą-metodą'}")
    if not state_ok:
        raise SystemExit(1)
    cert = {"property": "P3", "verdict": "PROVED",
            "verdict_scope": "PROVED: state-bound + action-envelope (bezwarunkowe). "
                             "local-robustness (ε-box): " + ("PROVED (informatywna)" if local_informative
                             else "UNPROVEN-tą-metodą — goły IBP luźny ≈ pełna skala (F-D3; auto_LiRPA "
                                  "NIEautoryzowany; obiekt demonstracyjny units=20 = osobna eskalacja/zgoda)"),
            "local_robustness_informative": local_informative,
            "method": "sound numpy-IBP (no auto_LiRPA)",
            "object": {"checkpoint": os.path.relpath(CKPT, _ROOT), "arm": "A_CFC (I3b golden recipe)",
                       "cell": "CfCCell(in=78,hidden=64,backbone=69) + head(64->6)",
                       "param_count_core": core_only, "param_count_core_plus_head": param_count,
                       "provenance": "results/i3b (F3 twin duel), MANIFEST_F3 gate_arms_v2 A_CFC"},
            "ts": "1/12",
            "theorems": {
                "state_bounded": f"∀ wejście: h' ∈ [−1,1]^64 (max|h'|={state_bound:.6f}); "
                                 "dowód strukturalny: kombinacja wypukła tanh",
                "action_envelope": {"lo": [round(x, 4) for x in env_lo],
                                    "hi": [round(x, 4) for x in env_hi],
                                    "note": "przy stanie∈[−1,1]^64; bezwarunkowa koperta akcji"},
                "local_robustness": local},
            "informative_vs_full_scale": informative,
            "banner_name": "liquid core (CfC recipe, units=64)",
            "notes": ["317 NIE dotyczy tego obiektu — banner '317' wyłącznie przy eksponacie v1.0 "
                      "(paper/NUMBERS.md, konfiguracja state-loop); certyfikat P3 podpisany realnym "
                      "param-countem swojego obiektu (27787 rdzeń).",
                      "AutoNCP-sparse-wiring: dług integracyjny (LiRPA nieautoryzowany, F-D3).",
                      "IBP jest SOUND; luźność na szerokich kostkach = znany limit metody (nie zmiękczamy)."],
            "z3_pip": None, "ibp": "numpy (sound interval arithmetic)",
            "model_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
            "ckpt_sha256": hashlib.sha256(open(CKPT, "rb").read()).hexdigest()}
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (ckpt_sha256={cert['ckpt_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
