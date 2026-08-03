"""proofs/conformance.py — P5: konformancja kod ↔ dowiedziony model (DP moduł 2).

Wiąże `s3c1/shield.py` z modelem z3 `proofs.verify.tau` (obiekt, na którym dowiedziono P1).
Dla KAŻDEGO tiku: ewaluuje `tau` na konkretnych wejściach (z3 concrete + simplify) i porównuje
DECYZJĘ + POWÓD + STAN-PO z realnym `Shield.step`. Dodatkowo: pełne pokrycie 15 przejść automatu
i przypadki brzegowe dokładnie na progach 24/36/72 tików (backlog P5). Zgodność ⇒ dowód P1 dotyczy
kodu, nie fikcji. Cert: proofs/certs/P5.json.

CLI: .venv/bin/python -m proofs.conformance
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from fractions import Fraction

import z3

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from s3c1.shield import Shield, ALLOW, HOLD, REFUSE, NO_MATCH, STALE_AT_DWELL, GEOFENCE  # noqa: E402
from proofs.verify import (tau, SEEKING, TRACKING, DWELL_GUARD, DONE,  # noqa: E402
                           ALLOW as M_ALLOW, HOLD as M_HOLD, REFUSE as M_REFUSE,
                           NONE, NO_MATCH as M_NM, STALE as M_ST, GEOFENCE as M_GEO)

CERT = os.path.join(_HERE, "certs", "P5.json")
DT = 1.0 / 12.0
GEO_LIM = 1.8
STATE_ID = {"SEEKING": SEEKING, "TRACKING": TRACKING, "DWELL-GUARD": DWELL_GUARD, "DONE": DONE}
DEC_ID = {ALLOW: M_ALLOW, HOLD: M_HOLD, REFUSE: M_REFUSE}
RSN_ID = {None: NONE, NO_MATCH: M_NM, STALE_AT_DWELL: M_ST, GEOFENCE: M_GEO}


def sh_pre(sh):
    """Wyciąga model-konfigurację z BIEŻĄCEGO stanu Shielda (przed krokiem)."""
    eh = sh.entry_hold_start_k
    ch = sh.ceiling_hold_start_k
    tm = sh.terminal is not None
    rsn = RSN_ID[sh.terminal[0]] if tm else NONE
    return {"st": STATE_ID[sh.state], "ent": sh.entered, "adm": sh.admitted,
            "ehs": eh is not None, "eh": (eh if eh is not None else 0),
            "chs": ch is not None, "ch": (ch if ch is not None else 0),
            "tm": tm, "rsn": rsn}


def sh_post(sh):
    d = sh_pre(sh); d["k"] = None
    return d


def eval_tau(pre, k, hl, age_fr, dist_fr, gt, gp):
    """Ewaluuje dowiedziony model tau na KONKRETNYCH wejściach → (dec, post-config)."""
    c = {"st": z3.IntVal(pre["st"]), "ent": z3.BoolVal(pre["ent"]), "adm": z3.BoolVal(pre["adm"]),
         "ehs": z3.BoolVal(pre["ehs"]), "eh": z3.IntVal(pre["eh"]),
         "chs": z3.BoolVal(pre["chs"]), "ch": z3.IntVal(pre["ch"]),
         "tm": z3.BoolVal(pre["tm"]), "rsn": z3.IntVal(pre["rsn"]), "k": z3.IntVal(k)}
    cp, dec, geo, _ = tau(c, z3.BoolVal(hl), z3.RealVal(str(age_fr)),
                          z3.RealVal(str(dist_fr)), z3.BoolVal(gt), z3.BoolVal(gp))
    g = lambda e: z3.simplify(e)
    b = lambda e: z3.is_true(g(e))
    i = lambda e: g(e).as_long()
    post = {"st": i(cp["st"]), "ent": b(cp["ent"]), "adm": b(cp["adm"]),
            "ehs": b(cp["ehs"]), "eh": i(cp["eh"]), "chs": b(cp["chs"]), "ch": i(cp["ch"]),
            "tm": b(cp["tm"]), "rsn": i(cp["rsn"])}
    return i(dec), post


LEAVES = ["latch", "geo", "nomatch", "seek", "3_hold", "3_admit", "3_track",
          "4_admit", "4_refuse", "4_hold", "5a_hold", "5a_allow", "5b_allow", "5b_refuse", "5b_hold"]


def leaf_of(pre, k, hl, age, dist, gt, gp):
    """Które z 15 przejść (dla pokrycia)."""
    old = hl and age > 2
    over = hl and age > 6
    geo = gt or gp
    if pre["tm"]:
        return "latch"
    if geo:
        return "geo"
    if not hl:
        return "nomatch" if k >= 36 else "seek"
    if not pre["ent"]:
        if dist < Fraction(1, 2):
            return "3_hold" if old else "3_admit"
        return "3_track"
    if not pre["adm"]:
        if not old:
            return "4_admit"
        return "4_refuse" if (k - pre["eh"]) >= 36 else "4_hold"
    if not pre["chs"]:
        return "5a_hold" if over else "5a_allow"
    if not over:
        return "5b_allow"
    return "5b_refuse" if (k - pre["ch"]) >= 36 else "5b_hold"


def _norm(p):
    """Normalizacja don't-care: eh/ch nieistotne gdy odpowiednia flaga False."""
    q = dict(p)
    if not q["ehs"]:
        q["eh"] = 0
    if not q["chs"]:
        q["ch"] = 0
    return q


