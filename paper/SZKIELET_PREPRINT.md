# SZKIELET_PREPRINT — mapa granicy mechanizmu (wersja scalona, 2026-07-24)

Status: JEDYNE zrodlo prawdy dla struktury papieru. Scala ujecie
"dwurezimowej mapy granicy" (watek portfolio) z wynikami fazy 3
(GRANICA). Proza powstaje w W2 (EN) wylacznie z tego szkieletu +
paper/CLAIMS.md + paper/NUMBERS.md + paper/FIGURES.md.
Zasada: zadna liczba nie wchodzi do prozy inaczej niz przez NUMBERS.md.

## Tytul roboczy (EN, kandydaci — decyzja Olgi w W2)
1. "Mapping the Boundary: A Pre-Registered Measurement Program of the
   Liquid Network Temporal Advantage Across Task Regimes"
2. "Where Liquid Networks Help, Hurt, and Fail to Train:
   A Pre-Registered Boundary Map"
3. "The Trainability Tax: Pre-Registered Limits of CfC Networks from
   Satellite Time Series to Vision-Based Flight"

Afiliacja: Independent Research (jak P0). Venue: arXiv cs.LG/cs.RO
(uwaga: endorsement dla pierwszego zgloszenia; alternatywa na start:
TechRxiv/Zenodo z DOI). Jezyk: EN.

## Teza syntezy (jedno zdanie, krecosłup calego papieru)
Kierunek efektu zalezy od zadania — slaby plus w rzadkiej obserwacji
open-loop (P0), minus przy detekcji onsetu pod niskim FAR (E6), zero
w sterowaniu state-loop (LiquidFlight) — ale zaden pomiar nie
przekracza pre-rejestrowanego progu, a w najbogatszym rezimie
(wizyjna petla zamknieta) pytanie nie osiaga warunkow pomiaru:
przewage poprzedza podatek trenowalnosci przy parytecie.

## Ramka narracyjna (box w Intro lub Discussion)
"Wynik negatywny jako atut": dlaczego null z pre-rejestracja ma wyzsza
wartosc dowodowa niz niejedna wygrana krzywa (kultura dem vs replikacje).

---

## 0. Abstract (elementy, ~200 slow)
mechanizm i twierdzenie pod testem ([4]) -> program: 7 pomiarow,
3 rezimy zadan, zamrozone kryteria -> wynik glowny: mapa + podatek
trenowalnosci (C1/C2) -> atrybucja wiringu (C4) -> ustalenia
inzynierskie (C5/C6) -> wniosek syntezy.

## 1. Introduction
- Twierdzenie pod testem: przewaga OOD sieci plynnych w percepcji/
  sterowaniu ([4] Chahine et al., Science Robotics 2023; rodowod
  LTC->CfC [1][2]).
- Luka pola: dema bez parytetu i pre-rejestracji; brak niezaleznych
  replikacji; nikt nie raportuje warstwy trenowalnosci.
- Wklady (lista, mapowanie na C1-C8): mapa granicy (7 pomiarow);
  podatek trenowalnosci przy parytecie; granica-jako-wariancja;
  atrybucja wiringu; ustalenia inzynierskie; metodologia bramek
  z regula stopu i arytmetycznym wczesnym rozstrzyganiem.

## 2. Related Work
- Liquid networks: LTC, CfC, NCP/AutoNCP, Liquid-S4; twierdzenia
  o odpornosci ([4]) i ich zrodla.
- SSM/Mamba jako kuzyni ciagloczasowi (kontekst, 1 akapit).
- Pre-rejestracja i replikacje w ML; imitation learning
  (DAgger, Ross et al.) i stabilnosc.

## 3. The Measurement Program (metodologia domu)
- 5 zasad (z kompendium portfolio): [WERYFIKACJA: lista z kompendium].
- Honest twin: parytet rdzenia +-2%, wspolne budzety/dane/enkoder.
- Zamrozone kryteria przed pomiarem; MIERZE=RAPORTUJE.
- Bramki i precondition; aneksy jako sankcjonowane odmrozenia
  z dowodem; regula stopu (ANEKS-4).
- Arytmetyczne wczesne rozstrzyganie precondition (formula; 13 cykli
  zamiast 40) — ekonomia protokolu.
- Kontrakt determinizmu (env/render/seedy; poza kernelami CUDA).

## 4. Harnesses (trzy instrumenty)
4.1 PASTIS twin (P0): Sentinel-2, para pszenica/kukurydza, dropout
    obserwacji, wspolny enkoder CNN, CfC vs GRU. [raport P0]
4.2 LiquidFlight (state-loop, v1.0): setpoint->DSL-PID 48 Hz,
    position-hold, klif; osie latencja/przerwy; panel tau. [dok. v1.0]
4.3 LiquidSight (vision-loop, faza 3): fly-to-target 64x64, warstwa
    wykonawcza z v1.0 (kopie sha256), ekspert privileged + DAgger,
    drabina T0-T3 + K-dystraktory (ANEKS-2), P-SANITY, F3_GATE.
    [DECYZJE_F3 + aneksy 1-4, P_SANITY, F3_GATE, raporty]

## 5. Results Across Regimes (rdzen papieru)
5.1 R1 — open-loop klasyfikacja, skala dni (P0): kierunkowy plus
    ponizej progu; crossover F1 przy d=0.6; slope. [NUMBERS.md/P0]
