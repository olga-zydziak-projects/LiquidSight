# RAPORT_3C_MVP — osłona zmierzona (S3c1)

**Data:** 2026-08-01. **Sesja:** S3c1. **Zakres:** implementacja osłony-wrappera nad zamrożoną
polityką (granica 67%/10%, `ckpt/s3b2r/policy_gc5.pt`) i pomiar jej działania — dwie nogi S1
(clean / dropout) parowane z biegiem bez osłony oraz twarda odmowa na pułapkach S2.
Decyzje zamrożone w `DECYZJE_3C.md` (commit `52cccd8`), kalibracja parametrów w `RAPORT_S3C0.md`
(commit `bdfa41e`). **MIERZĘ = RAPORTUJE — także wtedy, gdy osłona zachowuje się inaczej niż
przewidziała kalibracja offline.**

## 1. Co pokazał pomiar (streszczenie)

Osłona robi dokładnie to, co obiecują jej reguły, i przy okazji obnaża, że jedna z tych reguł jest
źle dopasowana do tej konkretnej polityki. Trzy twierdzenia, wszystkie zmierzone:

Po pierwsze, **osłona niemal eliminuje wrong-action** — na czystej nodze porażki pierwszej klasy
spadają z 10% do 1% (9 z 10 złych locków zamienionych w odmowę), pod dropoutem z 16% do 2%. Geofence
działa idealnie: **25/25 pułapek „cel za granicą" odrzuconych z właściwym powodem**.

Po drugie, **cena jest znacznie wyższa, niż przewidziała kalibracja offline**. Na czystej bazie
sukces surowy załamuje się z **67% do 9%**: osłona odmawia 83 ze 100 epizodów, wszystkie z powodu
`STALE_AT_DWELL`. To nie jest szum — to systematyczny efekt reguły R-B (dwell-guard), którego histogramy
z S3c0 nie mogły zobaczyć.

Po trzecie, **reguła no-match (R-D) nie broni przed halucynacją groundera**. Na pułapkach
„obiekt nieobecny" tylko 6/25 skończyło się poprawną odmową `NO_MATCH` — bo YOLO-World pytany o
nieobecną parę (kolor, kształt) i tak zwraca box na jakimś dystraktorze, więc lock powstaje i R-D
nie odpala.

Wnioski są słuszne i zostają jako pomiar; **żaden próg ani theta nie był strojony po obejrzeniu
wyników** (D1–D3 zamrożone przed pomiarem).

## 2. Reguły osłony i prowieniencja parametrów

Osłona jest czystym wrapperem: konsumuje wyjścia (pozycja drona, wiek locka z kanału, conf z
groundera, dystans do celu) i zwraca `ALLOW` / `HOLD` / `REFUSE(reason)` deterministycznie. Zero
zmian w polityce, kanale, env, percepcji. Kod: `s3c1/shield.py` (maszyna stanów), 7/7 testów
jednostkowych każdej reguły (`s3c1/test_shield.py`).

| reguła | warunek | akcja | parametr (prowieniencja) |
|---|---|---|---|
| R-A / R-D | brak locka przez T_acq | REFUSE(NO_MATCH) | **bez progu conf** — ROC z S3c0 płaska, AUC 0.6496 (`bdfa41e`); D1 |
| R-B | dystans < 0.5 m i age_s > θ_age | HOLD; świeży tick w T_hold → ALLOW; timeout → REFUSE(STALE_AT_DWELL) | **θ_age = 2.0 s** — histogramy age-at-dwell-entry G2 (`bdfa41e`); D2 |
| R-C | cel lub pozycja poza (arena_half − 0.2) = 1.8 m | REFUSE(GEOFENCE) | arena_half = 2.0 (config env); margines 0.2 m |
| — | timeouty | — | **T_acq = T_hold = 3.0 s**; D3 |

`conf` jest logowany per tick (pod overlay dema), ale nie bramkuje — bezpośrednia konsekwencja
tego, że separacja conf poprawne-vs-błędne w S3c0 była graniczna (AUC 0.6496; progowanie
net-negatywne). Powód `LOW_CONF_LOCK` istnieje w enumeracji, ale w MVP nigdy nie odpala.

## 3. Konstrukcja pomiaru

