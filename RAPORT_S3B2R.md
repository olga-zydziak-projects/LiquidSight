# RAPORT_S3B2R — ANEKS-3B zastosowany (kanał bez conf + live-fed) + PRECONDITION-R

**Data:** 2026-07-27. **Sesja:** S3b2-R. **Zakres:** sankcjonowana naprawa z DIAG-3B —
kanał celu 5-dim BEZ conf (ANEKS-3B Z1) + dane treningowe LIVE-FED (Z2), retrening,
**PRECONDITION-R** wg tych samych poprzeczek co G1 (≥85% ∧ wrong-lock ≤8%). Bramka G1
**FROZEN**; grounder/env/ekspert/config **bez zmian**. MIERZĘ = RAPORTUJĘ.
**Werdykt: PRECONDITION-R FAIL → STOP** (per T4: żadnych napraw; **G1-R nieuruchomiony** —
sweep zabramkowany za preconditionem).

## Aneks zastosowany (T2)
- **Kanał 5-dim** `(cx,cy,w,h,age_s)` — **conf USUNIETY** z wejścia; rdzeń **83→64**
  (28 608 param; total 155 110). conf **logowany** per tick (`results/s3b2r/conf_log.jsonl`),
  **nie podawany** polityce. **Assert `conf_nie_w_wejsciu: true`** (target_dim=5).
- **Dane LIVE-FED**: BC (270+30 val) i DAgger (3×100) zbierane z **żywego YOLO** (serwer
  `.venv_s3b0`) wg kontraktu D3. Asserty kontraktu (72 000 klatek, 1887 dostarczeń):
  delivery_frame_ok ✓, age_monotonic_ok ✓.

## Trening (T3) — przepis v2, seed 45020, lr 1e-3, cykl solo
| etap | store | best_val | rollout | czas |
|---|---|---|---|---|
| r0 (BC) | 270 | 0.00046 | — | 305 s |
| r1 | 370 | 0.00362 | 8.0% | 96+460 s |
| r2 | 470 | 0.00491 | 46.0% | 94+732 s |
| r3 | 570 | 0.00453 | 55.0% | 95+685 s |

BC collect 231 s. **Cykl 2698 s = 0.75 h.** best_val ~4·10⁻³ (wyżej niż GT-fed S3b2 ~8·10⁻⁴)
i rollout 8→46→55% (wolniej niż GT-fed 10→78→94) — **spodziewane**: kanał live jest szumny
(błędy groundera in-FOV ~14% + no-lock w martwym polu), polityka fituje trudniejszy rozkład.

## PRECONDITION-R (T4) — 100 ep eval 46500-46599, żywy kanał — **FAIL**
| metryka | wynik | próg | werdykt |
|---|---|---|---|
| **sukces** | **67.0%** | ≥ 85% | ✗ |
| **wrong-lock** | **10.0%** | ≤ 8% | ✗ |
| no-arrival + dwell | 23.0% | — | — |
| katastrofy | 0 | — | — |

**Per-komórka:** K3_A0 64.7 / K3_A1 82.4 / K5_A0 76.5 / **K5_A1 50.0** / K8_A0 82.4 /
**K8_A1 43.8**. Komórki **A1 (kolor współdzielony, kształt rozstrzyga) najsłabsze** —
grounder myli obiekty tego samego koloru → wrong-lock.

**Audyt per-tick (diagnostyka):** tick-precision designated **20.8%** / other 10.1% /
no-det 69.1%; flip median 0. designated 20.8% **= dokładnie frakcja widoczności (T2)**:
polityka poprawnie locka wskazanego na tikach dolotu (in-FOV) i mostkuje martwe pole pamięcią
(jak GT-fed); other 10.1% = fałszywe locki (głównie A1).

## Porównanie i status hipotez
- **vs G1-FAIL: 12% → 67% (+55 pp), wrong-lock 20% → 10% (−10 pp).** Ogromny odzysk
  **potwierdza dowodowo DIAG-3B**: conf-shift był dominującą przyczyną (88 pp); usunięcie conf
  + live-fed odzyskuje większość straty. Kierunek naprawy **trafny**.
- **Ale niewystarczająco** do zamrożonej bramki (67% < 85%). Reszta **~18 pp + wrong-lock 2 pp
  ponad próg** to **jakość boxa / widoczność** — dokładnie składowe **(A)/(C)** z DIAG-3B,
  które „mają sens dopiero po (B)". (B) zrobione; residuum = (A)+(C).
- **Hipoteza odświeżania 1 Hz:** nadal NIE jest mechanizmem odzysku — poprawa pochodzi z
  **usunięcia conf** (a nie z odświeżania); flip 0 (lock stabilny), odzysk = warunkowanie na
  poprawnym wczesnym locku + pamięć.
- **oracle+conf1.0 (DIAG-3B) = 80%** vs live-fed real **67%**: różnica 13 pp = realny grounder
  (błędy in-FOV 14% + jitter) wobec oracle idealnego — spójne.

## STOP — punkty decyzyjne (NIE wykonane)
PRECONDITION-R FAIL zatrzymuje sesję przed sweepem (G1-R). Dalsza naprawa poza mandatem
(kolejny aneks = decyzja człowieka). Wskazane przez residuum:
1. **(B)+(A) rewizja obserwowalności** — utrzymać wskazanego w kadrze dłużej (stożek/FOV) →
   mniej no-lock w martwym polu, więcej poprawnych locków, mniej fałszywych A1.
2. **(B)+(C) OWLv2 live** — in-FOV 99% (vs YOLO 85.6) i mniej mylenia A1; koszt: 0.5 Hz.
   (Uwaga: OWLv2 poza-FOV zwraca więcej fałszywych locków — do rozważenia z (A).)
Rekomendacja sesji (do decyzji Olgi): **(B) już działa i potwierdza diagnozę; residuum to
(A)/(C) — najpierw (A) (tanio, adresuje no-lock i część wrong-lock A1).**

## Reprodukcja
```
.venv/bin/python -m train.s3b2r train    # live-fed BC+DAgger -> ckpt/s3b2r/policy_gc5.pt (~0.75h)
.venv/bin/python -m train.s3b2r precond   # PRECONDITION-R (100 ep) -> results/s3b2r/precond_R.json (FAIL)
# G1-R (sweep) NIE uruchomiony — zabramkowany za PRECONDITION-R.
```
Artefakty: `results/s3b2r/{train_log,precond_R,precond_R_audit}.json`, `conf_log.jsonl`.
Bramka G1_GATE.md — nietknięta. Aneks: `ANEKS_3B_KANAL.md` + linia w `DECYZJE_3B.md`.
