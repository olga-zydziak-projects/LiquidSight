# RAPORT_DP — demo-proof: co dowiedzione, co zmierzone, co UNPROVEN

**Data:** 2026-08-03. **Faza:** DP (demo-proof), sesja finalna (moduły 1–9). **Charakter:** BUDOWA
pokazowa, **nie pomiar** — zero nowych liczb; każda liczba na ekranie pochodzi z zamrożonego raportu
(RECON_DP §C) albo z certyfikatu solvera. **Podstawa:** `PRE_DP0.md` (RATYFIKOWANE), `RECON_DP.md`,
`ANEKS_DP1_A2.md`. Zasada nadrzędna: **certyfikaty dowodowe to jedyna nowa kategoria artefaktów DP;
trafiają wyłącznie do kolumny PROVED, nigdy MEASURED.** Sweep 46600–46649 nietknięty.

Tożsamość: **dowodzimy, gdzie dowód istnieje; mierzymy, gdzie nie istnieje; odmawiamy, gdzie ani
jedno, ani drugie.** Player: `demo_proof/liquidsight_proof.html` (self-contained EN).

---

## 1. PROVED — certyfikaty (odtwarzalne od zera)

Każdy certyfikat: `proofs/certs/<P>.json`, verdykt + metoda + wersja solvera + `sha256`. Weryfikacja:
`python -m proofs.{verify,geofence,conformance,p4_verify,a4_verify,net_ibp}` — buduje model od zera,
porównuje z hashem.

| własność | verdykt | metoda / solver | model_sha256 |
|---|---|---|---|
| **P1** własności osłony | **PROVED** | 1-indukcja z3 5.0.0 (6 zobowiązań UNSAT) | `7676fc05190b770b` |
| **P2** geofence | **PROVED** | bariera + próg, z3 5.0.0 NRA | `2cef2f314da4cea4` |
| **P5** konformancja kod↔model | **PASS** | per-tik tau≡shield, 15/15 przejść, A-lock testowany | `74bfbadab102adea` |
| **P4** autoryzacja | **PASS** | gramatyka+admisja+HMAC, 2000 property | `a83239fbe8eda57e` |
| **A4** pamięć korekt | **PASS** | alias→klasa, podpisany, niezmienniki | `db2480a21dcaaa06` |
| **P3** zakres akcji sieci | **PROVED\*** | sound numpy-IBP na A_CFC (I3b) | `b9f522eaba79fd76` |

**Treść (skrót):**
- **P1(a)** sufit nieprzekraczalny po admisji (bezwarunkowe via I8 „dostarczenie⇒admisja");
  **P1(b)** geofence⇒REFUSE (wzmocnione); **P1(c)** REFUSE zawsze z powodem; **P1(d)** HOLD<36 tików
  (=T_hold, `shield.py:30/112/131`). Solver złapał realny błąd niezmiennika (off-by-one na progu) —
  **wzmocniono niezmiennik, nie zmiękczono własność**.
- **P2:** przy `VEL_LIM=1`, `Δt=1/12`, margines `1/5`, decel `≥ A_min=30/7` (dokładnie, ułamki
  wymierne) dron respektujący osłonę **nigdy nie opuszcza 2.0 m**; ostrość progu 30/7 dowiedziona
  w obie strony.
- **P5:** 0 rozbieżności tau≡shield (300+13 epizodów); **A-lock zweryfikowany na realnym `Tracker5`**
  (monotoniczny, 6000 tików) + 3 ścieżki łamiące A-lock; kontrprzykłady off-by-one jako wektory.
- **P4/A4:** parser deterministyczny (zero LLM w torze autoryzacji); admisja z rekordami HMAC
  (łańcuch per lot, odtwarzalny, sabotaż wykryty); alias→klasa rozwiązywany PRZED frazą.
- **P3:** obiekt = **istniejący checkpoint A_CFC z I3b** (złota recepta CfCCell, rdzeń 27787 param,
  `results/i3b/ckpt/A_CFC|0.001|45011.pt`). **PROVED bezwarunkowo:** stan liquid `h'∈[−1,1]^64` dla
  DOWOLNEGO wejścia (`max|h'|=1.000000`, dowód strukturalny) + koperta akcji.

---

## 2. MEASURED — liczby z raportów (RECON_DP §C)

Wyłącznie te; każda z prowieniencją. **Nagranie ≠ pomiar.**

| twierdzenie | liczba | źródło |
|---|---|---|
| desygnacja / wrong-lock | **67% / 10%** (próg 85/8 frozen, niespełniony) | RAPORT_3B · RAPORT_3C_MVP §2 · G1_GATE |
| sufit wykonalności | GT-fed **100%** | RAPORT_3B §9 |
| krzywa G2 (bez osłony, populacja 46500–46549) | **80/66/44/30**; L5 **−4** vs p0.5 **−36 pp** | RAPORT_S3B4 |
| księgowość osłony (dropout) | **16/28** porażek→abstynencja; sukces **15/22** | RAPORT_3C_MVP §5 |
| geofence pułapki | **25/25** | RAPORT_3C_MVP §6 |
| limit obiekt-nieobecny (uczciwie) | **6/25** (halucynacja groundera) | RAPORT_3C_MVP §6 |
| komórka 3d (inwersja) | Δ = **−5.8**, NEGATYWNY | RAPORT_3D §2 |
| eksponat v1.0 (state-loop) | klif **~102→779 ms**, CfC-32 500–1300 ms, τ≈35 ms, **„317"** (AutoNCP-20) | paper/NUMBERS.md · LiquidFlight RD/C01 |

**„317" wyłącznie przy eksponacie v1.0** z jawną konfiguracją state-loop (setpoint→DSL-PID 48 Hz,
oś obs-dropout OOD); plansza **nie łączy** „317" z certyfikatem P3 w jednym podpisie (P3 podpisany
realnym param-countem **27787**).

