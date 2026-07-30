# RAPORT_S3B4 — G2: krzywa zrywanego strumienia semantycznego (charakteryzacja)

**Data:** 2026-07-30. **Sesja:** S3b4/G2. **Model FROZEN:** `ckpt/s3b2r/policy_gc5.pt` (S3b2-R).
**ZERO treningu, zero dźwigni.** RAMOWANIE: charakteryzacja (krzywa degradacji) — **BEZ progu
akceptacyjnego**. MIERZĘ = RAPORTUJE. Oś, sceny, metryki, parowanie pre-rejestrowane (`G2_GATE.md`).

## Mechanizm
Grounder odpytywany **co tick** (determinizm + naturalny no-det); pod dropoutem **dostarczenie** do
trackera stłumione wg maski `f(seed_maski, epizod)` (pula 45100+). Tracker mostkuje przerwę wg
kontraktu D3 (ZOH + rosnący age) — **kontrakt niezmieniony**. Sceny **46500-46549 (50 ep),
IDENTYCZNE między poziomami (parowanie)**.

## T1 — sonda rozdzielczości (46550-46569, 20 ep, poza pomiarem)
`p=0.5 → 30%`, `L=5 → 40%`. Reguła: oba w `[62,67]`→+p0.9 (nie); oba `≤15%`→+p0.1 (nie);
**inaczej siatka bazowa bez zmian** (zastosowane). Oś jest gradientem — rozdzielczość adekwatna.

## Kontrola spójności p0 vs precond-R — ZDIAGNOZOWANA (rozbieżność 13 pp)
p0 (50 ep, 46500-46549) = **80.0%**; precond-R (100 ep, 46500-46599) = **67.0%**; Δ=13 pp (>10 → diagnoza).
- p0 jest **deterministycznie identyczne** z mechaniką precond per-seed (bez dropoutu: reset, greedy
  act, grounder co tick, ZOH; dodatki eval_level = tylko odczyty GT-seg/stanu, nie zmieniają dynamiki).
  → p0(46500-46549) = precond zawężony do tych 50 seedów.
- **Przyczyna: trudność wewnątrz-komórkowa seedów, nie kompozycja.** Skład komórek K×A niemal
  identyczny w obu połówkach (9/8/9/8/8/8 vs 8/9/8/8/9/8). Pierwsze 50 seedów jest łatwiejsze
  (K8_A1 75% tu vs 43.8% na 100; K8_A0 100% vs 82.4%; K3_A0 88.9% vs 64.7%). wrong-lock identyczny
  (10% w obu) — brak anomalii/kontaminacji. Model/env/YOLO frozen.
- **Wniosek:** krzywa jest **parowana** (te same 50 scen w każdym poziomie) → degradacja mierzona
  względem **kotwicy parowanej p0=80%**; trudność sceny wyzerowana przez parowanie. Wartości
  bezwzględne są ~13 pp optymistyczne vs populacja 67%; **kształt krzywej (Δ vs p) jest ważny**.

## T3 — krzywa degradacji (50 ep/poziom, sd binomialne)

### Bernoulli (drop losowy per tick)
| p | sukces | sd | Δ vs p0 | wrong-lock | eff-no-det (drop/nat) | entered-dwell |
|---|---|---|---|---|---|---|
| **0.00** | **80.0%** | ±5.7 | — | 10.0% | 72.8% (0/72.8) | 45/50 |
| **0.25** | **66.0%** | ±6.7 | −14 | 12.0% | 79.0% (25.8/72.6) | 44/50 |
| **0.50** | **44.0%** | ±7.0 | −36 | 16.0% | 87.2% (47.2/75.2) | 38/50 |
| **0.75** | **30.0%** | ±6.5 | −50 | 14.0% | 93.6% (74.0/78.0) | 30/50 |

### Burst (ciągłe okno przerwy, start po pierwszym locku)
| L | sukces | sd | Δ vs p0 | wrong-lock | eff-no-det (drop/nat) | entered-dwell |
|---|---|---|---|---|---|---|
| **2 s** | **80.0%** | ±5.7 | **0** | 12.0% | 76.6% (20.0/72.8) | 45/50 |
| **5 s** | **76.0%** | ±6.0 | **−4** | 8.0% | 80.6% (50.0/72.4) | 44/50 |