def run_episode(hover, ticks, coverage, mism):
    """ticks: lista (has_lock, age|None, dist, pos). Porównuje tau≡Shield per tik (bez break na
    REFUSE — kolejne tiki pokrywają latch)."""
    sh = Shield(); sh.reset(hover_xy=hover)
    gt = max(abs(hover[0]), abs(hover[1])) > GEO_LIM
    for k, (hl, age, dist, pos) in enumerate(ticks):
        pre = sh_pre(sh)
        gp = max(abs(pos[0]), abs(pos[1])) > GEO_LIM
        age_val = age if age is not None else Fraction(0)
        m_dec, m_post = eval_tau(pre, k, hl, age_val, dist, gt, gp)
        coverage.add(leaf_of(pre, k, hl, age_val, dist, gt, gp))
        d = sh.step(k, pos, hl, (float(age) if (hl and age is not None) else None), 0.02, float(dist))
        s_dec = DEC_ID[d["decision"]]
        s_post = sh_post(sh)                       # zawiera rsn z terminala (sh_pre)
        mp, sp = _norm(m_post), _norm(s_post)
        if m_dec != s_dec or any(mp[x] != sp[x] for x in
                ("st", "ent", "adm", "ehs", "eh", "chs", "ch", "tm", "rsn")):
            mism.append({"k": k, "pre": pre, "in": [hl, str(age), str(dist), gt, gp],
                         "model": {"dec": m_dec, **mp}, "shield": {"dec": s_dec, **sp}})
            return  # stop epizodu na pierwszej rozbieżności


def gen_random(seed):
    """Deterministyczne pseudo-losowe trajektorie respektujące A-lock (lock monotoniczny)."""
    import random
    rng = random.Random(seed)
    hover = (Fraction(rng.randint(-19, 19), 10), Fraction(rng.randint(-19, 19), 10))
    ticks = []
    locked = False
    for k in range(60):
        if not locked and rng.random() < 0.3:
            locked = True
        hl = locked
        age = Fraction(rng.randint(0, 96), 12) if hl else None      # 0..8 s
        dist = Fraction(rng.randint(0, 30), 20)                     # 0..1.5 m
        px = Fraction(rng.randint(-20, 20), 10); py = Fraction(rng.randint(-20, 20), 10)
        ticks.append((hl, age, dist, (px, py)))
    return hover, ticks


