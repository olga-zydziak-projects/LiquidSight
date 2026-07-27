# RAPORT_S3B2R3 — DIAG-B4 + ANEKS-3B-3 (F2+F3) → PRECONDITION-R3 FAIL (regresja)

**Data:** 2026-07-27. **Sesja:** S3b2-R3. **Zakres:** DIAG-B4 → dźwignie F1/F2/F3 (wg reguł)
→ retrening → PRECONDITION-R3. G1_GATE.md **FROZEN**. MIERZĘ = RAPORTUJĘ.
**Werdykt: PRECONDITION-R3 FAIL (11%, REGRESJA z 67%) → STOP z audytem; G1-R nieuruchomiony.**

## T1 — DIAG-B4 (replay frozen model, eval-only, 27 B4 vs 67 OK)
| metryka | B4 | OK |
|---|---|---|
| **near-miss% (min-dist ≤ 0.5 m)** | **96.3%** | — |
| lost% (> 0.5 m) | 3.7% | — |
| J = mediana błędu centroidu (px@256) | 0.54 | 0.49 |
| J_last (ostatni box przed martwym polem) | 0.50 | 0.52 (ratio 0.96) |
| korelacja Δbox ↔ Δhover | **0.218** | — |

**Ustalenie:** B4 = **precyzja dwell**, nie kanał: dron dolatuje ≤0.5 m (96%), nie utrzymuje
r_goal=0.25 m; box **dokładny** (~0.5 px, jak OK); polityka **nie wisi gdzie wskazał box**
(korelacja 0.22). Deficyt = wykonawca przy martwym polu terminalnym.

## T2 — dźwignie aktywowane (arytmetyka T1)
| dźwignia | reguła | ewaluacja | status |
|---|---|---|---|
| F1 EMA | J_last≥1.5×OK lub J≥8px | 0.96<1.5, 0.54<8 | **NIEAKTYWNA** |
| F2 gating (IoU≥0.2 ∨ age>2.0) | B3≥2 | B3=3 | **AKTYWNA** |
| F3 +1 runda DAgger (r4, 47100-47199) | near-miss≥60% | 96.3% | **AKTYWNA** |
STOP-warunki niespełnione → kontynuacja z F2+F3.

## T4 — retrening (v2, live-fed, F2+F3, seed 45020) — cykl 1.09 h
| etap | best_val | rollout |
|---|---|---|
| r0 (BC 270) | 0.00046 | — |
| r1 | 0.00550 | 5.0% |
| r2 | 0.00562 | 28.0% |
| r3 | 0.00693 | 57.0% |
| **r4 (F3)** | 0.00772 | **57.0%** (plateau) |

**F2 odrzuciło 741 dostarczeń** (train). Asserty PASS (conf_nie_w_wejsciu ✓). F3 (r4) **nie
podniósł** rolloutu ponad 57% (= poziom S3b2-R bez r4).

## T5 — PRECONDITION-R3 — **FAIL (regresja)**
| metryka | R3 | S3b2-R (bez dźwigni) | próg |
|---|---|---|---|
| **sukces** | **11.0%** | 67.0% | ≥85% ✗ |
| **wrong-lock** | 7.0% | 10.0% | ≤8% ✓ |

**Per-komórka R3:** K3_A0 11.8 / K3_A1 5.9 / K5_A0 17.6 / K5_A1 6.2 / K8_A0 5.9 / K8_A1 18.8 —
zapaść we wszystkich.

**Audyt per-tick (STOP-diagnostyka):** tick-precision designated **20.6%** (≈ S3b2-R 20.8%,
grounder bez zmian), other 7.6% (F2 obniżyło fałszywe locki), no-det 71.6%. **age-histogram
przesunięty W GÓRĘ:** `[1208, 1800, 2674, 2260, 4058]` vs S3b2-R `[2472,…,3156]` — **locki
STARSZE (zamrożone)**. F2 odrzuciło 133 dostarczeń w eval.

## Diagnoza regresji: **F2 gating backfired**
Grounder wykrywa wskazanego tak samo (20.6%), ale **F2 (IoU≥0.2) ODRZUCA legalne aktualizacje**:
kolejne boxy wskazanego przy szybkim dolocie (1 s między tikami) mają **IoU<0.2** — obiekt
znacząco przesuwa się w kadrze 256 podczas zbliżania → nowy box nie nakłada się na ZOH → **lock
zamraża się na starej pozycji** (age-hist skew w górę). Efekt: polityka traci cel → 11%.
Próg IoU≥0.2 jest **nieadekwatny dla dynamiki dolotu** (założenie „kolejne boxy się nakładają"
fałszywe przy ruchomej kamerze). F3 (+1 runda) plateau 57% — bez korzyści.

## Trajektoria i wniosek
**12% (G1-FAIL) → 67% (S3b2-R: conf usunięty + live-fed) → 11% (S3b2-R3: F2+F3).** Dźwignie
aktywowane regułami **pogorszyły** wynik. Najlepszy stan pozostaje **S3b2-R = 67%**
(`ckpt/s3b2r/policy_gc5.pt`).

Zgodnie z T5: **STOP z audytem, zero dalszych napraw.** Ustalenia dla decyzji człowieka:
1. **F2 (IoU-gating) odrzucić** — nieadekwatny dla dolotu; gdyby gating, to na innej metryce
   (np. odległość centroidu w świecie po back-projekcji, nie IoU pikselowe).
2. **B4 (precyzja dwell, 27 pp) NIE jest adresowalny** dostępnymi klasami (kanał/budżet):
   F3 (budżet) plateau, F2 (kanał) szkodzi. To potwierdza, że B4 leży w **wykonawcy/
   warunkowaniu** — dźwignia **spoza listy** (reward dwell, pojemność rdzenia/pamięć,
   ekspert-precyzja) = **decyzja człowieka / nowy mandat**.

## Higiena
Percepcja/kamera/scena/ekspert/parametry/progi/YOLO — nietknięte; DIAG-B4 tylko replay frozen;
G1_GATE.md frozen; G1-R nieuruchomiony (zabramkowany za precondition). Najlepszy model
(S3b2-R 67%) zachowany. Artefakty: `results/s3b2r3/{train_log,precond_R,precond_R3_audit,
f2_gating}.json`, `results/s3b2r/diag_b4.json`.
