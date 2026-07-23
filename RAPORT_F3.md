# RAPORT_F3 — bieg wiazacy I3b: GRANICA trenowalnosci CfC

**Data:** 2026-07-24
**Galaz:** **GRANICA** (par.4). **Brak werdyktu par.5** — teza F3_PRE0 nietestowalna w tym harnessie, bo ramie orzekajace (A_NCP) nie spelnia precondition.
**Status:** STOP par.4. FAZY B (A_GRU x10) i C (sweep OOD) **pominiete** (bramka po FAZIE A). **ZERO ewaluacji OOD.** **MIERZĘ = RAPORTUJĘ.**

---

## 0. Streszczenie

Po pelnej restauracji dzialajacego przepisu frozen C1 (konstrukcja rdzeni — ANEKS-3; procedura treningu — ANEKS-4) i po wyczerpaniu jedynej dozwolonej dzwigni (siatka lr {3e-4, 1e-3}, par.4), **zadne ramie CfC nie osiaga precondition ≥90% sukcesu nominalnego przy parytecie rdzeni** (27 648 ±2%). Najlepsza noga: **A_NCP @ 1e-3** — pojedynczy seed 92%, ale srednia 72–75% z **duza wariancja miedzy seedami (49–92%)**. Dominujaca porazka: **dwell** (nieprecyzyjne utrzymanie zawisu); tilt **wyeliminowany** przez naprawe procedury + lr. Kontrola **A_GRU pod identyczna procedura = 100%** (seed 45010, lr 1e-3), wiec harness i procedura sa sprawne — granica jest **specyficzna dla CfC przy parytecie**. To **komorka mapy programu (granica trenowalnosci)**, nie falsyfikacja tezy.

---

## 1. Kryterium i mechanika (par.4, zamrozone)

Precondition: srednia sukcesu nominalnego ≥90% z **10 seedow (45010–45019)**, poziom **T0**, eval 100 scen (43000–43099). Trening = procedura v2 (ANEKS-4: 4 etapy OD ZERA — BC=runda0 + DAgger 1..3, best-val, 120 epok/etap). Siatka lr {3e-4, 1e-3} — **jedyna** dozwolona dzwignia (reguła stopu ANEKS-4: zero zmian instrumentu). **Wczesne rozstrzygniecie arytmetyczne** (arytmetyka na zamrozonym kryterium): po k seedach z suma S, jesli `S + (10−k)·100 < 900` → noga FAIL.

---

## 2. Macierz precondition (FAZA A) — WSZYSTKIE NOGI FAIL

| ramie | lr | seedy (nominal %) | S | k (rozstrz.) | `S+(10−k)·100` | werdykt | śr. |
|---|---|---|---|---|---|---|---|
| A_NCP | 3e-4 | 22, 11 | 33 | 2 | 833 < 900 | **FAIL** | 16,5% |
| **A_NCP** | **1e-3** | 92, 79, 69, 49 (+86, 77) | 289 (452/6) | 4 | 889 < 900 | **FAIL** | **72,2% (k4) / 75,3% (6 seedow)** |
| A_CFC | 3e-4 | 18, 36 | 54 | 2 | 854 < 900 | **FAIL** | 27,0% |
| A_CFC | 1e-3 | 44, 57, 65 | 166 | 3 | 866 < 900 | **FAIL** | 55,3% |

`oper_lr = {}` (zadne ramie nie ma lr operacyjnego). `any_cfc_pass = False` → **BRAMKA GRANICA**.
(Seedy 45014=86, 45015=77 policzone rownolegle przed rozstrzygnieciem k=4 — zachowane jako pomiar, nie zmieniaja werdyktu; batch 45016–45019 **nigdy nie uruchomiony** — reguła oszczedzila kompletny batch.)

---

## 3. Pelne dane per seed (13 pelnych cykli)

Kolumny: nominal% | porazki | rollout DAgger (r1→r2→r3) | best_val (r0→r3) | best_epoch (r0→r3) | czas cyklu.

