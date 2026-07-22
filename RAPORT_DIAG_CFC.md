# RAPORT_DIAG_CFC — diagnoza niesprawnosci ramion CfC (nominal-only)

**Data:** 2026-07-23
**Status:** **PRZYCZYNA USTALONA (z dowodem).** Niesprawnosc ramion CfC w I3a to **defekty KONSTRUKCJI rdzenia vs zlota referencja frozen v1.0/C1** (dzialajacy closed-loop CfC-32), NIE fundamentalna niezdolnosc CfC ani zle hiperparametry. Trzy defekty: **(1) brak backbone w A_CFC**, **(2) skala/kanal Δt (ncps.torch.CfC nie przyjmuje jawnego ts przy batch>1 -> arm uwieziony w ts=1.0; optimum to ts w sekundach)**, **(3) readout A_NCP z 6 neuronow motorycznych zamiast pelnego stanu.** Rekomendacja: **ANEKS-3 sciezka (A) — naprawa instrumentu (bug-fix)**. **Zero ewaluacji OOD**; sondy tylko nominal (43000-43099), krotkie (BC-8, bez DAgger), checkpointy w results/diag/. **MIERZĘ = RAPORTUJĘ.** Nic nie wdrozono na stale.

---

## 1. Zloty diff — CfC w liquidsight (bieg wiazacy) vs frozen v1.0/C1 (dzialajacy)

Zrodla frozen (czytane): `src/models.py` (CfCCell), `src/c1_models.py` (C1PolicyCfC/AutoNCP, WiredCfCCell), `src/c1_common.py` (ts=dt/TS_TICK), `src/c1_train.py` (recipe).

| aspekt | frozen C1 (100% closed-loop) | liquidsight (10-19%) | ryzyko |
|---|---|---|---|
| komorka | custom `CfCCell` (closed-form 'default') + custom `WiredCfCCell` | `ncps.torch.CfC` (dense) / `CfC(AutoNCP)` | wysokie |
| **backbone** | `Linear(in+h→64)+lecun_tanh` (JEST) | A_CFC `backbone_layers=0` (BRAK) | **wysokie** |
| **kanal Δt (ts)** | `ts=dt/TS_TICK` jawnie per-krok | `timespans=None` (ncps **odrzuca jawne ts przy batch>1** — bug) | **wysokie** |
| ts nominal | 48 Hz: dt=CTRL_DT → ts=1.0 | 12 Hz: brak jawnego ts; przy dt/CTRL_DT byloby 4.0 | wysokie |
| **A_NCP readout** | `head(h[:, motor])`, 6 motor z units=20 (30% stanu) | 6 motor z units=64 (9% stanu) | **wysokie** |
| normalizacja wejscia | `set_norm` (in_mean/in_std, Δt nietkniete) | brak | srednie |
| epoki / recipe | 120/rundę, **retrening OD ZERA + best-val** | BC 15 + DAgger 10, continue, final-epoch | srednie |
| lr / clip / batch | 1e-3 / 1.0 / 16 ep | {3e-4,1e-3} / 1.0 / 16 ep | niskie |

Uwaga: te same enkoder/glowa/budzet w liquidsight uczą **GRU do 100%** — wiec roznica GRU-vs-CfC lezy w rdzeniu CfC (komorka/backbone/ts/readout), nie w pipeline.

---

## 2. Mechanizm porazki (T2) — to NIE-DOLOT, wtornie jitter

Sondy BC-8 (bez DAgger), eval 50 nominal (43000-43049), metryki trajektorii. Kluczowy dyskryminator: **dolot→r_goal** (czy dron kiedykolwiek wchodzi w r_goal). Nominal jest u wszystkich niski (0-6%), bo bez DAgger (kowariancyjny shift — GRU tez wymaga DAgger by domknac hold).

| ramie/sonda | rdzen | BC MSE (koniec) | **dolot→r_goal** | hover_sp_var (jitter) | r_goal cross |
|---|---|---|---|---|---|
| gru (ref) | 27648 | 0.0026 | **37/50** | 0.0075 | 1.8 |
| **A_CFC bieg wiazacy** (ncps, bez bb) | 27984 | 0.0029 | **8/50** | 0.0094 | 0.4 |
| **A_NCP bieg wiazacy** (readout 6) | 27571 | **0.0220** | **8/50** | 0.0007 | 0.2 |

