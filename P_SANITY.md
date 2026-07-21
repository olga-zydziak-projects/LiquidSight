# P_SANITY — bramka zdolnosci instrumentu (FROZEN z chwila tego commita)
Werdykty wylacznie wg ponizszych progow; zmiana progow po commicie
zabroniona. Wykonanie pomiarow: sesja I2.
Ramie P-SANITY: GRU — wynik pre-rejestrowanego rzutu moneta
(numpy default_rng(40000).integers(0,2), 0=GRU 1=CfC, wynik 0,
wykonany 2026-07-22 na etapie planowania, poza ta sesja).
P1 zdolnosc: ramie GRU po BC + 3xDAgger (dane wylacznie T0) osiaga
   >= 90% sukcesu na 100 epizodach eval (sceny 43000-43099, tekstury T0).
   FAIL -> naprawa instrumentu wylacznie na nominalu (rozdzielczosc /
   ilosc danych / rundy DAgger), powtorka P1; pomiar tezy (F3_GATE)
   zakazany do PASS.
P2 rozdzielczosc osi: ta sama polityka, 50 epizodow/poziom na T0-T3
   (sceny 43100-43149, identyczne na kazdym poziomie): wymagane >= 2
   poziomy ze srednim sukcesem w pasmie [30%, 85%].
   Wszystko > 85% -> wzmocnienie T3 (K: 4->8, jitter koloru do +-0.05)
   i powtorka P2 — dozwolone, bo F3_GATE jeszcze nie frozen.
   Skok z >85% do <30% miedzy sasiednimi poziomami -> dodac poziom
   posredni miedzy nimi i powtorzyc P2.
P3 sufit: ekspert privileged, 50 epizodow/poziom na tych samych scenach
   43100-43149, T0-T3: >= 95% sukcesu na KAZDYM poziomie (os dotyka
   wylacznie pikseli, ekspert pikseli nie widzi). FAIL -> blad
   konstrukcji sceny, STOP fazy do diagnozy.
Po PASS P1-P3: zamrozenie F3_GATE (metryka: % sukcesu sparowanego na
poziomie wskazanym przez P2; wskaznik: margines CfC-GRU; prog: margines
> pooled std; n seedow: z pomiaru czasu treningu P1).
