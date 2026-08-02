# PRE_DP0 — pre-rejestracja fazy DP (demo-proof)

**Data:** 2026-08-03. **Etap:** P (dokument zamrożony; kończy się STOP na ratyfikację). **Podstawa:**
`RECON_DP.md`. **Charakter:** faza **BUDOWY** pokazowej, **nie pomiarowa** — żadna nowa liczba nie
powstaje; każda liczba na ekranie ma wpis w tabeli prowieniencji (§7). System ZAMROŻONY po S3c1-R;
kanał bez filtra (werdykt 3d NEGATYWNY). `[PROPOZYCJA]` = do ratyfikacji człowieka.

> **STATUS: RATYFIKOWANE** (człowiek, 2026-08-03). Ratyfikowany pakiet: F-D1 (APPLIED wszędzie,
> panel od A1, bounded ≤3 re-record, scena flipująca wypada), F-D2 (artefakt P3 budowany w DP:
> param-count = fakt strukturalny z checkpointu, bound wyłącznie z solvera), F-D3 (stack:
> **z3-solver z pip, wersja PRZYPIĘTA w `requirements-proofs.txt` i wpisywana do każdego certyfikatu**;
> **numpy-IBP dla P3**; **auto_LiRPA NIE bez osobnej zgody**; lokalny **PCDL+HMAC** z długiem
> integracyjnym), zakres P3 (minimum **AutoNCP-20**; gc5 warunkowo — jeśli goły IBP da przedziały
> bez wartości informacyjnej, gc5 dostaje status **UNPROVEN-tą-metodą** i **nic nie doinstalowujemy**),
> F-D4/F-D5 (założenia P2 jawne; alias rozwiązywany PRZED frazą — autoryzacja zawsze widzi kanoniczny
> spec). Etap B **autoryzowany**, kolejność §8; commit per moduł. **Formalizacja P1 wymaga ODRĘBNEJ
> ratyfikacji** (predykaty modelu) przed pierwszym odpaleniem solvera.

## Zasady nadrzędne DP (uzupełnienie ratyfikacyjne)

**Certyfikaty dowodowe są jedyną kategorią nowych artefaktów, jakie faza DP produkuje; trafiają
wyłącznie do kolumny PROVED, nigdy MEASURED.** (Nagrania to ilustracje ze zmierzonych konfiguracji,
nie nowe artefakty-liczby; liczby-banery pochodzą z zamrożonych raportów, RECON §C.)

---

## §1 Tożsamość dema

**„Dowodzimy, gdzie dowód istnieje; mierzymy, gdzie nie istnieje; odmawiamy, gdzie ani jedno, ani
drugie."** Demo DP = system pokazowy zbudowany na **zmierzonych** (bramki 3b/3c/G2) i **dowiedzionych**
(certyfikaty osłony/geofence/autoryzacji) klockach. Ekran ma **dwie kolumny prawdy**: **PROVED**
(certyfikaty solverów z hashem) i **MEASURED** (bramki z raportów). Sieci płynne występują jako
**zmierzony wątek** (eksponat v1.0 + komórka 3d na mapie granicy + kandydat P3-liquid), **nie jako
obietnica** — werdykt 3d (Δ=−5,8, NEGATYWNY) jest na planszy jako uczciwy wynik, nie ukrywany.

---

## §2 Akty [PROPOZYCJA — lista ZAMKNIĘTA, nic ponad]

Osłona w trybie **APPLIED** wszędzie, gdzie panel osłony jest na ekranie (konstrukcyjne rozwiązanie
problemu shadow z v1, RECON §D). Panel osłony widoczny od **A1**. Wszystkie epizody z prowieniencją.

- **A1 „Komenda"** — konsola NL: `fly to the {color} {shape}` → parser → admisja (rekord podpisany
  HMAC) → lot nad terenem do celu. Epizod: eval **46513**, clean, SUKCES (noga A). Osłona APPLIED,
  transparentna (clean 67→63 zmierzone; ewentualny późny HOLD-sufit benign). Baner: **67% / 10%**
  (próg 85/8 frozen, niespełniony).