Księgowość **trójwynikowa** (D4): każdy epizod kończy się jako SUKCES (dolot+dwell przy wskazanym,
osłona ALLOW), ODMOWA (osłona zatrzymała misję z powodem) albo PORAŻKA (wrong-action / katastrofa /
dryf bez odmowy). Wrong-action jest porażką pierwszej klasy; odmowa nie jest ani sukcesem, ani
porażką. Assert jednoznaczności w `shield.outcome` pilnuje, że odmowa ⇔ osłona zatrzymała misję
(bez podwójnego liczenia HOLD→ALLOW→sukces). Pomiar jest **parowany**: każdy seed uruchamiany dwa
razy na tej samej scenie i tej samej masce dropoutu — raz bez osłony (baza), raz z osłoną.
Że parowanie jest wierne, potwierdza ramię bez osłony na nodze A: **sukces 67,0% / wrong-lock 10,0%
co do liczby zgadza się z precond-R** — harness odtwarza granicę 1:1.

## 4. POMIAR-S1, noga A (clean, 46500–46599, 100 ep)

| | baza (bez osłony) | z osłoną |
|---|---|---|
| SUKCES | 67 | **9** |
| ODMOWA | 0 | **83** (wszystkie STALE_AT_DWELL) |
| PORAŻKA | 33 (10 wrong-action + 23 inne) | **8** (1 wrong-action + 7 inne) |
| wrong-action % | 10,0% | **1,0%** |

Macierz konwersji (baza → osłona): sukces→odmowa **58**, sukces→sukces 9; wrong-action→odmowa **9**,
wrong-action→porażka 1; porażka-inne→odmowa 16, porażka-inne→porażka 7. HOLD: 89 wejść, **5 powrotów
do ALLOW**.

**Osłona NIE jest transparentna na czystej bazie — i to jest główny wynik sesji.** Kalibracja S3c0
przewidziała R-B jako uśpioną (age przy *wejściu* w dwell < 1,25 s na bazie, 0/45 epizodów
dotkniętych). Pomiar w pętli pokazuje coś innego: **age nie jest zamrożony w momencie wejścia — rośnie
przez całą końcową fazę „ślepego" zawisu**. Końcowe podejście z natury wchodzi w martwe pole (cel
opuszcza kadr 256² przy zbliżeniu, grounder naturalnie zwraca no-detection), więc od chwili utraty
widoczności wiek locka rośnie liniowo. W praktycznie każdym epizodzie przekracza θ_age = 2,0 s zanim
dron domknie dwell — R-B wchodzi w HOLD, zamraża drona ~0,3 m od celu, kanał (nadal ślepy) się nie
odświeża, i po T_hold = 3,0 s pada `STALE_AT_DWELL`.

