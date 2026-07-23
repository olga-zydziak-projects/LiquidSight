# ANEKS-4 do F3_GATE — procedura treningu (2026-07-24)
Powod: po naprawie konstrukcji (ANEKS-3) BC fituje, ale procedura
DAgger bramki (dotrening-kontynuacja + checkpoint final-epoch)
destabilizuje komorki ciagloczasowe: A_CFC 78/100 tilt (gorzej niz po
samym BC), A_NCP kolaps rolloutow 1->0->0; A_GRU odporny na te sama
procedure. Frozen C1 (dzialajacy closed-loop CfC) trenowal inaczej —
to ostatnia rozbieznosc przepisu wzgledem zlotej referencji.

Zloty przepis (frozen `src/c1_train.py`, odczyt T1):
- (a) rundy DAgger = retrening OD ZERA na pelnym agregacie kazda runde
  [c1_train.py:181-196 petla + agregacja `dataset = dataset + new`;
  c1_train.py:127-131 `train_from_scratch` = swiezy model + swiezy Adam];
- (b) selekcja = best-val (min val_mse) [c1_train.py:135,151-156];
  walidacja = rollouty eksperta na rozlacznym zbiorze [c1_train.py:85-95;
  c1_common.py:67 `C1_VAL`];
- (c) epoki = 120 per etap (BC=runda0 i kazda runda) [c1_train.py:37];
  ROUNDS=3 [c1_train.py:39]; Adam lr, batch 16 ep, grad clip 1.0
  [c1_train.py:38,40,131,149].

Zmiany (jedyne; symetrycznie dla WSZYSTKICH ramion, par.3 F3_GATE):
Z1 rundy DAgger: retrening OD ZERA na pelnym agregacie w kazdej
   rundzie [Z-FROZEN: potwierdzone — c1_train.py:181-196 (petla rnd0..3
   ta sama `train_from_scratch`, agregacja `dataset = dataset + new`),
   c1_train.py:127-131 (swiezy model+optymalizator, init seed co runda)];
   kanoniczna forma DAgger (Ross et al. 2011).
Z2 selekcja checkpointu: best-val na kazdym etapie; split walidacyjny
   10% epizodow (dotad monitoringowy) zostaje przemianowany na
   selekcyjny — symetrycznie, ta sama lista epizodow dla wszystkich
   ramion i seedow [Z-FROZEN: mechanizm — c1_train.py:135 (best=inf),
   :151-155 (per-epoka val, deepcopy best_state gdy vl<best), :156
   (load best_state); analog frozen walidacji-eksperta c1_train.py:85-95
   / c1_common.py:67. Konkretnie: `data/bc/split.json` klucz `val`
   (30 epizodow, co 10-ty z 44000-44299, ekspert-etykietowane), staly
   dla wszystkich ramion i seedow; walidacja pozostaje ekspertowa i
   stala przez wszystkie rundy].
Z3 liczby epok per etap: [Z-FROZEN: BC=120, runda=120; prowieniencja
   c1_train.py:37 (EPOCHS=120), :39 (ROUNDS=3), :181 (petla obejmuje
   runde 0 i rundy 1..3 ta sama funkcja train_from_scratch)].

Lr per ramie i siatka fallback par.4: BEZ ZMIAN (A_GRU 1e-3;
A_NCP/A_CFC 3e-4; frozen uniform 1e-3 NIE jest adoptowany — par.4
poza mandatem). Dane, sceny, poziom T2b, n=10, prog par.5,
wskazniki par.6: BEZ ZMIAN. Konstrukcja rdzeni (ANEKS-3): BEZ ZMIAN.
Normalizacja wejsc (set_norm frozen): NIE adoptowana — to konstrukcja,
zamknieta ANEKS-3; aneks dotyka wylacznie procedury.

Koszt: czas cyklu wzrosnie symetrycznie (retrening od zera x4 etapy po
120 epok, vs BC-15 + DAgger-10x3) — nowa jednostka kosztu zmierzona
w smoke tej sesji.

REGULA STOPU (wiazaca): ANEKS-4 domyka zgodnosc przepisu z frozen C1.
Dalszych aneksow instrumentalnych w fazie 3a NIE BEDZIE. Jesli po
ANEKS-4 ramie CfC nie osiagnie precondition par.4 (wlacznie z siatka
lr), FAIL przechodzi w WYNIK: STOP par.4 i decyzja czlowieka o
raportowaniu granicy trenowalnosci CfC w tym harnessie jako komorki
mapy programu.

Higiena tezy: zero ewaluacji OOD od poczatku fazy; zmiana jest
restauracja pre-istniejacego przepisu z zamrozonego v1.0, stosowana
symetrycznie; diagnozy wylacznie nominalne; defekt dzialal przeciw
ramieniu faworyzowanemu.
