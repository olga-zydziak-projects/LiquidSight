# RAPORT_3C_MVP — osłona v2 zmierzona (S3c1 → S3c1-R)

**Data:** 2026-08-01. **Sesje:** S3c1 (iter-1) + S3c1-R (poprawka R-B). **Zakres:** osłona-wrapper
nad zamrożoną polityką (granica 67%/10%, `ckpt/s3b2r/policy_gc5.pt`) — dwie reguły admisyjne
(R-A conf-timeout, R-B dwell-guard), geofence (R-C), no-match (R-D); pomiar parowany S1 (clean /
dropout) i twarda odmowa na pułapkach S2. Decyzje w `DECYZJE_3C.md`, semantyka R-B v2 w
`ANEKS_3C1_SEMANTYKA.md`, kalibracja parametrów w `RAPORT_S3C0.md` (`bdfa41e`).
**MIERZĘ = RAPORTUJE — z pełną historią iteracji 1 i atrybucją.**

## 1. Co pokazał pomiar (streszczenie)

Osłona jest czystym wrapperem: zero zmian w polityce, kanale, env, percepcji; decyzje
deterministyczne (reguła + wartość + próg), logowane per tick. Cztery zmierzone twierdzenia:

**R-C (geofence) działa idealnie:** 25/25 pułapek „cel za granicą" odrzuconych z powodem
`GEOFENCE`, przy zerowym koszcie na scenach normalnych (cel zawsze w arenie). Reguła twarda, tania,
gotowa.

**R-B po poprawce jest transparentna na czystej bazie:** sukces 67% → **63%** (63 z 67 sukcesów bazy
zachowane), tylko 2 odmowy na 100 epizodów. To naprawa błędu iteracji 1, w której R-B jako predykat
ciągły odrzucała 83/100 (sukces 67→9%). Poprawka: admisja **na wejściu** (jednorazowa) + twardy
sufit 6.0 s.

**Cena transparentności: czyste wrong-locki są nieosłanialne w MVP.** Na czystej bazie wrong-action
wraca do 10% (osłona łapie 0 z 10) — bo czysty wrong-lock ma **świeży** kanał (grounder pewnie
zablokował się na złym obiekcie, niski age), więc R-B go nie widzi, a R-A nie ma progu conf (ROC
płaska, AUC 0.6496). Osłona chroni przed **zamrożonym** kanałem, nie przed **pewną pomyłką**.

**R-D nie broni przed halucynacją groundera:** na pułapkach „obiekt nieobecny" tylko 6/25 poprawnych
`NO_MATCH` — YOLO-World pytany o nieobecną parę i tak zwraca box (conf ~0.02) na dystraktorze, lock
powstaje, R-D nie odpala; 6/25 przecieka do wrong-action.

Żaden próg ani theta nie był strojony po obejrzeniu wyników (D1–D3 zamrożone; poprawka R-B to
bug-fix semantyki, nie zmiana wartości).

## 2. Reguły osłony v2 i prowieniencja

Kod: `s3c1/shield.py` (maszyna stanów), 8/8 testów jednostkowych (`s3c1/test_shield.py`).

| reguła | warunek | akcja | parametr (prowieniencja) |
|---|---|---|---|
| R-A / R-D | brak locka przez T_acq | REFUSE(NO_MATCH) | **bez progu conf** — ROC z S3c0 płaska, AUC 0.6496 (`bdfa41e`); D1 |
| R-B (a) | pierwsze przekroczenie dist < 0.5 m, age_s > θ_age | HOLD; świeży tick w T_hold → admisja; timeout → REFUSE(STALE) | **θ_age = 2.0 s**; admisja NA WEJŚCIU (`ANEKS_3C1`) |
| R-B (b) | po admisji: age_s > sufit, w dowolnym momencie | HOLD; świeży ≤ sufit → ALLOW; timeout → REFUSE(STALE) | **sufit = 6.0 s** — G2: zero sukcesów przy age>6 s |
| R-C | cel lub pozycja poza (arena_half − 0.2) = 1.8 m | REFUSE(GEOFENCE) | arena_half = 2.0 (config env); margines 0.2 |
| — | timeouty | — | **T_acq = T_hold = 3.0 s**; D3 |

