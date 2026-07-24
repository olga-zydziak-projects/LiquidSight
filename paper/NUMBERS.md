# NUMBERS.md — liczby kanoniczne preprintu (W1, faza 3)

**Data:** 2026-07-24. **JEDYNE zrodlo liczb dla prozy W2** — zadna liczba nie
wchodzi do papieru inaczej niz przez ten plik. Kazda komorka ma zrodlo.
Rozbieznosci miedzy zrodlami oznaczone ⚠. **MIERZE = RAPORTUJE.**

Skroty zrodel: `MF`=MANIFEST_F3.json; `RF`=RAPORT_F3.md; `fA`=results/i3b/
fazaA_wynik.json; `prog`=results/i3b/progress.jsonl; `p2r`=results/
psanity_p2r.json; `p3r`=results/psanity_p3r.json; `Gru2`=results/
smoke_A_GRU_proc2.json; `I3A`=RAPORT_I3A.md; `I3AR`=RAPORT_I3AR.md;
`PR2`=RAPORT_PSANITY_R2.md; `DIAG`=RAPORT_DIAG_CFC.md; `A3`=ANEKS_3...md.

---

## T1 — Parytet rdzeni ramion (v1 i v2)

Referencja = rdzen GRU **27 648**; pasmo ±2% = **[27 095, 28 201]** (`MF gate_arms_v1/v2`).

### v1 (I3a, przed ANEKS-3) — `MF gate_arms_v1`; `I3A §1`
| ramie | konfiguracja rdzenia | rdzen param | delta% | glowa | w pasmie |
|---|---|---|---|---|---|
| A_GRU | GRUCell(78→64) | 27 648 | +0,00 | 390 | ✓ |
| A_NCP | CfC(78, AutoNCP(units=64,out=6,seed0)) | 27 571 | −0,28 | 42 | ✓ |
| A_CFC | CfC(78, units=53, backbone_layers=0) | 27 984 | +1,22 | 324 | ✓ |

### v2 (I3a-R, po ANEKS-3) — `MF gate_arms_v2`; `I3AR §1`
| ramie | konfiguracja rdzenia | rdzen param | delta% | glowa | w pasmie |
|---|---|---|---|---|---|
| A_GRU | GRUCell(78→64) | 27 648 | +0,00 | 390 | ✓ |
| A_NCP | CfC(78, AutoNCP(64,6,seed0)); readout stan pelny(64); ts=0,0833s manual | 27 571 | −0,28 | 390 | ✓ |
| A_CFC | CfCCell(78, hidden=64, backbone=69); ts=0,0833s manual | 27 787 | +0,50 | 390 | ✓ |

**⚠ Uwagi prowieniencji:**
1. A_CFC rdzen **rozny miedzy v1 (27 984) a v2 (27 787)** — inna konstrukcja
   (dense bez backbone → CfCCell z backbone). Oba w pasmie.
2. A_CFC v2 realizacja `hidden=64/bb=69` (27 787) **rozni sie od propozycji
   ANEKS-3 Z1** `hidden=70/bb=64` (27 736). Powod udokumentowany: symetria glow
   Linear(64→6)=390 (`I3AR §1`; `MF gate_arms_v2.opis`). Rozbieznosc rozwiazana,
   nie sprzeczna.
3. Glowy: v1 rozne (390/42/324) → v2 ujednolicone **390** we wszystkich (symetria
   twin; dla A_NCP element naprawy readoutu) (`MF gate_arms_v2`; `A3 Z3`).
4. ts sekundy v2 = **0,08333** (1/12 s, tik kamery 12 Hz) (`MF gate_arms_v2`; `A3 Z2`).

---

## T2 — Precondition FAZA A: wszystkie nogi (seed-po-seedzie)

Kryterium: srednia ≥90% z 10 seedow (45010–45019), poziom T0, eval 100 scen
(43000–43099). Wczesne rozstrzygniecie: **`S+(10−k)·100 < 900 → FAIL`**
(`F3_GATE §4`; `RF §1`). Zrodla wierszy: `fA`; `prog`; `RF §2-3`.

