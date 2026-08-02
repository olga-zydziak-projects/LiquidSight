# P1 — formalizacja automatu osłony (moduł 1 DP; DO RATYFIKACJI przed solverem)

**Data:** 2026-08-03. **Obiekt:** `s3c1/shield.py` (osłona v2 S3c1-R), read-only. **Cel:** model
tranzycyjny osłony jako obiekt indukcji z3 + predykaty P1(a)–(d) + niezmiennik indukcyjny. **Solver
NIE był odpalany** — ten dokument jest do ODRĘBNEJ ratyfikacji (PRE_DP0 F-D3). Stałe wyłącznie jako
ułamki wymierne (zero floatów).

---

## 1. Stałe (dokładne, z `shield.py:29-37` / DECYZJE_3C)
`θ_age = 2`, `ceiling = 6`, `near = 1/2`, `geo_lim = arena_half − margin = 2 − 1/5 = 9/5`,
`dt = 1/12`, `t_acq = t_hold = 3`. **Progi czasu w tikach:** `t_acq/dt = 36`, `t_hold/dt = 36`
(dokładnie, bo `3/(1/12)=36`). Czas występuje w modelu **wyłącznie** jako porównania całkowite
`k ≥ 36`, `k − eh ≥ 36`, `k − ch ≥ 36` — więc age/dist trzymamy jako Real dokładny, czas jako Int.

## 2. Zmienne stanu (konfiguracja `c`), z `shield.reset` + `_decide`
| zmienna | typ | znaczenie |
|---|---|---|
| `state` | enum {SEEKING, TRACKING, DWELL_GUARD, DONE} | stan automatu |
| `entered` | Bool | przekroczono `dist<near` choć raz |
| `admitted` | Bool | admisja dwell przyznana |
| `eh` | Int⊎{⊥} | `entry_hold_start_k` (⊥ = None) |
| `ch` | Int⊎{⊥} | `ceiling_hold_start_k` |
| `term` | Bool | `terminal ≠ None` (REFUSE zatrzasnięty) |
| `reason` | enum {NONE, NO_MATCH, STALE, GEOFENCE} | powód terminala |
| `k` | Int ≥ 0 | numer tiku (czas = k·dt) |

Konfiguracja startowa `c0` (`reset`): `SEEKING, entered=⊥F, admitted=F, eh=⊥, ch=⊥, term=F,
reason=NONE, k=0`.

## 3. Wejście per tik (dowolne, z ograniczeniem `valid`)
`has_lock: Bool`, `age: Real` (istotne gdy has_lock; `age ≥ 0`), `dist: Real ≥ 0`,
`geo_t: Bool` (= `max(|hover_x|,|hover_y|) > geo_lim`, stałe w epizodzie),
`geo_p: Bool` (= `max(|pos_x|,|pos_y|) > geo_lim`). Predykaty pomocnicze:
`old = has_lock ∧ age > θ_age`, `over = has_lock ∧ age > ceiling`. `valid`: `age ≥ 0 ∧ dist ≥ 0`,
`k' = k+1`.

## 4. Relacja przejścia `τ(c, input) → (c', decision, reason')` — LUSTRO `_decide` (`shield.py:65-136`)
Kolejność warunków (priorytet), decyzja ∈ {ALLOW, HOLD, REFUSE}:

```
0. term:                         → (DONE, REFUSE, reason)                     [latch, :66-68]
1. geo_t ∨ geo_p:  term:=T; reason:=GEOFENCE; state:=DONE
                                 → (REFUSE, GEOFENCE)                          [:70-78]
2. ¬has_lock: state:=SEEKING
     k ≥ 36:  term:=T; reason:=NO_MATCH; state:=DONE → (REFUSE, NO_MATCH)      [:83-86]
     else:                                            → (ALLOW, —)             [:87]
3. has_lock ∧ ¬entered:
     dist < near:  entered:=T
        old:   eh:=k; state:=DWELL_GUARD             → (HOLD, —)               [:95-99]
        ¬old:  admitted:=T; state:=TRACKING          → (ALLOW, —)              [:100-102]
     dist ≥ near: state:=TRACKING                    → (ALLOW, —)              [:103-104]
4. has_lock ∧ entered ∧ ¬admitted:                                            [:106-117]
     ¬old:  admitted:=T; eh:=⊥; state:=TRACKING      → (ALLOW, —)
     (k−eh) ≥ 36:  term:=T; reason:=STALE; state:=DONE → (REFUSE, STALE)
     else:  state:=DWELL_GUARD                        → (HOLD, —)
5. has_lock ∧ admitted:                                                       [:118-136]
     ch=⊥:
        over:  ch:=k; state:=DWELL_GUARD             → (HOLD, —)
        ¬over: state:=TRACKING                        → (ALLOW, —)
     ch≠⊥:
        ¬over: ch:=⊥; state:=TRACKING                → (ALLOW, —)
        (k−ch) ≥ 36:  term:=T; reason:=STALE; state:=DONE → (REFUSE, STALE)
        else:  state:=DWELL_GUARD                     → (HOLD, —)
```