```
sukces %   krzywa degradacji (parowana, kotwica p0=80)
 80 |●p0..........................●L2      Burst niemal płaski:
 76 |                              ●L5     ●───────────● (L2→L5, −4pp)
 66 |    ●p.25
 55 |
 44 |         ●p.50               Bernoulli spadek stromy:
 33 |              ●p.75          ●───●───●───● (~−0.65pp / pp dropoutu)
    +----+----+----+----+----
      0  .25  .50  .75   (Bernoulli p)
```

## Interpretacja mostkowania (ZOH + pamięć GRU) — WYNIK GŁÓWNY

**1. Ciągłość przerwy decyduje, nie jej objętość.** L5 usuwa 50% ticków (5/10) **ciągle** → −4 pp;
p0.50 usuwa ~47% ticków **losowo** → −36 pp. **Ta sama objętość utraty, różnica 32 pp.** Polityka
mostkuje pojedynczą lukę 2-5 s niemal idealnie (ZOH + pamięć rdzenia), ale rozproszona utrata
przerzedza **krytyczne odświeżenia** rozsiane po całym epizodzie.

**2. Świeżość kanału w momencie wejścia w dwell to mechanizm.** Histogram age przy wejściu w dwell
(bins [0,.1,.25,.5,.75,1.01]):
- p0: `[20,25,0,0,0]` — wszystkie świeże (age_n<0.25, <2 s).
- p0.50: `[10,16,4,0,8]` / p0.75: `[2,12,5,0,11]` — ogon w górnym binie (**8, 11 epizodów wchodzi w
  dwell z kanałem starym >6 s**) → utrata precyzji zawisu (ściana B4) → więcej porażek dwell.
- L5: `[13,28,3,0,0]` — **świeże jak p0**. Poza oknem burstu strumień jest nienaruszony, więc
  **końcówka dolotu wciąż dostaje świeże odświeżenia**. To mechanistycznie tłumaczy łagodność burstu:
  liczy się świeżość w terminalnym momencie dwell, a burst (zwykle) zostawia końcówkę nietkniętą,
  podczas gdy Bernoulli zatruwa ją równomiernie.

**3. Do jakiego p wykres „trzyma się bazy"?** W paśmie ~1 sd binomialnego (±6-7 pp) od kotwicy p0=80:
- **Bernoulli: do p≈0.25** (66% vs 80%, −14 pp ≈ 2 sd — brzeg pasma; degradacja już istotna).
- **Burst: przez całe L∈{2,5} s** (80/76%, w obrębie ~1 sd). Mostkowanie ciągłych przerw jest mocne.

**4. wrong-lock vs p — kradzież NIE rośnie pod dropoutem.** wrong-lock: 10→12→16→14% (Bernoulli),
8-12% (burst) — słaby wzrost, szczyt p0.50 (16%). **Dekompozycja: kradzież = 0 na WSZYSTKICH
poziomach**; pierwszy-zły ≤1; reszta = **„inne"** (in 5/6/8/6). Znaczenie: wzrost wrong-lock pod
dropoutem to **nie aktywna kradzież percepcyjna, lecz dryf polityki w martwym polu** przy
zagłodzonym/nieświeżym kanale (designated dostarczony wcześnie z daleka, brak odświeżeń przy
terminalu → dron dryfuje do innego obiektu bez podania mu błędnego boxu). Spójne ze ścianą 2
(pierwszy-zły/kradzież) jako problemem odrębnym — dropout jej nie napędza.

**5. Tryb porażki niezmienny.** near-miss% porażek pozostaje wysoki (90-96%) na wszystkich poziomach:
polityka wciąż **dolatuje** (near-miss), porażki to **precyzja dwell** (ściana B4) — dropout mnoży
ten sam tryb porażki, nie tworzy nowego. Efektywny no-det rośnie 73→94% (Bernoulli) głównie przez
składnik dropout (naturalny stabilny ~73-78%).

## Podsumowanie
Zrywany strumień semantyczny jest **mostkowany asymetrycznie**: pojedyncze ciągłe przerwy (burst do
5 s) niemal bez kosztu (ZOH+pamięć), rozproszona utrata (Bernoulli) degraduje stromo (~−0.65 pp/pp),
bo przerzedza świeżość kanału w terminalnym momencie dwell. Dropout **nie** wywołuje kradzieży locku
(kradzież=0); wzrost wrong-lock to dryf w martwym polu. Charakteryzacja bez progu; twierdzenia
progowe → RAPORT_3B. Sweep 46600-46649 **nietknięty/czysty**. Artefakty:
`results/s3b4/{probe,probe_decision,grid,measure}.json`.
