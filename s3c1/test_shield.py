"""Testy jednostkowe reguł osłony (syntetyczne przebiegi, bez env/polityki).

Uruchom: .venv/bin/python -m s3c1.test_shield
Każdy test buduje ręcznie sekwencję sygnałów (k, pos, has_lock, age_s, conf, dist)
i sprawdza decyzje/wynik. dt=1/12 s, T_acq=T_hold=3.0 s (36 kroków), theta_age=2.0 s.
"""
from s3c1.shield import (Shield, ALLOW, HOLD, REFUSE, SEEKING, TRACKING, DWELL_GUARD,
                         NO_MATCH, STALE_AT_DWELL, GEOFENCE)

DT = 1.0 / 12.0
FAR = (0.0, 0.0)     # pozycja w środku areny (geofence nie odpala)


def _sh():
    s = Shield(); s.reset(hover_xy=(1.2, 0.3)); return s


def test_no_match():
    """Brak locka przez cały czas -> REFUSE(NO_MATCH) dokładnie przy t=T_acq."""
    s = _sh()
    for k in range(0, 36):
        d = s.step(k, FAR, has_lock=False, age_s=None, conf=None, dist_to_hover=1.5)
        assert d["decision"] == ALLOW and d["state"] == SEEKING, (k, d)
    d = s.step(36, FAR, has_lock=False, age_s=None, conf=None, dist_to_hover=1.5)
    assert d["decision"] == REFUSE and d["reason"] == NO_MATCH, d
    out = s.outcome(env_success=False, env_fail_type="no_arrival", wrong_action=False)
    assert out["wynik"] == "ODMOWA" and out["refuse_reason"] == NO_MATCH, out
    print("OK test_no_match: REFUSE(NO_MATCH) @ k=36 (3.0 s)")


def test_tracking_allow():
    """Lock świeży, dron daleko -> ALLOW przez cały epizod (osłona transparentna)."""
    s = _sh()
    for k in range(0, 120):
        age = min((k % 12) * DT, 1.0)               # świeży kanał (<1 s), resety co tick
        d = s.step(k, FAR, has_lock=True, age_s=age, conf=0.03, dist_to_hover=0.8)
        assert d["decision"] == ALLOW and d["state"] == TRACKING, (k, d)
    out = s.outcome(env_success=True, env_fail_type=None, wrong_action=False)
    assert out["wynik"] == "SUKCES" and out["n_hold_enter"] == 0, out
    print("OK test_tracking_allow: ALLOW/TRACKING caly epizod, 0 HOLD -> SUKCES")


def test_dwell_hold_then_release():
    """Martwe pole + stary kanał -> HOLD; świeży tick -> powrót ALLOW."""
    s = _sh()
    # wejście w martwe pole ze starzejącym się kanałem
    d = s.step(40, (1.2, 0.3), has_lock=True, age_s=2.5, conf=0.02, dist_to_hover=0.3)
    assert d["decision"] == HOLD and d["state"] == DWELL_GUARD, d
    for k in range(41, 50):                          # trzyma (age rośnie, ale < T_hold)
        d = s.step(k, (1.2, 0.3), has_lock=True, age_s=2.5 + (k - 40) * DT, conf=0.02, dist_to_hover=0.3)
        assert d["decision"] == HOLD, (k, d)
    # świeży tick: age spada <= theta -> ALLOW
    d = s.step(50, (1.2, 0.3), has_lock=True, age_s=0.2, conf=0.05, dist_to_hover=0.3)
    assert d["decision"] == ALLOW and d["state"] == TRACKING, d
    assert s.n_hold_enter == 1 and s.n_hold_release == 1, (s.n_hold_enter, s.n_hold_release)
    print("OK test_dwell_hold_then_release: HOLD -> odswiezenie -> ALLOW (enter=1, release=1)")


def test_dwell_hold_then_stale_refuse():
    """Martwe pole + kanał nie odświeża się przez T_hold -> REFUSE(STALE_AT_DWELL)."""
    s = _sh()
    d = s.step(40, (1.2, 0.3), has_lock=True, age_s=2.5, conf=0.02, dist_to_hover=0.3)
    assert d["decision"] == HOLD, d
    # 36 kroków HOLD (3.0 s) bez odświeżenia -> timeout na kroku 40+36=76
    last = None
    for k in range(41, 77):
        last = s.step(k, (1.2, 0.3), has_lock=True, age_s=2.5 + (k - 40) * DT,
                      conf=0.02, dist_to_hover=0.3)
    assert last["decision"] == REFUSE and last["reason"] == STALE_AT_DWELL, last
    out = s.outcome(env_success=False, env_fail_type="dwell", wrong_action=False)
    assert out["wynik"] == "ODMOWA" and out["refuse_reason"] == STALE_AT_DWELL, out
    print(f"OK test_dwell_hold_then_stale_refuse: REFUSE(STALE_AT_DWELL) @ k={last['k']} (~3.0 s HOLD)")


def test_geofence_target():
    """Cel poza (arena_half - margines)=1.8 -> REFUSE(GEOFENCE) natychmiast (k=0)."""
    s = Shield(); s.reset(hover_xy=(1.95, 0.1))
    d = s.step(0, (-1.0, 0.0), has_lock=False, age_s=None, conf=None, dist_to_hover=2.9)
    assert d["decision"] == REFUSE and d["reason"] == GEOFENCE, d
    out = s.outcome(env_success=False, env_fail_type=None, wrong_action=False)
    assert out["wynik"] == "ODMOWA" and out["refuse_rule"] == "R-C", out
    print("OK test_geofence_target: REFUSE(GEOFENCE) @ k=0 (cel 1.95 > 1.8)")


def test_geofence_trajectory():
    """Pozycja drona wychodzi poza 1.8 w locie -> REFUSE(GEOFENCE)."""
    s = _sh()
    d = s.step(10, (1.0, 0.0), has_lock=True, age_s=0.3, conf=0.04, dist_to_hover=0.5)
    assert d["decision"] == ALLOW, d
    d = s.step(11, (1.85, 0.0), has_lock=True, age_s=0.3, conf=0.04, dist_to_hover=0.6)
    assert d["decision"] == REFUSE and d["reason"] == GEOFENCE, d
    print("OK test_geofence_trajectory: REFUSE(GEOFENCE) gdy pozycja 1.85 > 1.8")


def test_clean_base_dormant():
    """Dron dolatuje w martwe pole, ale kanał świeży (<2 s) -> nigdy HOLD (R-B uśpiona)."""
    s = _sh()
    for k in range(0, 120):
        dist = 1.5 if k < 60 else 0.2               # po 60 w martwym polu
        age = min((k % 12) * DT + 0.2, 1.3)         # kanał świeży (< theta_age=2.0)
        d = s.step(k, (0.5, 0.0), has_lock=(k >= 2), age_s=age, conf=0.03, dist_to_hover=dist)
        assert d["decision"] == ALLOW, (k, d)
    assert s.n_hold_enter == 0, s.n_hold_enter
    print("OK test_clean_base_dormant: martwe pole + kanal swiezy -> 0 HOLD (uspiona)")


if __name__ == "__main__":
    tests = [test_no_match, test_tracking_allow, test_dwell_hold_then_release,
             test_dwell_hold_then_stale_refuse, test_geofence_target,
             test_geofence_trajectory, test_clean_base_dormant]
    for t in tests:
        t()
    print(f"\n=== {len(tests)}/{len(tests)} testów PASS ===")
