# RAPORT_S3B2R7 — kurikulum GT+live → PRECONDITION-R7 FAIL (60%) → GRANICA ZMIERZONA; mandat zamknięty

**Data:** 2026-07-30. **Sesja:** S3b2-R7 (OSTATNIA iteracja precondition w mandacie, klauzula końca ANEKS-3B-7).
**Zakres:** JEDNA dźwignia — Z2' skład BC = 300 live + 100 GT-fed (pula 47300-47399, box=gt_bbox_256,
ekspert STANDARDOWY); przepis S3b2-R + Z1 (val stratyfikowany) + ROUNDS=3. F2 OFF. G1_GATE.md **FROZEN**.
MIERZĘ = RAPORTUJE. **Werdykt: PRECONDITION-R7 FAIL 60% → klauzula końca aktywowana; granica raportowana
przy NIETKNIĘTYM progu G1; sweep 46600-46649 CZYSTY; najlepszy model pozostaje S3b2-R = 67%.**

## T2/T3 — retrening (S3b2-R + Z1 + BC 300 live + 100 GT-fed, F2 off) — cykl 1.10 h
| etap | train | val | best_val @ epoka | rollout |
|---|---|---|---|---|
| r0 (BC 400) | 368 | 32 | 0.00018 @116 | — |
| r1 | 460 | 40 | 0.00622 @100 | 10.0% |
| r2 | 552 | 48 | 0.00917 @119 | 49.0% |
| r3 | 644 | 56 | 0.01084 @105 | 59.0% |

- **best-epoki wszystkie późne [116,100,119,105]** — Z1 selektor stabilny (bez defektu F-3b-3).
- **Zgodność profili prędkości eksperta (lekcja F-3b-4) POTWIERDZONA:** p95 |v| — BC_live 0.924 /
  BC_gt 0.921 / r1 0.919 / r2 0.936 / r3 0.924; mediana 0.0 wszędzie; `profil_predkosci_zgodny=True`
  (rozstęp median <0.05, p95 <0.1). **Żadnego rozjazdu etykiet** — w przeciwieństwie do R6 hover-rich.
- Asserty kontraktu: `n_frames=84000`, `delivery_frame_ok`, `age_monotonic_ok`, `conf_nie_w_wejsciu`,
  `F2_off_0_odrzucen`, `profil_predkosci_zgodny` — **wszystkie PASS**.

## T4 — PRECONDITION-R7 — **FAIL (60%, poniżej bazy)**
| metryka | R7 | S3b2-R (baza) | próg |
|---|---|---|---|
| **sukces** | **60.0%** | 67.0% | ≥85% ✗ |
| **wrong-lock** | **12.0%** | 10.0% | ≤8% ✗ |
| no-arrival | 16 | — | — |
| dwell (przegrany) | 12 | — | — |
| katastrofy | 0 | 0 | — |

**Per-komórka:** K3_A0 70.6 / K3_A1 76.5 / K5_A0 70.6 / **K5_A1 37.5** / K8_A0 70.6 / **K8_A1 31.2**.
Kolaps K5_A1/K8_A1 (kolor współdzielony, wysokie K) powtarza się — sygnatura ściany B4, nie składu BC.

## T4a — kubełki B1-B4 (S3b2-R vs R7) — **B4 NIEZMIENIONE**
| kubełek | S3b2-R | R7 |
|---|---|---|
| B1 nigdy-nie-zlockowane | 3 pp | 5 pp |
| B2 późno | 0 pp | 0 pp |
| B3 kradzież | 3 pp | 6 pp |
| **B4 lock poprawny, przegrany** | **27 pp** | **29 pp** |
B4 near-miss **89.7%** (dolatuje, nie trzyma) · other-tick dist median **0.305 m**.

**GT+live kurikulum NIE ruszyło B4 (27→29, w szumie).** Mechanizm testowany — transfer umiejętności
zawisu z reżimu GT-fed (który dowodnie osiąga 100%, S3b2) na politykę żyjącą na żywym interfejsie —
**NIE zadziałał**. To najsilniejszy jak dotąd dowód, że ściana B4 jest własnością **żywego interfejsu
(kanał stary @1 Hz w martwym polu terminalnym)**, nie danych treningowych: etykiety GT-fed (dokładny
box, spójność etykieta↔kanał) **nie potrafią nauczyć trzymania r_goal, gdy kanał, który polityka
realnie napotka przy dolocie, jest stary**. Skład BC wyczerpany jako dźwignia.

