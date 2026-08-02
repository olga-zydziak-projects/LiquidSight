# RAPORT_3D — mikro-filtr temporalny kanału celu: pomiar i werdykt

**Data:** 2026-08-03. **Sesja:** 3d/M (pomiar). **Podstawa:** `PRE_3D0.md` (RATYFIKOWANE w całości
2026-08-02), `RECON_3D.md`. **System ZAMROŻONY:** polityka `ckpt/s3b2r/policy_gc5.pt`, kanał
`Tracker5`, env, percepcja — nietknięte; filtr wpięty jako drop-in na `target5[0:4]` (age_n
nietknięte). **Zasada:** MIERZĘ = RAPORTUJE. Werdykt dwustronny; **wynik negatywny jest wynikiem**.
Każda liczba krosowana z JSON w `results/s3d/` (§9). Sweep G1 46600–46649 nietknięty.

---

## 1. Streszczenie

Hipoteza: mikro-filtr temporalny na kanale celu poprawia sukces end-to-end pod degradacją łącza, a
rdzeń continuous-time (CfC, A3) robi to lepiej niż odpowiedniki bez natywnego mechanizmu czasu.
**Pomiar obala hipotezę w obie strony jej istotnych składowych.** Filtry uczone **redukują** offline
RMSE boxa o ~43% (0,131 → 0,074 vs duch ZOH) i **wszystkie trzy** przechodzą precondition P-3D — a
mimo to **pogarszają sukces w zamkniętej pętli na każdej z trzech nóg**. Werdykt pierwotny:
**NEGATYWNY** (Δ = succ(A3) − max(A0,A1,A2) = 33,2 − 39,0 = **−5,8 pp**, |Δ| > pooled_std = 1,57).
Porządek jest **monotoniczny i pouczający**: **A0 (brak filtra) > A1 (Kalman ≈ ZOH) > A2 (GRU) > A3
(CfC)** — im mocniej filtr przekształca kanał z semantyki ZOH, tym gorzej. Oba ramiona uczone są
**NIETRANSPARENTNE** (psują czystą bazę o 8–10 pp). Rdzeń continuous-time **nie daje przewagi** —
A2 (GRU) jest wszędzie ≥ A3 (CfC).

Domknięcie: w pętli zamkniętej **A3 (CfC) jest najlepszym estymatorem boxa** (najniższy online RMSE
na każdej nodze) i **najgorszym systemem** — uporządkowanie po jakości boxa jest dokładnie odwrotne
do uporządkowania po sukcesie.

Główny wynik naukowy: **poprawa metryki zastępczej (RMSE boxa) anty-koreluje z wartością end-to-end**
dla zamrożonej polityki uczonej na duchu ZOH. Wygładzony/ekstrapolowany box to shift wejścia (kuzyn
F-3b-1); klasyk (Kalman) też nie pomaga. **Duch ZOH, na którym polityka była trenowana, jest
optymalnym wejściem** — filtrowanie kanału to ślepy zaułek dla tej zamrożonej polityki.

---

## 2. Werdykt pierwotny (zamrożony, PRE_3D0 §6)

Metryka pierwotna: sukces na nodze **p=0,5**, N=100 (46500–46599), parowane; A0/A1 jeden bieg, A2/A3
średnia po 5 seedach filtra (45040–45044).

| ramię | succ p50 | per-seed (A2/A3) | sd po seedach |
|---|---|---|---|
| **A0** no-filter | **39,0** | — | — |
| **A1** Kalman-CV | **37,0** | — | — |
| **A2** mikro-GRU | **34,0** | 32 / 33 / 35 / 36 / 34 | 1,41 |
| **A3** mikro-CfC | **33,2** | 33 / 32 / 34 / 31 / 36 | 1,72 |

```
pooled_std = sqrt((sd_s(A2)² + sd_s(A3)²)/2) = sqrt((1,414² + 1,720²)/2) = 1,575   (F3-GATE §5)
Δ = succ(A3) − max(succ(A0), succ(A1), succ(A2)) = 33,2 − 39,0 = −5,8
−5,8 < −1,575  ⇒  WERDYKT: NEGATYWNY
```