**Ustalenie:** obie konfiguracje wiazace CfC **nie DOSIEGAJA celu** (8/50), gdy GRU dosiega 37/50. To nie jest przede wszystkim jitter zawisu — to **awaria mapowania percepcja→setpoint / lokalizacji celu** (dron nie leci we wlasciwe miejsce). A_NCP dodatkowo **nie fituje nawet BC** (0.022 — waskie gardlo 6-neuronowego readoutu). Jitter (hover_sp_var) jest wtorny (nieco wyzszy u A_CFC bez backbone, 0.0094 vs 0.0075).

---

## 3. Sondy kontrolowane (T3) — jedna zmienna na sonde

### S1 — backbone i skala Δt (A_CFC)
| wariant | dolot→r_goal | hover_sp_var |
|---|---|---|
| ncps bez backbone (bieg wiazacy) | 8/50 | 0.0094 |
| **ncps Z backbone** | **35/50** | 0.0036 |
| frozen-cell, ts=1.0 | 15/50 | 0.0025 |
| **frozen-cell, ts=sekundy (0.0833)** | **39/50** | 0.0046 |
| frozen-cell, ts=4.0 | 9/50 | 0.0092 |

- **Backbone**: dodanie backbone do ncps CfC podnosi dolot **8→35** (≈GRU) i tnie jitter. Brak backbone = glowny defekt reaching.
- **Skala Δt**: przy poprawnej komorce (backbone+jawne ts) dolot silnie zalezy od ts: **sekundy(0.083)→39**, tick(1.0)→15, 4.0→9. ts=sekundy dorownuje GRU (37).
- **Kanal ts w biegu wiazacym jest zepsuty**: `ncps.torch.CfC` **odrzuca jawne `timespans` przy batch>1** (potwierdzone: scalar/`(B,1)`/`(B,)` → wyjatek; dziala tylko `None`=1.0). Native-Δt CfC — jedyny mechanizm tezy — jest w tej implementacji **nieuzywalny w treningu batchowym**; arm uwieziony w ts=1.0 (dolot 15).

### S2 — reżim bramki czasu po init (rozklad tau)
Napęd bramki `|t_a·ts|` po init skaluje sie z ts: 0.083→**0.010**, 1.0→0.125, 4.0→**0.501** (std bramki g: 0.038 / 0.053 / 0.147). Brak twardej saturacji przy init, ale przy **ts=4.0 bramka szeroko przelacza** (niestabilne aktualizacje stanu → dolot 9, jitter 0.0092); przy **ts=sekundy bramka ≈ stala** (σ(t_b), stabilny rdzen). Potwierdza S1: maly ts = stabilny reżim, duzy ts = niestabilny.

### S3 — readout A_NCP (motor vs stan pelny)
| readout | BC MSE (koniec) | dolot→r_goal |
|---|---|---|
| **6 neuronow motorycznych (bieg wiazacy)** | **0.0220** | **8/50** |
| **stan pelny (64)** | **0.0047** | **26/50** |

Czytanie tylko 6/64 neuronow **dławi A_NCP** (nie fituje BC, nie dosiega). Pelny stan → 4.7× nizszy BC MSE i 3× lepszy dolot. **Defekt konstrukcyjny ramienia** (frozen czytal 6/20=30%, moje 6/64=9%).

---

## 4. Ustalona przyczyna

Niesprawnosc ramion CfC to **suma trzech defektow konstrukcji rdzenia** wzgledem zlotej referencji, kazdy z dowodem:
1. **A_CFC bez backbone** (backbone_layers=0, wymuszony parytetem bez backbone) → nie dosiega celu (dolot 8/50 vs 35/50 z backbone).
2. **Kanal Δt zepsuty/suboptymalny**: `ncps.torch.CfC` nie przyjmuje jawnego ts przy batch>1 → ts uwieziony na 1.0 (suboptimum); optimum to ts w sekundach (dolot 39 vs 15), bo utrzymuje bramke czasu w stabilnym reżimie (S2).
3. **A_NCP readout 6-motor** zamiast pelnego stanu → nie fituje BC (0.022), nie dosiega (8/50); pelny stan naprawia (0.0047 / 26/50).