## 5. Niezmiennik indukcyjny `Inv(c)` (kandydat)
- **I1** `term ⇒ (reason ≠ NONE ∧ state = DONE)`
- **I2** `state = DONE ⇔ term`
- **I3** `admitted ⇒ entered`
- **I4** `eh ≠ ⊥ ⇒ (entered ∧ ¬admitted ∧ ¬term ∧ state = DWELL_GUARD ∧ 0 ≤ k − eh ≤ 35)`
- **I5** `ch ≠ ⊥ ⇒ (admitted ∧ ¬term ∧ state = DWELL_GUARD ∧ 0 ≤ k − ch ≤ 35)`
- **I6** `¬(eh ≠ ⊥ ∧ ch ≠ ⊥)`  (hold wejścia i hold sufitu nigdy naraz)
- **I7** `(eh ≠ ⊥ ⇒ 0 ≤ eh ≤ k) ∧ (ch ≠ ⊥ ⇒ 0 ≤ ch ≤ k)`

## 6. Predykaty własności P1(a)–(d) (na wyjściu `τ`, gdy `Inv(c)` ∧ `valid`)
- **P1(b) geofence w tym samym tiku:** `(geo_t ∨ geo_p) ⇒ decision = REFUSE ∧ reason' = GEOFENCE`.
  *(Wzmocnienie względem brzmienia PRE „∈{HOLD,REFUSE}": kod daje ZAWSZE REFUSE — dowodzimy
  silniejsze, co spełnia dysjunkcję. Odnotowane jawnie.)*
- **P1(c) REFUSE ma powód:** `decision = REFUSE ⇒ reason' ∈ {NO_MATCH, STALE, GEOFENCE}` (niepusty,
  wyliczony).
- **P1(a) sufit nie przekroczony po cichu:** `(decision = ALLOW ∧ has_lock ∧ admitted') ⇒ age ≤ ceiling`.
  *(ZAKRES: `admitted'` = po admisji. Faza DOLOTU przed admisją (`3: dist ≥ near`) legalnie ALLOW
  przy dowolnym age — to kompetentny „ślepy finisz" (RAPORT_3C_MVP §3), świadomie POZA P1(a).
  Brzmienie zakresu do ratyfikacji.)*
- **P1(d) HOLD ograniczony:** `¬(eh ≠ ⊥ ∧ k − eh ≥ 36 ∧ ¬term) ∧ ¬(ch ≠ ⊥ ∧ k − ch ≥ 36 ∧ ¬term)`
  — żaden żywy HOLD nie trwa ≥ 36 tików (= T_hold); przy k−start = 36 wymuszony REFUSE. Wynika z
  I4/I5 utrzymanych indukcyjnie (bound ≤ 35 w stanie żywym).

## 7. Zobowiązania dowodowe (1-indukcja) dla z3
- **BAZA:** `Inv(c0)`.
- **KROK:** `∀ c, input: Inv(c) ∧ valid(input) ⇒ Inv(τ.c') ∧ P1(a) ∧ P1(b) ∧ P1(c) ∧ P1(d)`.
  z3 sprawdza NEGACJĘ: `Inv(c) ∧ valid ∧ (¬Inv(c') ∨ ¬P1x)` → oczekiwane **UNSAT** (własność trzyma).
  SAT = kontrprzykład (trasa) → poprawa Inv lub eskalacja (zasada 6: UNPROVEN, nie zmiękczanie).
- **Odtwarzalność (zasada 3):** `python -m proofs.verify` buduje model od zera, uruchamia z3
  (wersja `z3-solver==5.0.0.0`, lib 5.0.0 — do certyfikatu), zwraca UNSAT + hash modelu; certyfikat
  w `proofs/certs/P1.json` z hashem, porównywany w CI lokalnym.

## 8. Uwagi do ratyfikacji (brzmienia)
1. **P1(b)** dowodzony jako REFUSE (silniejszy niż PRE {HOLD,REFUSE}) — OK?
2. **P1(a)** ma zakres „po admisji"; faza dolotu (ślepy finisz) świadomie wyłączona — brzmienie OK?
3. **P1(d)** jako „żywy HOLD < 36 tików = T_hold" (bounded), nie pełna liveness temporalna — OK?
4. Age/dist jako **Real dokładny**, czas jako **Int** (progi 36) — zero floatów. OK?
5. Niezmiennik I1–I7 — czy wystarczający/za mocny? (z3 rozstrzygnie po ratyfikacji; jeśli za słaby →
   kontrprzykład, wzmacniamy; jeśli sprzeczny → SAT bazy, korygujemy.)

*Formalizacja gotowa. Solver NIE odpalony. Czeka na ratyfikację „jednym słowem" (PRE_DP0).*
