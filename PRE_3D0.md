# PRE_3D0 — pre-rejestracja fazy 3d (mikro-filtr temporalny kanału celu)

**Data:** 2026-08-02. **Etap:** P (dokument zamrożony; kończy się STOP na ratyfikację człowieka).
**Podstawa:** `RECON_3D.md` (etap R). **Zasada:** MIERZĘ = RAPORTUJE; kryteria zamrażane PRZED
pomiarem; po zobaczeniu wyników nie zmienia się progów, poziomów ani n. System po S3c1-R
**ZAMROŻONY**: polityka `ckpt/s3b2r/policy_gc5.pt`, kanał `Tracker5`, osłona v2, env, percepcja —
nietykalne. Elementy `[PROPOZYCJA]` = decyzje projektowe do ratyfikacji człowieka.

> **STATUS:** OCZEKUJE NA RATYFIKACJĘ. Etap M (pomiar) nie startuje bez dopisku „RATYFIKOWANE"
> (commit z ręki człowieka lub jawna adnotacja w tym pliku).

---

## 1. Hipoteza

Mikro-filtr temporalny wpięty na kanale celu — między dostarczeniami groundera (~1 Hz) a wejściem
polityki (tick 12 Hz), w miejscu ducha ZOH — **poprawia sukces end-to-end pod degradacją łącza**
(dropout dostarczeń), a rdzeń **continuous-time (CfC z jawnym Δt w sekundach)** robi to **lepiej** niż
odpowiedniki bez natywnego mechanizmu czasu (GRU z Δt jako cechą; Kalman-CV; brak filtra).

Hipoteza jest **DWUSTRONNA**: pogorszenie sukcesu (filtr szkodzi zamrożonej polityce przez shift
wejścia) jest **pełnoprawnym wynikiem**, nie porażką pomiaru. „Klasyk (Kalman) wystarcza" oraz
„filtr nie pomaga / szkodzi" to publikowalne wyniki.

---

## 2. Ramiona [PROPOZYCJA]

Cztery ramiona ewaluacji. Wszystkie karmią **tę samą zamrożoną politykę**; różni je wyłącznie to,
co trafia w `target5[0:4]`.

| ramię | nazwa | rdzeń | uczony? | rola |
|---|---|---|---|---|
| **A0** | `no-filter` | — (duch ZOH bit-w-bit) | nie | kontrola; kotwica porównywalności z G2/S3c1-R |
| **A1** | `Kalman-CV` | filtr Kalmana constant-velocity | nie (strojony) | kontrola klasyczna |
| **A2** | `mikro-GRU` | GRUCell, Δt jako cecha wejścia | tak (5 seedów) | rdzeń dyskretny |
| **A3** | `mikro-CfC` | CfCCell + backbone, Δt w sekundach, krokowanie ręczne | tak (5 seedów) | rdzeń continuous-time (orzekający) |

**Parytet A2 ↔ A3 (ścisły):**
- budżet rdzenia **≤ 4 000 parametrów**, dopasowanie **±2%** (jak pasmo F3);
- **identyczne wejście i wyjście**: wejście per tick = `[bx, by, bw, bh, has_delivery, Δt_norm]`
  (box = najświeższe dostarczenie ZOH lub zera przy no-lock; `has_delivery` = 1 na ticku świeżego
  dostarczenia; `Δt_norm` = sekundy od ostatniego dostarczenia / AGE_MAX); wyjście = `[cx,cy,w,h]`;
- **identyczna procedura treningu** (§4): te same dane, seedy, epoki, optymalizator, strata, selekcja;
- różnica **wyłącznie w rdzeniu**: A2 podaje `Δt_norm` jako zwykłą cechę do GRUCell; A3 podaje `Δt` w
  **sekundach** jako natywny timespan do CfCCell (krokowanie ręczne komórką — obejście buga
  `ncps 1.0.1` timespans@batch>1, `ANEKS_3_KONSTRUKCJA_RDZENI.md:18-23`).

