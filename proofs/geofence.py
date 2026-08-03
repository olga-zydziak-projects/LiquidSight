"""proofs/geofence.py — P2: dron respektujący osłonę nigdy nie opuszcza ogrodzenia (DP moduł 3).

Twierdzenie O MODELU dynamiki (założenia jawne), NIE o pełnym PyBullet. Stałe wyłącznie wymierne
(zero floatów): VEL_LIM=1, Δt=1/12, geo_lim=9/5, arena_half=2, A_min=30/7.

MODEL (rzut na najgorszą oś poziomą; p = współrzędna na zewnątrz ≥0, v = prędkość na zewnątrz):
- osłona sprawdza pozycję co tik (12 Hz); `p > geo_lim (1.8)` ⇒ REFUSE ⇒ position-hold (hamowanie).
- ZAŁOŻENIA: (i) |v| ≤ VEL_LIM=1 (ograniczenie zadanej prędkości `_scale_setpoint`, models/policy.py:24);
  (ii) hamowanie ciągłe z decel ≥ A_min (bariera p+v²/2A zachowana: d/dt(p+v²/2A)=v−v=0);
  (iii) detekcja w ≤1 tik (dron przebywa ≤ VEL_LIM·Δt zanim osłona zareaguje); (iv) rzut poziomy.
BARIERA (niezmiennik): Inv(p,v) = 0≤v≤VEL_LIM ∧ p + v²/(2·A_min) ≤ arena_half.
Zobowiązania z3 (NRA): baza, krok-ALLOW, krok-BRAKE, bezpieczeństwo p≤2, ostrość progu A_min=30/7.

CLI: .venv/bin/python -m proofs.geofence
"""
from __future__ import annotations
import hashlib
import json
import os
from fractions import Fraction

import z3

_HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(_HERE, "certs", "P2.json")

VEL = z3.RealVal("1")
DT = z3.RealVal("1/12")
GEO = z3.RealVal("9/5")          # arena_half − margin = 2 − 1/5
ARENA = z3.RealVal("2")
AMIN = z3.RealVal("30/7")        # 0.5/(1/5 − 1/12) — próg dokładny
BRAKE = z3.RealVal("1") / (2 * AMIN)     # v²·BRAKE = droga hamowania (=7/60)


def inv(p, v):
    return z3.And(v >= 0, v <= VEL, p + BRAKE * v * v <= ARENA)


def prove():
    res = {}
    p, v, vp = z3.Real("p"), z3.Real("v"), z3.Real("vp")

    # BAZA: start w arenie (p≤geo_lim, 0≤v≤VEL) ⇒ Inv
    s = z3.Solver(); s.add(p <= GEO, v >= 0, v <= VEL); s.add(z3.Not(inv(p, v)))
    res["base_start_in_fence"] = str(s.check())

    # KROK ALLOW: Inv ∧ p≤geo_lim ⇒ Inv(p+v·Δt, vp) dla dowolnego vp∈[0,VEL]
    pa = p + v * DT
    s = z3.Solver(); s.add(inv(p, v), p <= GEO, vp >= 0, vp <= VEL)
    s.add(z3.Not(inv(pa, vp)))
    res["step_allow"] = str(s.check())

    # KROK BRAKE (hamowanie ciągłe, bariera zachowana): p>geo_lim, (p',v') z p'+BRAKE·v'²=p+BRAKE·v²,
    # 0≤v'≤v, p'≥p ⇒ Inv(p',v') ∧ p'≤ARENA
    pp, vpp = z3.Real("pp"), z3.Real("vpp")
    s = z3.Solver()
    s.add(inv(p, v), p > GEO, vpp >= 0, vpp <= v, pp >= p,
          pp + BRAKE * vpp * vpp == p + BRAKE * v * v)
    s.add(z3.Not(z3.And(inv(pp, vpp), pp <= ARENA)))
    res["step_brake"] = str(s.check())

    # BEZPIECZEŃSTWO: Inv ⇒ p ≤ ARENA (brak katastrofy geofence env: |pos|>2)
    s = z3.Solver(); s.add(inv(p, v)); s.add(z3.Not(p <= ARENA))
    res["safety_p_le_arena"] = str(s.check())

    # OSTROŚĆ PROGU: ∀A≥30/7 model bezpieczny; ∀0<A<30/7 NIEbezpieczny (30/7 dokładny)
    A = z3.Real("A")
    delta = lambda a: GEO + VEL * DT + (VEL * VEL) / (2 * a)     # max pozycja = geo+detekcja+hamowanie
    s = z3.Solver(); s.add(A >= AMIN); s.add(z3.Not(delta(A) <= ARENA))
    res["threshold_A_ge_amin_safe"] = str(s.check())            # unsat = bezpieczny dla wszystkich A≥30/7
    s = z3.Solver(); s.add(A > 0, A < AMIN, delta(A) <= ARENA)
    res["threshold_A_lt_amin_unsafe"] = str(s.check())          # unsat = żadne A<30/7 nie jest bezpieczne
    return res


def main():
    res = prove()
    allok = all(v == "unsat" for v in res.values())
    print("=== P2 geofence (z3 NRA, bariera) ===")
    for k, v in res.items():
        print(f"  {k}: {v}" + ("  ✓" if v == "unsat" else "  !!"))
    print(f"WERDYKT P2: {'PROVED' if allok else 'UNPROVEN'}")
    if not allok:
        print("!! Zobowiązanie nie-unsat — zasada 6: UNPROVEN, nie zmiękczamy. Brak certyfikatu.")
        raise SystemExit(1)
    # kontrola tożsamości wymiernej δ(A_min)=margines dokładnie
    assert Fraction(9, 5) + Fraction(1, 12) + Fraction(1, 1) / (2 * Fraction(30, 7)) == Fraction(2), "δ≠2"
    cert = {"property": "P2", "verdict": "PROVED", "method": "barrier induction + threshold (z3 NRA)",
            "z3_pip": "5.0.0.0", "z3_lib": z3.get_version_string(),
            "obligations": res,
            "constants_rational": {"VEL_LIM": "1", "dt": "1/12", "geo_lim": "9/5",
                                   "arena_half": "2", "A_min": "30/7", "brake_coef_v2": "7/60"},
            "delta_exact": "geo_lim + VEL·dt + VEL²/(2·A_min) = 9/5 + 1/12 + 7/60 = 2 (= arena_half)",
            "assumptions": ["|v|≤VEL_LIM (models/policy.py:24 _scale_setpoint)",
                            "hamowanie ciągłe decel≥A_min (bariera p+v²/2A zachowana)",
                            "detekcja ≤1 tik (12 Hz, shield.step per k)",
                            "rzut na najgorszą oś poziomą"],
            "code_refs": {"vel_lim": "models/policy.py:24 (VEL_LIM=1.0)",
                          "shield_geo": "s3c1/shield.py:70-78 (R-C, geo_lim=arena_half−margin=1.8)",
                          "env_geofence": "env/liquidsight_env.py:188-190 (|pos|>2.0 katastrofa)"},
            "theorem": "Inv(p,v)=0≤v≤1 ∧ p+(7/60)v²≤2  ⇒  p≤2 (dron nie opuszcza ogrodzenia)",
            "model_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    if os.path.exists(CERT):
        old = json.load(open(CERT))
        print(f"certyfikat istnieje — zgodność: {'TAK' if old.get('obligations') == res else 'NIE'}")
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (model_sha256={cert['model_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