| ramie | lr | seedy: nominal% (45010→) | S | k | `S+(10−k)·100` | werdykt | srednia |
|---|---|---|---|---|---|---|---|
| A_NCP | 3e-4 | 22, 11 | 33 | 2 | 833 < 900 | **FAIL** | 16,5% |
| A_NCP | 1e-3 | 92, 79, 69, 49, [86, 77] | 289 | 4 | 889 < 900 | **FAIL** | 72,2% (k4) / 75,3% (6s) |
| A_CFC | 3e-4 | 18, 36 | 54 | 2 | 854 < 900 | **FAIL** | 27,0% |
| A_CFC | 1e-3 | 44, 57, 65 | 166 | 3 | 866 < 900 | **FAIL** | 55,3% |

`oper_lr = {}`; `any_cfc_pass = False` → **BRAMKA GRANICA** (`fA`).
Seedy 45014=86, 45015=77 policzone rownolegle **przed** rozstrzygnieciem k=4
(zachowane jako pomiar, nie zmieniaja werdyktu); batch 45016–45019 **nigdy
nieuruchomiony** (`RF §2`).
Srednia 6 seedow A_NCP@1e-3 = (92+79+69+49+86+77)/6 = 452/6 = **75,33%**;
srednia k4 = (92+79+69+49)/4 = 289/4 = **72,25 → 72,2%**.

---

## T3 — Pelne dane per cykl (13 cykli I3b) — `prog`; `RF §3`

Kolumny: nominal% | porazki | rollout DAgger r1→r2→r3 | best_val r0→r3 | best_epoch r0→r3 | sec_cykl.

### A_NCP @ 1e-3 (najlepsza noga)
| seed | nom% | porazki | rollout | best_val r0→r3 | best_epoch | sec_cykl |
|---|---|---|---|---|---|---|
| 45010 | **92** | dwell 8 | 44→32→53 | .000174→.000735→.000773→.000587 | 117,109,49,65 | 18 889,3 |
| 45011 | 79 | dwell 21 | 43→37→52 | .000153→.000552→.000761→.000696 | 118,90,43,39 | 19 138,1 |
| 45012 | 69 | dwell 31 | 25→11→36 | .000169→.001639→.001851→.001187 | 118,30,29,115 | 19 441,2 |
| 45013 | 49 | dwell 51 | 9→1→13 | .000184→.0015→.001835→.001711 | 119,41,26,37 | 18 986,6 |
| 45014 | 86 | dwell 14 | 32→12→37 | .000121→.00076→.001057→.000878 | 119,47,44,50 | 19 471,4 |
| 45015 | 77 | dwell 23 | 25→38→23 | .000152→.000646→.000952→.000934 | 119,52,35,92 | 18 992,2 |

### A_NCP @ 3e-4
| seed | nom% | porazki | rollout | best_val r0→r3 | best_epoch | sec_cykl |
|---|---|---|---|---|---|---|
| 45010 | 22 | dwell 76, tilt 2 | 22→13→25 | .000566→.001791→.001973→.001843 | 115,46,47,34 | 8 742,0 |
| 45011 | 11 | dwell 89 | 12→0→12 | .000721→.002559→.002478→.002428 | 115,45,46,40 | 19 081,3 |

### A_CFC @ 1e-3
| seed | nom% | porazki | rollout | best_val r0→r3 | best_epoch | sec_cykl |
|---|---|---|---|---|---|---|
| 45010 | 44 | dwell 56 | 0→8→44 | .000648→.001095→.000926→.000965 | 113,81,97,86 | 13 107,9 |
| 45011 | 57 | dwell 43 | 2→14→40 | .000631→.000708→.001072→.001127 | 115,81,104,100 | 14 810,0 |
| 45012 | 65 | dwell 35 | 0→34→44 | .00047→.000735→.001421→.001041 | 116,107,118,115 | 12 839,9 |

### A_CFC @ 3e-4
| seed | nom% | porazki | rollout | best_val r0→r3 | best_epoch | sec_cykl |
|---|---|---|---|---|---|---|
| 45010 | 18 | dwell 70, tilt 12 | 8→0→6 | .000887→.005571→.003664→.002938 | 118,37,56,53 | 7 154,3 |
| 45011 | 36 | dwell 64 | 2→0→8 | .000889→.004062→.003624→.002709 | 99,45,55,100 | 15 056,7 |

