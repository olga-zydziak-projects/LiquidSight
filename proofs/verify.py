"""proofs/verify.py — dowód P1 (własności osłony) przez 1-indukcję w z3.

Model = lustro `s3c1/shield.py` (RECON §A, proofs/P1_FORMALIZATION.md). Stałe wymierne (zero
floatów): θ_age=2, ceiling=6, near=1/2, geo_lim=9/5, t_hold=t_acq=3 s = 36 tików (dt=1/12).
Zobowiązania: BAZA `Inv(c0)` i KROK `Inv(c) ∧ valid ⇒ Inv(c') ∧ P1(a..d)`. z3 sprawdza NEGACJĘ
(oczekiwane UNSAT = własność trzyma). Przy UNSAT generuje certyfikat proofs/certs/P1.json
(wynik + wersja z3 + cytaty linii + sha256 tego pliku). Zasada 3: odtwarzalne od zera.

CLI: .venv/bin/python -m proofs.verify        # dowód + zapis/porównanie certyfikatu
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

import z3

_HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(_HERE, "certs", "P1.json")

# --- enumeracje (Int) -------------------------------------------------------
SEEKING, TRACKING, DWELL_GUARD, DONE = 0, 1, 2, 3
ALLOW, HOLD, REFUSE = 0, 1, 2
NONE, NO_MATCH, STALE, GEOFENCE = 0, 1, 2, 3
# --- stałe wymierne (z shield.py:29-37) -------------------------------------
THETA = z3.RealVal(2)          # θ_age
CEIL = z3.RealVal(6)           # sufit
NEAR = z3.RealVal(1) / 2       # martwe pole
THOLD = 36                     # t_hold/dt = 3 / (1/12)  (shield.py:30,112,131)
TACQ = 36                      # t_acq/dt  = 3 / (1/12)  (shield.py:30,83)


def _sv(p):
    """Symboliczna konfiguracja z prefiksem p."""
    return {
        "st": z3.Int(p + "st"), "ent": z3.Bool(p + "ent"), "adm": z3.Bool(p + "adm"),
        "ehs": z3.Bool(p + "ehs"), "eh": z3.Int(p + "eh"),
        "chs": z3.Bool(p + "chs"), "ch": z3.Int(p + "ch"),
        "tm": z3.Bool(p + "tm"), "rsn": z3.Int(p + "rsn"), "k": z3.Int(p + "k"),
    }


def domain(c):
    """Ograniczenia dziedzinowe (typy enum, k≥0)."""
    return z3.And(c["st"] >= 0, c["st"] <= 3, c["rsn"] >= 0, c["rsn"] <= 3, c["k"] >= 0)


def inv(c):
    """Niezmiennik indukcyjny I1–I8 (proofs/P1_FORMALIZATION §5)."""
    I1 = z3.Implies(c["tm"], z3.And(c["rsn"] != NONE, c["st"] == DONE))
    I2 = (c["st"] == DONE) == c["tm"]
    I3 = z3.Implies(c["adm"], c["ent"])
    # ¬tm w GUARDzie (po REFUSE ehs/chs zostają ustawione — don't-care przy latchu);
    # bound ≤36: przy k−start=35 osłona HOLD-uje, post ma k−start=36 (żywy stan tuż przed REFUSE)
    I4 = z3.Implies(z3.And(c["ehs"], z3.Not(c["tm"])),
                    z3.And(c["ent"], z3.Not(c["adm"]), c["st"] == DWELL_GUARD,
                           0 <= c["k"] - c["eh"], c["k"] - c["eh"] <= 36))
    I5 = z3.Implies(z3.And(c["chs"], z3.Not(c["tm"])),
                    z3.And(c["adm"], c["st"] == DWELL_GUARD,
                           0 <= c["k"] - c["ch"], c["k"] - c["ch"] <= 36))
    I6 = z3.Not(z3.And(c["ehs"], c["chs"]))
    I7 = z3.And(z3.Implies(c["ehs"], z3.And(0 <= c["eh"], c["eh"] <= c["k"])),
                z3.Implies(c["chs"], z3.And(0 <= c["ch"], c["ch"] <= c["k"])))
    I8 = z3.Implies(z3.And(c["ent"], z3.Not(c["adm"]), z3.Not(c["tm"])),
                    z3.And(c["st"] == DWELL_GUARD, c["ehs"]))
    return z3.And(domain(c), I1, I2, I3, I4, I5, I6, I7, I8)


def valid(c, hl, age, dist, gt, gp):
    """valid(input) + A-lock (monotoniczność locka): entered ⇒ has_lock."""
    return z3.And(age >= 0, dist >= 0, z3.Implies(c["ent"], hl))


def _pick(pairs, default):
    """nested If: pairs=[(cond,val),...] w kolejności priorytetu."""
    e = default
    for cond, val in reversed(pairs):
        e = z3.If(cond, val, e)
    return e


def tau(c, hl, age, dist, gt, gp):
    """Relacja przejścia: lustro shield._decide. Zwraca (post-config, decision)."""
    k = c["k"]
    old = z3.And(hl, age > THETA)
    over = z3.And(hl, age > CEIL)
    geo = z3.Or(gt, gp)
    # liście (wzajemnie wykluczające, w kolejności priorytetu — §4)
    L_latch = c["tm"]
    base = z3.Not(c["tm"])
    L_geo = z3.And(base, geo)
    ok = z3.And(base, z3.Not(geo))
    L_nomatch = z3.And(ok, z3.Not(hl), k >= TACQ)
    L_seek = z3.And(ok, z3.Not(hl), k < TACQ)
    hlok = z3.And(ok, hl)
    L3_hold = z3.And(hlok, z3.Not(c["ent"]), dist < NEAR, old)
    L3_admit = z3.And(hlok, z3.Not(c["ent"]), dist < NEAR, z3.Not(old))
    L3_track = z3.And(hlok, z3.Not(c["ent"]), dist >= NEAR)
    e4 = z3.And(hlok, c["ent"], z3.Not(c["adm"]))
    L4_admit = z3.And(e4, z3.Not(old))
    L4_refuse = z3.And(e4, old, (k - c["eh"]) >= THOLD)
    L4_hold = z3.And(e4, old, (k - c["eh"]) < THOLD)
    e5 = z3.And(hlok, c["ent"], c["adm"])
    L5a_hold = z3.And(e5, z3.Not(c["chs"]), over)
    L5a_allow = z3.And(e5, z3.Not(c["chs"]), z3.Not(over))
    L5b_allow = z3.And(e5, c["chs"], z3.Not(over))
    L5b_refuse = z3.And(e5, c["chs"], over, (k - c["ch"]) >= THOLD)
    L5b_hold = z3.And(e5, c["chs"], over, (k - c["ch"]) < THOLD)

    order = [L_latch, L_geo, L_nomatch, L_seek, L3_hold, L3_admit, L3_track,
             L4_admit, L4_refuse, L4_hold, L5a_hold, L5a_allow, L5b_allow, L5b_refuse, L5b_hold]
    dec_v = [REFUSE, REFUSE, REFUSE, ALLOW, HOLD, ALLOW, ALLOW,
             ALLOW, REFUSE, HOLD, HOLD, ALLOW, ALLOW, REFUSE, HOLD]
    st_v = [DONE, DONE, DONE, SEEKING, DWELL_GUARD, TRACKING, TRACKING,
            TRACKING, DONE, DWELL_GUARD, DWELL_GUARD, TRACKING, TRACKING, DONE, DWELL_GUARD]

    def pick_ord(vals):
        return _pick(list(zip(order, vals)), vals[-1])

    dec = pick_ord(dec_v)
    st2 = pick_ord(st_v)
    ent2 = z3.If(z3.Or(L3_hold, L3_admit), True, c["ent"])
    adm2 = z3.If(z3.Or(L3_admit, L4_admit), True, c["adm"])
    ehs2 = z3.If(L3_hold, True, z3.If(z3.Or(L3_admit, L4_admit), False, c["ehs"]))
    eh2 = z3.If(L3_hold, k, c["eh"])
    chs2 = z3.If(L5a_hold, True, z3.If(L5b_allow, False, c["chs"]))
    ch2 = z3.If(L5a_hold, k, c["ch"])
    tm2 = z3.Or(L_latch, L_geo, L_nomatch, L4_refuse, L5b_refuse)
    rsn2 = z3.If(L_latch, c["rsn"],
                 z3.If(L_geo, GEOFENCE,
                       z3.If(L_nomatch, NO_MATCH,
                             z3.If(z3.Or(L4_refuse, L5b_refuse), STALE, NONE))))
    cp = {"st": st2, "ent": ent2, "adm": adm2, "ehs": ehs2, "eh": eh2,
          "chs": chs2, "ch": ch2, "tm": tm2, "rsn": rsn2, "k": k + 1}
    leaves = {"e4": e4, "e5": e5, "L4_hold": L4_hold, "L5b_hold": L5b_hold}
    return cp, dec, geo, leaves


def props(c, cp, dec, geo, leaves, hl, age, gt, gp):
    """P1(a)–(d) na wyjściu przejścia (proofs/P1_FORMALIZATION §6)."""
    k = c["k"]
    P1b = z3.And(z3.Implies(geo, dec == REFUSE),
                 z3.Implies(z3.And(z3.Not(c["tm"]), geo), cp["rsn"] == GEOFENCE))
    P1c = z3.Implies(dec == REFUSE, z3.Or(cp["rsn"] == NO_MATCH, cp["rsn"] == STALE, cp["rsn"] == GEOFENCE))
    P1a = z3.Implies(z3.And(dec == ALLOW, hl, cp["ent"]), age <= CEIL)   # bezwarunkowe przez I8
    # P1d: żadna decyzja HOLD kontynuująca hold nie zapada gdy (k−start) ≥ T_hold (=36) —
    # na progu osłona REFUSE-uje, nie HOLD-uje ("rozstrzyga się w ≤ T_hold").
    P1d = z3.And(z3.Not(z3.And(dec == HOLD, leaves["e4"], (k - c["eh"]) >= THOLD)),
                 z3.Not(z3.And(dec == HOLD, leaves["e5"], c["chs"], (k - c["ch"]) >= THOLD)))
    return {"P1a": P1a, "P1b": P1b, "P1c": P1c, "P1d": P1d}


def prove():
    c = _sv("c_")
    hl, age, dist = z3.Bool("hl"), z3.Real("age"), z3.Real("dist")
    gt, gp = z3.Bool("gt"), z3.Bool("gp")
    cp, dec, geo, leaves = tau(c, hl, age, dist, gt, gp)
    P = props(c, cp, dec, geo, leaves, hl, age, gt, gp)

    results = {}
    # BAZA: c0 = reset (SEEKING, wszystko False/None, k=0)
    c0 = {"st": z3.IntVal(SEEKING), "ent": z3.BoolVal(False), "adm": z3.BoolVal(False),
          "ehs": z3.BoolVal(False), "eh": z3.IntVal(0), "chs": z3.BoolVal(False),
          "ch": z3.IntVal(0), "tm": z3.BoolVal(False), "rsn": z3.IntVal(NONE), "k": z3.IntVal(0)}
    sb = z3.Solver(); sb.add(z3.Not(inv(c0)))
    results["base"] = str(sb.check())          # oczekiwane: unsat (Inv(c0) trzyma)

    # KROK: Inv(c) ∧ valid ⇒ Inv(c') ∧ P1(a..d).  Sprawdzamy NEGACJĘ per własność.
    pre = z3.And(inv(c), valid(c, hl, age, dist, gt, gp))
    for name, goal in [("inv_step", inv(cp)), *[(k, v) for k, v in P.items()]]:
        s = z3.Solver(); s.add(pre); s.add(z3.Not(goal))
        results[name] = str(s.check())         # oczekiwane: unsat
    return results


def _self_sha():
    return hashlib.sha256(open(__file__, "rb").read()).hexdigest()


def main():
    res = prove()
    allunsat = all(v == "unsat" for v in res.values())
    print("=== P1 dowód (z3) ===")
    for k, v in res.items():
        print(f"  {k}: {v}" + ("  ✓" if v == "unsat" else "  !! (SPODZIEWANO unsat)"))
    verdict = "PROVED" if allunsat else "UNPROVEN"
    print(f"WERDYKT P1: {verdict}")
    if not allunsat:
        print("!! Któreś zobowiązanie NIE jest unsat — kontrprzykład istnieje (zasada 6: UNPROVEN, "
              "nie zmiękczamy). Nie zapisuję certyfikatu PROVED.")
        sys.exit(1)
    cert = {
        "property": "P1", "verdict": "PROVED", "method": "1-induction (z3)",
        "z3_pip": "5.0.0.0", "z3_lib": z3.get_version_string(),
        "obligations": res,
        "constants_rational": {"theta_age": "2", "ceiling": "6", "near": "1/2",
                               "geo_lim": "9/5", "t_hold_ticks": THOLD, "t_acq_ticks": TACQ,
                               "dt": "1/12"},
        "assumptions": ["A-lock: entered ⇒ has_lock (monotoniczność locka, Tracker5)"],
        "code_refs": {"shield": "s3c1/shield.py:65-136 (_decide)",
                      "t_hold": "s3c1/shield.py:30 (t_hold_s=3.0, dt=1/12); :112,:131 (nierówność)"},
        "properties": {
            "P1a": "(ALLOW ∧ has_lock ∧ entered') ⇒ age ≤ 6  (bezwarunkowe via I8)",
            "P1b": "(geo) ⇒ REFUSE  ∧  (¬term ∧ geo) ⇒ reason=GEOFENCE  [wzmocnione]",
            "P1c": "REFUSE ⇒ reason ∈ {NO_MATCH,STALE,GEOFENCE}",
            "P1d": "żywy HOLD < 36 tików (=T_hold); k−start=36 ⇒ REFUSE",
        },
        "model_sha256": _self_sha(),
    }
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    # porównanie z istniejącym certyfikatem (zasada 3: odtwarzalność)
    if os.path.exists(CERT):
        old = json.load(open(CERT))
        same = (old.get("model_sha256") == cert["model_sha256"] and old.get("obligations") == res)
        print(f"certyfikat istnieje — zgodność modelu+wyników: {'TAK' if same else 'NIE (zmiana!)'}")
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (model_sha256={cert['model_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