---

## 3. UNPROVEN / GRANICA DOWODU (jawnie, niezmiękczone)

- **P3 robustność lokalna: UNPROVEN-tą-metodą.** Goły sound numpy-IBP na kostce ±ε daje przedziały
  ≈ pełna skala setpointu nawet przy ε=0.01 (znany limit metody na szerokim rdzeniu). Zgodnie z
  ratyfikacją: **auto_LiRPA nieautoryzowany, brak demonstratora units=20** — status UNPROVEN-tą-metodą
  utrzymany. **Puenta na planszy (zamierzona, nie przypis):** „local robustness of the network is not
  provable by sound IBP at this width — that is why a proved automaton (P1, P2, P5) stands between the
  network and actuation."
- **Percepcja NIE jest dowodzona.** Tożsamość locka poza dowodem; **limit 6/25** (open-vocab grounder
  halucynuje box) pozostaje limitem, cytowany w MEASURED. Dowodzimy własności **osłony i geometrii**,
  nie poprawności zadaniowej percepcji.
- **Sukces misji ∈ MEASURED**, nie PROVED (67/10 to koperta, nie twierdzenie).

---

## 4. Akty (5) — nagrania APPLIED z prowieniencją

Osłona **APPLIED** we wszystkich aktach (rozwiązanie problemu shadow z v1). Każdy akt: podpisany
łańcuch admisji (P4). Manifest: `results/demo_proof/manifest.json`.

| akt | seed | maska | wynik | admisja | próby | prowieniencja |
|---|---|---|---|---|---|---|
| **A1** Command | 46513 | clean | **SUKCES** | ALLOW | 2 | eval 46500–46599 |
| **A2** The link | **46502** | burst L5 (45105) | **SUKCES** | ALLOW | 1 | 46500–46549 (ANEKS_DP1) |
| **A3a** Hard rules (geofence) | 47425 | geofence | **REFUSE(GEOFENCE)** | REFUSE na admisji | 1 | pułapki 47400–47449 |
| **A3b** Hard rules (stale) | 46503 | Bernoulli p0.5 (45102) | **REFUSE(STALE_AT_DWELL)** | ALLOW→runtime REFUSE | 1 | 46500–46549 |
| **A4** Correction | 46505 | clean | **SUKCES** | NO_MATCH→korekta→ALLOW | 1 | eval 46500–46599 |

Wszystkie **match z oczekiwaniem prowieniencji**; łańcuchy authz zweryfikowane. A4: alias
(np. crimson→red) rozwiązany PRZED frazą — autoryzacja widzi kanoniczny spec, grounder frazę „red …".