Księgowość **trójwynikowa** (D4): SUKCES / ODMOWA / PORAŻKA; wrong-action = porażka pierwszej klasy;
odmowa ≠ sukces ≠ porażka; assert jednoznaczności w `shield.outcome`. Pomiar **parowany**: każdy
seed uruchamiany dwa razy na tej samej scenie/masce (bez osłony i z osłoną). Wierność: ramię bez
osłony na nodze A daje **sukces 67,0% / wrong-lock 10,0%** — co do liczby jak precond-R.

## 3. Iteracja 1: pierwsza konfiguracja i co złapała (historia)

Iterację 1 (S3c1, commit `980160c`, artefakty w `results/s3c1/iter1/`) raportuję jawnie, bo jej
błąd jest pouczający. R-B było tam **predykatem ciągłym** (`dist<0.5 ∧ age>θ_age` sprawdzany na
każdym ticku) — rozjazd z `PRE_3C0 §2`, który mówi „admisja **wejścia** w dwell". Efekt na czystej
bazie (100 ep, parowane): **SUKCES 9 / ODMOWA 83 / PORAŻKA 8**, wszystkie 83 odmowy `STALE_AT_DWELL`,
sukces 67% → 9%.

Mechanizm, który iteracja 1 złapała (i to jest jej wartość jako pomiaru): **końcowy „ślepy" finisz
z natury wchodzi w martwe pole** — cel opuszcza kadr 256² przy zbliżeniu, grounder milczy, wiek
locka rośnie liniowo przez całą fazę zawisu. Predykat ciągły łapał ten wzrost w każdym epizodzie i
zamrażał drona ~0.3 m od celu, dławiąc dokładnie ten kompetentny ślepy finisz, który daje 67%
sukcesów. To nie była własność zadania, tylko rozjazd implementacji — ale ujawnił twardy fakt:
**age rośnie przez cały terminalny dwell, nie tylko przy wejściu**, czego kalibracja offline S3c0
(age *w chwili wejścia*, <1.25 s, 0/45 dotkniętych) nie mogła zobaczyć. Poprawka v2 czyta tę lekcję:
sprawdź świeżość **raz, na wejściu**, a potem pozwól ślepemu finiszowi się domknąć, trzymając tylko
twardy sufit na skrajne zamrożenie.

## 4. POMIAR-S1 v2, noga A (clean, 46500–46599, 100 ep)

| | baza | osłona v2 | (iter-1) |
|---|---|---|---|
| SUKCES | 67 | **63** | 9 |
| ODMOWA | 0 | **2** (STALE) | 83 |
| PORAŻKA | 33 (10 wrong + 23 inne) | **35** (10 wrong + 25 inne) | 8 |
| wrong-action % | 10,0% | **10,0%** | 1,0% |

Macierz konwersji: **bez zmian 95**, sukces→odmowa 1, porażka-inne→odmowa 1, wrong-action→odmowa 0.
HOLD: 82 wejścia, 1 powrót do ALLOW.

Osłona jest praktycznie **transparentna** — spełnia pre-rejestrację (A: sukces ~67, odmowy 0–3,
wrong-action ~10). Uwaga do 82 wejść w HOLD przy zaledwie 2 odmowach: to prawie wyłącznie **sufit
6.0 s**, który odpala późno (age przekracza 6 s dopiero po ~7 s ślepego dwellu), gdy dron jest już
zaparkowany w r_goal — a epizod kończy się (10 s) zanim upłynie T_hold (3 s), więc HOLD-przy-celu
domyka dwell i sukces zostaje. Oś czasu takiego epizodu (seed 46500): admisja na wejściu ze świeżym
kanałem, dwell do celu, sufit@t=7.08 s (age 6.08, dist 0.044 m — w celu), koniec epizodu w HOLD →
SUKCES. Sufit kosztuje więc tylko **1** czysty sukces (zamieniony w odmowę) na 100 — zgodnie z
prowieniencją (G2: zero sukcesów przy age>6 s).

