# RAPORT_S3B2 — polityka goal-conditioned + P-SANITY-3B

**Data:** 2026-07-26. **Sesja:** S3b2. **Zakres:** kanał celu w polityce, retrening
goal-conditioned (GT-fed), zamrożenie i pomiar P-SANITY-3B, sufit per-komórka.
**ZERO groundera live (S3b3), ZERO dropoutu (G2/S3b4), ZERO zmian kanału wejść 3a.**
MIERZĘ = RAPORTUJĘ.

## Werdykt P1-3b — **PASS**
Polityka goal-conditioned (GT-fed) na 100 epizodach eval **46500–46599**, deterministycznie:

| metryka | wynik | próg P-SANITY-3B | werdykt |
|---|---|---|---|
| **sukces** | **100.0%** (100/100) | ≥ 90% | ✓ |
| **wrong-lock** | **0.0%** (0/100) | < 2% | ✓ |
| no-arrival | 0 | — | — |
| dwell | 0 | — | — |
| katastrofy | 0 | (klif bez zmian) | — |

Wrong-lock **0%** przy celu podanym z GT potwierdza, że **kanał celu i warunkowanie
działają** (polityka desygnuje właściwy obiekt, nie myli z dystraktorem — także w A1,
gdzie kolor jest współdzielony i rozstrzyga kształt). Sukces per-komórka **100% wszędzie**
(K3/5/8 × A0/A1).

## Sufit per-komórka (charakteryzacja, sweep 46600–46649, 50 ep) — wiersz odniesienia G1

| K \ A | A0 | A1 |
|---|---|---|
| **K=3** | 100% (8/8) | 100% (8/8) |
| **K=5** | 100% (8/8) | 100% (9/9) |
| **K=8** | 100% (8/8) | 100% (9/9) |
| **średnia** | **100.0%** (50/50), wrong-lock **0.0%** | |

Sufit GT-fed = **100% we wszystkich komórkach** (min = max = 100%). To odniesienie dla G1:
grounder live (YOLO-World, precyzja offline 0.868) będzie mierzony względem tego sufitu —
ile percepcja live traci względem GT-fed. **Bez zmian modelu/przepisu po obejrzeniu**
(charakteryzacja, nie strojenie).

## Model (T3)
Rdzeń goal-conditioned (`models/policy_gc.py`): wejście rdzenia **78 → 84** (+6 kanał celu
concat z feat+kin+dt); enkoder i głowa **bez zmian**. Parytet nie obowiązuje (brak twin).

| moduł | parametry |
|---|---|
| enkoder | 126 112 |
| **rdzeń GRU (84→64)** | **28 800** (3a: 27 648; Δ **+1 152** = 6·64·3) |
| głowa Linear(64→6) | 390 |
| **razem** | **155 302** |

## Trening (T4) — przepis v2 (ANEKS-4), seed 45020, lr 1e-3, best-val, 120 epok/etap

Retrening OD ZERA na agregacie każdą rundę. BC = 270 scen (46000–46269), val = 30 holdout
(46270–46299, 10% wg ANEKS-4 Z2). DAgger 3×100 (r1 46300–46399, r2 46400–46499, r3 47000–47099).

| etap | store | best_val (@epoka) | rollout sukces | czas (rollout+train) |
|---|---|---|---|---|
| r0 (BC) | 270 | 0.00041 @117 | — | 473 s |
| r1 (DAgger) | 370 | 0.00136 @116 | 10.0% | 91+555 s |
| r2 (DAgger) | 470 | 0.00119 @118 | 78.0% | 89+616 s |
| r3 (DAgger) | 570 | 0.00080 @114 | 94.0% | 88+739 s |

BC collect: 181 s. **Łączny czas cyklu: 2832 s = 0.79 h.** Rollout DAgger wspina się
**10 → 78 → 94%** (aggregate zamyka się dla GRU goal-conditioned; wynik eval 100% > rollout r3
bo eval to czysta polityka best-val na rozłącznych scenach). best_val ~1e-3 (poziom F3 GRU).

## Kontrakt kanału celu (D3) — asserty w kodzie zbierania danych

Źródło = `gt_bbox_256` wskazanego, **conf=1.0**; tick co 12 klatek; dostarczenie na klatce
`k_del = k_src + 2` (L_deliver 0.10 s / (1/12 s) = 1.2 → ceil 2); `age_s = (k−k_src)·(1/12)`
znormalizowany /AGE_MAX=8.0; ZOH między dostarczeniami; przed pierwszym dostarczeniem no-lock
(zera + age=1.0). Asserty na **każdym** epizodzie treningu (72 000 klatek):

| assert | wynik |
|---|---|
| n_frames | 72 000 |
| n_deliveries | 1 342 |
| **delivery_frame_ok** (dostarczenie na k_src+2) | **✓** |
| **age_monotonic_ok** (age rośnie w obrębie locka) | **✓** |
| **reset_on_delivery_ok** (age spada przy nowym locku) | **✓** |

Wszystkie asserty PASS — kontrakt D3 zrealizowany dokładnie.

## Znane różnice train ↔ live (do weryfikacji G1)
- **conf = 1.0 (GT-fed)** w S3b2; grounder live (YOLO-World) zwróci conf < 1 oraz bbox z
  błędem (precyzja@1 0.868, wrong-object 0.083 — RAPORT_S3B0). Polityka trenowana na
  idealnym locku; **G1 (S3b3) zmierzy stratę** względem sufitu GT-fed (100%).
- Źródło bbox jest z pozy o ~1 klatkę (83 ms) do przodu względem obs (artefakt kadencji env);
  nieistotne dla sygnału 1 Hz z ZOH.

## Co zostaje do S3b3+ (poza zakresem S3b2)
- **G1:** grounder live (YOLO-World @1 Hz) w pętli zamiast GT-fed; strata względem sufitu 100%.
- **G2 / S3b4:** oś dropoutu (D6), maski 45100+; zamrożenie po sondzie.
- **B1 (D7):** RAPORT_BASELINE_GRU.

## Reprodukcja
```
.venv/bin/python -m train.s3b2 train     # BC 300 + DAgger 3x100 -> ckpt/s3b2/policy_gc.pt (~0.8h)
.venv/bin/python -m train.s3b2 eval       # P1-3b (100 ep eval) -> results/s3b2/p1_3b.json
.venv/bin/python -m train.s3b2 ceiling    # sufit sweep (50 ep) -> results/s3b2/ceiling.json
```
Artefakty: `results/s3b2/{train_log,contract_asserts,p1_3b,ceiling}.json`;
model `ckpt/s3b2/policy_gc.pt` (gitignored, odtwarzalny z seeda 45020).
