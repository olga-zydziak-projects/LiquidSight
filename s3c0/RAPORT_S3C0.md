# RAPORT_S3C0 — kalibracja offline progów osłony (R-A conf, R-B age)

**Data:** 2026-07-31. **Sesja:** S3c0. **Zakres:** kalibracja OFFLINE punktów pracy dwóch reguł
osłony admisyjności — R-A (brama na conf pierwszego locka) i R-B (brama na wiek kanału przy
wejściu w dwell). ZERO lotów, ZERO treningu, zero zmian w kodzie systemu; wyłącznie analiza
istniejących logów. **MIERZĘ = RAPORTUJE — sesja PROPONUJE, wybiera człowiek.**

Wszystkie liczby mają ścieżkę źródła. Zapisy tylko w `s3c0/` i `results/s3c0/`.

---

## 0. Dwie uwagi wstępne (dyscyplina pomiaru)

**PRE_3C0 nie istnieje w repo.** Mandat odsyła do „PRE_3C0 (w repo)" i „ryzyka z PRE par.7",
ale w drzewie nie ma takiego pliku — jedyne ślady koncepcji osłony to zdanie w `ANEKS_3B_KANAL.md`
(„niepewność należy do osłony, nie do wykonawcy") i notka w `RAPORT_3B.md:272` („conf ma być
sygnałem niepewności dla osłony/admisyjności, nie dla wykonawcy"). Prowadziłem sesję według
reguł decyzyjnych zapisanych w samym mandacie (są samowystarczalne); brak dokumentu PRE_3C0
odnotowuję jako rozbieżność, nie uzupełniam go.

**R4–R7 nie wchodzą do zbioru kalibracyjnego conf.** `conf_log.jsonl` z biegów R4/R5/R6/R7 zawiera
tylko `{seed, k, conf, det}` — jest w nim wartość conf i fakt detekcji, ale **nie ma etykiety GT**
(designated / other). Bez niej nie da się zbudować pary „(conf pierwszego locka, lock poprawny/
błędny)". Etykieta GT jest wyłącznie w plikach `*_tick_audit.jsonl`, które istnieją tylko dla
**R** (`results/s3b2r/precond_R_audit_tick_audit.jsonl`) i **R3**
(`results/s3b2r3/precond_R3_audit_tick_audit.jsonl`), plus sweep G1
(`results/s3b3/tick_audit.jsonl`, seedy 46600–46649 — użyty walidacyjnie, osobno). Kalibracja conf
opiera się więc na R i R3; SWEEP służy jako trzeci, niezależny punkt kontrolny.

---

## 1. T1 — zbiór kalibracyjny conf

Pierwszy lock epizodu = pierwszy tik (najmniejsze `k`) z jakąkolwiek detekcją; etykieta „poprawny"
gdy `matched == designated`, „błędny" gdy `other`/`background`. Każdy z biegów pokrywa pełne
100 epizodów puli ewaluacyjnej 46500–46599 i w **każdym** epizodzie pada jakiś pierwszy lock
(brak epizodów całkowicie bez detekcji), więc zbiór to komplet 100 par na bieg.

| bieg (model) | źródło | epizody z lockiem | poprawne | błędne | AUC (bieg) |
|---|---|---|---|---|---|
| R (67%) | `results/s3b2r/precond_R_audit_tick_audit.jsonl` | 100 | 92 | 8 | 0.698 |
| R3 (11%) | `results/s3b2r3/precond_R3_audit_tick_audit.jsonl` | 100 | 91 | 9 | 0.597 |
| **R+R3 (zbiorczo)** | — | **200** | **183** | **17** | **0.650** |
| SWEEP G1 (walid.) | `results/s3b3/tick_audit.jsonl` | 50 | 45 | 5 | 0.716 |

Rozkłady conf pierwszego locka (R+R3): poprawne — mediana 0.045, maks 0.745; błędne — mediana
~0.016, maks 0.164. Kierunek jest właściwy (błędne locki mają niższą pewność), ale **przesunięcie
między biegami jest realne**: sam R separuje przyzwoicie (AUC 0.70), R3 prawie wcale (0.60),
choć to ten sam grounder i ta sama pula — różni się tylko polityka, która wybiera moment i obiekt
pierwszego locka. To dokładnie ostrzeżenie z mandatu o przesunięciach między modelami; zbiorcze
AUC 0.65 jest wypadkową, nie liczbą stabilną.

---

## 2. T2 — separacja R-A i punkty pracy θ_conf

**Zbiorcze AUC = 0.6496**, tuż **poniżej** progu płaskości 0.65 z mandatu, z rozrzutem per-bieg
0.60–0.72. Formalnie: krzywa **graniczna/płaska** → reguła mandatu każe **ograniczyć R-A do
wariantu NO_MATCH/timeout** (osłona odmawia tylko, gdy grounder nic nie zwraca lub przekracza
budżet czasu — bez progu na conf). Poniżej i tak podaję trzy punkty pracy θ_conf, żeby pokazać
człowiekowi, ile *kosztowałoby* progowanie mimo wszystko (na zbiorze kalibracyjnym R+R3):

| θ_conf | błędne locki złapane (odrzucone) | poprawne locki utracone (odrzucone) |
|---|---|---|
| 0.0023 (p5 poprawnych) | 1/17 = 5.9% | 10/183 = 5.5% |
| 0.0042 (p10) | 2/17 = 11.8% | 19/183 = 10.4% |
| 0.0145 (p25) | 9/17 = 52.9% | 46/183 = 25.1% |

Wymiana jest **niekorzystna na całej długości**: żeby złapać połowę błędnych locków trzeba
poświęcić ćwierć poprawnych. Powód jest strukturalny i zgodny z ustaleniem **F-3b-1**: conf liczony
na praktycznie zdegenerowanym (stałym) wejściu jest słabym sygnałem — wiele poprawnych locków ma
równie niską pewność jak błędne, więc rozkłady nakładają się w dolnym zakresie (fig. `fig_conf_dist.png`).

Krzywe ROC per-bieg i zbiorczo: `results/s3c0/fig_roc_conf.png`.

---

## 3. T3 — separacja R-B i punkty pracy θ_age

Wiek kanału przy wejściu w dwell (`age_at_dwell_entry`, znormalizowany age/AGE_MAX=8.0s) ze
wszystkich sześciu poziomów G2 plus osobno z bazy p0.00 (frozen S3b2-R bez dropoutu).
Źródło: `results/s3b4/measure.json` → `results[poziom].episodes[*]`.

Pooled (wszystkie poziomy, 246 epizodów które weszły w dwell — 188 sukces / 58 porażka):

| kubełek wieku | <0.8s | 0.8–2s | 2–4s | 4–6s | >6s |
|---|---|---|---|---|---|
| **sukces** (n=188) | 67 | 104 | 17 | 0 | 0 |
| **porażka** (n=58) | 9 | 27 | 0 | 1 | **21** |

Obraz jest asymetryczny i czytelny: **wszystkie** sukcesy wchodzą w dwell z wiekiem <4s (95. percentyl
= 2.0s), podczas gdy porażki mają wyraźny **ogon 21 epizodów przy wieku >6s** — kanał zamrożony,
lock stary. To są porażki wywołane utratą dostarczeń (dropout Bernoulli), nie porażki bazowe.
Uwaga równoważąca: **większość porażek (36/58) siedzi w niskim wieku** (<2s) — to porażki precyzji
dwell (B4) przy świeżym kanale, których żadna brama wieku nie złapie. R-B adresuje więc wyłącznie
tryb „zamrożony kanał", nie ścianę B4.

Baza p0.00 osobno: sukcesy wchodzą w dwell z wiekiem maks **1.25s** (mediana 0.83s), porażek tylko 5.
Baza jest „świeża" w całości.

Propozycje θ_age (pooled):

| θ_age | sukces utracony (pooled) | porażka złapana (pooled) | epizody bazy p0 dotknięte |
|---|---|---|---|
| 1.86s (p90 sukcesów) | 19/188 = 10.1% | 22/58 = 37.9% | 0/45 |
| **2.0s (p95 sukcesów)** | **9/188 = 4.8%** | **22/58 = 37.9%** | **0/45** |

**θ_age = 2.0s** jest wyraźnie lepszy: ta sama zdobycz (38% porażek), o połowę mniejszy koszt sukcesów,
i — co najważniejsze — **nie dotyka ani jednego epizodu czystej bazy** (0/45). Brama jest uśpiona,
gdy kanał jest zdrowy, a odzywa się dopiero przy zamrożeniu. Histogramy: `results/s3c0/fig_age_dwell.png`.

---

## 4. T4 — sucha symulacja replay (ESTYMATA, nie pomiar)

Przeliczenie na logach bazy, co zrobiłaby osłona przy każdym punkcie pracy. **To estymata na
zapisanych epizodach, nie pomiar** — właściwy pomiar (z realną odmową w pętli) to S3c1.

**R-A na bazie 67% (100 epizodów, 46500–46599)** — źródła: tick_audit R (pierwszy lock+conf+etykieta)
złączony z `diag_lite_episodes.json` (wynik/epizod). Macierz konwersji:

| θ_conf | wrong-action → odmowa | sukces → odmowa (fałszywa) | inna-porażka → odmowa | sukces bez zmian |
|---|---|---|---|---|
| 0.0023 | 0 | 3 | 1 | 64 |
| 0.0042 | 1 | 6 | 4 | 61 |
| 0.0145 | 6 | **15** | 8 | 52 |

Wniosek jest jednoznaczny i zgadza się z AUC: progowanie conf jest **net-negatywne**. Przy θ=0.0145
osłona przechwytuje 6 z 10 błędnych akcji, ale przy okazji **fałszywie odmawia 15 sukcesów** — dwa
poświęcone sukcesy na jedną złapaną złą akcję. Przy niskich progach łapie zero błędnych akcji (błędne
locki nie są wcale najniższe w conf). To potwierdza, że conf nie nadaje się jako brama admisyjności
na tym instrumencie.

**R-B na bazie p0.00 (50 epizodów 46500–46549, frozen S3b2-R; offset +13pp trudności vs populacja
67%, udokumentowany w RAPORT_S3B4)** — źródło: `measure.json[p0.00].episodes`. Macierz konwersji:

| θ_age | porażka → odmowa | sukces → odmowa (fałszywa) | sukces bez zmian | nie wszedł w dwell |
|---|---|---|---|---|
| 1.86s | 0 | 0 | 40 | 5 |
| 2.0s | 0 | 0 | 40 | 5 |

Na czystej bazie **R-B nie odpala ani razu** — zero fałszywych odmów, zero utraconych sukcesów.
Jest uśpiony (wszystkie wejścia w dwell są świeże) i cała jego wartość ujawnia się dopiero pod
dropoutem (ogon 21 porażek z §3, obecny na poziomach G2, nieobecny na bazie). To pożądana własność
osłony: nie szkodzi, gdy kanał jest zdrowy.

---

## 5. Do decyzji człowieka

**D1 — θ_conf (reguła R-A).** Rekomendacja sesji: **nie ustawiać progu conf; ograniczyć R-A do
wariantu NO_MATCH/timeout** — AUC 0.65 jest graniczne i niestabilne między biegami (0.60–0.72),
a replay pokazuje wymianę ok. 2 fałszywych odmów sukcesu na 1 złapaną złą akcję. Jeśli człowiek
mimo to chce twardej podłogi conf, najmniej szkodliwy jest θ=0.0023 (traci ~5% sukcesów), ale łapie
praktycznie zero złych akcji — czyli bezużyteczny.

**D2 — θ_age (reguła R-B).** Rekomendacja sesji: **θ_age = 2.0s** (0.25 znormalizowane) — nie dotyka
żadnego epizodu czystej bazy (0/45), a przechwytuje ~38% porażek trybu „zamrożony kanał"; koszt
4.8% sukcesów w scenariuszach z dropoutem. To jedyna z dwóch reguł, która niesie realny zysk przy
znikomym ryzyku.

Obie liczby to **punkty pracy do wyboru, nie decyzje**. Pomiar właściwy (osłona w pętli, z odmową)
= S3c1.

---

## 6. Higiena

Read-only na wszystkim poza `s3c0/` i `results/s3c0/`. Sweep G1 46600–46649 tylko odczytany
(walidacyjnie), nietknięty. Model, env, ekspert, YOLO, kontrakt D3 — nietknięte; zero treningu,
zero lotów. Artefakty: `results/s3c0/{conf_calib.json, age_replay.json, fig_roc_conf.png,
fig_conf_dist.png, fig_age_dwell.png}`, skrypty `s3c0/{calib_conf.py, calib_age.py, make_figures.py}`.
