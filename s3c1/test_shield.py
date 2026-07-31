"""Testy jednostkowe reguł osłony (syntetyczne przebiegi, bez env/polityki).

Uruchom: .venv/bin/python -m s3c1.test_shield
R-B v2 (S3c1-R): admisja NA WEJŚCIU (jednorazowa) + sufit twardy 6.0 s.
dt=1/12 s, θ_age=2.0 s, T_acq=T_hold=3.0 s (36 kroków), sufit=6.0 s.
"""
from s3c1.shield import (Shield, ALLOW, HOLD, REFUSE, SEEKING, TRACKING,
                         NO_MATCH, STALE_AT_DWELL, GEOFENCE)

DT = 1.0 / 12.0
FAR = (0.0, 0.0)


def _sh():
    s = Shield(); s.reset(hover_xy=(1.2, 0.3)); return s


# ---- reguły niezmienione (R-A/R-D no-match, R-C geofence) -------------------
def test_no_match():
    s = _sh()
    for k in range(0, 36):
        d = s.step(k, FAR, has_lock=False, age_s=None, conf=None, dist_to_hover=1.5)
        assert d["decision"] == ALLOW and d["state"] == SEEKING, (k, d)
    d = s.step(36, FAR, has_lock=False, age_s=None, conf=None, dist_to_hover=1.5)
    assert d["decision"] == REFUSE and d["reason"] == NO_MATCH, d
    assert s.outcome(False, "no_arrival", False)["wynik"] == "ODMOWA"
    print("OK test_no_match: REFUSE(NO_MATCH) @ k=36 (3.0 s)")


def test_geofence_target():
    s = Shield(); s.reset(hover_xy=(1.95, 0.1))
    d = s.step(0, (-1.0, 0.0), has_lock=False, age_s=None, conf=None, dist_to_hover=2.9)
    assert d["decision"] == REFUSE and d["reason"] == GEOFENCE, d
    print("OK test_geofence_target: REFUSE(GEOFENCE) @ k=0 (cel 1.95 > 1.8)")


def test_geofence_trajectory():
    s = _sh()
    assert s.step(10, (1.0, 0.0), True, 0.3, 0.04, 0.6)["decision"] == ALLOW
    d = s.step(11, (1.85, 0.0), True, 0.3, 0.04, 0.6)
    assert d["decision"] == REFUSE and d["reason"] == GEOFENCE, d
    print("OK test_geofence_trajectory: REFUSE(GEOFENCE) gdy pozycja 1.85 > 1.8")


# ---- R-B v2: cztery przypadki z mandatu -----------------------------------
def test_entry_fresh_no_hold():
    """Wejście z age 0.3 -> admisja OK; dwell kończy się przy age 2.3 BEZ hold."""
    s = _sh()
    d = s.step(10, (1.2, 0.3), True, 0.3, 0.03, 0.4)          # pierwsze przekroczenie <0.5
    assert d["decision"] == ALLOW and s.admitted, d
    last = None
    for k in range(11, 35):                                    # age rośnie 0.3 -> ~2.3
        age = 0.3 + (k - 10) * DT
        last = s.step(k, (1.2, 0.3), True, age, 0.03, 0.2)
        assert last["decision"] == ALLOW, (k, age, last)       # >2.0 ale <6.0 sufit -> ALLOW
    assert s.n_hold_enter == 0 and last["values"]["age_s"] >= 2.2, (s.n_hold_enter, last)
    assert s.outcome(True, None, False)["wynik"] == "SUKCES"
    print(f"OK test_entry_fresh_no_hold: admisja@age0.3, dwell do age {last['values']['age_s']} bez HOLD -> SUKCES")


