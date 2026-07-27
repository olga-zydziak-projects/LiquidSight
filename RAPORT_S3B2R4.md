# RAPORT_S3B2R4 — F2 off + czysty test F3 → PRECONDITION-R4 FAIL (8%) → STOP definitywny

**Data:** 2026-07-27. **Sesja:** S3b2-R4. **Zakres:** F2 wyłączone na stałe (ANEKS-3B-4 Z1),
CZYSTY test F3 (+1 runda DAgger r4) na zdrowym kanale S3b2-R. G1_GATE.md **FROZEN**.
MIERZĘ = RAPORTUJE. **Werdykt: PRECONDITION-R4 FAIL (8%) → STOP DEFINITYWNY** (lista dźwigni
w mandacie wyczerpana; G1-R nieuruchomiony).

## T2/T3 — retrening (F2 OFF, ROUNDS=4, live-fed, seed 45020) — cykl 1.27 h
| etap | store | best_val @ epoka | rollout |
|---|---|---|---|
| r0 (BC 270) | 270 | 0.00046 @117 | — |
| r1 | 370 | 0.00348 @119 | 7.0% |
| r2 | 470 | 0.00396 @96 | 47.0% |
| r3 | 570 | 0.00562 @113 | 55.0% |
| **r4 (F3)** | 670 | 0.00594 **@6** | **72.0%** |

F2 OFF potwierdzone (plain Tracker5; **0 odrzuconych dostarczeń**; n_deliveries 1964 vs R3 1252).
Asserty PASS (conf_nie_w_wejsciu ✓).

**Czysta wartość F3 na ROLLOUCIE: pozytywna** — r4 podniósł rollout **55 → 72%** (+17 pp).
To obala plateau z R3 (57% było SKONFUNDOWANE zepsutym F2). **DAgger-budżet DZIAŁA on-policy.**

## T4 — PRECONDITION-R4 — **FAIL (regresja 67 → 8%)**
| metryka | R4 | S3b2-R | próg |
|---|---|---|---|
| **sukces** | **8.0%** | 67.0% | ≥85% ✗ |
| wrong-lock | 3.0% | 10.0% | ≤8% ✓ |

**Per-komórka R4:** K3_A0 11.8 / K3_A1 0.0 / K5_A0 5.9 / K5_A1 12.5 / K8_A0 11.8 / K8_A1 6.2.

## Diagnoza regresji: **patologia selekcji best-val przy r4**
Rollout r4 = 72% (dobry), ale **wdrożony model = best-val@epoka 6** (r0-r3 minimalizowały
val @96-119; **r4 @6** — wyraźny odstający). Mechanizm: **val = tylko 30 epizodów BC**
(ekspert-czyste), a agregat treningu przy r4 = 670 ep zdominowany przez **DAgger** (polityka-
szumne). BC-val minimalizuje się WCZEŚNIE (epoka 6) i rośnie (model oddala się od czystego BC),
więc best-val wybiera **niedotrenowany checkpoint** → 8% eval. Rollout (72%) dotyczy modelu r3
(uzytego do zbierania r4), NIE zapisanego modelu r4@6.

**Ustalenie inżynierskie F-3b-3:** best-val na val-BC-only staje się **niewiarygodny** gdy
rośnie udział DAgger (r4). Dodanie rundy poprawia rollout, ale psuje selekcję checkpointu.

## T4 — kubełki B1-B4 na R4 (mandat: pomiar r4 nawet przy FAIL) — SKONFUNDOWANE
| kubełek | S3b2-R (przed) | R4 (po) |
|---|---|---|
| B1 nigdy-nie-zlockowane | 3 pp | 5 pp |
| B2 późno | 0 pp | 0 pp |
| B3 kradzież | 3 pp | 0 pp |
| **B4 lock poprawny, przegrany** | **27 pp** | **87 pp** |

**B4 27→87 pp jest SKONFUNDOWANE** patologią best-val@6: to niedotrenowany model gorzej
utrzymuje zawis (other-tick dist median 0.55 m vs R 0.17 m), a nie czysty efekt r4 na precyzję.
**Czystej wartości r4 na B4 NIE DA SIĘ ocenić** — best-val wybrał zły checkpoint. (F3 na
ROLLOUCIE pozytywne; na WDROŻONYM modelu — zablokowane selekcją.)

## Trajektoria i STOP
**12% (G1-FAIL) → 67% (S3b2-R) → 11% (R3: F2 szkodliwy) → 8% (R4: F3 rollout+, ale best-val
psuje wdrożenie).** Najlepszy stan pozostaje **S3b2-R = 67%** (`ckpt/s3b2r/policy_gc5.pt`).

**STOP DEFINITYWNY (Z3):** lista dźwigni w mandacie (F1/F2/F3 = kanał + budżet) **wyczerpana**;
F2 szkodliwy, F3 pozytywny-na-rollouct-ale-zablokowany-selekcją. **Zero dalszych treningów.**
B4 (precyzja dwell) **nie jest domykalny** dostępnymi klasami.

## Opcje spoza listy (decyzja człowieka / nowy mandat)
1. **Naprawa selekcji checkpointu** (warunek wstępny każdej kolejnej rundy): val zawierający
   DAgger albo selekcja po ROLLOUCIE (nie BC-val) — F3 miałby wtedy czystą szansę (rollout 72%).
2. **Hover-rich BC** — dodać epizody eksperta z fazy zawisu (precyzja dwell u źródła).
3. **Pojemność rdzenia / pamięć** — GRU 5-dim może nie utrzymywać celu w martwym polu jak GT-fed.
4. **World-gating** (odłożony) — gating na dystansie po back-projekcji zamiast pixel-IoU.
Rekomendacja sesji: **najpierw (1)** — bez naprawy selekcji każdy test budżetu (F3) jest
zaślepiony; potem (2)/(3) na precyzję dwell (B4).

## Higiena
Percepcja/kamera/scena/ekspert/parametry/progi/YOLO/kontrakt D3 — nietknięte; F2 OFF
(0 odrzuceń); G1_GATE.md frozen; G1-R nieuruchomiony. Najlepszy model (S3b2-R 67%) zachowany.
Artefakty: `results/s3b2r4/{train_log,precond_R,diag_lite,diag_lite_episodes}.json`.