A3 (rdzeń orzekający) jest istotnie gorszy niż najlepsza alternatywa — którą jest **A0 (brak
filtra)**. `results/s3d/verdict_3d.json`.

---

## 3. Wynik główny: rozjazd precondition ↔ pętla zamknięta

To najostrzejszy pomiar fazy. Filtry uczone **miażdżą** offline RMSE boxa, a to **nie przekłada się**
na sukces — przeciwnie.

| ramię | offline RMSE (val, precond P-3D) | vs ZOH | succ p50 (pętla) | vs A0 |
|---|---|---|---|---|
| A0 / ZOH | **0,1309** | — | **39,0** | — |
| A1 Kalman | 0,1299 | −0,8% (PASS) | 37,0 | −2,0 |
| A2 GRU | 0,0741 | **−43,4%** (PASS) | 34,0 | −5,0 |
| A3 CfC | 0,0745 | **−43,1%** (PASS) | 33,2 | −5,8 |

**Precondition P-3D (§5 PRE) spełniony przez wszystkie trzy ramiona** (RMSE < ZOH na wstrzymanym
48300–48399, maska = etykieta ∧ lock, pokrycie 0,117; `results/s3d/precond_p3d.json`). A jednak
**kierunek w pętli jest odwrotny do siły offline**: im niższy RMSE, tym niższy sukces (A2/A3 mają
RMSE 2× lepszy niż Kalman, a sukces gorszy). Metryka zastępcza „box bliżej GT" **anty-koreluje** z
wartością dla zamrożonej polityki. Mechanizm §7.

To empirycznie potwierdza nazwane ryzyko `PRE_3D0 §3/§7.1`: polityka uczona na **semantyce ducha
ZOH** traktuje wygładzony/ekstrapolowany box jako **poza-rozkładowy** — dokładnie kuzyn F-3b-1
(zdegenerowane/przesunięte wejście jako mina OOD).

---

## 4. Constraint transparencji (noga clean)

`succ(ramię) ≥ succ(A0) − 3 pp` (A0 clean = 67,0; próg = 64,0).

| ramię | succ clean | status |
|---|---|---|
| A0 | 67,0 | — (kotwica; reprodukuje granicę precond-R 67/10 **bit-w-bit**) |
| A1 Kalman | 64,0 | **OK** (= próg 64,0) |
| A2 GRU | 58,6 | **NIETRANSPARENTNE** (−8,4 pp) |
| A3 CfC | 56,8 | **NIETRANSPARENTNE** (−10,2 pp) |

Oba ramiona uczone są nietransparentne niezależnie od wyniku na dropoucie: psują czystą bazę o
8–10 pp. Kalman jest transparentny na styk, ale i tak net-negatywny na dropoucie (§2). A0 clean =
**67,0% / wrong-lock 10,0%** — pomiar wierny (identyczny z granicą 3b).

---

## 5. Metryki wtórne (poza werdyktem)

### 5.1 wrong-lock per noga (średnia po seedach dla A2/A3)
| noga | A0 | A1 | A2 | A3 |
|---|---|---|---|---|
| clean | 10,0% (kradzież 3) | 8,0% (2) | 13,2% (kradzież 3,6) | 11,4% (kradzież 4,0) |
| p50 | 15,0% (1) | 13,0% (1) | 16,6% (1,4) | 14,8% (1,6) |
| L5 | 10,0% (1) | 10,0% (2) | 13,4% (3,4) | 11,8% (3,2) |

Filtry **nie zachowują** pożądanej własności (brak wzrostu kradzieży): wrong-lock rośnie o ~2–3 pp,
a kradzież na clean rośnie z **3 → ~4** — filtr ekstrapolujący ruch w martwym polu dryfuje/kradnie
lock (nazwane ryzyko `PRE_3D0 §7.2`). **Uwaga o kotwicy:** G2 raportował kradzież=0 (50 ep,
46500–46549); tu baza A0 ma kradzież=3 (100 ep, 46500–46599). To **nie sprzeczność**, lecz znana
niestabilność dekompozycji wrong-lock (RAPORT_3B §3: R6=5/R7=6); własność zachowania odnoszę do
bazy A0 w tym biegu, nie do zera.