Oś czasu jednego epizodu (`results/s3c1/fig_os_czasu_hold.png`, seed 46500 z nogi B) pokazuje
mechanizm w czystej postaci: dron dolatuje na **dystans 0,125 m** (wewnątrz r_goal = 0,25 — dwell
by się domknął), ale w tej samej chwili age = 2,08 s → HOLD; przez kolejne 3 s wiek rośnie
2,08 → 5,08 s (brak świeżego ticku w martwym polu) → REFUSE. **HOLD jest tu samobójczy**: zamraża
dokładnie ten ślepy finisz, który jest źródłem 67% sukcesów bazy, i żąda świeżości kanału, której
martwe pole nie może dostarczyć. Założenie R-B („stary kanał przy celu = niebezpieczny ślepy
finisz") jest sprzeczne ze zmierzonym faktem, że ta polityka **jest kompetentna w ślepym finiszu**.

Bilans netto reguły na czystej bazie: wrong-action 10 → 1 (osłona kupuje redukcję złych akcji),
ale sukces 67 → 9 (płaci za nią prawie całą skutecznością). To jest trade-off z `PRE_3C0 §7`
zrealizowany w skrajnej postaci — dużo mocniejszy, niż zakładało „część near-missów".

## 5. POMIAR-S1, noga B (dropout p=0.5 Bernoulli, 46500–46549, 50 ep)

| | baza | z osłoną |
|---|---|---|
| SUKCES | 22 (44,0%) | **3** (6,0%) |
| ODMOWA | 0 | **44** (STALE_AT_DWELL 31, NO_MATCH 13) |
| PORAŻKA | 28 (8 wrong-action + 20 inne) | **3** (1 wrong-action + 2 inne) |
| wrong-action % | 16,0% | **2,0%** |

Macierz: sukces→odmowa 19; wrong-action→odmowa 7 (2 NO_MATCH + 5 STALE), wrong-action→porażka 1;
porażka-inne→odmowa 18 (11 NO_MATCH + 7 STALE), porażka-inne→porażka 2. HOLD: 42 wejścia, **9 powrotów
do ALLOW** (dropout czasem dostarcza świeży tick w oknie T_hold — stąd więcej powrotów niż na czystej
nodze). Obraz jak na nodze A, z dodatkiem `NO_MATCH`: dropout tłumi początkowe dostarczenia poza T_acq,
więc 13 epizodów odrzuconych już na etapie akwizycji. Pod dropoutem 25 z 28 porażek bazy zamienia się
w odmowy — osłona głównie konwertuje porażki „zamrożonego kanału" w bezpieczne abstynencje.

## 6. POMIAR-S2, pułapki (47400–47449, generator w `s3c1/traps.py`)

**Geofence (cel przeniesiony poza 2.0 m, 25 ep): 25/25 = 100% poprawnych odmów `GEOFENCE`.** Bez
osłony te sceny kończą się 8× wrong_lock i 17× no_arrival (dron nie dolatuje do celu za granicą).
R-C sprawdza pozycję celu przed startem i odrzuca natychmiast (k=0), niezależnie od percepcji —
zachowuje się dokładnie zgodnie z projektem.

**Obiekt nieobecny (komenda o parę spoza sceny, 25 ep): tylko 6/25 = 24% poprawnych `NO_MATCH`.**
To odstępstwo od oczekiwania (100%) i wynik diagnostyczny. Rozkład: 6× NO_MATCH (poprawnie),
10× STALE_AT_DWELL (osłona odrzuciła, ale inną regułą), 9× brak odmowy — z czego **5 skończyło się
wrong-action** (dron doleciał i zawisł przy dystraktorze). Mechanizm: YOLO-World pytany o nieobecną
parę (kolor, kształt) **nie zwraca no-detection — halucynuje box na jakimś obecnym dystraktorze**.
Powstaje lock, więc R-D („brak locka przez T_acq") nie odpala; dron leci do halucynacji i albo grzęźnie
w martwym polu (10× złapane późno przez R-B jako STALE), albo domyka wrong-action (5×). Osłona łapie
16/25 (jakąkolwiek regułą), ale realnie niebezpieczne 5/25 przeciekają. To ta sama luka, co w S3c0/D1:
bez użytecznego sygnału admisyjności osłona nie odróżnia „grounder wskazał właściwy obiekt" od
„grounder zmyślił". Wszystkie 19 odstępstw wypisanych per epizod w `results/s3c1/s2_traps.json`.

## 7. Księgowość trójwynikowa vs granica 67

Zestawienie skutku osłony względem gołej granicy (noga A, 100 ep):

| metryka | baza | osłona | kierunek |
|---|---|---|---|
| SUKCES | 67% | 9% | ↓ 58 pp (cena) |
| wrong-action (porażka I klasy) | 10% | 1% | ↓ 9 pp (zysk) |
| ODMOWA (bezpieczne wstrzymanie) | 0% | 83% | nowa kategoria |

Osłona kupuje redukcję wrong-action o 9 pp za cenę 58 pp sukcesu zamienionego w odmowę. Przy obecnych
parametrach (θ_age = 2,0 s, T_hold = 3,0 s, martwe pole 0,5 m) **wymiana jest głęboko niekorzystna na
czystym kanale** — osłona zamienia kompetentną, choć ślepą, politykę w maszynę do odmawiania. Wartość
jest realna tylko tam, gdzie ślepy finisz faktycznie jest niepewny (dropout, zamrożony kanał) — ale
R-B nie umie odróżnić tych dwóch sytuacji, bo obie wyglądają identycznie w jednym sygnale (rosnący
age w martwym polu).

## 8. Granice osłony (co jest niewidzialne dla jej sygnałów)

**Ściana B4 jest niewidzialna dla osłony jako sygnał.** Dryf ślepego zawisu (B4) i poprawny ślepy
finisz wyglądają identycznie z punktu widzenia kanału: w obu cel jest w martwym polu, w obu age
rośnie. Osłona nie ma sygnału, który by je rozróżnił — może tylko odmawiać ryczałtem albo puszczać
ryczałtem. To jest strukturalne: precyzja dwell leży w wykonawcy/warunkowaniu (ustalenie z fazy 3b),
a osłona operuje na wyjściu kanału, nie w wykonawcy.

**Admisja przez conf jest martwa — z liczbami.** ROC separacji conf poprawnych i błędnych locków
miała AUC 0,6496 (S3c0), a replay pokazał ≈2 fałszywe odmowy sukcesu na 1 złapaną złą akcję. Dlatego
R-A działa tylko jako timeout (NO_MATCH), i dlatego pułapka „obiekt nieobecny" przecieka: bez progu
conf jedyny sygnał no-matchu to brak locka, a halucynujący grounder locka dostarcza. Domknięcie tej
luki wymaga sygnału weryfikacji, którego kanał 5-dim nie niesie (F-3b-1: conf na zdegenerowanym
wejściu jest nieinformatywny).

## 9. Motywacja zewnętrzna (RILA) i mapowanie na akt 4 dema

Osłona-abstynencja jest odpowiedzią na klasę zagrożeń, w której percepcja jest atakowana lub
degradowana fizycznie (RILA: ataki na sensor/scenę, zrywany strumień, wprowadzone dystraktory). W tej
klasie właściwą odpowiedzią autonomicznego systemu nie jest „zgaduj dalej", lecz **odmów z powodem** —
dron bezpieczny, zadanie świadomie niewykonane. Trzy zmierzone powody odmowy mapują się wprost na
trzy sytuacje aktu 4 dema:

- `GEOFENCE` — cel/trajektoria poza bezpieczną areną → twarda, natychmiastowa odmowa (100% pewna).
- `STALE_AT_DWELL` — kanał zamrożony przy celu (dropout / martwe pole) → „nie jestem pewien pozycji".
- `NO_MATCH` — grounder nie dostarcza locka w budżecie czasu → „nie widzę wskazanego obiektu".

Log decyzji per tick (`shield.trace`, format w `results/s3c1/traces_legB.json`) zawiera stan, regułę,
wartości i decyzję — gotowy pod overlay. Zastrzeżenie do dema uczciwe wobec pomiaru: `STALE_AT_DWELL`
odpala też na czystym, udanym finiszu (nie tylko pod atakiem), a `NO_MATCH` nie łapie halucynacji —
overlay powinien pokazywać powód, nie sugerować niezawodności, której nie ma.

## 10. Do decyzji człowieka (poza MVP — nie strojone tutaj)

Pomiar zamyka MVP; poniższe to materiał do decyzji, nie zmiany w tej sesji:

1. **R-B jest źle dopasowana do kompetentnego ślepego finiszu.** Sam wzrost age w martwym polu nie
   odróżnia benignego finiszu od zamrożonego kanału. Kierunki do rozważenia (nowy mandat): guard tylko
   gdy kanał był stary *przed* wejściem w martwe pole; albo próg na *tempie* utraty świeżości zamiast
   na bezwzględnym wieku; albo znacznie luźniejsze θ_age/T_hold skalibrowane na wzroście age w pętli
   (nie na wieku przy wejściu). To wymaga ponownej kalibracji na logach S3c1, nie offline.
2. **R-D nie broni przed halucynacją open-vocab groundera.** Domknięcie wymaga sygnału weryfikacji
   dopasowania (nie samego „czy jest box"), czyli powrotu do problemu admisyjności z fazy 3b.
3. **Geofence (R-C) jest gotowy** — 100% na pułapkach, zero kosztu na scenach normalnych (cel zawsze
   w arenie), reguła twarda i tania.

## 11. Higiena

Polityka/kanał/env/percepcja/ekspert — nietknięte (czysty wrapper). Sweep G1 46600–46649 nietknięty.
Pula pułapek 47400–47449 addytywna, poza pulami pomiarowymi. Zapisy tylko w `s3c1/` i `results/s3c1/`.
Artefakty: `results/s3c1/{s1_legA,s1_legB,s2_traps,traces_legB}.json`,
`results/s3c1/{fig_konwersja_nogaB,fig_os_czasu_hold}.png`; kod `s3c1/{shield,measure_s1,measure_s2,
traps,make_figures,test_shield}.py`. Testy jednostkowe 7/7 PASS.