def test_entry_stale_hold_then_readmit():
    """Wejście z age 2.5 -> HOLD -> świeży tick -> re-admisja -> sukces."""
    s = _sh()
    d = s.step(10, (1.2, 0.3), True, 2.5, 0.02, 0.4)
    assert d["decision"] == HOLD and not s.admitted, d
    for k in range(11, 16):
        assert s.step(k, (1.2, 0.3), True, 2.5 + (k - 10) * DT, 0.02, 0.4)["decision"] == HOLD
    d = s.step(16, (1.2, 0.3), True, 0.2, 0.05, 0.4)           # świeży tick
    assert d["decision"] == ALLOW and s.admitted, d
    # po admisji dwell biegnie swobodnie mimo age>2.0
    assert s.step(20, (1.2, 0.3), True, 2.4, 0.05, 0.3)["decision"] == ALLOW
    assert s.n_hold_enter == 1 and s.n_hold_release == 1, (s.n_hold_enter, s.n_hold_release)
    assert s.outcome(True, None, False)["wynik"] == "SUKCES"
    print("OK test_entry_stale_hold_then_readmit: HOLD -> świeży tick -> admisja -> SUKCES")


def test_entry_stale_hold_then_timeout():
    """Wejście z age 2.5 -> HOLD -> brak odświeżenia przez T_hold -> REFUSE."""
    s = _sh()
    assert s.step(10, (1.2, 0.3), True, 2.5, 0.02, 0.4)["decision"] == HOLD
    last = None
    for k in range(11, 47):                                    # 10+36=46 -> timeout
        last = s.step(k, (1.2, 0.3), True, 2.5 + (k - 10) * DT, 0.02, 0.4)
    assert last["decision"] == REFUSE and last["reason"] == STALE_AT_DWELL, last
    assert s.outcome(False, "dwell", False)["wynik"] == "ODMOWA"
    print(f"OK test_entry_stale_hold_then_timeout: REFUSE(STALE) @ k={last['k']} (admisja wejścia)")


def test_ceiling_starvation_refuse():
    """Admisja OK, potem zagłodzenie do age 6.1 -> sufit twardy -> REFUSE."""
    s = _sh()
    assert s.step(10, (1.2, 0.3), True, 0.3, 0.03, 0.4)["decision"] == ALLOW  # admisja
    # age rośnie; sufit 6.0 przekroczony gdy age>6.0
    last = None; hit_ceiling_k = None
    for k in range(11, 120):
        age = 0.3 + (k - 10) * DT
        last = s.step(k, (1.2, 0.3), True, age, 0.02, 0.3)
        if age > 6.0 and hit_ceiling_k is None:
            hit_ceiling_k = k
            assert last["decision"] == HOLD, (k, age, last)    # pierwszy raz >6 -> HOLD
        if last["decision"] == REFUSE:
            break
    assert last["decision"] == REFUSE and last["reason"] == STALE_AT_DWELL, last
    assert (last["k"] - hit_ceiling_k) * DT >= 3.0 - 1e-6
    print(f"OK test_ceiling_starvation_refuse: sufit@age>6 (k={hit_ceiling_k}) -> REFUSE @ k={last['k']}")


def test_clean_base_transparent():
    """Wejście świeże, dwell przy świeżym kanale -> 0 HOLD, transparentna."""
    s = _sh()
    for k in range(0, 120):
        dist = 1.5 if k < 60 else 0.2
        age = min((k % 12) * DT + 0.2, 1.3)                    # kanał świeży
        d = s.step(k, (0.5, 0.0), has_lock=(k >= 2), age_s=(age if k >= 2 else None),
                   conf=0.03, dist_to_hover=dist)
        assert d["decision"] == ALLOW, (k, d)
    assert s.n_hold_enter == 0
    print("OK test_clean_base_transparent: świeży kanał -> 0 HOLD (transparentna)")


if __name__ == "__main__":
    tests = [test_no_match, test_geofence_target, test_geofence_trajectory,
             test_entry_fresh_no_hold, test_entry_stale_hold_then_readmit,
             test_entry_stale_hold_then_timeout, test_ceiling_starvation_refuse,
             test_clean_base_transparent]
    for t in tests:
        t()
    print(f"\n=== {len(tests)}/{len(tests)} testów PASS (R-B v2) ===")
