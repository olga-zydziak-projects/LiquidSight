# ANEKS-3B-3 do DECYZJE_3B — precyzja kanału i budżet (2026-07-27)

Powód: PRECONDITION-R FAIL 67%; DIAG-B4 (replay frozen model, eval-only) wyjaśnia
dominujący kubełek **B4 (27 pp — lock poprawny, epizod przegrany)**:

| metryka (27 B4 vs 67 OK) | B4 | OK |
|---|---|---|
| **near-miss% (min-dist ≤ 0.5 m)** | **96.3%** | — |
| J = mediana błędu centroidu boxa (px@256) | 0.54 | 0.49 |
| J_last (ostatni box przed martwym polem) | 0.50 | 0.52 |
| korelacja Δbox ↔ Δhover | **0.218** | — |

**Ustalenie:** B4 to **problem precyzji zawisu (dwell), nie kanału**: dron dolatuje na
≤0.5 m (96%) lecz nie utrzymuje r_goal=0.25 m; box **dokładny** (~0.5 px, jak w sukcesach,
J_last ratio 0.96); polityka **nie wisi tam, gdzie wskazał box** (korelacja 0.22 → miss NIE
wynika z szumu boxa). Deficyt leży w wykonawcy przy martwym polu terminalnym (brak świeżego
locka w fazie dwell → utrzymanie z pamięci mniej precyzyjne niż GT-fed).

## Dźwignie warunkowe (aktywacja WYŁĄCZNIE wg reguł; arytmetyka na T1)
**F1 — filtr kanału EMA (α=0.5) na (cx,cy,w,h); martwe pole zamraża STAN EMA.**
- Reguła: `J_last(B4) ≥ 1.5×J_last(OK)` LUB `J ≥ 8 px`.
- Ewaluacja: ratio 0.96 (<1.5), J 0.54 (<8) → **NIEAKTYWNA** (box dokładny — nie ma czego filtrować).

**F2 — gating dostarczeń (przeniesiona L2): nowy box nadpisuje ZOH tylko gdy
`IoU(nowy, bieżący ZOH) ≥ 0.2` LUB `age_s > 2.0` (re-akwizycja); odrzucone logowane.**
- Reguła: `B3 ≥ 2 pp` (spełniona z DIAG-lite: B3=3) → **AKTYWNA**.

**F3 — budżet: +1 runda DAgger (r4, 100 rolloutów, pula 47100-47199, dopisana do D8).
Limit twardy: jedna runda.**
- Reguła: `near-miss% ≥ 60%` (problem precyzji, nie informacji).
- Ewaluacja: 96.3% (≥60) → **AKTYWNA**.

**STOP-warunki (bez treningu):** [near-miss%<60 ∧ F1-nieaktywna] — NIE (96.3≥60);
[F1 aktywna ∧ korelacja~0] — NIE (F1 nieaktywna). → **BRAK STOP; kontynuacja z F2+F3.**

## Werdykt: aktywne **F2 (gating) + F3 (+1 runda DAgger)**; F1 nieaktywna
F1 nie ma czego naprawiać (box dokładny). B4 = precyzja dwell → F3 dokłada dane on-policy
w pobliżu celu (ekspert uczy precyzyjnego zawisu); F2 usuwa marginalną kradzież (B3, 3 pp).
Klasa zmian w mandacie: **logika kanału (F2) + budżet nominalny (F3)**; percepcja/kamera/
scena/ekspert/progi/YOLO — bez zmian. Bramka G1 zamrożona.

## D8 — uzupełnienie (ANEKS-3B-3)
DAgger **r4 = pula 47100-47199** (F3, jednorazowo). Reszta pul bez zmian.