## T4b — DEKOMPOZYCJA wrong-lock (ściana druga)
| mechanizm | epizody | pp |
|---|---|---|
| **pierwszy-lock-zły** | 2 | **2.0** |
| **kradzież-w-locie** (lock poprawny nadpisany other) | 6 | **6.0** |
| inne (bg / brak dostarczenia) | 4 | 4.0 |
Wrong-lock (12%) pozostaje problemem **odrębnym** od B4. W R7 dominuje **kradzież-w-locie (6 pp)**
nad pierwszy-zły (2 pp) — odwrotnie niż R6 (7/5); rozkład mechanizmów zmienny między biegami, ale
suma stabilna ~10-17%. Kradzież celowałby world-gating (odłożony); pierwszy-zły — reguła admisyjności
(D3-3c, odłożona). Obie **poza mandatem**.

## T5 — G1-R: NIEURUCHOMIONY (klauzula końca)
PASS był warunkiem koniecznym G1-R. FAIL → **sweep 46600-46649 pozostaje CZYSTY** (bramka G1 nietknięta,
zero ewaluacji na puli sweep). Możliwe przyszłe ponowne uzbrojenie osobnym mandatem człowieka.

## GRANICA ZMIERZONA — mandat precondition zamknięty (klauzula końca ANEKS-3B-7)
Trajektoria pełna: **12% (G1 live) → 67% (S3b2-R conf-fix) → 11% (R3 F2) → 8% (R4 F3+zły-val) →
58% (R5 val-fix, F3 net-neg) → 53% (R6 hover-rich, szkodliwy) → 60% (R7 GT+live, neutralny→neg).**
**Żadna dźwignia w mandacie** — kanał (F1/F2), budżet DAgger (F3), procedura-selekcja (Z1), dane
(Z2 hover-rich, **Z2' GT+live**) — **nie przebiła 67%**. Najlepszy model = **S3b2-R 67%**
(`ckpt/s3b2r/policy_gc5.pt`, zachowany).

### Ściana 1 — B4 (precyzja dwell, ~27-29 pp) — GRANICA SYSTEMOWA POTWIERDZONA
Polityka dolatuje (near-miss ~90-96%), nie trzyma r_goal 0.25 m gdy kanał stary (martwe pole terminalne
@1 Hz). GT-fed potrafił (100%, S3b2); live-fed nie. **Wyczerpane w mandacie:** budżet (F3 neg), dane
hover-rich (neg), **dane GT+live (R7 neutralne — 27→29)**. Dowód R7 lokalizuje przyczynę: **własność
żywego interfejsu, nie danych** (domieszka reżimu-który-potrafi nie przeniosła umiejętności). **Poza
mandatem (decyzja człowieka):** (a) pojemność/pamięć rdzenia (GRU-64 5-dim może nie utrzymywać celu
w martwym polu); (b) gęstszy tick / krótsze L_deliver w martwym polu (zmiana D2/D3 = decyzja); (c)
przyjęcie sufitu < 85% na tym instrumencie (rewizja progu G1 = decyzja, nie fix).

### Ściana 2 — wrong-lock (~10-17%) — PROBLEM ODRĘBNY
pierwszy-lock-zły + kradzież (mix zmienny: R6 7/5, R7 2/6). **Poza mandatem:** reguła admisyjności
(D3-3c, odłożona — conf jako sygnał niepewności do OSŁONY, nie wykonawcy) → pierwszy-zły; world-gating
(odłożony) → kradzież. **Mapuje na 3c-MVP** (reguła admisyjności desygnacji).

## Decyzja programu (klauzula końca honorowana)
Eksploracja dźwigni precondition **zakończona bez przekroczenia 67%**; granica zmierzona i zlokalizowana
(ściana 1 = interfejs live, nie dane — dowód R7). **Program przechodzi do G2 (oś dropoutu D6, na
najlepszym modelu S3b2-R 67%) i 3c-MVP (reguła admisyjności → ściana 2).** Naprawa selekcji (Z1)
zostaje w przepisie. **Żadnych dalszych dźwigni precondition bez nowego mandatu człowieka.**

## Higiena
Ekspert std (obie kolekcje + DAgger, identyczny profil prędkości — zweryfikowane), kamera, scena,
parametry, progi, YOLO, kontrakt D3 — nietknięte. GT-fed = wariant kolekcji (box=gt_bbox_256, ten sam
kontrakt 5-dim). F2 off (0 odrzuceń). G1 frozen; G1-R nieuruchomiony; sweep 46600-46649 czysty.
Najlepszy model (S3b2-R 67%) zachowany. Artefakty: `results/s3b2r7/{train_log,precond_R,diag_r6}.json`
+ `conf_log.jsonl`.