**A_NCP @ 1e-3** (najlepsza noga):
| seed | nom% | porazki | rollout | best_val r0→r3 | best_ep | s |
|---|---|---|---|---|---|---|
| 45010 | **92** | dwell 8 | 44→32→53 | .000174→.000587 | 117,109,49,65 | 18889 |
| 45011 | 79 | dwell 21 | 43→37→52 | .000153→.000696 | 118,90,43,39 | 19138 |
| 45012 | 69 | dwell 31 | 25→11→36 | .000169→.001187 | 118,30,29,115 | 19441 |
| 45013 | 49 | dwell 51 | 9→1→13 | .000184→.001711 | 119,41,26,37 | 18987 |
| 45014 | 86 | dwell 14 | 32→12→37 | .000121→.000878 | 119,47,44,50 | 19471 |
| 45015 | 77 | dwell 23 | 25→38→23 | .000152→.000934 | 119,52,35,92 | 18992 |

**A_NCP @ 3e-4:** 45010=22% (dwell76,tilt2; rollout 22→13→25); 45011=11% (dwell89; 12→0→12).
**A_CFC @ 1e-3:** 45010=44% (dwell56; 0→8→44); 45011=57% (dwell43; 2→14→40); 45012=65% (dwell35; 0→34→44).
**A_CFC @ 3e-4:** 45010=18% (dwell70,tilt12; 8→0→6); 45011=36% (dwell64; 2→0→8).

**Kontrola A_GRU @ 1e-3, seed 45010 (procedura v2):** **100%** (dwell 0), best_val r0→r3 = .000168→.000112, rollout DAgger 18→100→100.

Checkpointy (9 biegow i3b) w `results/i3b/ckpt/`; pelny log w `results/i3b/progress.jsonl`. Laczny czas treningu: ~57 h skumulowanego compute (13 cykli, wykonane rownolegle 3–6-way).

---

## 4. Sygnatura granicy (mechanizm)

1. **BC fituje znakomicie, agregat DAgger — nie.** Dla wszystkich CfC best_val po samym BC (r0) jest bardzo niski (~0.00012–0.0009), ale po agregacji DAgger (stany odwiedzane przez polityke) best_val **rosnie** (r1–r3), a best_epoch robi sie **wczesny** (np. A_NCP@1e-3 s45013: 119→41→26→37). To znaczy: **CfC przy parytecie nie domyka dopasowania do poszerzonej dystrybucji DAgger** tak dobrze, jak do czystego BC eksperta. Kontrola A_GRU trzyma best_val nisko przez wszystkie rundy (.000168→.000112) — **rozny rezim**.
2. **Tilt wyeliminowany, zostaje dwell.** Naprawa procedury (ANEKS-4) + lr 1e-3 usunela niestabilnosc: **0 tilt na 1e-3** (vs 78/100 przed ANEKS-4). Rezydualna porazka to **dwell** — dolot poprawny, ale utrzymanie w r_goal przez t_dwell nieprecyzyjne.
3. **Wysoka wariancja miedzy seedami.** A_NCP@1e-3: 49–92% (rozstep 43 p.p.). GRU (kontrola) = 100% stabilnie. CfC przy parytecie jest **niekonsystentny** — to jadro granicy: nie „nie uczy sie", lecz „uczy sie niestabilnie i dwell-limited, srednio ponizej 90%".

---

## 5. Cztery restauracje przepisu (kazda z dowodem) + dzwignia lr

Program przywracal dzialajacy przepis frozen v1.0 (C1) etapami, kazdy z prowieniencja:

| # | restauracja | zrodlo/dowod | efekt |
|---|---|---|---|
| DIAG | diagnoza rozbieznosci CfC vs frozen C1 | RAPORT_DIAG_CFC | lokalizacja 4 defektow |
| R1 | konstrukcja: backbone rdzenia | ANEKS-3 Z1 (c1_models.py) | BC-only stabilny |
| R2 | konstrukcja: ts w SEKUNDACH (jawny) | ANEKS-3 Z2 | poprawny rezim czasowy |
| R3 | konstrukcja: readout PELNEGO stanu (64) | ANEKS-3 Z3 | dolot 8→26/50 |
| R4 | procedura: od-zera + best-val + 120 epok | ANEKS-4 (c1_train.py:37,39,127-131,135,151-156,181-196) | tilt 78→0..12; nominal 4%→do 92% (1 seed) |
| lr | dzwignia par.4: 1e-3 zamiast 3e-4 | siatka par.4 | A_NCP 17%→92% (seed 45010) |

Kumulatywnie: tilt zniknal, najlepszy pojedynczy seed skoczyl z ~4% do **92%** — ale **srednia z 10 seedow nie przekracza 90%** na zadnej nodze. Wszystkie cztery restauracje byly **konieczne** (kazda przesuwala CfC ku frozen), lacznie z lr — a mimo to **niewystarczajace** do precondition przy parytecie.