def gen_boundary():
    """Przypadki brzegowe dokładnie na progach: k−start=24/36/72, age=2.0/6.0 (backlog P5)."""
    eps = []
    IN = (Fraction(3, 10), Fraction(0))                            # pozycja w arenie
    hover = (Fraction(12, 10), Fraction(3, 10))
    # (1) wejście stare age=2.0 dokładnie (θ_age): przy age>2 old; age==2 NIE old -> admisja
    t = [(True, Fraction(2), Fraction(4, 10), IN)]                 # dist<0.5, age==θ -> admit ALLOW
    eps.append((hover, t))
    # (2) entry-HOLD do timeoutu 36 tików: wejście stare, age stale >2, licz do k−eh=36
    t = [(True, Fraction(25, 12) + Fraction(kk, 12), Fraction(4, 10), IN) for kk in range(40)]
    eps.append((hover, t))
    # (3) sufit: admisja świeża, potem age rośnie do 6.0 i 6.0+ (ceiling/dt=72 od startu epizodu)
    t = [(True, Fraction(3, 10), Fraction(4, 10), IN)]             # admisja @k0
    t += [(True, Fraction(3, 10) + Fraction(kk, 12), Fraction(4, 10), IN) for kk in range(1, 90)]
    eps.append((hover, t))
    # (4) NO_MATCH dokładnie na k=36 (t_acq): brak locka do 36
    t = [(False, None, Fraction(15, 10), IN) for _ in range(40)]
    eps.append((hover, t))
    # (5) geofence pozycja == próg 1.8 (nie >) vs 1.81 (>)
    eps.append(((Fraction(3, 10), Fraction(0)),
                [(True, Fraction(3, 10), Fraction(4, 10), (Fraction(18, 10), Fraction(0))),   # ==1.8 nie geo
                 (True, Fraction(3, 10), Fraction(4, 10), (Fraction(181, 100), Fraction(0)))]))  # >1.8 geo
    return eps


def gen_alock():
    """NOWE (1): ścieżki czyszczące lock po `entered` (A-lock ZŁAMANE) — konformancja tau≡shield
    musi trzymać BEZWARUNKOWO (A-lock to założenie dowodu, nie funkcji przejścia). Pokrywa
    seek/nomatch 'w locie'."""
    IN = (Fraction(3, 10), Fraction(0)); hv = (Fraction(12, 10), Fraction(0))
    eps = []
    # (a) lock+admisja świeża, potem lock ZNIKA wcześnie (k<36) -> SEEKING w locie, później NO_MATCH
    t = [(True, Fraction(3, 10), Fraction(4, 10), IN)]              # admisja
    t += [(False, None, Fraction(4, 10), IN) for _ in range(45)]   # lock zniknął: seek -> nomatch@36
    eps.append((hv, t))
    # (b) lock, wejście STARE -> entry-HOLD, potem lock znika (REFUSE-in-flight ścieżka)
    t = [(True, Fraction(3), Fraction(4, 10), IN)]                  # stare -> HOLD
    t += [(False, None, Fraction(4, 10), IN) for _ in range(45)]
    eps.append((hv, t))
    # (c) lock miga: True/False naprzemiennie po entered (abort-like)
    t = [(True, Fraction(3, 10), Fraction(4, 10), IN)]
    t += [((k % 2 == 0), (Fraction(1, 3) if k % 2 == 0 else None), Fraction(4, 10), IN) for k in range(40)]
    eps.append((hv, t))
    return eps


def gen_offbyone():
    """NOWE (2): kontrprzykłady z biegu solvera odtworzone jako wektory — entry-hold do k−eh=36,
    ceiling do k−ch=36, latch po REFUSE (ehs≠⊥ przy tm=True)."""
    IN = (Fraction(3, 10), Fraction(0)); hv = (Fraction(12, 10), Fraction(0))
    eps = []
    # entry-hold: stare od wejścia (age>2), HOLD 4_hold do k−eh=36 -> 4_refuse, potem latch
    t = [(True, Fraction(3), Fraction(4, 10), IN) for _ in range(45)]
    eps.append((hv, t))
    # ceiling: admisja świeża, potem age=7 (>6) -> 5a_hold/5b_hold do k−ch=36 -> 5b_refuse, latch
    t = [(True, Fraction(3, 10), Fraction(4, 10), IN)]
    t += [(True, Fraction(7), Fraction(4, 10), IN) for _ in range(45)]
    eps.append((hv, t))
    return eps