Dowod, ze to NIE fundamentalna niezdolnosc: **poprawnie zbudowana komorka (frozen-style, backbone, ts=sekundy) dosiega 39/50 ≈ GRU 37/50** przy identycznym BC-8 — czyli po DAgger (jak GRU: 2→57→100) domykalaby precondition. To **bug-fix, nie strojenie**: enkoder/glowa/budzet/lr/dane bez zmian; zmienia sie wylacznie wadliwa konstrukcja rdzenia (przywrocenie przepisu C1, ktory dzialal 100% closed-loop).

---

## 5. Propozycja tresci ANEKS-3 — sciezka (A): naprawa instrumentu (bug-fix)

**Uzasadnienie wyboru (A) nad (B):** przyczyna to defekty implementacji (backbone/ts/readout), nie hiperparametry — sweep (B) nie naprawi braku backbone ani zepsutego kanalu ts. (A) przywraca zloty przepis frozen C1.

Proponowany zakres zmian kodu (do zatwierdzenia przez czlowieka; **nie wdrozone**):
- **A_CFC**: zastapic `ncps.torch.CfC` komorka **frozen-style `CfCCell(input=78, hidden=70, backbone=64)`** (closed-form 'default', jak `frozen v1.0/models.CfCCell`) → **27 736 param rdzenia (+0.32%, w pasmie ±2%)**; **jawne ts w sekundach (0.0833)** per-krok (custom cell — brak buga ncps batch>1).
- **A_NCP**: readout z **pelnego stanu** (`Linear(units→6)`) zamiast 6 motor; **jawne ts w sekundach**; komorka wired w stylu frozen `WiredCfCCell` (maski AutoNCP na gestych macierzach — akceptuje ts). Re-solve `units` pod parytet ±2% (readout w glowie, nie w rdzeniu — parytet rdzenia zachowany).
- **Bez zmian**: enkoder (jak P-SANITY), glowa Linear(→6)+skalowanie, budzet (batch16/clip1.0/BC15/DAgger×3), lr {3e-4,1e-3}, dane i sceny F3_GATE, poziom bramki T2b, n=10.
- **Charakter**: bug-fix (przywrocenie dzialajacej komorki CfC z frozen), nie strojenie instrumentu na osi. Parytet rdzenia utrzymany; dowod parytetu naprawionych ramion → MANIFEST przed I3b.
- **Weryfikacja po aneksie (I3b/T3-smoke)**: powtorzyc smoke nominalny (BC+DAgger, seed 45010) — oczekiwane ≥90% nominal dla naprawionych ramion, potem precondition n=10.

**Alternatywa (B) — mini-sweep** (odrzucona jako pierwszy wybor): symetryczny sweep lr/epok WSZYSTKICH ramion z retreningiem A_GRU pod ta sama procedura. Nie adresuje braku backbone/readoutu; do rozwazenia tylko gdyby (A) nie domknela precondition.

---

## 6. Zgodnosc z zakresem
Zero OOD (tylko nominal 43000-43099). Bramka/aneksy/config/env/expert/frozen_v1/checkpoint sanity/models bieg wiazacy **nietkniete** — warianty sond wylacznie w `diag/`, checkpointy w `results/diag/`. Zadnej zmiany wdrozonej na stale. Sondy krotkie (BC-8, bez DAgger).

---

## STOP
Przyczyna: defekty konstrukcji rdzenia CfC (brak backbone; kanal Δt zepsuty w ncps + zla skala ts; readout A_NCP 6-motor) — dowiedzione sondami nominalnymi; poprawna komorka dosiega jak GRU. Rekomendacja: **ANEKS-3 sciezka (A)** — naprawa instrumentu. Decyzja i wdrozenie — czlowiek.