Kalman-CV (A1) i no-filter (A0) **nie podlegają** parytetowi (kontrole klasyczne). Kalman-CV: stan
`(cx,cy,w,h,ċx,ċy,ẇ,ḣ)`, model przejścia constant-velocity z **rzeczywistym Δt** między
dostarczeniami, aktualizacja pomiarem na ticku dostarczenia, predykcja (ekstrapolacja) na tickach
bez dostarczenia; Q/R strojone na zbiorze treningowym (§4), **bez uczenia gradientowego**.

**Uwaga (A.2/D-1 z RECON):** wszystkie ramiona filtrujące (A1/A2/A3) podmieniają **tylko
`target5[0:4]`**; `target5[4]` (age_n) pozostaje **prawdziwym** wiekiem ostatniego dostarczenia
(nietknięte). Przy no-lock (`[0,0,0,0,1.0]`) filtr działa **pass-through** (brak toru → nic do
wygładzenia); A0 to trywialnie duch ZOH.

---

## 3. Wpięcie [PROPOZYCJA — kluczowa decyzja do ratyfikacji]

Polityka pozostaje **ZAMROŻONA** (`policy_gc5.pt`). Filtr jest **drop-inem** wpiętym za
`target5 = tr.vector(k)`, tuż przed `model.act(obs, target5, …)` (RECON §A.2). Na każdym ticku 12 Hz
podaje polityce wygładzoną estymatę `(cx,cy,w,h)` w miejsce ducha ZOH; **`age` pozostaje prawdziwym
wiekiem** ostatniego dostarczenia (osłona i semantyka age nietknięte).