### 5.2 RMSE boxa ONLINE (pętla zamknięta, podzbiór n=30, 46500–46529)
Dense GT per tik; filtr/ZOH vs GT (maska ∧ lock). `results/s3d/rmse_online.json`.

| noga | A0 (ZOH) | A1 Kalman | A2 GRU (s45041) | A3 CfC (s45041) |
|---|---|---|---|---|
| clean (n=30) | 0,1116 | 0,1087 | 0,0752 | **0,0703** |
| p50 (n=24) | 0,1286 | 0,1271 | 0,0917 | **0,0876** |
| L5 (n=30) | 0,1241 | 0,1310 | 0,0769 | **0,0718** |

**To ZAOSTRZA paradoks §3, nie łagodzi.** W pętli zamkniętej filtry uczone mają box RMSE o ~35–45%
niższy niż ZOH — a **A3 (CfC) jest NAJLEPSZYM estymatorem boxa na KAŻDEJ nodze** (najniższy online
RMSE), będąc jednocześnie **NAJGORSZYM w sukcesie** (§2). Anty-korelacja jest monotoniczna i pełna:
uporządkowanie po jakości boxa (A3 < A2 < A1 < A0 RMSE) jest **dokładnie odwrotne** do uporządkowania
po sukcesie (A0 > A1 > A2 > A3). „Lepszy box" nie jest tylko nieinformatywny dla sukcesu tej
zamrożonej polityki — jest **anty-predykcyjny**. (n=24 na p50: 6/30 epizodów pod dropoutem nie miało
tików z GT-on-frame ∧ lock; udokumentowane, bez cichego capu.) `results/s3d/rmse_online.json`.

### 5.3 rozkład age przy wejściu w dwell + liczba wejść
Age (bins `[0,.1,.25,.5,.75,1.01]`) — age_n nietknięte przez filtr, ale **liczba epizodów
wchodzących w dwell spada z filtrem**:

| | A0 clean | A2 clean | A0 p50 | A2 p50 |
|---|---|---|---|---|
| hist | [44,38,1,0,0] | [43,26,0,0,0] | [20,26,6,0,13] | [18,20,2,0,13] |
| **weszło w dwell** | **82** | **69** | **65** | **53** |

To bezpośredni dowód mechanizmu (§7): filtr degraduje **fazę dolotu** (mniej epizodów w ogóle
dochodzi do celu), nie tylko terminalny zawis. Ogon age>6 s (bin 5) pod p50 pozostaje (13 epizodów)
— filtr go nie usuwa (bo age jest prawdziwe, z założenia).

### 5.4 asymetria burst (zachowana)
A0: p50 39,0 vs L5 63,0 — asymetria G2 (ciągła przerwa mostkowana lepiej niż rozproszona) jest
zachowana we wszystkich ramionach; filtr nie zmienia jakościowego kształtu G2, tylko obniża poziom.

---

## 6. A2 vs A3 — hipoteza continuous-time obalona

Parytet §2 dotrzymany: A2 GRU **3140** param, A3 CfC **3177** param (|Δ|/max = **1,16%** ≤ 2%; oba
≤ 4000; identyczne wejście `[bx,by,bw,bh,has_delivery,age_n]` / wyjście `[cx,cy,w,h]` / procedura
treningu — lr 1e-3, 300 epok, batch 32, clip 1,0, best-val). Różnica: A3 podaje ts=1/12 s w
SEKUNDACH do CfCCell (przepis frozen ANEKS-3), A2 podaje age_n jako cechę.

| | offline RMSE (val, med) | succ clean | succ p50 | succ L5 |
|---|---|---|---|---|
| A2 GRU | 0,0741 | 58,6 | **34,0** | 58,2 |
| A3 CfC | 0,0745 | 56,8 | **33,2** | 55,4 |