---

## 5. A2 — protokół antyselekcyjny (ANEKS_DP1)

Seed **46507** przypięty w PRE_DP0 §2 **flipnął pod APPLIED**: 3/3 próby PORAZKA(dwell) — burst pokrył
wejście w dwell, osłona (R-B) zatrzymała ślepy finisz. Per F-D1 scena wypadła; **reguł nie
zmiękczono**. Podmiana wg reguły **zamrożonej PRZED przeszukaniem** (`ANEKS_DP1_A2.md`, commit
`26b66a0`, poprzedza bieg): kandydaci burst-L5 z 46500–46549 w **porządku rosnącym**, pierwszy SUKCES
pod APPLIED wygrywa. Wynik biegu:

| kandydat | wynik pod APPLIED |
|---|---|
| 46500 | REFUSE(STALE_AT_DWELL) — odrzucony |
| 46501 | REFUSE(STALE_AT_DWELL) — odrzucony |
| **46502** | **SUKCES — seed A2** |

Zero wyboru estetycznego. Flip 46507 + odrzuceni w manifeście A2; na planszy przy banerze G2:
„seed pinned in PRE failed under the shield … the same conservatism that converts 16/28 failures into
abstention". Baner G2 z podpisem warunków (populacja 46500–46549, **bez osłony**).

---

## 6. Dług integracyjny (nazwany, przyszłe opcje)

- **ProofGate / PCDL:** brak kernela w repo → **lokalny PCDL** (rekord decyzji + HMAC-SHA256,
  `demo_proof/authz.py`). Integracja z ProofGate = przyszły mandat.
- **auto_LiRPA (CROWN):** nieautoryzowany — tight P3 robustność lokalna czeka na osobną zgodę.
- **AutoNCP-sparse-wiring IBP:** dług (numpy-IBP przez ncps WiredCfCCell = ryzyko niepoprawności;
  wybrano frozen CfCCell dla soundness).
- **Demonstrator units=20:** nie zbudowany (trening = nowa aktywność wymagająca zgody).

---

## 7. Higiena i odtwarzalność

- **Zamrożone nietknięte:** polityka gc5, osłona v2, kanał, env, grounder, sweep 46600–46649,
  raporty, DEMO.md, paper/ — wyłącznie odczyt. Kanał bez filtra (werdykt 3d NEGATYWNY).
- **Dowody odtwarzalne** (zasada 3): `python -m proofs.*` od zera, porównanie z hashem; z3
  przypięty `z3-solver==5.0.0.0` (`requirements-proofs.txt`), lib 5.0.0 w każdym certyfikacie;
  P3 = numpy sound-IBP.
- **Nagranie ≠ pomiar:** bounded ≤3 próby/scenę, licznik w manifeście, retry po padzie WSL z
  weryfikacją artefaktów; scena flipująca **wypada** (A2/46507), reguł nie zmiękczano.
- **Teren:** warstwa **wyłącznie prezentacyjna** playera; na ekranie jawne „terrain is third-person
  visualization; the network sees the 64² camera". Wejście sieci 64² bez zmian.
- **UNPROVEN jawne**, brzmienie własności nieosłabiane (zasada 6); plansza w PROVED tylko domknięte.

---

## 8. Artefakty

`RECON_DP.md`, `PRE_DP0.md`, `ANEKS_DP1_A2.md`, `RAPORT_DP.md`; kod `demo_proof/` (record, player,
language, authz, memory) + `proofs/` (verify, geofence, conformance, p4_verify, a4_verify, net_ibp,
P1_FORMALIZATION); certyfikaty `proofs/certs/{P1,P2,P3,P4,P5,A4}.json`; player
`demo_proof/liquidsight_proof.html` (11.2 MB, 5 aktów, sha w commicie).

---

*Faza DP domknięta na etapie montażu: 5 aktów w APPLIED, 6 certyfikatów (P1/P2 PROVED z3, P5/P4/A4
PASS, P3 zakres-akcji PROVED + robustność lokalna UNPROVEN-tą-metodą), dwie kolumny prawdy
PROVED/MEASURED, protokół antyselekcyjny A2. **STOP przed bramką wzrokową — decyzję o akceptacji
wizualnej dema podejmuje człowiek.***