**Przestrzeń filtra — decyzja D-1 (RECON §D-1).** Dwie opcje:
- **(a) image-space [REKOMENDACJA]** — filtr operuje wprost na `(cx,cy,w,h)` w kadrze 256²; wyjście
  = wejście polityki bez projekcji; drop-in dosłowny z §2. Koszt: etykieta GT-box znika w martwym
  polu (cel poza kadrem), więc filtr uczy się interpolacji/ekstrapolacji **fazy dolotu**, nie samego
  terminalnego zawisu. To jest zgodne z celem („mostkowanie przerw pod dropoutem"), a nie ze ścianą
  B4 (która leży w wykonawcy, nie na kanale — ustalenie 3b).
- **(b) world-space (odrzucona w tej fazie)** — filtr w przestrzeni świata (po back-projekcji
  `gt_target_pos`), potem projekcja do `(cx,cy,w,h)`. Zaleta: gęsta etykieta 12 Hz także off-frame
  (RAPORT_3B mandat, `RAPORT_3B.md:250-252`). Koszt: dokłada komponent back-projekcji (kamera/pozy),
  rozszerza zakres i ryzyko błędu projekcji, wychodzi poza „mikro-filtr". **Odrzucona:** za duży
  zakres jak na MVP pomiarowe; nazwana jako przyszły mandat.

**Nazwane ryzyko (kuzyn F-3b-1):** polityka była uczona na semantyce **ducha ZOH**; wygładzone/
ekstrapolowane boxy to **shift wejścia** zamrożonej polityki. Dlatego (i) **A0 jest kontrolą**, (ii)
kryterium zawiera **constraint transparencji** na nodze clean (§6): filtr, który psuje clean, jest
raportowany jako NIETRANSPARENTNY niezależnie od zysku na dropoucie.

**Wariant odrzucony — retrening polityki per ramię.** Można by trenować politykę na wyjściu każdego
filtra (usuwa shift wejścia). Odrzucony: (1) łamie zamrożenie `policy_gc5.pt` — rdzeń całego programu
3b–3c; (2) mnoży koszt (4 polityki × trening pełny zamiast filtry ≤4k param/minuty); (3) miesza dwa
efekty (filtr vs adaptacja polityki), niszcząc izolację, którą ta faza ma zmierzyć. Pomiar 3d mierzy
filtr **jako drop-in do systemu, który istnieje**, a nie hipotetyczny system współtrenowany.

---

## 4. Dane treningowe filtrów [PROPOZYCJA]

Uczenie **OFFLINE, nadzorowane**. Polityka NIE uczestniczy w zbieraniu (filtr uczy się rekonstrukcji
kanału niezależnie od kontrolera → brak sprzężenia z zamrożoną polityką).

- **Wejście:** strumień dostarczeń kanału (żywy YOLO przez `.venv_s3b0`, kontrakt D3: tick 1 Hz,
  L_deliver, ZOH, no-lock) **z maskami degradacji** + `Δt` od ostatniego dostarczenia. Wejście
  per tick jak w §2.
- **Etykieta (D-1/D-2 z RECON):** **GT box celu w kadrze 256²** (`info["gt_bbox_256"]`), renderowany
  przez kolektor **per tick 12 Hz** (read-only `drone_camera(...want_seg=True)`+`bbox_from_mask`,
  wzorzec `train/s3b4.py:102`). Na tickach **off-frame** (box=`None`) etykieta nie istnieje → te ticki
  są **maskowane w stracie i w RMSE** (uczymy i mierzymy filtr tam, gdzie jest prawda obrazowa).
  Strata = MSE na `(cx,cy,w,h)` na tickach z etykietą.
- **Kolektor sceny/trajektorii:** ekspert-desygnowany leci scenę (jak dane BC 3b), grounder karmi
  kanał na żywo; logujemy per tick: wejście filtra + etykietę GT + `Δt`. (Trajektoria eksperta jest
  wystarczająco reprezentatywna dla rozkładu boxów dolotu; polityka zamrożona i tak leci podobnie.)
- **Pule (RECON §B.3, wolne, rozłączne z zajętymi):**
  - **filtr-train sceny: 48000–48299 (300 ep)**;
  - **filtr-val sceny (wstrzymane): 48300–48399 (100 ep)** — precondition P-3D i selekcja;
  - **maski treningowe: 45200–45209** (rodzina 45100+, **rozłączne** z 45100–45107/45150–45151);
    losowane z tej samej rodziny co pomiarowe (`default_rng([mask_seed, ep]`), Bernoulli p=0.5 i
    burst L5 mieszane w treningu, by filtr widział oba reżimy);
  - **seedy init/shuffle: 45040–45044** (5 seedów, **PAROWANE A2↔A3** po indeksie — jak par. F3).
- **5 seedów treningu per ramię uczone (A2, A3).** A1 (Kalman): Q/R strojone **raz** na zbiorze
  treningowym (grid/MLE na 48000–48299), deterministyczne. A0: brak.
- **Higiena:** pule pomiarowe (eval 46500–46599, sweep 46600–46649) **NIE są dotykane** w treningu;
  maski treningowe **rozłączne** z pomiarowymi (45102/45105).

---

## 5. Precondition P-3D (przed jakąkolwiek ewaluacją zamkniętej pętli)

Na **wstrzymanym zbiorze walidacyjnym 48300–48399** (ten sam skrypt dla wszystkich ramion, maski
z rodziny treningowej): **RMSE boxa ramienia < RMSE ducha ZOH** (baseline A0 liczony tym samym
skryptem, na tych samych tickach z istniejącą etykietą GT).

- RMSE liczone na `(cx,cy,w,h)` po tickach z etykietą (off-frame maskowane, D-2).
- Ramię, które **nie bije ZOH offline**, ma status **FAIL-PRECOND** i **nie wchodzi** do pętli
  (raportowane jawnie w RAPORT_3D). A2/A3: precondition liczone **per seed** i agregowane
  (raportujemy rozkład; ramię wchodzi, jeśli mediana seedów bije ZOH — próg zamrożony: mediana).
- **Precondition NIE jest tezą** — to warunek dopuszczenia do kosztownej pętli zamkniętej. Bicie ZOH
  offline nie przesądza wyniku end-to-end (shift wejścia, §3).
