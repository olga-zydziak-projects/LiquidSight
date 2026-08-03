# RECON_MC — rekonesans wykonalności misji ciągłej (faza MC, B0)

**Data:** 2026-08-03. **Etap:** B0 (read-only + smoke poza pulami). **Charakter:** BUDOWA, nie pomiar —
żadna liczba pomiarowa nie powstaje; liczby ze smoke'a to **dowody wykonalności** (seed 49502 poza
wszystkimi pulami), nie banery ani twierdzenia. Zasady DP bez zmian. Wynik zasila `PRE_MC0.md`.

## (a) Ciągła sesja wielokomendowa — wymaga MISSION-RUNNERA

**Stan env:** `env.reset` (`env/liquidsight_env.py:89-120`) **niszczy i odtwarza sim** (`self.close()`
→ nowy `CtrlAviary`, spawn drona z regionu treningowego `p0`), epizod capuje na **480 tików kontroli
= 10 s** (`CONTROL_STEPS`, `env.step` ustawia `done` przy `ctick>=480` i short-circuituje po `done`).
Misja **90–180 s = 1080–2160 tików polityki** → **nie zmieści się w jednym epizodzie** i nie da się
przedłużyć bez dotykania frozen (config/env).

**Runner (wyceniony, potrzebny):** `demo_proof/mission_runner.py` — jedna scena K8; per noga:
`env.reset(ten sam seed)` [scena deterministycznie identyczna] + **teleport drona do pozycji końcowej
poprzedniej nogi** (`resetBasePositionAndOrientation` + zerowanie prędkości) → **carry-over**; nadpisanie
`env.hover` = cel nogi; re-arm `Tracker5`+`Shield`+komenda; run polityki APPLIED; **trace konkatenowany**
(globalny licznik tików). **Uczciwie:** to **konkatenacja segmentów** (nowy klient sim per noga), nie
jeden literalny nieprzerwany sim — trace i obraz ciągłe (dron kontynuuje z carry-over), ale „sim
nieprzerwany" w sensie jednego klienta **nieosiągalny bez dotykania frozen** (§d-1).

## (b) Noga z pozycji poprzedniego celu = LOT DEMONSTRACYJNY POZA ROZKŁADEM SPAWNU — DEGRADUJE

Polityka `gc5` trenowana: spawn w połowie **−x**, cele w stożku **+x** (`config/env_f3.json aneks_1`).
Noga startująca z **poprzedniego celu** (dowolna pozycja, cel może być z boku/za dronem) jest **poza
rozkładem**. **Smoke (seed 49502, K8/A0, 3 nogi, poza pulami) — zmierzone:**

| noga | start | komenda | min-dist | wynik |
|---|---|---|---|---|
| LEG1 | SPAWN (w rozkładzie) | fly to the red sphere | **0.032 m** | **ARRIVED** |
| LEG2 | carry-over (poza spawnem) | fly to the green box | 0.494 m | NEAR |
| LEG3 | carry-over (poza spawnem) | fly to the green cylinder | 0.610 m | MISS |

**Wniosek (kluczowy dla §2 PRE):** nogi in-distribution (ze spawnu) dolatują czysto; nogi z carry-over
**degradują do NEAR/MISS**. To realizacja nazwanego ryzyka (b). **Bez mitygacji misja nie domyka nóg.**

**Mitygacja rekomendowana — transit „return home" między nogami lotu:** każda noga LOTU (policy) startuje
**z home ≈ regionu spawnu** (in-distribution → czysty lot); przejście do home realizuje **skryptowany
transit egzekutorem** (`env.step` z setpointem `[home_xy, z_hover, 0]`), **BEZ polityki** (return-home nie
jest zadaniem grounderowym „fly to {color}{shape}", tylko stałą pozycją). Egzekutor (setpoint→DSL-PID)
jest tym samym mechanizmem co position-hold osłony — **nie dotyka frozen**. Gramatyka ma `return home`,
więc transit jest naturalną częścią narracji. Wariant alternatywny (bez transitu): akceptacja NEAR/MISS
na nogach demo z jawnym labelem — słabszy pokaz. **Rekomendacja: transit home przed każdą nogą lotu.**

## (c) Sterowalność burstu — TAK, W pełni

Maska burst (`train/s3b4.py:110-114` `burst_window`): `window=[start, start+Lt)`, `start = earliest +
u·(latest−earliest)`, `earliest=first_lock+1`, `Lt=round(L/tick)`. `u` pochodzi z seedu maski — ale
**runner może ustawić `start` JAWNIE** (stały offset względem wejścia nogi), tak by okno przerwy wypadło
**W TRAKCIE dolotu**, a NIE na wejściu w dwell (lekcja 46507: burst pokrywający dwell-entry → HOLD →
porażka). Kontrolowalne per noga: burst w środku dolotu L2, offset przypięty w PRE. **Feasible.**

## (d) Rozbieżności prompt ↔ repo / stan (do PRE, nie decyzja własna)

- **§d-1 „sim nieprzerwany":** nieosiągalny literalnie (cap 480/10 s + reset odtwarza sim). Runner
  konkatenuje segmenty (reset-per-leg + teleport carry-over) → trace/obraz ciągłe, ale to segmenty,
  nie jeden klient sim. Nazwać w PRE §1/§5 jako **misja = konkatenacja demo-legów**.
- **§d-2 nogi carry-over degradują** (smoke b). Scenariusz §2 z nogami startującymi „z pozycji
  poprzedniego celu" da NEAR/MISS bez mitygacji → **PRE §2 powinno wpiąć transit home przed nogami
  lotu** (mitygacja z promptu b). To lekko rozszerza §2 (dodaje segmenty transit) — decyzja do
  ratyfikacji. Bez transitu: akceptacja NEAR/MISS (labelowana).
- **§d-3** return-home realizowany **skryptowym transitem egzekutora** (nie polityką) — czysty,
  deterministyczny, bez frozen; do zapisania w PRE §2/§3 jako typ segmentu.
- **§d-4** długość trace ~1080–2160 tików × (256²+64² base64) → **budżet MB playera** rośnie; mitygacja:
  klatki panelowe na niższym fps (np. co 2–3 tik) przy zachowaniu WSZYSTKICH zdarzeń w logu napisów.
  Do wyceny w PRE §6.
- **§d-5** brak nowej liczby pomiarowej: min-dist ze smoke to feasibility (poza pulami), nie baner;
  na ekranie misji tylko inwentarz DP + zdarzenia trace.

## Higiena
Smoke `demo_proof/mc_smoke.py` (seed 49502, poza pulami, zero zapisu klatek/pomiaru). Zamrożone
nietknięte. Sweep 46600–46649 nietknięty. Następny krok: `PRE_MC0.md` (STOP na ratyfikację scenariusza).