**Suma sec_cykl (13 cykli) = 205 710,9 s ≈ 57,1 h** skumulowanego compute
(policzone z `prog`; zgodne z „~57 h" `RF §3`). Wykonanie rownolegle 3–6-way
→ czas scienny znacznie krotszy (patrz T7, adnotacja niemiarodajnosci).

---

## T4 — Kontrola A_GRU (procedura v2) — `Gru2`; `RF §5-6`

| ramie | lr | seed | nominal | porazki | rollout DAgger | best_val r0→r3 | best_epoch | sec_cykl |
|---|---|---|---|---|---|---|---|---|
| A_GRU | 1e-3 | 45010 | **100%** | {} (dwell 0) | 18→100→100 | .000168→.000247→.000179→.000112 | 119,101,116,118 | 6 079,6 |

BC train_mse start→koniec = 0,155613 → 0,000106 (`Gru2`). Kontrola trzyma
best_val monotonicznie nisko przez wszystkie rundy — rozny rezim niz CfC (C6a).

---

## T5 — Drabina osi P2R (polityka) i P3R (ekspert)

### P2R — polityka dagger.pt, 50 ep/poziom, sceny 43100–43149 — `p2r`; `PR2 §1`
| poziom | K | rodzina | sukces% | katastrofy | dwell | tilt | pasmo [30,85] |
|---|---|---|---|---|---|---|---|
| T0 | 0 | A (pula) | 100,0 | 0 | 0 | 0 | >85 |
| T1 | 0 | A (held-out) | 100,0 | 0 | 0 | 0 | >85 |
| T2 | 0 | B | 64,0 | 1 | 17 | 1 | ✓ |
| T2a | 1 | B | 46,0 | 2 | 25 | 2 | ✓ |
| T2b | 2 | B | 36,0 | 3 | 29 | 3 | ✓ |
| T2c | 3 | B | 24,0 | 3 | 35 | 3 | <30 |
| T3 | 4 | B | 16,0 | 3 | 39 | 3 | <30 |

Poziomy w pasmie {T2, T2a, T2b}=3 → **P2R PASS** (≥2). Poziom bramki F3_GATE =
**T2b (36%)** (najciezszy w pasmie). Zgodnosc z R1: T0/T1/T2/T3 = 100/100/64/16
identyczne (`PR2 §1`).

### P3R — ekspert privileged, 50 ep/poziom, te same sceny — `p3r`; `PR2 §2`
| poziom | T0 | T1 | T2 | T2a | T2b | T2c | T3 | prog |
|---|---|---|---|---|---|---|---|---|
| sukces% | 100 | 100 | 100 | 100 | 100 | 100 | 100 | ≥95/poziom → **PASS** |

(T2a/T2b/T2c z `p3r`; T0–T3 cytowane z R1 w `PR2 §2`.)

---

## T6 — Smoke'y: linia restauracji przepisu (seed 45010, nominal)

| etap | procedura | ramie | lr | nominal% | rollout DAgger | porazki | zrodlo |
|---|---|---|---|---|---|---|---|
| **I3a** (v1, przed ANEKS-3) | BC-15+DAgger-10, continue, final-ep | A_NCP | 3e-4 | 12,0 | 2→6→0 | dwell77/tilt11 | `I3A §2` |
| I3a | v1 | A_NCP | 1e-3 | 19,0 | 1→0→0 | 75/6 | `I3A §2` |
| I3a | v1 | A_CFC | 3e-4 | 10,0 | 7→1→8 | 65/25 | `I3A §2` |
| I3a | v1 | A_CFC | 1e-3 | 18,0 | 1→3→3 | 81/1 | `I3A §2` |
| I3a | v1 | A_GRU | 1e-3 | **100,0** | 2→57→100 | — | `I3A §2` |
| **I3a-R** (v1, po ANEKS-3) | v1 | A_NCP | 3e-4 | 4,0 | 1→0→0 | 82/14 | `I3AR §2` |
| I3a-R | v1 | A_CFC | 3e-4 | 4,0 | 4→2→3 | dwell18/**tilt78** | `I3AR §2` |
| **I3a-R2** (v2, po ANEKS-4) | od-zera×4, best-val, 120 ep | A_NCP | 3e-4 | 22,0 | 22→13→25 | 76/2 | `prog` (smoke_A_NCP_proc2_lr3e-4) |
| I3a-R2 | v2 | A_CFC | 3e-4 | 18,0 | 8→0→6 | 70/12 | `prog` (smoke_A_CFC_proc2_lr3e-4) |
| I3a-R2 | v2 | A_NCP | 1e-3 | **92,0** | 44→32→53 | dwell8 | `prog` (smoke_A_NCP) |
| I3a-R2 | v2 | A_CFC | 1e-3 | 44,0 | 0→8→44 | dwell56 | `prog` (smoke_A_CFC) |
| I3a-R2 | v2 | A_GRU | 1e-3 | **100,0** | 18→100→100 | dwell0 | `Gru2` |

Trend restauracji (A_NCP): I3a 12% → I3a-R 4% (konstrukcja naprawiona, procedura
v1 psuje) → I3a-R2 22% (v2, 3e-4) → **92% (v2, 1e-3)**. Sygnatura: kazda
restauracja przesuwala ku frozen, lacznie niewystarczajaco do precondition
(`RF §5`).

---

## T7 — Czasy (jednostka kosztu programu)

**⚠ Adnotacja niemiarodajnosci:** czasy scienne cykli I3b (T3) pochodza z biegow
**rownoleglych 3–6-way** na jednym GPU (RTX 5070 Ti) — sa **niemiarodajne jako
koszt-per-ramie** (rywalizacja o GPU). Miarodajne per-ramie sa czasy SOLO ponizej.

### Koszt SOLO per cykl (jeden bieg na GPU)
| procedura | ramie | sec_cykl | uwaga | zrodlo |
|---|---|---|---|---|
| v1 (BC-15+DAgger-10×3) | A_GRU | ~444 s (7,4 min) | zgodny z P-SANITY R1 (~420 s) | `I3A §3` |
| v1 | A_NCP | ~662–675 s (11,2 min) | ncps per-step, launch-bound | `I3A §3` |
| v1 | A_CFC | ~492–544 s (8,7 min) | ncps per-step dense | `I3A §3` |
| v1 (pelny e2e z collect) | A_GRU | ~7,0 min (collect 113+BC 58,6+DAgger 362 s); e2e ~8,9 min | | `PR2 §5` |
| **v2** (od-zera×4, 120 ep) | A_GRU | **6 079,6 s (1,69 h)** SOLO | kontrola | `Gru2` |
| v2 | A_NCP | ~18 900–19 500 s (5,2–5,4 h) | z biegow I3b (mix solo/rownolegly) | `prog` |
| v2 | A_CFC | ~12 800–15 100 s (3,6–4,2 h) | jw. | `prog` |

Skala v1→v2: koszt cyklu rosnie ~10× (retrening od zera ×4 etapy po 120 ep vs
BC-15+DAgger-10×3), symetrycznie dla wszystkich ramion (`ANEKS_4 §Koszt`).
GRU v2 SOLO (6 080 s) << CfC v2 (~13–19,5 k s): CfC per-step (petla Pythona po
120 tikach) ~1,5× wolniejszy + wiecej ep efektywnych.

---

## T8 — Liczniki programu — `git log`; dokumenty

| licznik | wartosc | zrodlo |
|---|---|---|
| commity (liquidsight, faza 3) | **24** | `git rev-list --count HEAD` |
| aneksy instrumentalne | **4** (A1 obserwowalnosc, A2 drabina osi, A3 konstrukcja rdzeni, A4 procedura) | `DECYZJE_F3.md`; commity fadc6fe/82f163a/a29df7f/c499ad1 |
| bramki zamrozone | **P-SANITY** (f897bf0) + **F3_GATE kryterium** (c0b2367) + parytet v1 (9e4f57d) + parytet v2 (c332a90) | `git log` |
| restauracje przepisu | **4** (R1 backbone, R2 ts=s, R3 readout, R4 procedura) + dzwignia lr | `RF §5` |
| pelne cykle treningu I3b | **13** (+1 kontrola A_GRU) | `prog` (13 rekordow); `RF §3` |
| checkpointy zapisane (i3b) | **9** (4 rekordy z ckpt=null = zaimportowane ze smoke) | `prog`; `RF §3` |
| cykle dla pelnego n=10 (4 nogi) | **40** (hipotetyczne bez wczesnego rozstrzygania) | `RF §2`; C7 |
| skumulowany compute I3b | **~57,1 h** (205 711 s) | `prog` (suma sec_cykl) |
| seedy treningowe (precondition) | 45010–45019 (n=10), uzyte 45010–45015 | `F3_GATE §2`; `prog` |
| poziom bramki / prog OOD | T2b (K=2, 36%) / M > pooled_std, n=10 (nieosiagniete) | `F3_GATE §2,§5`; `PR2 §4` |

---

## T9 — P0 (companion, PASTIS twin) — domkniecie GAP-1

**⚠ ZRODLO TYMCZASOWE.** Ponizsze liczby pochodza z **promptu W2** (dyktowane),
oznaczone `[P0:prompt]`. `paper/sources/` **nie zawiera** RAPORT_P0 (sprawdzone
W2). **Do potwierdzenia z PDF w W3**: `RAPORT_P0, Tab. 1-3 + par. 5`. Do tego
czasu w prozie EN traktowac jako **[TODO-src: P0 PDF]**. Rezim: open-loop
klasyfikacja Sentinel-2 (pszenica/kukurydza), CfC vs GRU, wspolny enkoder CNN,
dropout obserwacji.

| metryka | CfC | GRU | uwaga | zrodlo |
|---|---|---|---|---|
| macro-F1 @ full cadence | 0,8802 ±0,0121 | 0,9073 ±0,0137 | GRU wyzej w nominale | `[P0:prompt]` |
| retencja R(0,6) | 0,6415 ±0,1138 | 0,5288 ±0,0622 | CfC wyzej pod dropoutem | `[P0:prompt]` |
| — margines retencji | \+0,1127 | — | pooled std 0,1759 → **null** (margines < pooled) | `[P0:prompt]` |
| crossover abs. F1 @ d=0,6 | 0,5642 ±0,0985 | 0,4798 ±0,0567 | CfC wyzej mimo startu −0,027 | `[P0:prompt]` |
| slope (F1 vs d) | −0,5095 | −0,6936 | CfC degraduje wolniej | `[P0:prompt]` |

**Stabilnosc rozrzutu wzgledem n (GAP-1: „granica = rozrzut populacyjny odporny
na n"):**
| n | margines retencji | pooled std | werdykt |
|---|---|---|---|
| 3 | \+0,1099 | 0,1706 | null (margines < pooled) |
| 15 | \+0,1127 | 0,1759 | null (margines < pooled) |

Interpretacja (lacznik do C3): margines i pooled std sa **niemal niezmienne
miedzy n=3 a n=15** — rozrzut populacyjny nie kurczy sie z n (to nie SEM);
granica jest wlasnoscia rozkladu miedzy-seedowego, nie brakiem probek. To ten
sam podpis, co w fazie 3 (A_NCP@1e-3 rozstep 43 pp). `[P0:prompt]`.

---

## Rozbieznosci zbiorczo (⚠)

1. **A_CFC rdzen v1 27 984 vs v2 27 787** — rozna konstrukcja, oba w pasmie (T1).
2. **A_CFC v2 realizacja 64/69 (27 787) vs propozycja ANEKS-3 70/64 (27 736)** —
   udokumentowane (symetria glow); rozwiazane (T1 ⚠2; `I3AR §1`).
3. **A_NCP@1e-3 srednia: 72,2% (k4) vs 75,3% (6 seedow)** — obie prawdziwe, rozny
   licznik seedow; werdykt na k4 (T2).
4. **Determinizm miedzy maszynami** — ROZWIAZANE (W2): szkielet i C8 poprawione
   na within-machine; cross-machine usuniete (`S0_NOTES.md:51-53`). Patrz GAP-2.
5. **Liczby P0 (T9)** — zrodlo tymczasowe `[P0:prompt]`; do potwierdzenia z
   RAPORT_P0 PDF w W3 (`paper/sources/` nie zawiera PDF). Patrz GAP-1.