- **Eskalacja:** jeśli precondition wycina **oba** ramiona uczone (A2 i A3 FAIL-PRECOND) → STOP i
  decyzja człowieka (raportujemy A0 vs A1 jako wynik częściowy).

---

## 6. Ewaluacja zamknięta i kryterium [PROPOZYCJA]

**Harness:** parowany, na bazie `s3c1/measure_s1.py`, **BEZ osłony** (izolacja efektu filtra;
interakcja filtr×osłona = pomiar wtórny, poza kryterium — D-5 z RECON). Nowy kod w `s3d/`; drop-in
filtra na `target5`; metryka pierwotna = **czysty sukces env** (`info["success"]`, jak `s3b4.py:120`).

**Epizody i nogi:** pula **eval 46500–46599**, maski **45100+** — rodzina G2 (D-3/D-4 z RECON):
- **clean** — brak maski;
- **Bernoulli p=0.5** — maska seed **45102** (jak G2/S1);
- **burst L=5 s** — maska seed **45105** (jak G2).
- **N = 100 epizodów na nogę** [PROPOZYCJA D-3: N=100 na 46500–46599; kotwicą werdyktu jest parowane
  **A0** w biegu, a liczby G2 80/66/44/30 (50 ep) są **referencją zewnętrzną**, ~13 pp optymistyczną
  vs populacja — `RAPORT_S3B4.md:17-28`]. **Parowanie:** te same epizody i maski dla każdego ramienia.

**Metryka pierwotna:** sukces na nodze **p=0.5**, uśredniony po **5 seedach filtra** (A2, A3);
A0 i A1 — **jeden bieg** (deterministyczne).

**WERDYKT (dwustronny, zamrożony):**
```
Δ = succ(A3) − max( succ(A0), succ(A1), succ(A2) )
pooled_std = sqrt( ( sd_s(A2)² + sd_s(A3)² ) / 2 )     # sd po 5 seedach filtra (F3_GATE §5)
Δ >  +pooled_std   ⇒  POZYTYWNY   (CfC bije najlepszy z pozostałych)
Δ <  −pooled_std   ⇒  NEGATYWNY   (CfC gorszy)
inaczej            ⇒  NULL
```
`succ(A2)`, `succ(A3)` = średnia po 5 seedach na nodze p=0.5; `succ(A0)`, `succ(A1)` = pojedynczy
bieg. `pooled_std` liczony **po seedach ramion uczonych** (dosłownie formuła F3-GATE §5,
`F3_GATE.md:55` — rozrzut populacyjny, nie SEM).

**Constraint transparencji (zamrożony):** na nodze **clean** `succ(ramię) ≥ succ(A0) − 3 pp`.
Naruszenie ⇒ ramię raportowane jako **NIETRANSPARENTNE** niezależnie od wyniku na dropoucie.

**Metryki wtórne (obowiązkowe, poza werdyktem):**
- **wrong-lock per noga** — filtr **NIE MOŻE** wprowadzać kradzieży locka (G2: kradzież=0; własność
  do zachowania, `RAPORT_S3B4.md:79-85`); dekompozycja pierwszy-zły/kradzież/inne jak w G2;
- **burst L5** — pełny wynik (transparencja na ciągłych przerwach);
- **RMSE boxa online** — RMSE filtra vs GT w pętli zamkniętej (nie tylko offline);
- **rozkład age** przy wejściu w dwell (histogram, biny G2 `[0,.1,.25,.5,.75,1.01]`).

---

## 7. Ryzyka nazwane

1. **Shift wejścia zamrożonej polityki** (§3) — polityka uczona na duchu ZOH; wygładzenie to OOD
   (kuzyn F-3b-1). Zabezpieczenie: A0 kontrola + constraint transparencji.
