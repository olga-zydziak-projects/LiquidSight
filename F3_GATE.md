# F3_GATE — kryterium pojedynku twin (FROZEN z chwila tego commita)
Zrodla decyzji: P_SANITY.md (koncowka), RAPORT_PSANITY_R2.md,
decyzje czlowieka 2026-07-23 (poziom T2b; trzy ramiona; n=10).

## 1. Teza i ramiona
Teza (F3_PRE0 par.0): rdzen liquid, przy parytecie parametrow rdzenia
i identycznym budzecie treningu, nadaje polityce wizyjnej w petli
zamknietej wieksza odpornosc na przesuniecie domeny percepcyjnej niz GRU.
Ramiona (wspolne: enkoder jak w P-SANITY, glowa Linear(->6) z tym samym
skalowaniem, wejscie rdzenia 78, tyk na klatce 12 Hz):
  A_GRU — GRU hidden 64, 27 648 param (referencja, jak P-SANITY);
  A_NCP — CfC z okablowaniem AutoNCP, parytet 27 648 +-2% (RAMIE
          ORZEKAJACE — wiernosc [4]: Chahine uzywal wiringu NCP;
          realizuje "CfC" z zapisu P_SANITY);
  A_CFC — dense CfC, parytet 27 648 +-2% (ramie opisowe: izoluje wklad
          wiringu od dynamiki ciaglej; ciaglosc z komorkami P0/C1).
Dokladne rozmiary/liczby parametrow: dowod parytetu (I3a) dopisywany do
MANIFEST_F3.json PRZED biegiem wiazacym; po dopisaniu — frozen.

## 2. Poziom bramki i zbiory
Poziom bramki: T2b (K=2) — najciezszy w pasmie [30,85] wg P2R.
Sweep: sceny 43100-43149 (50, identyczne dla wszystkich ramion i seedow),
pelna drabina {T0,T1,T2,T2a,T2b,T2c,T3} raportowana.
Nominal (precondition): sceny 43000-43099 (100 ep).
Dane: BC 300 ep eksperta, sceny 44000-44299 — ZBIOR WSPOLNY dla
wszystkich ramion; DAgger 3 rundy x 100 rolloutow, sceny 44300-44399 /
44400-44499 / 44500-44599 (procedura identyczna; tresc rolloutow zalezy
od polityki — symetryczne z konstrukcji).
Seedy treningowe: 45010-45019 (n=10), sparowane po indeksie miedzy
ramionami (seed steruje init + shuffle + kolejnoscia rolloutow ta sama
procedura per ramie).

## 3. Budzety i hiperparametry
Identyczne dla wszystkich ramion: batch 16 epizodow, Adam, clip 1.0,
BC 15 epok, DAgger dotrening 10 epok/runde, dane i sceny jw.
Rozne WYLACZNIE lr (pochodzenie udokumentowane):
  A_GRU: 1e-3 (potwierdzone P-SANITY R1);
  A_NCP, A_CFC: 3e-4 (symetryczny sweep P0).
Fallback nominalny (pre-rejestrowany, tylko sciezka precondition par.4):
siatka {3e-4, 1e-3}.

## 4. Warunek zdolnosci nominalnej (precondition, nie teza)
Per RAMIE: srednia po seedach z sukcesu nominal (43000-43099) >= 90%.
FAIL ramienia -> sankcjonowana naprawa WYLACZNIE nominalna (lr z siatki
fallback; nic innego), pelny retrening WSZYSTKICH seedow ramienia, log;
wyczerpanie -> STOP do decyzji czlowieka, bez werdyktu tezy.
Pojedyncze seedy NIE sa wykluczane ani naprawiane — niestabilnosc
treningu jest czescia mierzonego rozkladu i wchodzi do pooled std.
ZAKAZ ewaluacji OOD przed spelnieniem precondition wszystkich ramion.

## 5. Wskaznik pierwotny i prog (orzekajace)
Per seed s, ramie a: succ(a,s) = odsetek sukcesow na 50 scenach T2b
(ewaluacja deterministyczna polityki).
M = mean_s succ(A_NCP,s) - mean_s succ(A_GRU,s), n=10.
pooled_std = sqrt( (sd_s(A_NCP)^2 + sd_s(A_GRU)^2) / 2 ), sd po seedach
(rozrzut populacyjny, jak w P0 — nie SEM).
WERDYKT: teza potwierdzona <=> M > pooled_std. Inaczej: niepotwierdzona.
Kierunek i wielkosc raportowane zawsze. Wynik przy n=10 WIAZACY;
zakaz zwiekszania n, zmiany poziomu bramki lub progu po obejrzeniu
JAKICHKOLWIEK wynikow OOD.

## 6. Wskazniki wtorne (pre-rejestrowane, NIEORZEKAJACE)
W1 marginesy opisowe na T2b: A_CFC-A_GRU oraz A_NCP-A_CFC (te same
   definicje co M).
W2 pelne krzywe drabiny: 7 poziomow x 3 ramiona, mean+-sd po seedach.
W3 panel uwagi: saliency = |grad( sum|setpoint_6D| , rgb )|, max po
   kanalach, binaryzacja top-2% pikseli; IoU z maska seg celu;
   klatki: co 4. klatka fazy dolotu (do pierwszego wejscia w r_goal),
   max 15 klatek/epizod, pierwsze 10 epizodow sweep per poziom per seed;
   raport: mean+-sd IoU per ramie per poziom (krzywa IoU vs K).
W4 histogram stalych czasowych tau dla A_CFC i A_NCP (agregat po
   seedach, te same klatki co W3).
W5 czasy scienne treningu per ramie (jednostka kosztu programu).

## 7. Raport i rygor
RAPORT_F3.md: werdykt wg par.5 + wszystkie wskazniki wtorne + logi
napraw precondition (jesli byly) + odchylenia (oczekiwane: zadne).
MIERZE = RAPORTUJE. Raporty poprzednich bramek nietkniete.