5.2 R2 — open-loop detekcja onsetu, niski FAR (E6): kierunek ujemny.
    [NUMBERS.md; WERYFIKACJA z RAPORT_E6: jednostka delty opoznienia
    (dni?), sens parametru d, mianownik FAR — trzy punkty flagowane
    juz w kompendium]
5.3 R3 — state-loop control, skala ms (C0/C1/A1): dzwignia Delta-t
    nienosna behawioralnie; zero wywrotek z architektury wykonawczej;
    tau jako wyjasnialnosc, nie przewaga. [NUMBERS.md/v1.0]
5.4 R4 — vision-loop (faza 3, wynik glowny):
    a) precondition par.4 nieosiagniety zadnym ramieniem CfC na calej
       siatce lr -> teza [4] NIETESTOWALNA przy parytecie (C1);
       zero ewaluacji OOD w calej fazie (higiena).
    b) podatek trenowalnosci: gradient GRU 100% / NCP-wired
       (srednie nog, szczyt 92, rozstep 43 pp) / dense <=65 (C2).
    c) granica jest wariancja, nie srednia (C3) — lacznik z P0
       (rozrzut populacyjny odporny na n).
    d) atrybucja wiringu (C4): wired trenuje sie tam, gdzie dense pada
       (wiele seedow, dwa lr).
    Figury: b (nominale seed-po-seedzie z poprzeczka 90),
    c (dynamika DAgger), e (best_val BC vs agregat).

## 6. Engineering Findings ("co jest potrzebne, zeby CfC w ogole biegl")
- Cztery restauracje przepisu z dowodami (DIAG + ANEKS-3/4):
  backbone; sciezka Delta-t (JEDNOSTKI ts: sekundy vs tiki — rezim
  bramki czasu; C5); readout pelnego stanu vs motor-only; procedura
  DAgger retrening-od-zera + best-val vs kontynuacja (C6; GRU odporny
  na obie).
- Bug biblioteki: ncps.torch.CfC odrzuca timespans przy batch>1
  (obejscie: krokowanie komorka). [MANIFEST_F3 + RAPORT_DIAG_CFC]
- Teza pomocnicza: "Delta-t nosne implementacyjnie, nie przewagowo".

## 7. Instrument Characterization & Protocol Economics
- C8: drabina GRU-sanity 100/100/64/46/36/24/16; sufit eksperta 100%
  na calej drabinie; determinizm bit-w-bit W OBREBIE JEDNEJ MASZYNY
  (within-machine; cross-machine NIE twierdzony — S0_NOTES.md:51-53:
  hashe miedzy maszynami moga sie roznic i to nie jest FAIL);
  s1_visibility jako bramka obserwowalnosci (lekcja
  ANEKS-1).
- Ekonomia: 13 pelnych cykli zamiast 40; batch nigdy nieodpalony;
  koszt jednostkowy cykli. [NUMBERS.md]

## 8. Discussion
- Synteza (teza z naglowka) + interpretacja: konstrukcja zadania
  decyduje, czy mechanizm moze sie ujawnic (wniosek (b) z P0,
  uogolniony na 7 pomiarow).
- Kultura dem vs falsyfikacja: co mapa wnosi, czego nie wnosi.
- Kiedy twin sie ponownie uzbraja: warunki odblokowania trenowalnosci
  (przepisy treningu komorek CT; trop: wrazliwosc na DAgger-kontynuacje
  jako otwarty problem badawczy).
- Nastepny habitat mechanizmu: sensory asynchroniczne / event stream
  (1 akapit, bez obietnic).

## 9. Limitations
sim-only (PyBullet, bez fotorealizmu i sim-to-real); jeden harness na
rezim; parytet w skali ~27k parametrow; n=10 (z regula finalnosci);
brak pomiaru OOD w R4 (konsekwencja precondition, nie wybor); jedna
rodzina zadan per rezim; zespol jednoosobowy; E6 — trzy punkty do
weryfikacji ze zrodlem.

## 10. Reproducibility & Artifacts
repo liquidflight v1.0 + liquidsight (tagi, commity bramek), zamrozone
dokumenty (F3_PRE0, DECYZJE_F3+aneksy, P_SANITY, F3_GATE), manifesty
sha256, pule seedow, raporty; P0 jako companion (PDF/arXiv).

## 11. Conclusion (pol strony)
Mapa granicy jako wynik pierwszego rzedu; podatek trenowalnosci jako
warstwa, ktorej pole nie raportuje; metodologia jako przenosny wklad.

## Appendices
A. Timeline bramek i aneksow (figura a) z jednozdaniowymi powodami.
B. Zamrozone kryteria verbatim (P_SANITY, F3_GATE par.4-5, regula stopu).
C. Tabele per-seed wszystkich nog + trajektorie DAgger.
D. Formula wczesnego rozstrzygania + zapis oszczednosci.

---

## Mapa twierdzen -> sekcje (dla W1/T4)
C1->5.4a | C2->5.4b | C3->5.4c | C4->5.4d | C5->6 | C6->6 | C7->3,7,D
| C8->7. Figury: a->App A | b->5.4 | c->5.4/6 | d->7 | e->6.

## Decyzje otwarte (Olga, przy W2)
- tytul (1-3) i abstrakt-akcent (mapa vs podatek trenowalnosci);
- glebokosc R1-R3 (pelne podsekcje vs skondensowana tabela mapy
  + odeslanie do P0/kompendium);
- venue startowe (arXiv z endorsementem vs TechRxiv/Zenodo teraz).
