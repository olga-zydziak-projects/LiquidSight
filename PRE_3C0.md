# PRE_3C0 — kickoff fazy 3c-MVP: oslona (2026-07-28)

Status: dokument DECYZYJNY. Cel MVP: warstwa gwarancji nad zmierzonym
systemem — zamiana znanych modow porazki w odmowe lub wstrzymanie
Z POWODEM, z pomiarem efektu. MVP zasila akt 4 dema i jest fundamentem
pelnego 3c (formalizacja Z3 — poza MVP, osobne PRE po demo).

Punkt wyjscia (zmierzony): granica 67%/10% (policy_gc5.pt, FROZEN);
wrong-lock w dwoch modach o niestabilnej proporcji (first-lock-bad /
kradziez); sciana B4 = dryf slepego zawisu przy starym kanale;
G2: statystyka wystarczajaca = swiezosc kanalu przy wejsciu w dwell;
conf logowany per tick od ANEKS-3B (siedem biegow logow do kalibracji).

## 0. Zasada konstrukcyjna

Oslona = CZYSTY WRAPPER nad kanalem i polityka. Zero zmian w polityce,
kanale, env, percepcji — wszystkie dotychczasowe pomiary pozostaja
wazne, oslona dziala na ich wyjsciach. Decyzje oslony sa
deterministyczne i wyjasnialne (regula + wartosc + prog).

Wyjscia oslony: ALLOW / HOLD (position-hold przez egzekutor —
mechanizm z v1.0) / REFUSE(reason).
Powody enumerowane: LOW_CONF_LOCK, STALE_AT_DWELL, GEOFENCE, NO_MATCH.

## 1. Ksiegowosc trojwynikowa (fundament pomiaru)

Od 3c kazdy epizod konczy sie jednym z TRZECH wynikow:
- SUKCES: dolot+dwell przy wskazanym, oslona ALLOW;
- ODMOWA: oslona zatrzymala misje z powodem (HOLD->timeout->REFUSE
  lub REFUSE wprost) — dron bezpieczny, zadanie niewykonane;
- PORAZKA: wrong-action (dolot/dwell przy zlym obiekcie) albo
  katastrofa albo dryf bez odmowy.
Odmowa NIE jest porazka i NIE jest sukcesem. Wrong-action pozostaje
porazka pierwszej klasy. Sens oslony: kupowac redukcje wrong-action
za cene czesci sukcesow zamienionych w odmowy — oba kierunki
raportowane zawsze.

## 2. Reguly MVP (parametry empiryczne)

R-A — admisja pierwszego locka: lock inicjalny przyjety tylko gdy
  conf >= theta_conf; ponizej -> HOLD i czekanie na lepszy tick;
  brak przez T_acq -> REFUSE(NO_MATCH lub LOW_CONF_LOCK).
  theta_conf: z krzywej ROC na ISTNIEJACYCH logach (tick_audit +
  conf_log biegow R..R7: conf lockow poprawnych vs blednych);
  punkt pracy pre-rejestrowany przed pomiarem S1.

R-B — admisja wejscia w dwell: gdy dystans < 0.5 m (martwe pole)
  i age_s > theta_age -> HOLD (zakaz slepego finiszu na starej
  referencji); tick nie przychodzi przez T_hold -> REFUSE
  (STALE_AT_DWELL). theta_age: z histogramow age-at-dwell-entry G2
  (sukcesy vs porazki). Zamierzony efekt: czesc B4 zamienia sie
  w odmowy — system mowi "nie jestem pewien pozycji" zamiast chybiac.

R-C — geofence: cel poza arena lub trajektoria wychodzaca poza
  granice -> REFUSE(GEOFENCE), przed startem lub w locie.

R-D — no-match: grounder bez dopasowania do komendy przez T_acq
  -> REFUSE(NO_MATCH). Kryje komendy-pulapki (obiekt nieobecny).

## 3. Decyzje D3c-1..5

| # | decyzja | rekomendacja |
|---|---|---|
| D1 | punkt pracy theta_conf | wybor Olgi z 2-3 punktow ROC zaproponowanych przez S3c0 (kazdy: ile wrong-lockow lapie / ile sukcesow kosztuje) |
| D2 | theta_age | odczyt z G2 (separacja histogramow), propozycja S3c0, zatwierdzenie Olgi |
| D3 | timeouty | T_acq = 3.0 s, T_hold = 3.0 s (proste, jawne; do rewizji po S1) |
| D4 | definicje wynikow | jak par. 1 (trojwynikowe; wrong-action = porazka pierwszej klasy) |
| D5 | zbior pulapek S2 | pula 47400-47449 (dopisac do D8): komendy wskazujace obiekt NIEOBECNY w scenie (25 ep) i cel za geofencem (25 ep); oczekiwanie: 100% odmow z wlasciwym powodem |

## 4. Pomiary fazy

POMIAR-S1 (skutecznosc oslony): eval 46500-46599, 100 ep, PAROWANE
  z oslona vs bez (te same sceny, ten sam model): macierz konwersji —
  ile wrong-actionow zlapanych (->ODMOWA), ile sukcesow utraconych
  (->ODMOWA), sukces netto, wrong-action netto; rozbicie per regula
  (R-A/R-B) i per mod porazki.
POMIAR-S2 (odmowa twarda): pula pulapek D5 — odsetek poprawnych
  odmow z wlasciwym powodem (oczekiwanie 100%).

Ramowanie: charakteryzacja (jak G2) — pre-rejestrowane sa reguly,
parametry (po S3c0) i zbiory; twierdzenia progowe formuluje
RAPORT_3C_MVP na zmierzonych liczbach.

## 5. Sekwencja sesji

S3c0 — kalibracja OFFLINE (zero lotow, zero treningu): ROC conf
  z istniejacych logow; histogramy age z G2; propozycje theta_conf
  (2-3 punkty pracy) i theta_age z wykresami -> STOP, decyzje
  D1/D2 Olgi.
S3c1 — implementacja wrappera + testy jednostkowe regul + POMIAR-S1
  + POMIAR-S2 + RAPORT_3C_MVP (+ hooki demo: log decyzji oslony
  per epizod w formacie pod overlay aktu 4).

## 6. Poza zakresem MVP

Formalizacja Z3 i dowody, weryfikacja polityki, zmiany
polityki/kanalu/env/percepcji, nowe dzwignie G1, montaz dema
(osobny etap), zmiany progow G1/G2.

## 7. Ryzyka (nazwane z gory)

- ROC conf moze byc plaska (YOLO conf zyje w 0.01-0.05; separacja
  poprawne/bledne niepewna) -> wtedy R-A ogranicza sie do
  NO_MATCH/timeout, raportujemy wprost.
- R-B zamieni czesc near-missow w odmowy: sukces surowy moze SPASC
  ponizej 67% przy spadku wrong-action — to jest istota trade-offu
  i oba kierunki sa raportowane, bez ukrywania.
- Podwojne liczenie HOLD->ALLOW->sukces: definicje D4 obowiazuja
  od poczatku pomiaru; asserty jednoznacznosci wyniku epizodu.
