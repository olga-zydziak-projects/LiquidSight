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
`k' = k+1`, oraz **założenie środowiskowe A-lock (monotoniczność locka):** `entered ⇒ has_lock`
(kanał `Tracker5`: po pierwszym dostarczeniu `has_lock` już nie wraca do fałszu — RECON/faza 3d;
`entered` powstaje wyłącznie przy `has_lock`, więc raz osiągnięte implikuje trwały lock). Bez A-lock
model dopuszczałby nierealny stan `entered ∧ ¬has_lock` (przejście do SEEKING bez reset flag) łamiący
I5 — A-lock jest jawnym, prawdziwym w systemie założeniem, wypisanym w certyfikacie.

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
- **I8 (dostarczenie ⇒ admisja; pomocniczy do P1(a)):** `(entered ∧ ¬admitted ∧ ¬term) ⇒
  (state = DWELL_GUARD ∧ eh ≠ ⊥)`. Znaczenie: między wejściem w martwe pole a admisją osłona
  **HOLD-uje, nigdy nie ALLOW** — więc każde ALLOW w dwell (konsumpcja dostarczenia) implikuje
  admisję. Dowodzony w tej SAMEJ indukcji; kompozycja z §6-P1(a) daje twierdzenie **bezwarunkowe**.

## 6. Predykaty własności P1(a)–(d) (na wyjściu `τ`, gdy `Inv(c)` ∧ `valid`)
- **P1(b) geofence ⇒ REFUSE (WZMOCNIONE):** `(geo_t ∨ geo_p) ⇒ decision = REFUSE` (zawsze REFUSE —
  świeże naruszenie przez R-C, stan terminalny przez latch; oba REFUSE) **∧** `(¬term ∧ (geo_t ∨
  geo_p)) ⇒ reason' = GEOFENCE`. *Wzmocnione względem pierwotnego „∈{HOLD,REFUSE}"; PRE §3
  zaktualizowane.*
- **P1(c) REFUSE ma powód:** `decision = REFUSE ⇒ reason' ∈ {NO_MATCH, STALE, GEOFENCE}` (niepusty,
  wyliczony).
- **P1(a) sufit nie przekroczony po cichu (BEZWARUNKOWE, kompozycja z I8):**
  `(decision = ALLOW ∧ has_lock ∧ entered') ⇒ age ≤ ceiling`. Predykat o KAŻDYM ALLOW konsumującym
  kanał w dwell (`entered'`), **bez warunku `admitted` w treści** — I8 rozładowuje admisję
  (`entered ∧ ALLOW ⇒ admitted`, bo `entered ∧ ¬admitted ⇒ HOLD`). Faza DOLOTU (`entered' = F`,
  `dist ≥ near`) poza zakresem przez `entered'`, nie przez ukryty warunek — kompetentny „ślepy
  finisz" (RAPORT_3C_MVP §3).
- **P1(d) HOLD ograniczony (nierówność z kodu):** `¬(eh ≠ ⊥ ∧ k − eh ≥ 36 ∧ ¬term) ∧
  ¬(ch ≠ ⊥ ∧ k − ch ≥ 36 ∧ ¬term)`. Stała **36 = T_hold/dt**: `shield.py:30` (`t_hold_s=3.0`,
  `dt=1/12`); nierówność `(k−start)·dt ≥ t_hold` przepisana z `shield.py:112` (wejście) i `:131`
  (sufit) jako `k−start ≥ 36`. Żaden żywy HOLD nie trwa ≥ 36 tików; przy `k−start = 36` REFUSE.
  Wynika z I4/I5 (bound ≤ 35), utrzymanych indukcyjnie.

## 7. Zobowiązania dowodowe (1-indukcja) dla z3
- **BAZA:** `Inv(c0)`.
- **KROK:** `∀ c, input: Inv(c) ∧ valid(input) ⇒ Inv(τ.c') ∧ P1(a) ∧ P1(b) ∧ P1(c) ∧ P1(d)`.
  z3 sprawdza NEGACJĘ: `Inv(c) ∧ valid ∧ (¬Inv(c') ∨ ¬P1x)` → oczekiwane **UNSAT** (własność trzyma).
  SAT = kontrprzykład (trasa) → poprawa Inv lub eskalacja (zasada 6: UNPROVEN, nie zmiękczanie).
- **Odtwarzalność (zasada 3):** `python -m proofs.verify` buduje model od zera, uruchamia z3
  (wersja `z3-solver==5.0.0.0`, lib 5.0.0 — do certyfikatu), zwraca UNSAT + hash modelu; certyfikat
  w `proofs/certs/P1.json` z hashem, porównywany w CI lokalnym.

## 8. Status ratyfikacji (2026-08-03)
**RATYFIKOWANE** (człowiek) — wszystkie 4 brzmienia, z dwiema dokładkami (naniesione):
1. **P1(a)** → dołożony niezmiennik pomocniczy **I8 „dostarczenie ⇒ admisja"** dowodzony w tej
   samej indukcji; kompozycja daje **twierdzenie bezwarunkowe** (§5-I8, §6-P1a).
2. **P1(b)** → wersja silniejsza (czyste REFUSE) z adnotacją „wzmocnione" (§6-P1b, PRE_DP0 §3).
3. **P1(d)** → stała 36 z cytatem `shield.py:30/112/131`, nierówność przepisana z kodu (§6-P1d);
   cytat trafia do certyfikatu.
4. Age/dist Real dokładny, czas Int (progi 24/36/72) — zero floatów.
**Backlog P5 (obowiązkowy):** przypadki brzegowe dokładnie na progach **24 / 36 / 72 tików**
(θ_age/dt=24, T_hold=36, ceiling/dt=72) — granica float-sekundy (`age > θ`) vs int-tiki
(`k−start ≥ 36`); konformancja pokrywa próg i ±1 tik / ±ε age.

*Formalizacja ratyfikowana. Następny krok: `proofs/verify.py` (model z3), bieg solvera, certyfikat
`proofs/certs/P1.json` z hashem, wersją z3 i cytatami linii.*
