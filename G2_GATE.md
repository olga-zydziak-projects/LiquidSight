# G2_GATE — oś G2 (zrywany strumień semantyczny) ZAMROŻONA (charakteryzacja)

**Data zamrożenia:** 2026-07-30. **Sesja:** S3b4/G2. **Podstawa:** D6 (DECYZJE_3B) + sonda
rozdzielczości T1 (S3b4). **Zasada:** MIERZĘ = RAPORTUJE. **RAMOWANIE:** G2 = **charakteryzacja**
(krzywa degradacji zrywanego strumienia semantycznego) — **BEZ progu akceptacyjnego**. Twierdzenia
progowe (jeśli w ogóle) → dopiero RAPORT_3B. Zmiana wartości po tym commicie zabroniona.

## Mechanizm (kontrakt D3 NIENARUSZONY)
Grounder jest odpytywany **co tick** (determinizm + naturalny no-det). Pod dropoutem **dostarczenie**
wyniku do trackera jest **stłumione** wg maski deterministycznej `maska = f(seed_maski, epizod)`.
Tracker mostkuje przerwę **jak przy naturalnym braku locku**: ZOH ostatniego boxu + rosnący `age`
(kontrakt D3 bez zmian — no-lock/AGE_MAX/ZOH). Model, env, ekspert, YOLO, parametry — **FROZEN**.

## Model
**FROZEN:** `ckpt/s3b2r/policy_gc5.pt` (S3b2-R, granica G1 = 67% / wrong-lock 10%). Zero treningu,
zero dźwigni.

## Oś FINALNA (pre-rejestrowana; korekta z T1 = BRAK)
- **Bernoulli** `p ∈ {0, 0.25, 0.5, 0.75}` — drop niezależny per tick dostarczenia.
- **Burst** `L ∈ {2, 5}` s — ciągłe okno przerwy; start **po pierwszym locku**, pozycja losowana
  ze `seed_maski` (offset `u`), okno = `[start, start+round(L/tick))`, tick = 1.0 s.
- **Sonda T1** (46550-46569, 20 ep, poza pomiarem): `p=0.5 → 30%`, `L=5 → 40%`. Reguła dostrojenia:
  oba w `[baza−5, baza]=[62,67]` → +p0.9 (nie); oba `≤15%` → +p0.1 (nie); **inaczej siatka bazowa
  bez zmian** (zastosowane). Oś jest gradientem (ani płaska, ani klif) — rozdzielczość adekwatna.

## Sceny pomiaru (parowanie)
**46500-46549 (50 ep/poziom), IDENTYCZNE między poziomami** — parowanie scen (ta sama scena w
każdym poziomie → różnica = wyłącznie dropout). Poziom `p=0` = **kontrola spójności** z
precondition-R (oczekiwanie ~67 ± szum binomialny; rozbieżność >10 pp → diagnoza przed dalszymi).

## Maski (pula 45100+, mapowanie zapisane)
| poziom | seed maski |
|---|---|
| p0.00 | 45100 |
| p0.25 | 45101 |
| p0.50 | 45102 |
| p0.75 | 45103 |
| L2 | 45104 |
| L5 | 45105 |
(sonda T1: probe_p0.50=45150, probe_L5=45151). Maska = `default_rng([seed_maski, seed_epizodu])`.

## Metryki per poziom (pre-rejestrowane)
- **sukces** (+ sd binomialne), **wrong-lock** (+ dekompozycja pierwszy-zły / kradzież / inne),
- **near-miss%** (udział porażek z min-dist ≤ 0.5 m),
- **efektywny no-det rate** (dropout + naturalny; + rozbicie na dropout i naturalny),
- **histogram age przy wejściu w dwell** (bins [0,.1,.25,.5,.75,1.01]).

## Poza zakresem
Trening, jakiekolwiek dźwignie, G1/sweep 46600-46649 (nietykalny), zmiany kontraktu/env, 3c, paper,
frozen. Sweep pozostaje CZYSTY do ewentualnego re-arm osobnym mandatem.