2. **Filtr ekstrapolujący ruch w martwym polu / dwell** — możliwa kradzież locka lub dryf (filtr
   „domyśla" ruch celu, który stoi). Stąd metryka wtórna **wrong-lock**; własność do zachowania:
   kradzież=0.
3. **Wariancja seedów uczonych filtrów** — dlatego `pooled_std` w werdykcie (nie porównanie średnich
   gołych).
4. **Przewaga Kalmana** — wynik „klasyk wystarcza" (A1 ≥ A2,A3) jest **pełnoprawnym, publikowalnym**
   wynikiem (werdykt NEGATYWNY lub NULL względem A3).
5. **Etykieta off-frame** (D-2) — RMSE/strata maskowane na off-frame; filtr nie jest uczony ani
   mierzony na terminalnym martwym polu (gdzie i tak leży wykonawca, nie kanał).

---

## 8. Budżet i reguła stopu

- **Trening:** 2 ramiona uczone (A2, A3) × 5 seedów + strojenie A1 (Q/R raz). Filtry ≤4k param →
  minuty/seed. Precondition P-3D na 48300–48399.
- **Ewaluacja:** 3 nogi × N=100 × ramiona {A0, A1, A2×5, A3×5} parowane na 46500–46599.
- **Limit: 2 sesje pomiarowe.**
- **Reguła stopu:** jeśli po pełnym budżecie werdykt nie zapada z powodu **awarii infrastruktury**
  (WSL/GPU exit 144, niedomknięte seedy) — **STOP i raport stanu**; **nie rozszerzamy n** po
  zobaczeniu wyników. Precondition wycinający oba ramiona uczone → STOP (eskalacja, §5).

---

## 9. Artefakty

- **Kod:** `s3d/` (filtry A1/A2/A3, kolektor danych, harness pomiarowy bez osłony, testy jednostkowe).
- **Wyniki:** `results/s3d/` — JSON per bieg z **sha256**; log treningu filtrów, precondition,
  3 nogi × ramiona.
- **Raport:** `RAPORT_3D.md` — każda liczba **krosowana** z plikiem źródłowym JSON; rozbieżności
  wypisane jawnie (nie uzgadniane po cichu).
- **Determinizm:** seedy jawne (§4), maski `default_rng([mask_seed, ep])`, init parowane A2↔A3.

---

## Decyzje do ratyfikacji (zebrane; z RECON §D)

| # | decyzja | rekomendacja R |
|---|---|---|
| **D-1** | przestrzeń filtra: image-space vs world-space | **image-space** (§3a) — dosłowny drop-in, off-frame nazwane |
| **D-2** | kadencja/maskowanie etykiety GT (off-frame=None) | etykieta 12 Hz z per-tick seg-render; off-frame maskowany w stracie i RMSE |
| **D-3** | N/nogę oraz kotwica G2 | **N=100** na 46500–46599; kotwica = parowane A0; G2 = referencja |
| **D-4** | maski nóg dropout | p0.5→**45102**, L5→**45105**, clean→brak (rodzina G2) |
| **D-5** | harness bez osłony | nowy `s3d/` = szkielet `measure_s1` minus Shield; metryka = sukces env |
| **D-6** | pooled_std jawnie | `sqrt((sd_s(A2)²+sd_s(A3)²)/2)` po 5 seedach (F3-GATE §5) |
| **§2** | wejście/wyjście filtra + parytet A2↔A3 | `[bx,by,bw,bh,has_delivery,Δt_norm]`→`[cx,cy,w,h]`, ≤4k param ±2% |
| **§4** | pule 3d | train 48000–48299, val 48300–48399, maski 45200–45209, init 45040–45044 |

---

*PRE_3D0 zamknięty. **STOP na ratyfikację człowieka.** Bez dopisku „RATYFIKOWANE" (commit z ręki
człowieka lub jawna adnotacja) etap M nie startuje. Do czasu ratyfikacji — żadnego treningu ani
ewaluacji poza smoke'ami infrastruktury (pojedynczy epizod, oznaczony jako smoke, poza pulami
pomiarowymi).*
