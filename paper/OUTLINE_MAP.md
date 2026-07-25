# OUTLINE_MAP.md — mapa C1–C8 i figur a–e na sekcje preprintu (W1)

**Data:** 2026-07-24. **Szkielet ZNALEZIONY w repo:** `paper/SZKIELET_PREPRINT.md`
(wersja scalona 2026-07-24, „mapa granicy mechanizmu"). Mapowanie ponizej
**uzywa jego struktury** (nie zastepuje jej ukladem standardowym). Szkielet ma
juz wlasna „Mapa twierdzen → sekcje" (linie 155–157) — **weryfikuje ja i
uszczegolawia**. Rozbieznosci oznaczone ⚠.

Uwaga zakresu: preprint jest **portfolio-level** (3 rezimy: R1 open-loop
klasyfikacja/P0, R2 detekcja onsetu/E6, R3 state-loop/LiquidFlight, R4 vision-
loop/faza 3). **W1 pokrywa wylacznie fazy 3 (R4) + metodologie/instrument**;
material R1–R3 (P0/E6/v1.0) to companion/portfolio — patrz LUKI w CLAIMS.md
(GAP-1 P0, GAP-3 E6).

---

## 1. Mapowanie twierdzen → sekcje szkieletu

| twierdzenie | ranga | sekcja szkieletu | zgodnosc z „Mapa" szkieletu (l.155-157) |
|---|---|---|---|
| **C1** teza [4] nietestowalna przy parytecie | glowne | **§5.1 akapit (C1)** (+ §1 wklady, §8 Discussion) | ✓ (W3.1: naglowki nienumerowane) |
| **C2** podatek trenowalnosci | glowne | **§5.1 akapit (C2)** (+ §0 Abstract, §1) | ✓ |
| **C3** granica = wariancja | glowne | **§5.1 akapit (C3)** (+ §8 synteza, lacznik P0) | ✓ |
| **C4** atrybucja wiringu | glowne | **§5.1 akapit (C4)** | ✓ |
| **C5** Δt nosne implementacyjnie | wtorne | **§6** (Engineering) | ✓ (C5→6) |
| **C6** wrazliwosc CT na DAgger | wtorne | **§6** (Engineering) | ✓ (C6→6) |
| **C7** metodologia jako wklad | wtorne | **§3** (Program), **§7** (Protocol economics), **App D** | ✓ (C7→3,7,D) |
| **C8** charakteryzacja instrumentu | wtorne | **§7** (Instrument charakteryzacja) | ✓ (C8→7) |

**Footnote'y** (z CLAIMS.md) — miejsca:
- C2a (dwell/tilt): §5.1 akapit (C2), przy fig. b.
- C6a (BC vs agregat): §6 + fig. e; sygnatura mechanizmu.
- C7a (ekonomia ~57,1 h): §7 + App D.

**⚠ Uwagi do mapy szkieletu:**
1. C3 → §5.1 akapit (C3) wymaga **GAP-1** (cytat P0 dla „rozrzut populacyjny odporny na n").
   Bez P0 czesc lacznikowa §8 zostaje jako teza syntezy bez liczby-mostu.
2. C7 rozlewa sie na 3 miejsca (§3 metodologia domu, §7 ekonomia, App D formula) —
   spojnosc: definicja formuly wczesnego rozstrzygania raz (App D), reszta cytuje.
3. §5.2 (R2/E6) i §5.1 (R1/P0) **nie sa pokryte W1** — poza faza 3.

---

## 2. Mapowanie figur → sekcje szkieletu

| figura | sekcja szkieletu | zgodnosc (l.157) | status (FIGURES.md) |
|---|---|---|---|
| **(a)** timeline bramek/aneksow | **App A** | ✓ (a→App A) | GOTOWE |
| **(b)** nominale seed-po-seedzie | **§5.4** | ✓ (b→5.4) | GOTOWE |
| **(c)** dynamika DAgger | **§5.4 / §6** | ✓ (c→5.4/6) | GOTOWE |
| **(d)** drabina + sufit eksperta | **§7** | ✓ (d→7) | GOTOWE |
| **(e)** best_val BC vs agregat | **§6** | ✓ (e→6) | CZ. GOTOWE (round-level) |

Zgodnosc pelna z „Mapa figur" szkieletu (l.157). Zero konfliktow.

---

## 3. Uklad standardowy (rezerwowy — gdyby szkielet odrzucony)

Szkielet JEST i jest uzyty (sekcja 1–2). Na wypadek decyzji Olgi o ukladzie
klasycznym, mapowanie zapasowe:

| sekcja standardowa | tresc z fazy 3 | twierdzenia / figury |
|---|---|---|
| Introduction | teza [4], luka pola (brak parytetu/pre-rejestracji) | C1 (wklady) |
| Related Work | liquid nets (LTC/CfC/NCP), pre-rejestracja, DAgger | — |
| Program & Methods | 5 zasad, honest twin, bramki, wczesne rozstrzyganie | C7; fig. a |
| Results | precondition GRANICA, podatek, wariancja, wiring | C1–C4; fig. b,c |
| Engineering findings | 4 restauracje, Δt/ncps bug, procedura DAgger | C5,C6; fig. e |
| Instrument characterization | drabina, sufit, determinizm | C8; fig. d |
| Limitations | (patrz sekcja 4) | — |
| Conclusion | mapa granicy + podatek jako warstwa | synteza |

---

## 4. Zastrzezenia do Limitations (zebrane, ze zrodlami)

Do sekcji §9 szkieletu (Limitations). Kazde ze zrodlem:

1. **sim-only** — PyBullet, bez fotorealizmu i sim-to-real (`SZKIELET §9`;
   zadanie zdefiniowane w `DECYZJE_F3.md` D1–D3, env sim).
2. **jeden harness na rezim** — fly-to-target 64×64, jedna rodzina zadan
   (`SZKIELET §9`; `F3_GATE §1`).
3. **parytet w skali ~27k parametrow rdzenia** — 27 648 ±2%; wynik moze nie
   uogolniac na inne pojemnosci (`MANIFEST_F3.json gate_arms_v2`; `F3_GATE §1`).
4. **n=10 (z regula finalnosci)** — realnie uzyte seedy 45010–45015 (wczesne
   rozstrzygniecie); zakaz zwiekszania n po obejrzeniu OOD (`F3_GATE §4-5`;
   NUMBERS.md T2).
5. **brak pomiaru OOD w R4** — konsekwencja nieosiagnietego precondition, NIE
   wybor projektowy (`RAPORT_F3.md §7`; C1).
6. **jedna rodzina zadan per rezim; zespol jednoosobowy** (`SZKIELET §9`).
7. **⚠ determinizm tylko w obrebie maszyny** — nie cross-machine (GAP-2;
   `S0_NOTES.md:51-53`). Do Limitations jako uczciwe zawezenie.
8. **budzet treningu ustalony** — „podatek trenowalnosci" mierzony przy BC-120+
   DAgger×3; wyzszy symetryczny budzet niezmierzony (`RAPORT_F3.md §8a`; C2).
9. **restauracje R1–R4 = sondy n=1** — ilustracyjne, nie statystyczne (GAP-4;
   `RAPORT_DIAG_CFC.md §3`).
10. **E6/R2 — trzy punkty do weryfikacji ze zrodlem** (poza repo; GAP-3;
    `SZKIELET §5.2, §9`).

---

## 5. Status szkieletu i decyzje otwarte (dla W2, z §Decyzje otwarte szkieletu)

Szkielet **dostarczony** (nie „do dostarczenia"). Decyzje Olgi przy W2
(`SZKIELET` l.159–163):
- tytul (kandydaci 1–3) i akcent abstraktu (mapa vs podatek trenowalnosci);
- glebokosc R1–R3 (pelne podsekcje vs skondensowana tabela mapy + odeslanie do
  P0/kompendium) — **zalezne od domkniecia GAP-1/GAP-3**;
- venue startowe (arXiv z endorsementem vs TechRxiv/Zenodo).
- ⚠ **papier/ vs paper/**: skonsolidowano do `paper/` (ta sesja); wewnetrzne
  odwolania szkieletu (`paper/CLAIMS.md` itd.) teraz rozwiazuja sie lokalnie.