- **A2 „Łącze"** — ten sam profil lotu pod **burst L5**; mostkowanie ZOH. Epizod: **46507**, maska
  L5 (`45105`), SUKCES (G2). Baner G2: **L5 −4 pp vs p0.5 −36 pp** („continuity is what matters").
- **A3 „Twarde reguły"** — (i) łącze martwe za długo: **46503**, Bernoulli p0.5 (`45102`) →
  HOLD → **REFUSE(STALE_AT_DWELL)** zamiast ślepego finiszu; baner noga B **16/28 porażek →
  abstynencja, SUKCES 15/22**. (ii) komenda na cel poza geofencem: **47425** → **odmowa admisji z
  certyfikatem P2 na ekranie**; baner **25/25**.
- **A4 „Korekta"** — komenda z nieznanym słowem (np. „crimson") → parser poza gramatyką →
  **REFUSE(NO_MATCH)** → człowiek mapuje alias (`crimson→red`) → **podpisany rekord do pamięci** →
  ta sama komenda → **ALLOW** → lot. Zero zmian wag/progów.
- **A5 „Plansza"** — kolumny **PROVED** (P1–P5 z hashami) / **MEASURED** (67/10, G2, noga B,
  25/25, 6/25) ze źródłami; **mapa granicy** z komórką 3d (inwersja); **eksponat v1.0** (CfC-32,
  τ≈35 ms, klif 102→779 ms; AutoNCP-20 317 z wynikiem P3 **jeśli domknięty**); **roadmapa:** tracker
  anti-UAV (CT vs Kalman/GRU/Mamba na publicznym wideo).

---

## §3 Warstwa dowodowa — własności [PROPOZYCJA brzmień; zamrażane w PRE]

- **P1 (indukcja/BMC po automacie osłony; solver z3 [F-D3])** — w żadnym osiągalnym stanie:
  (a) brak dostarczenia przy age > sufit bez przejścia do HOLD/REFUSE; (b) naruszenie geofence ⇒
  decyzja ∈ {HOLD, REFUSE} **w tym samym ticku**; (c) każde REFUSE niesie **niepusty** powód;
  (d) HOLD rozstrzyga się w **≤ T_hold** (bounded model checking, T_hold=3.0 s z kodu). Obiekt =
  automat z RECON §A (przestrzeń skończona → domykalne).
- **P2 (indukcja po dynamice; interwały + z3 [F-D3])** — stałe w modelu Z3 **wyłącznie jako dokładne
  ułamki wymierne** (zero floatów w certyfikatach): `Δt = 1/12`, `margines = 1/5`, `VEL_LIM = 1`.
  Naddatek `δ = VEL_LIM·Δt + VEL_LIM²/(2·A_min) = 1/12 + 1/(2·A_min)`; warunek `δ < margines` daje
  **próg dokładny** `A_min = 0,5/(1/5 − 1/12) = (1/2)/(7/60) = 30/7 m/s² (≈ 4,286)`. Przy
  `decel ≥ 30/7` dron respektujący osłonę **nigdy nie opuszcza ogrodzenia 2,0 m**. **Założenia jawne
  (F-D4):** (i) |prędkość| ≤ VEL_LIM=1, (ii) decel ≥ A_min=30/7, (iii) osłona APPLIED, (iv) projekcja
  pozioma. Twierdzenie **o modelu dynamiki**, nie o pełnym PyBullet; certyfikat niesie ułamki, nie
  dziesiętne.
- **P3 (weryfikacja sieci; IBP numpy [F-D3])** — ograniczenia wyjścia pilota dla kostki wejść.
  **[PROPOZYCJA — minimum ratyfikowalne: JEDNA sieć = AutoNCP-20 (317 param)]**, sound output-range
  jednego kroku (interval bound propagation, czysto-numpy); gc5 (28,8k, GRU) jako rozszerzenie jeśli
  budżet pozwoli. Wynik = **twierdzenie o zakresie akcji**, nie o poprawności zadaniowej. **Uwaga
  F-D2:** AutoNCP-20 to sieć **budowana w DP** pod P3 (param-count = fakt strukturalny; bound =
  wynik solvera) — nie liczba-banner z raportu.
- **P4 (autoryzacja; HMAC stdlib)** — żadna misja bez sparsowania do spec i admisji; **spec wykonany
  ≡ spec admitowany**; poza gramatyką ⇒ REFUSE(NO_MATCH); każdy rekord decyzji **podpisany HMAC**,
  odtwarzalny łańcuch per lot.
