"""s3c1/shield.py — osłona MVP jako CZYSTY WRAPPER (maszyna stanów per epizod).

Zero zmian w polityce/kanale/env/percepcji. Osłona konsumuje sygnały wyjściowe
(pozycja drona, wiek locka z kanału, conf z groundera, dystans do celu) i zwraca
decyzję ALLOW / HOLD / REFUSE(reason) — deterministycznie (reguła + wartość + próg).

Reguły (DECYZJE_3C, PRE_3C0 §2):
  R-A/R-D  SEEKING: brak locka przez T_acq -> REFUSE(NO_MATCH). Bez progu conf (D1).
  R-B      DWELL-GUARD: dystans < NEAR i age_s > theta_age -> HOLD; świeży tick w
           T_hold -> ALLOW; timeout -> REFUSE(STALE_AT_DWELL).
  R-C      GEOFENCE: cel lub pozycja poza (arena_half - margines) -> REFUSE(GEOFENCE),
           w każdym stanie.
HOLD = position-hold przez egzekutor v1.0 (setpoint = [pozycja bieżąca, prędkość 0]);
realizowany przez harness (osłona sygnalizuje HOLD, harness podmienia akcję).

conf jest logowany per tick, ale NIE bramkuje (D1: ROC płaska, AUC 0.6496).
"""
from __future__ import annotations

ALLOW, HOLD, REFUSE = "ALLOW", "HOLD", "REFUSE"
# stany
SEEKING, TRACKING, DWELL_GUARD, DONE = "SEEKING", "TRACKING", "DWELL-GUARD", "DONE"
# powody
NO_MATCH, STALE_AT_DWELL, GEOFENCE, LOW_CONF_LOCK = \
    "NO_MATCH", "STALE_AT_DWELL", "GEOFENCE", "LOW_CONF_LOCK"


class Shield:
    def __init__(self, arena_half=2.0, margin=0.2, near=0.5, theta_age_s=2.0,
                 t_acq_s=3.0, t_hold_s=3.0, dt=1.0 / 12.0):
        self.geo_lim = arena_half - margin           # 1.8 m
        self.near = near
        self.theta_age_s = theta_age_s
        self.t_acq_s = t_acq_s
        self.t_hold_s = t_hold_s
        self.dt = dt

    def reset(self, hover_xy):
        """hover_xy: (x, y) celu misji (do bramki geofence celu)."""
        self.hover = (float(hover_xy[0]), float(hover_xy[1]))
        self.state = SEEKING
        self.terminal = None            # (reason, rule) po REFUSE
        self.hold_start_k = None
        self.n_hold_enter = 0
        self.n_hold_release = 0
        self.trace = []                 # log decyzji per tick (pod overlay dema)

    # -- pojedynczy krok polityki -------------------------------------------
    def step(self, k, pos, has_lock, age_s, conf, dist_to_hover):
        d = self._decide(k, pos, has_lock, age_s, dist_to_hover)
        d["t"] = round(k * self.dt, 4)
        d["values"] = {"dist": round(float(dist_to_hover), 3),
                       "age_s": (round(float(age_s), 3) if age_s is not None else None),
                       "conf": (round(float(conf), 4) if conf is not None else None),
                       "pos": [round(float(pos[0]), 3), round(float(pos[1]), 3)],
                       "has_lock": bool(has_lock)}
        self.trace.append(d)
        return d

    def _decide(self, k, pos, has_lock, age_s, dist):
        if self.terminal is not None:
            r, rule = self.terminal
            return {"k": k, "state": DONE, "decision": REFUSE, "reason": r, "rule": rule}

        # R-C geofence (każdy stan, najwyższy priorytet)
        if max(abs(self.hover[0]), abs(self.hover[1])) > self.geo_lim:
            self.terminal = (GEOFENCE, "R-C"); self.state = DONE
            return {"k": k, "state": DONE, "decision": REFUSE, "reason": GEOFENCE,
                    "rule": "R-C", "detail": "cel poza geofence"}
        if max(abs(float(pos[0])), abs(float(pos[1]))) > self.geo_lim:
            self.terminal = (GEOFENCE, "R-C"); self.state = DONE
            return {"k": k, "state": DONE, "decision": REFUSE, "reason": GEOFENCE,
                    "rule": "R-C", "detail": "trajektoria poza geofence"}

        # R-A/R-D no-match: brak locka przez T_acq
        if not has_lock:
            self.state = SEEKING
            if k * self.dt >= self.t_acq_s:
                self.terminal = (NO_MATCH, "R-A"); self.state = DONE
                return {"k": k, "state": DONE, "decision": REFUSE, "reason": NO_MATCH,
                        "rule": "R-A"}
            return {"k": k, "state": SEEKING, "decision": ALLOW, "reason": None, "rule": None}

        # lock aktywny — R-B dwell-guard
        guard = (dist < self.near) and (age_s is not None and age_s > self.theta_age_s)
        if self.hold_start_k is not None:            # jesteśmy w HOLD
            if not guard:                            # świeży tick lub wyjście z martwego pola
                self.hold_start_k = None; self.n_hold_release += 1
                self.state = TRACKING
                return {"k": k, "state": TRACKING, "decision": ALLOW, "reason": None,
                        "rule": "R-B", "detail": "HOLD zwolniony (kanał odświeżony)"}
            if (k - self.hold_start_k) * self.dt >= self.t_hold_s:
                self.terminal = (STALE_AT_DWELL, "R-B"); self.state = DONE
                return {"k": k, "state": DONE, "decision": REFUSE, "reason": STALE_AT_DWELL,
                        "rule": "R-B"}
            self.state = DWELL_GUARD
            return {"k": k, "state": DWELL_GUARD, "decision": HOLD, "reason": None, "rule": "R-B"}
        else:
            if guard:
                self.hold_start_k = k; self.n_hold_enter += 1; self.state = DWELL_GUARD
                return {"k": k, "state": DWELL_GUARD, "decision": HOLD, "reason": None,
                        "rule": "R-B", "detail": "wejście HOLD (martwe pole + stary kanał)"}
            self.state = TRACKING
            return {"k": k, "state": TRACKING, "decision": ALLOW, "reason": None, "rule": None}

    # -- podsumowanie epizodu -----------------------------------------------
    def outcome(self, env_success, env_fail_type, wrong_action):
        """Rozstrzyga wynik trójwynikowy epizodu (D4). Assert jednoznaczności."""
        refused = self.terminal is not None
        if refused:
            res = "ODMOWA"
        elif wrong_action:
            res = "PORAZKA"           # wrong-action = porażka I klasy
        elif env_success:
            res = "SUKCES"
        else:
            res = "PORAZKA"           # dryf/dwell/no-arrival/katastrofa bez odmowy
        # jednoznaczność (D4): dokładnie jedna z trzech klas; odmowa nigdy nie jest sukcesem
        assert res in ("SUKCES", "ODMOWA", "PORAZKA")
        assert (res == "ODMOWA") == refused, "odmowa <=> osłona zatrzymała misję (bez podwójnego liczenia)"
        return {"wynik": res,
                "refuse_reason": (self.terminal[0] if refused else None),
                "refuse_rule": (self.terminal[1] if refused else None),
                "n_hold_enter": self.n_hold_enter, "n_hold_release": self.n_hold_release}