---

## 6. Kontrola: procedura i harness sprawne

A_GRU pod **identyczna** procedura v2 i lr 1e-3 osiaga **100%** (seed 45010), best_val monotonicznie niski. To wyklucza tezy „procedura zepsuta" / „harness nieuczalny" / „ekspert wadliwy". **Granica jest wlasnoscia CfC przy parytecie param + tym budzecie treningu**, nie instrumentu. Defekt (gdyby byl) dzialalby przeciw ramieniu faworyzowanemu — tu instrument jest czysty, a mimo to CfC nie domyka.

---

## 7. Higiena tezy i zakres

- **Zero OOD** przez cala faze (tylko nominal 43000–43099 + poziom T0). FAZY B, C **pominiete** przez bramke — zaden wynik OOD nie zostal obejrzany, wiec par.5 pozostaje nietkniety i niepodwazony.
- Reguła stopu ANEKS-4 **dochowana**: jedyna uzyta dzwignia to lr z siatki par.4; zero zmian konstrukcji/procedury/env/eksperta/scen/danych.
- F3_GATE par.2–7, P_SANITY, env/, expert/, config/, frozen_v1/, checkpoint sanity, ~/liquidflight/ — **nietkniete**. Raporty poprzednie (I1/I2/DIAG/I3AR) nietkniete.
- Seedy pojedyncze **nie wykluczane ani naprawiane** (par.4); zero crashy/NaN (0 retry infrastrukturalnych).

---

## 8. Decyzje czlowieka — framing wyniku 3a i przejscie do 3b

**Wynik fazy 3a:** zmierzona **granica trenowalnosci rdzeni ciagloczasowych (CfC dense + CfC/AutoNCP)** w harnessie vision-twin fly-to-target, przy **parytecie rdzeni 27 648 ±2%**, budzecie **BC-120 + DAgger×3 (od zera, best-val)** i nadzorze ekspert-DAgger. Przy tych warunkach CfC uczy sie **niestabilnie miedzy seedami i dwell-limited**, ze srednia ponizej progu 90%; GRU — stabilnie 100%.

**Czego to NIE jest:** to **nie falsyfikacja F3_PRE0**. Teza (liquid > GRU na przesuniecie percepcyjne) wymaga ramienia orzekajacego A_NCP na precondition; bez precondition **testu nie ma**. Wynik jest komorka mapy, nie wyrokiem o tezie.

**Opcje przejscia do 3b (poza mandatem tego biegu — wymagaja nowego pre-rejestru):**
- **(a) Wyzszy budzet treningu, SYMETRYCZNIE** dla wszystkich ramion, do progu gdzie A_NCP osiaga precondition (parytet budzetu zachowany) — najblizsze duchowi tezy; ryzyko: GRU tez rosnie, wiec pojedynek dalej uczciwy.
- **(b) Zluzowanie parytetu param** (CfC z wieksza pojemnoscia) — **zmienia teze** (nie byloby juz „przy parytecie rdzenia"); do jawnej decyzji.
- **(c) Inny task/horyzont/harness**, gdzie przewaga ciaglego czasu jest silniejsza (dluzsze zaleznosci, zmienne dt) — nowa komorka mapy.
- **(d) Raport granicy jako wynik 3a** i publikacja mapy programu bez werdyktu pojedynku.

Rekomendacja robocza: **(a)** jako nastepny pre-rejestr (utrzymuje rdzen tezy: parytet + rowny budzet), z A_NCP@1e-3 jako punktem startowym (najblizej progu: 92% best seed, 75% srednia).

---

## STOP

**Galaz: GRANICA.** Zadne ramie CfC nie spelnilo precondition par.4 na zadnej nodze lr. Srednie nog: A_NCP 3e-4=16,5% / 1e-3=72,2%(k4); A_CFC 3e-4=27,0% / 1e-3=55,3%. Rozstrzygniecia arytmetyczne przy k=2/4/2/3 seedach. Dominujacy typ porazki: **dwell** (tilt wyeliminowany). Brak werdyktu par.5 (A_NCP nie uczestniczy). Zero OOD. Nastepny ruch = decyzja czlowieka (rekom. (a): symetryczny wzrost budzetu, nowy pre-rejestr 3b).