- **P5 (konformancja model↔kod; property-based)** — testy wiążące `shield.py` z modelem z P1: pełne
  pokrycie przejść automatu, **równość decyzji kod ≡ model** na generowanych trajektoriach. Baner:
  „proved on model + conformance-tested implementation". **Warunek zaliczenia P1/P2** (ryzyko 1).

**GRANICA DOWODU (obowiązkowa, na ekranie).** Dowód **NIE obejmuje**: (1) **percepcji** — tożsamość
locka nie jest dowodzona; **limit 6/25** (obiekt nieobecny → halucynacja groundera) pozostaje limitem,
cytowany w kolumnie MEASURED; (2) **sukcesu misji** — sukces jest w MEASURED (67/10), nie PROVED.
Dowodzimy własności **osłony i geometrii**, nie poprawności zadaniowej percepcji.

---

## §4 Warstwa języka [PROPOZYCJA]

Gramatyka **zamknięta, deterministyczna** (zero LLM w torze autoryzacji):
`fly to the {color} {shape}` | `hold` | `resume` | `return home` | `abort` (+ pułapka: cel poza
ogrodzeniem). `{color} ∈ {red, green, blue}`, `{shape} ∈ {box, sphere, cylinder}` (paleta D4).
Parser → spec `{action, color?, shape?}`; atrybuty budują frazę groundera **dokładnie**
`"{color} {shape}"` (kontrakt F-D5: `grounder_server` robi `set_classes([phrase])`). Komendy spoza
gramatyki (nieznane słowo/atrybut) → **REFUSE(NO_MATCH)** (materiał A4). Cel poza areną → odmowa
admisji (P2/geofence).

---

## §5 Pamięć korekt [PROPOZYCJA zakresu MVP]

Korekta człowieka = **mapowanie aliasu na klasę znaną gramatyce** (np. `crimson → red`), zapisywane
jako **podpisany rekord** (HMAC) i aktywne **od następnej komendy**. **Zero zmian wag, zero zmian
progów osłony, zero LLM.** Alias rozwijany PRZED budową frazy groundera (F-D5). Wariant rozszerzony
(egzemplarz-embedding do weryfikacji locka) — **przyszły mandat, poza DP**.

---

## §6 Teren

Warstwa **wyłącznie prezentacyjna** playera (heightmapa/tekstury/skybox w widoku 3D third-person).
**Wejście sieci 64² BEZ ZMIAN** — sieć widzi to samo co w pomiarach. Zdanie jawne na planszy i w PRE:
**„teren jest wizualizacją trzecioosobową; sieć widzi to samo co w pomiarach".** Zakaz sugerowania
wpływu terenu na wynik. Env/kanał/percepcja nietknięte — teren żyje tylko w playerze.

---

## §7 Prowieniencja

**Tabela banerów** (baner → liczba → raport → plik JSON → sha256) — kanoniczna, powtórzona w playerze
i README. Liczby wyłącznie z RECON §C. **Manifest epizodów** jak v1 + **licznik prób re-record**
(≤3/scenę) + tryb osłony (APPLIED). **Certyfikaty** (własność → model → wynik solvera → hash →
skrypt `python -m proofs.verify`): każda własność P* ma wpis odtwarzalny od zera; niezgodność
hash = STOP.

| baner (EN) | liczba | źródło | plik |
|---|---|---|---|
| designation envelope | 67% / 10% (gate 85/8) | RAPORT_3B / RAPORT_3C_MVP §2 | (do wpisania w B) |
| broken link | L5 −4 vs p0.5 −36 pp | RAPORT_S3B4 | ” |
| shield accounting | 16/28 → abstention; 15/22 | RAPORT_3C_MVP §5 | ” |
| geofence | 25/25 | RAPORT_3C_MVP §6 | ” |
| absent-object limit | 6/25 (honest) | RAPORT_3C_MVP §6 | ” |
| 3d inversion | Δ=−5,8 NEGATIVE | RAPORT_3D §2 | verdict_3d.json |
| v1.0 exhibit | 102→779 ms; τ≈35 ms | paper/NUMBERS.md, liquidflight `RD`/`C01` | ” |

---

## §8 Plan budowy i kryteria ukończenia [PROPOZYCJA]