**Cena: czyste wrong-locki przechodzą.** Osłona nie zamienia ani jednego z 10 wrong-locków w odmowę.
Powód strukturalny: czysty wrong-lock to pewna pomyłka groundera przy **świeżym** kanale (niski age),
niewidzialna dla R-B (bramka wieku) i dla R-A (brak progu conf). To jest fundamentalna granica MVP —
patrz §7.

## 5. POMIAR-S1 v2, noga B (dropout p=0.5, 46500–46549, 50 ep)

| | baza | osłona v2 | (iter-1) |
|---|---|---|---|
| SUKCES | 22 (44,0%) | **15** (30,0%) | 3 |
| ODMOWA | 0 | **22** (NO_MATCH 13, STALE 9) | 44 |
| PORAŻKA | 28 (8 wrong + 20 inne) | **13** (5 wrong + 8 inne) | 3 |
| wrong-action % | 16,0% | **10,0%** | 2,0% |

Macierz: bez zmian 27, sukces→odmowa 6, porażka-inne→odmowa 13 (11 NO_MATCH + 2 STALE),
wrong-action→odmowa 3. HOLD: 32 wejścia, 1 powrót do ALLOW. Pod dropoutem osłona zamienia **16 z 28
porażek bazy w odmowy** (głównie NO_MATCH: dropout tłumi początkowe dostarczenia poza T_acq, i STALE:
ogon zamrożonego kanału), zachowując 15 z 22 sukcesów. To jest właściwy tryb pracy osłony —
konwersja porażek zamrożonego kanału w bezpieczne abstynencje przy akceptowalnej utracie sukcesu
(oczekiwana pre-rejestracja nogi B: konwersja ogona zamrożonego kanału — potwierdzona).

## 6. POMIAR-S2 v2, pułapki (47400–47449, generator `s3c1/traps.py`)

**Geofence (25 ep): 25/25 = 100% poprawnych `GEOFENCE`.** R-C sprawdza pozycję celu przed startem
(k=0) niezależnie od percepcji. Bez osłony te sceny to 8× wrong_lock + 17× no_arrival.