A2 (GRU) jest **wszędzie ≥ A3 (CfC) w SUKCESIE** — offline (median RMSE marginalnie) i we wszystkich
trzech nogach. **Natywny mechanizm czasu nie daje przewagi w sukcesie**; jeśli cokolwiek, CfC jest
marginalnie gorszy. Składowa hipotezy „CfC lepszy niż nie-CT" jest **obalona** (kierunek przeciwny;
|Δ_A2−A3| < pooled_std na p50 → różnica A2/A3 w sukcesie sama w sobie NIEISTOTNA, ale konsekwentna).

**Paradoks w mikroskali A2 vs A3.** W ONLINE RMSE boxa (§5.2) jest **odwrotnie**: **A3 (CfC) jest
lepszym estymatorem** niż A2 (GRU) na każdej nodze (clean 0,070 vs 0,075; p50 0,088 vs 0,092; L5
0,072 vs 0,077). Czyli rdzeń continuous-time robi **lepszy filtr**, a **gorszy system**. To
domyka tezę §3 na poziomie samej pary uczonej: jakość estymaty boxa i wartość end-to-end są
**rozłączne, wręcz przeciwstawne** dla zamrożonej polityki na duchu ZOH.

---

## 7. Mechanizm i interpretacja

**Dlaczego lepszy box daje gorszy sukces?** Polityka `policy_gc5` była trenowana (S3b2-R) na kanale
o semantyce **ducha ZOH**: box zamrożony między dostarczeniami 1 Hz, skokowo aktualizowany, z age
rosnącym liniowo. To jest rozkład, na którym rdzeń GRU polityki nauczył się kojarzyć „stan kanału →
setpoint". Filtr — nawet gdy zbliża box do GT — produkuje **trajektorię boxa niewidzianą w
treningu**: gładką, interpolowaną, ekstrapolującą ruch. Dla zamrożonej polityki to **przesunięcie
dystrybucji wejścia** (kuzyn F-3b-1: cecha, której statystyka odbiega od treningowej, degraduje
zachowanie, choć „obiektywnie" niesie więcej informacji).

Dowód mechanistyczny (§5.3): z filtrem **mniej epizodów dochodzi do celu** (dwell-entry clean
82→69, p50 65→53). Degradacja jest w **fazie dolotu** (polityka źle interpretuje wygładzony box),
nie w terminalnym zawisie — spójne z 3b (ściana B4 leży w wykonawcy, kanał jej nie napędza; tu
odwrotnie potwierdzone: „naprawa" kanału nie pomaga, a szkodzi dolotowi).

**Monotoniczność A0>A1>A2>A3** domyka argument: A1 (Kalman ≈ ZOH, RMSE prawie identyczny) szkodzi
minimalnie; A2/A3 (RMSE 2× niższy, box mocno przekształcony) szkodzą najmocniej. **Wielkość shiftu
wejścia, nie jakość estymaty, przewiduje szkodę.**

**„Klasyk wystarcza"? Nie.** Wynik nie jest „Kalman wystarcza" (PRE §7.4) — Kalman też jest
net-negatywny (−2 pp p50). Właściwym wnioskiem jest: **żaden filtr nie pomaga; duch ZOH (brak
filtra) jest optymalnym wejściem** dla tej zamrożonej polityki. Poprawa percepcji kanału wymagałaby
**współtreningu polityki** (wariant odrzucony w PRE §3, bo łamie zamrożenie) — sam drop-in nie
wystarcza i szkodzi.

---

## 8. Rozbieżności odnotowane (jawnie)

1. **Precondition PASS vs werdykt NEGATYWNY.** Nie sprzeczność — to wynik główny (§3). Precondition
   (RMSE offline) NIE jest tezą (PRE §5); mierzy zdolność rekonstrukcji kanału, nie wartość
   end-to-end. Rozjazd jest raportowanym odkryciem.
2. **kradzież: G2=0 vs A0=3.** Różne pule (50 ep 46500–46549 vs 100 ep 46500–46599) i znana
   niestabilność dekompozycji (RAPORT_3B §3). Własność „brak wzrostu kradzieży" odnoszona do bazy
   A0 tego biegu, nie do zera bezwzględnego (§5.1).
3. **A0 p50 39% (tu) vs G2 p0.5 44% (50 ep).** Pełna pula 46500–46599 jest trudniejsza niż pierwsza
   połowa (RAPORT_S3B4: pierwsze 50 seedów ~łatwiejsze); parowanie wewnętrzne (A0 kotwicą) czyni
   porównanie ramion ważnym, liczby G2 są referencją zewnętrzną (zgodnie z notą porównywalności
   PRE §6).
4. **A0 L5 63% (tu) vs G2 L5 76% (50 ep).** Jak (3); asymetria burst zachowana jakościowo.

---

## 9. Tabela źródeł i sha256

| twierdzenie | liczba | źródło (results/s3d/) | sha256[:16] |
|---|---|---|---|
| werdykt / pooled_std | NEGATYWNY / Δ −5,8 / 1,575 | `verdict_3d.json` | ec0cee350d7184d0 |
| precondition | ZOH 0,1309 / A1 0,1299 / A2 0,0741 / A3 0,0745 | `precond_p3d.json` | 4e3f26f3af34cc78 |
| A0 p50 | 39,0% | `eval_A0_p50.json` | ed52e8f23b5d0db3 |
| A3 s45040 p50 | 33,0% | `eval_A3_s45040_p50.json` | 4dabe4a868474b09 |
| dane treningowe | 300 ep, GT-cov 0,166 | `data_train.npz` | a889c48716ccee3d |
| dane walidacyjne | 100 ep, GT-cov 0,161 | `data_val.npz` | bc24dff817f7c301 |
| Kalman Q/R | q=0,03 r=0,1 | `kalman_qr.json` | — |
| trening filtrów | A2/A3 5 seedów, best-val | `train_log_all.json` | — |
| RMSE-online (n=30) | A3 najniższy / A0 najwyższy (§5.2) | `rmse_online.json` | 3d6d41da566b5f20 |

Wszystkie 36 biegów pomiaru: `eval_{A0,A1,A2_s45040..44,A3_s45040..44}_{clean,p50,L5}.json`.
Werdykt/transparencja liczone `s3d/verdict.py`; parowanie = te same 100 scen/maski dla ramion
(clean bez maski; p50 maska 45102; L5 maska 45105 — rodzina G2).

---

## 10. Higiena i zgodność z PRE

- **Zamrożone nietknięte:** polityka/kanał/env/percepcja — czysty drop-in na `target5[0:4]`;
  `target5[4]` (age_n) prawdziwe (weryfikacja: age-hist §5.3 identyczna semantyka jak G2).
- **Kryteria zamrożone przed pomiarem:** werdykt, transparencja, N=100, pule (48000–48299 train /
  48300–48399 val / maski 45200–45202 train, 45102/45105 pomiar / init 45040–45044) — wszystkie z
  ratyfikowanego PRE_3D0; **zero strojenia po zobaczeniu wyników**.
- **Parytet A2↔A3** dotrzymany (1,16% ≤ 2%, oba ≤ 4000; §6).
- **Determinizm:** seedy jawne, maski `default_rng([mask_seed, seed])`, artefakty z sha256 (§9),
  testy jednostkowe 7/7 (`s3d/test_filters.py`).
- **Sweep G1 46600–46649 nietknięty; próg 85/8 nietknięty.** Eval 46500–46599 czytany read-only.
- **WSL/GPU:** 36 biegów bez padu (driver z retry `s3d/run_eval.sh`); artefakty zweryfikowane.
- **Budżet:** zmieszczono w limicie (1 sesja pomiarowa: kolekcja ~22 min, trening ~min, eval ~2 h).

---

*Faza 3d: mikro-filtr temporalny kanału celu zmierzony. Werdykt NEGATYWNY: filtrowanie kanału (uczone
i klasyczne) pogarsza sukces zamrożonej polityki mimo ~43% redukcji offline RMSE boxa; rdzeń
continuous-time nie daje przewagi; duch ZOH (brak filtra) jest optymalnym wejściem. Rozjazd
precondition↔pętla to główny, publikowalny wynik. Sweep czysty, próg nietknięty.*
