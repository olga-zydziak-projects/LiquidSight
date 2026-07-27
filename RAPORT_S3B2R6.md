# RAPORT_S3B2R6 — hover-rich BC → PRECONDITION-R6 FAIL (53%) → STOP; mandat wyczerpany

**Data:** 2026-07-28. **Sesja:** S3b2-R6. **Zakres:** JEDNA dźwignia — hover-rich BC (Z2 aktywne),
przepis S3b2-R + Z1 (stratyfikowany val) + ROUNDS=3. G1_GATE.md **FROZEN**. MIERZĘ = RAPORTUJE.
**Werdykt: PRECONDITION-R6 FAIL 53% → STOP (Z3); hover-rich szkodliwy; mandat dźwigni wyczerpany;
najlepszy model pozostaje S3b2-R = 67%.**

## T2/T3 — retrening (S3b2-R + Z1 + hover-rich BC 400, F2 off) — cykl 1.05 h
| etap | train | val | best_val @ epoka | rollout |
|---|---|---|---|---|
| r0 (BC 400) | 368 | 32 | 0.00201 @107 | — |
| r1 | 460 | 40 | 0.01052 @112 | 4.0% |
| r2 | 552 | 48 | 0.01552 @112 | 44.0% |
| r3 | 644 | 56 | 0.01247 @105 | 43.0% |

- **Hover-rich mechanizm potwierdzony:** age>2.0 frac **BC_hover 0.739 vs BC_std 0.632** (+10.7 pp
  gęstości stanów dwell pod wysokim age). best-epoki **wszystkie późne [107,112,112,105]** (Z1 stabilny).
  Asserty PASS (F2_off, conf_nie_w_wejsciu).

## T4 — PRECONDITION-R6 — **FAIL (53%, regresja)**
| metryka | R6 | S3b2-R (baza) | próg |
|---|---|---|---|
| **sukces** | **53.0%** | 67.0% | ≥85% ✗ |
| **wrong-lock** | **17.0%** | 10.0% | ≤8% ✗ |

**Per-komórka:** K3_A0 58.8 / K3_A1 70.6 / K5_A0 64.7 / **K5_A1 25.0** / K8_A0 64.7 / **K8_A1 31.2**.

## T4a — kubełki B1-B4 (S3b2-R vs R6)
| kubełek | S3b2-R | R6 |
|---|---|---|
| B1 nigdy-nie-zlockowane | 3 pp | **8 pp** |
| B2 późno | 0 pp | 0 pp |
| B3 kradzież | 3 pp | 2 pp |
| **B4 lock poprawny, przegrany** | **27 pp** | **37 pp** |
B4 near-miss 81% · other-tick dist median 0.33 m.

**Hover-rich POGORSZYŁ B4 (27→37) i B1 (3→8).** Mechanizm szkody: **ekspert szybki najazd
(v_max=2.0) → etykiety BC z agresywnymi setpointami, których polityka nie wykonuje własną
dynamiką (DSL-PID) → rozjazd rozkładu etykiet (BC fast vs DAgger/eval std)** → więcej
nie-dolotów (B1) i wrong-locków. Hover-rich realizowalny w mandacie (szybszy ekspert) **szkodzi**.

## T4b — DEKOMPOZYCJA wrong-lock (ściana druga; z tick-auditu)
| mechanizm | epizody | pp |
|---|---|---|
| **pierwszy-lock-zły** (polityka przykleja się do błędnej pierwszej detekcji) | 7 | **7.0** |
| **kradzież-w-locie** (lock poprawny nadpisany other) | 5 | **5.0** |
| inne (bg / brak dostarczenia) | 5 | 5.0 |
Wrong-lock (17%) to **odrębny problem** od B4 — dwa mechanizmy (pierwszy-zły ~7 pp większy niż
kradzież ~5 pp). Gating pixel-IoU (F2, odrzucony) celował w kradzież; **pierwszy-zły** wymaga
innej dźwigni (reguła admisyjności / próg conf jako sygnał — poza mandatem).

## Trajektoria i STOP — MANDAT WYCZERPANY
**12% → 67% (S3b2-R) → 11% (R3 F2) → 8% (R4 F3+zły-val) → 58% (R5 val-fix, F3 net-neg) →
53% (R6 hover-rich, szkodliwy).** **Żadna dźwignia w mandacie** (kanał F1/F2, budżet F3,
procedura-selekcja Z1, dane Z2 hover-rich) **nie przebiła 67%**; kilka regresowało.
**Najlepszy model = S3b2-R 67%** (`ckpt/s3b2r/policy_gc5.pt`).

**STOP (Z3):** zero dalszych treningów. **Dwie ściany, obie poza mandatem:**

### Ściana 1 — B4 (precyzja dwell, ~27 pp), granica systemowa
Polityka dolatuje (near-miss ~81-96%), ale nie trzyma r_goal 0.25 m gdy kanał stary (martwe pole
terminalne). GT-fed to potrafił (100%); live-fed nie. **Wyczerpane w mandacie:** budżet (F3 neg),
dane (hover-rich neg). **Poza mandatem (decyzja człowieka):**
- **Z2' kurikulum GT+live** (transfer zawisu z reżimu GT-fed, który dowodnie go uczy) — pre-spec, nieaktywne;
- **pojemność rdzenia / pamięć** (GRU-64 5-dim może nie utrzymywać celu w martwym polu);
- **granica systemowa:** przyjąć sufit < 85% na tym instrumencie (rewizja progu G1 = decyzja, nie fix).

### Ściana 2 — wrong-lock (~10-17%), problem odrębny
first-lock-bad (7 pp) + kradzież (5 pp). **Poza mandatem:** reguła admisyjności (D3-3c, odłożona
— conf jako sygnał niepewności do OSŁONY, nie wykonawcy) celowałaby w pierwszy-zły; world-gating
(odłożony) w kradzież.

**Rekomendacja sesji:** eksploracja dźwigni w mandacie zakończona bez przekroczenia 67%.
Kolejny krok wymaga **decyzji człowieka o nowym mandacie** (Z2' kurikulum / pojemność / reguła
admisyjności) **albo rewizji progu G1** (granica systemowa). Naprawa selekcji (Z1) zostaje.

## Higiena
Ekspert std / DAgger / eval, kamera, scena, parametry, progi, YOLO, kontrakt D3 — nietknięte;
hover-rich = wariant kolekcji (ta sama klasa HoverExpert); F2 off (0 odrzuceń); G1 frozen;
G1-R nieuruchomiony. Najlepszy model (S3b2-R 67%) zachowany. Artefakty:
`results/s3b2r6/{train_log,precond_R,diag_lite,diag_r6}.json`.
