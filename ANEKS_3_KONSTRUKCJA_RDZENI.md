# ANEKS-3 do F3_GATE — naprawa konstrukcji rdzeni CfC (2026-07-24)
Powod: precondition par.4 FAIL obu ramion CfC (10-19% nominal na calej
siatce lr) przy A_GRU 100% w identycznym harnessie. Diagnoza
(RAPORT_DIAG_CFC, nominal-only, zero OOD) wykazala trzy defekty
KONSTRUKCJI wzgledem zlotej referencji frozen C1 — dzialajacego
closed-loop CfC z zamrozonego liquidflight-v1.0:
(1) A_CFC zbudowany bez backbone (8/50 dolotow vs 35/50 z backbone);
(2) kanal Delta-t martwy: wrapper ncps.torch.CfC odrzuca jawne
    timespans przy batch>1 (bug biblioteki), wiec ramiona tkwily w
    ts=1.0 [tiki] zamiast sekund; skala ts steruje rezimem bramki
    czasu (napęd |t_a*ts|: 0.010 @0.083s / 0.125 @1.0 / 0.501 @4.0)
    — zla skala unieruchamia komorke (dolot 39 vs 15 vs 9);
(3) A_NCP readout z 6 neuronow motorycznych = 9% stanu (frozen czytal
    30%): BC 0.022 vs 0.0047, dolot 8/50 vs 26/50 przy pelnym stanie.
Dowod rozstrzygajacy: komorka wg przepisu frozen (CfCCell + backbone +
ts=sekundy) osiaga 39/50 dolotow ~ GRU 37/50 przy identycznym BC-8.
Zmiany (jedyne):
Z1 A_CFC: komorka stylu frozen C1 — CfCCell z backbone
   (units=70, backbone=64); rdzen 27 736 param (+0.32%, pasmo +-2% OK).
Z2 oba ramiona CfC: krokowanie manualne komorka (CfCCell /
   WiredCfCCell) z jawnym ts w SEKUNDACH: 1/12 s = 0.08333 na tik
   kamery; obejscie buga wrappera (bug odnotowany w MANIFEST_F3
   i raportach jako ograniczenie biblioteki ncps 1.0.1).
Z3 A_NCP: okablowanie AutoNCP bez zmian (rdzen 27 571 param, bez
   zmian); readout z PELNEGO stanu (64) zamiast 6 motorycznych;
   glowa Linear(64->6) — od teraz identyczna we wszystkich trzech
   ramionach (dla A_NCP element naprawy; A_GRU/A_CFC bez zmian).
Co sie NIE zmienia: enkoder, skalowanie wyjscia glowy, budzety
i hiperparametry par.3 (lr per ramie + siatka fallback wlacznie),
dane i sceny, poziom bramki T2b, n=10, prog i wskazniki par.5-6,
procedury par.4 i par.7.
Higiena tezy: (a) zero ewaluacji OOD od poczatku fazy (potwierdzone
w I3a i DIAG); (b) naprawa przywraca PRE-ISTNIEJACY przepis z
zamrozonego v1.0 — nie jest konstrukcja post-hoc; (c) diagnoza
wylacznie nominalna; (d) wszystkie trzy defekty dzialaly PRZECIW
ramieniu faworyzowanemu — ich pozostawienie czyniloby werdykt
niemiarodajnym w obie strony.
Procedura po aneksie: nowy dowod parytetu -> MANIFEST_F3
(gate_arms_v2, poprzednia sekcja zachowana jako v1), pelnocyklowy
smoke nominalny obu ramion (seed 45010), dopiero po nim I3b.