Kolejność modułów: (1) **formalizacja osłony + P1** → (2) **P5 konformancja** → (3) **P2 geofence**
→ (4) **P4 gramatyka + admisja + rekordy HMAC** → (5) **A4 pamięć korekt** → (6) **P3 weryfikacja
sieci** (AutoNCP-20) → (7) **teren/player** → (8) **nagrania aktów** (APPLIED, bounded ≤3/scenę) →
(9) **montaż + plansza**. Moduł **ukończony ⇔** testy zielone **∧** certyfikat/artefakt w repo z
hashem **∧** wpis w tabeli prowieniencji. **Budżet: 7–9 sesji**; przekroczenie = STOP i raport stanu.

---

## §9 Ryzyka nazwane

1. **model ≠ kod** → **P5 jako warunek zaliczenia P1/P2** (konformancja przed uznaniem dowodu).
2. **ProofGate nieosiągalny (F-D3)** → z3 instalowalny (P1/P2/P5); P3 przez numpy-IBP; **lokalny
   minimalny PCDL** (rekord + HMAC, `proofs/`) z **długiem integracyjnym** nazwanym (integracja z
   ProofGate = przyszły mandat).
3. **UNPROVEN** dla którejś własności → **raportowane jawnie** (RAPORT_DP), brzmienie NIE osłabiane;
   **plansza pokazuje tylko domknięte** (UNPROVEN nie trafia do kolumny PROVED).
4. **re-record w APPLIED niestabilny (F-D1)** → limit **≤3 próby/scenę**; po limicie scena **wypada**
   z aktu (nie zmiękczamy reguł, żeby „weszła"). Dotyczy zwłaszcza A2 (burst pod sufitem 6 s).
5. **scope creep** → lista aktów §2 **zamknięta**; własności §3 zamknięte.

---

## §10 Artefakty

`demo_proof/` (recorder APPLIED, parser/konsola, player HTML single-file EN, README), `proofs/`
(modele P1–P5, certyfikaty z hashem, `verify.py`), `RECON_DP.md`, `PRE_DP0.md`, `RAPORT_DP.md`
(co dowiedzione / zmierzone / UNPROVEN — każda pozycja z hashem). Zamrożone (gc5, osłona, kanał, env,
grounder, sweep 46600–46649, raporty, DEMO.md, paper/) — wyłącznie odczyt.

---

## Decyzje do ratyfikacji (z RECON §F + solvery §E)

| # | decyzja | rozstrzygnięcie ratyfikacyjne (2026-08-03) |
|---|---|---|
| **F-D1** | tryb osłony nagrań | **RATYFIKOWANE:** APPLIED wszędzie, panel od A1, bounded ≤3 re-record, scena flipująca **wypada** z aktu |
| **F-D2** | AutoNCP-20 / P3 | **RATYFIKOWANE:** artefakt P3 budowany w DP; **param-count = fakt strukturalny z checkpointu**, bound **wyłącznie z solvera** |
| **F-D3** | solver stack | **RATYFIKOWANE:** z3-solver z pip **PRZYPIĘTY w `requirements-proofs.txt`, wersja w każdym certyfikacie**; numpy-IBP dla P3; **auto_LiRPA NIE bez osobnej zgody**; lokalny PCDL+HMAC, dług integracyjny nazwany |
| **F-D4** | brzmienie P2 | **RATYFIKOWANE:** ułamki wymierne (Δt=1/12, margines=1/5, VEL_LIM=1), **A_min=30/7 (dokładnie)**; zero floatów w certyfikatach |
| **F-D5** | gramatyka↔grounder | **RATYFIKOWANE:** parser produkuje `"{color} {shape}"`; **alias rozwiązywany PRZED frazą — autoryzacja widzi kanoniczny spec** |
| **P3 zakres** | ile sieci | **RATYFIKOWANE:** minimum AutoNCP-20; **gc5 warunkowo** — jeśli goły IBP nieinformatywny → **UNPROVEN-tą-metodą**, nic nie doinstalowujemy |
| **§2 akty** | lista zamknięta A1–A5 | **RATYFIKOWANE** (zamknięta) |
| **§8 budżet** | 7–9 sesji | **RATYFIKOWANE** |
| **formalizacja P1** | predykaty modelu | **ODRĘBNA ratyfikacja** przed pierwszym odpaleniem solvera (moduł 1) |

---

*PRE_DP0 zamknięty. **STOP na ratyfikację człowieka.** Bez adnotacji „RATYFIKOWANE" etap B nie
startuje. Do czasu ratyfikacji — zero kodu produkcyjnego i zero nagrań (rekonesans i PRE nie tworzą
artefaktów wykonawczych).*
