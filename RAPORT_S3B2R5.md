# RAPORT_S3B2R5 — naprawa selekcji (F-3b-3) + czysty re-test F3 → PRECONDITION-R5 FAIL (58%)

**Data:** 2026-07-28. **Sesja:** S3b2-R5. **Zakres:** ANEKS-3B-5 Z1 (walidacja selekcyjna =
stratyfikowany held-out z pełnego agregatu) + czysty re-test F3. G1_GATE.md **FROZEN**.
MIERZĘ = RAPORTUJE. **Werdykt: F-3b-3 POTWIERDZONE i naprawione; ale F3 (+1 runda) net-negatywny
na wdrożeniu → PRECONDITION-R5 FAIL 58% → STOP (Z3); G1-R nieuruchomiony.**

## T2/T3 — retrening (stratyfikowany val, F2 off, ROUNDS=4) — cykl 1.13 h
val = held-out **8% KAŻDEJ rundy** (seed 45021): BC 24 + r1/r2/r3/r4 po 8 = **56 ep**.

| etap | train | val | best_val @ **epoka** | rollout |
|---|---|---|---|---|
| r0 (BC) | 276 | 24 | 0.00021 @**118** | — |
| r1 | 368 | 32 | 0.00712 @**113** | 1.0% |
| r2 | 460 | 40 | 0.00984 @**70** | 47.0% |
| r3 | 552 | 48 | 0.01103 @**25** | 51.0% |
| **r4** | 644 | 56 | 0.00957 @**119** | 33.0% |

**F-3b-3 POTWIERDZONE i NAPRAWIONE:** best-epoka r4 = **119** (późna, jak r0/r1), vs R4 **@6**.
Stratyfikowany val (z DAgger) naprawił selekcję checkpointu → wdrożony model r4 jest dotrenowany.
Asserty PASS (F2_off_0_odrzucen ✓, conf_nie_w_wejsciu ✓). (rollout r4=33% jest na modelu r3,
który wypadł @25 — pośrednia niestabilność selekcji przy val z DAgger; final r4@119 dobry.)

## T4 — PRECONDITION-R5 — **FAIL (58%)**
| metryka | R5 (4 rd, fix) | S3b2-R (3 rd) | R4 (4 rd, zły val) | próg |
|---|---|---|---|---|
| **sukces** | **58.0%** | 67.0% | 8.0% | ≥85% ✗ |
| **wrong-lock** | **14.0%** | 10.0% | 3.0% | ≤8% ✗ |

**Per-komórka R5:** K3_A0 58.8 / K3_A1 82.4 / K5_A0 52.9 / K5_A1 56.2 / K8_A0 64.7 / K8_A1 31.2.

## T4 — kubełki B1-B4 (S3b2-R vs R5) + other-dist
| kubełek | S3b2-R (przed) | R5 (po) |
|---|---|---|
| B1 nigdy-nie-zlockowane | 3 pp | 5 pp |
| B2 późno | 0 pp | 0 pp |
| B3 kradzież | 3 pp | 4 pp |
| **B4 lock poprawny, przegrany** | **27 pp** | **33 pp** |
other-tick dist median: 0.17 m (R) → **0.28 m** (R5).

## Wnioski (dwa, rozdzielone)
1. **F-3b-3 POTWIERDZONE (defekt procedury, naprawiony).** Naprawa selekcji odzyskała **8% → 58%**
   (+50 pp) — dowód, że val-BC-only łamał wybór checkpointu przy agregacie zdominowanym DAgger.
   Naprawa jest **słuszna i zostaje** (poprawna procedura).
2. **F3 (+1 runda DAgger) — net-NEGATYWNY na wdrożeniu, nawet z naprawioną selekcją.**
   4 rundy (58%) **< 3 rundy (67%)**; B4 **27→33 pp**, wrong-lock **10→14%**. Dodatkowa runda
   dokłada szum on-policy bez korzyści dla precyzji dwell. **Budżet (F3) nie domyka B4.**

**Najlepszy model pozostaje S3b2-R = 67%** (`ckpt/s3b2r/policy_gc5.pt`).

## Trajektoria i STOP (Z3)
**12% (G1-FAIL) → 67% (S3b2-R) → 11% (R3: F2 szkodliwy) → 8% (R4: F3+zły val) → 58% (R5:
val naprawiony, ale F3 net-negatywny).** **Lista dźwigni w mandacie wyczerpana** (kanał F1/F2,
budżet F3, procedura-selekcja) — żadna nie przekroczyła 67%. B4 (precyzja dwell, ~27-33 pp)
**nie jest domykalny** klasami w mandacie.

**STOP** (zero dalszych treningów). Opcje **spoza listy** (decyzja człowieka / nowy mandat):
1. **Z2 hover-rich BC** (pre-spec, pula 47200-47299) — +100 ep eksperta z wydłużonym zawisem:
   precyzja dwell **u źródła danych** (nie budżet rund). **Najbardziej celowana w B4.**
2. **Pojemność rdzenia / pamięć** — GRU-64 5-dim może nie utrzymywać celu w martwym polu jak
   GT-fed; większy rdzeń / dłuższa pamięć.
3. **Granica systemowa** — przyjąć, że desygnacja live przy martwym polu terminalnym +
   szumnym boxie ma sufit < 85% na tym instrumencie (rewizja progu = decyzja, nie w mandacie).
Rekomendacja sesji: **Z2 (hover-rich BC)** — adresuje B4 u źródła; jeśli nie domknie, to (3)
granica systemowa. **Naprawa selekcji (Z1) zostaje w każdym scenariuszu.**

## Higiena
Percepcja/kamera/scena/ekspert/parametry/progi/YOLO/kontrakt D3 — nietknięte; F2 off (0 odrzuceń);
G1_GATE.md frozen; G1-R nieuruchomiony (zabramkowany za precondition). Najlepszy model
(S3b2-R 67%) zachowany. Artefakty: `results/s3b2r5/{train_log,precond_R,diag_lite,
diag_lite_episodes}.json`.