def explicit_offbyone_asserts():
    """Bezpośrednie asercje na shield.py — regresja błędu niezmiennika (k−eh=35 HOLD / 36 REFUSE;
    ehs≠⊥ zostaje przy tm=True po REFUSE)."""
    sh = Shield(); sh.reset(hover_xy=(1.2, 0.0))
    # k=0 wejście stare -> HOLD, eh=0
    d = sh.step(0, (0.3, 0.0), True, 3.0, 0.02, 0.4)
    assert d["decision"] == HOLD and sh.entry_hold_start_k == 0, d
    last = None
    for k in range(1, 36):                                  # k−eh = 1..35 -> HOLD
        last = sh.step(k, (0.3, 0.0), True, 3.0, 0.02, 0.4)
        assert last["decision"] == HOLD, (k, last)          # k−eh=35 (k=35) wciąż HOLD
    d36 = sh.step(36, (0.3, 0.0), True, 3.0, 0.02, 0.4)     # k−eh=36 -> REFUSE(STALE)
    assert d36["decision"] == REFUSE and d36["reason"] == STALE_AT_DWELL, d36
    assert sh.entry_hold_start_k == 0 and sh.terminal is not None   # ehs≠⊥ ∧ tm=True
    d37 = sh.step(37, (0.3, 0.0), True, 3.0, 0.02, 0.4)     # latch
    assert d37["decision"] == REFUSE and d37["reason"] == STALE_AT_DWELL, d37
    return {"entry_hold_35_HOLD": True, "entry_hold_36_REFUSE": True, "latch_after_refuse": True,
            "ehs_set_while_terminal": True}


def test_tracker_alock_monotonic():
    """NOWE (1): A-lock na REALNYM kanale — Tracker5.has_lock jest MONOTONICZNY (raz True → True).
    Pokrywa założenie certyfikatu P1 testem, nie deklaracją."""
    try:
        from train.s3b2r import Tracker5, K_DEL  # noqa
    except Exception as e:
        return {"tested": False, "reason": f"import Tracker5 failed: {e}"}
    import random
    checked = 0
    for seed in range(50):
        rng = random.Random(seed)
        tr = Tracker5()
        was_lock = False
        for k in range(120):
            # dostarczenie ~1 Hz z dropoutem, box dowolny
            if k % 12 == 0 and rng.random() > 0.4:
                tr.observe(k, [rng.randint(0, 100), rng.randint(0, 100),
                               rng.randint(120, 200), rng.randint(120, 200)])
            v = tr.vector(k)
            has_lock = tr._cur is not None
            if was_lock and not has_lock:
                return {"tested": True, "monotonic": False, "seed": seed, "k": k}
            was_lock = was_lock or has_lock
            checked += 1
    return {"tested": True, "monotonic": True, "ticks_checked": checked}


def main():
    coverage = set(); mism = []
    n_rand = 300
    for seed in range(n_rand):
        run_episode(*gen_random(seed), coverage, mism)
    extra = gen_boundary() + gen_alock() + gen_offbyone()
    for hover, ticks in extra:
        run_episode(hover, ticks, coverage, mism)
    missing = [l for l in LEAVES if l not in coverage]
    # NOWE: asercje bezpośrednie + A-lock na kanale
    ob = explicit_offbyone_asserts()
    al = test_tracker_alock_monotonic()
    alock_ok = al.get("tested") and al.get("monotonic")

    ok = (not mism) and (not missing) and alock_ok
    print("=== P5 konformancja kod↔model ===")
    print(f"  rozbieżności tau≡shield: {len(mism)}  (epizody: {n_rand} losowych + {len(extra)} celowanych)")
    print(f"  pokrycie przejść: {len(coverage)}/15" + (f"  BRAK: {missing}" if missing else "  (pełne)"))
    print(f"  off-by-one regresja: {ob}")
    print(f"  A-lock (Tracker5 monotoniczny): {al}")
    if mism:
        print("  PIERWSZA ROZBIEŻNOŚĆ:", json.dumps(mism[0], ensure_ascii=False, default=str))
    print(f"WERDYKT P5: {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(1)
    cert = {"property": "P5", "verdict": "PASS",
            "method": "per-tick conformance: proven-model tau ≡ shield.py (decision+reason+state)",
            "z3_pip": "5.0.0.0", "z3_lib": z3.get_version_string(),
            "episodes_random": n_rand, "episodes_targeted": len(extra),
            "transitions_covered": sorted(coverage), "coverage": f"{len(coverage)}/15",
            "mismatches": 0, "boundary_thresholds_ticks": [24, 36, 72],
            "alock_property_tested": al, "offbyone_regression": ob,
            "adversarial_alock_violating_paths": len(gen_alock()),
            "binds": "P1 (proofs/certs/P1.json) — dowód dotyczy kodu, nie fikcji; A-lock pokryty testem",
            "model_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (model_sha256={cert['model_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