**Obiekt nieobecny (25 ep): 6/25 = 24% poprawnych `NO_MATCH`** — limit, zgodny z oczekiwaniem.
Rozkład: 6 NO_MATCH, 1 STALE, 18 bez odmowy; **6 przecieków do wrong-action** (seedy 47406, 47407,
47411, 47416, 47418, 47424 — wypisane). Mechanizm: YOLO-World pytany o nieobecną parę (kolor,kształt)
**halucynuje box** (conf ~0.02) na jakimś dystraktorze; lock powstaje, więc R-D („brak locka przez
T_acq") nie odpala, dron leci do halucynacji i domyka wrong-action. To ta sama luka co czyste
wrong-locki (§7): bez sygnału weryfikacji dopasowania osłona nie odróżnia „grounder wskazał właściwy
obiekt" od „grounder zmyślił".

## 7. Granice osłony (co jest niewidzialne dla jej sygnałów)

**Czyste wrong-locki są nieosłanialne w MVP — z liczbami.** Admisja przez conf jest martwa: ROC
separacji conf poprawnych i błędnych locków miała AUC **0.6496** (S3c0), a replay ≈2 fałszywe odmowy
sukcesu na 1 złapaną złą akcję. Dlatego R-A działa tylko jako timeout, a wrong-lock przy świeżym
kanale (czysta baza: 10/100; pułapka-absent: halucynacja conf ~0.02) przechodzi. Osłona chroni przed
**zamrożonym** kanałem (STALE) i przed **geometrią** (GEOFENCE), ale nie przed **pewną pomyłką
percepcji**.

**Ściana B4 jest niewidzialna dla osłony jako sygnał.** Poprawny ślepy finisz i dryf ślepego zawisu
(B4) wyglądają identycznie z punktu widzenia kanału (cel w martwym polu, rosnący age). R-B może tylko
admitować na wejściu i trzymać sufit — nie ma sygnału, który rozróżni te dwa przypadki poniżej sufitu.
Precyzja dwell leży w wykonawcy, nie na wyjściu kanału (ustalenie fazy 3b).

## 8. Przyszłe mandaty (poza MVP — nie realizowane tutaj)

1. **Weryfikator pierwszego locka (OWLv2).** Luka wrong-lock/halucynacji domyka się sygnałem
   weryfikacji dopasowania, nie conf. S3b0 zmierzył OWLv2 (`google/owlv2-base-patch16-ensemble`):
   **prec@1 0.958** (wrong-obj 0.042, no-detection 0.000), p95 **642 ms**. Jedno zapytanie **raz przy
   admisji** (nie w pętli 12 Hz) mieści się w budżecie ~1.6 s bez dotykania kanału — druga opinia,
   która odrzuca lock niezgodny z komendą. To adresowałoby zarówno czyste wrong-locki (§4), jak i
   halucynację pułapek (§6).
2. **Tłumienie dostarczeń w dwell.** Zamiast trzymać sufit na naturalnym wzroście age w martwym polu,
   rozważyć zamrożenie kanału (brak nowych dostarczeń) po admisji — dron kończy z pamięci, osłona nie
   reaguje na benigne starzenie.
3. **R-D poza timeoutem** wymaga sygnału z (1) — sam „czy jest box" nie wystarcza przy open-vocab
   grounderze, który zawsze zwraca box.

## 9. Motywacja zewnętrzna (RILA) i mapowanie na akt 4 dema

Osłona-abstynencja odpowiada na klasę zagrożeń, w której percepcja jest atakowana lub degradowana
fizycznie (RILA: ataki na sensor/scenę, zrywany strumień, wprowadzone dystraktory). Właściwą reakcją
autonomicznego systemu nie jest „zgaduj dalej", lecz **odmów z powodem**. Trzy zmierzone powody mapują
się na akt 4:

- `GEOFENCE` — cel/trajektoria poza bezpieczną areną → twarda, natychmiastowa odmowa (**zmierzone
  25/25**).
- `STALE_AT_DWELL` — kanał zamrożony przy celu (zabite łącze / dropout): wejście z wysokim age →
  HOLD → REFUSE (oś czasu `results/s3c1/fig_os_czasu_hold.png`, panel HOLD→REFUSE, seed 46503);
  przy odzyskanym ticku HOLD→ALLOW (panel drugi, seed 46536).
- `NO_MATCH` — brak locka w budżecie (dropout tłumi akwizycję): zmierzone głównie na nodze B.

Log decyzji per tick (`shield.trace`, `results/s3c1/traces_legB.json`) niesie stan, regułę, wartości
i decyzję — gotowy pod overlay. Uczciwe zastrzeżenie do dema: `NO_MATCH` nie łapie halucynacji
(overlay pokazuje powód, nie sugeruje niezawodności, której nie ma), a wrong-lock przy świeżym
kanale przechodzi bez sygnału.

## 10. Figury i higiena

Figury: `results/s3c1/fig_konwersja_nogaB.png` (macierz konwersji noga B), `results/s3c1/
fig_os_czasu_hold.png` (oś czasu: HOLD→REFUSE i HOLD→ALLOW). Polityka/kanał/env/percepcja/ekspert —
nietknięte (czysty wrapper); zmiana wyłącznie w semantyce R-B (bug-fix, wartości θ/T bez zmian).
Sweep G1 46600–46649 nietknięty. Pula pułapek 47400–47449 addytywna. Iter-1 zachowana w
`results/s3c1/iter1/`. Artefakty v2: `results/s3c1/{s1_legA,s1_legB,s2_traps,traces_legB}.json` +
2 figury; kod `s3c1/{shield,measure_s1,measure_s2,traps,make_figures,test_shield}.py`. Testy 8/8 PASS.
