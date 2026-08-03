# RAPORT_MC — mission cut: co nagrano, próby, odstępstwa

**Data:** 2026-08-03. **Faza:** MC (mission cut), B2. **Charakter:** BUDOWA, **nie pomiar** — zero
nowych liczb pomiarowych; min-dist per noga to feasibility (poza pulami), nie baner. **Podstawa:**
`PRE_MC0.md` (RATYFIKOWANE, wariant A), `RECON_MC.md`, `ANEKS_MC1_MISSION.md`. Zamrożone nietknięte;
sweep 46600–46649 nietknięty.

## Co nagrano
**Jedna ciągła rejestracja** na scenie **49508** (K8/A0, `scene_sha256 2fc0d5cbcef7`), **517 tików
(~43 s)**, **259 klatek** (panele co 2 tik, rider 4), **33 zdarzenia**, **łańcuch admisji zweryfikowany**
(`authz_ok=True`). Sim **ciągły, bez teleportu** (soft re-arm liczników; `self.env`/dron nietknięte).

| noga | segment | wynik | min-dist |
|---|---|---|---|
| **L1** `fly to the red box` | LEARNED-LEG (gc5, APPLIED) | **dwell** | 0.158 m |
| — reposition to launch | SCRIPTED-TRANSIT (executor) | — | — |
| **L2** `fly to the blue sphere` + burst L5 | LEARNED-LEG | **burst bridged** (dwell) | 0.087 m |
| **L3** `fly to the red sphere` (relokowany poza geofence) | ADMISSION-REFUSE | **REFUSE(GEOFENCE)** (cert P2) | — |
| **L4** `fly to the crimson box`→korekta→`red box` | authz+memory + LEARNED-LEG | **korekta OK; dolot NEAR** | 0.42 m |
| **L5** `return home` → land | SCRIPTED-TRANSIT + LANDING | landed | — |

Napisy: **`subtitles.vtt` GENEROWANY z logu zdarzeń** (33/33 napisów ze zdarzeń; assert „zero
odręcznych"). Player: `demo_proof/liquidsight_mission.html` (tryb mission; link do aktów DP —
nietknięte). Instrumenty W2. Etykiety segmentów LEARNED-LEG / SCRIPTED-TRANSIT.

## Próby (bounded ≤3/nogę, PRE §4)
3 pełne rejestracje. L1/L2/L3/L5 czyste we wszystkich. **L4 dolot terminalny deterministycznie NEAR**
(0.377 / 0.42 / 0.42) — bounded ≤3 wyczerpany; **raportowane jako near, nie zmiękczone** (subtitle
„L4 approach to (near) red box").

## Odstępstwa (jawne)
1. **Obwiednia polityki** (jedno zdanie, znane ustalenie 3b, bez nowej liczby): `gc5` dolatuje tylko
   do celów w **stożku czołowym +x (±25°, 1–2 m)** (`config/env_f3.json:15-16`, `ANEKS_1:11`,
   `DECYZJE_3B D4`). Mitygacja: **per-leg launch** (ANEKS_MC1 §B) — każda noga lotu startuje z launch
   ustawionego tak, by cel był +x-przed.
2. **Burst L2 w terminalnym dwellu** (seed 45105, **offset=4**), nie przed dotarciem — bo dolot w
   obwiedni (~2 s) jest za krótki na burst 5 s przed dotarciem; bridging w dwellu (link FROZEN, dron
   trzyma z pamięci, dwell domyka) to wykonalny klean demo (dynamika DP A2). Nazwane (ANEKS_MC1 §E).
3. **L4 dolot NEAR (0.42):** **korekta się udała** (crimson → NO_MATCH → alias podpisany → ALLOW);
   terminalny lot do red box nie domyka dwellu — prawdopodobnie akumulacja stanu/yaw w długiej
   ciągłej misji. Bounded ≤3 wyczerpany → **STOP/eskalacja** (poniżej).
4. **Recon smoke carry-over:** nogi startujące z pozycji poprzedniego celu degradują (LEG spawn
   ARRIVED / carry-over NEAR-MISS) — stąd per-leg launch (RECON_MC §b). Jedno zdanie, bez liczby na
   planszę.
5. **„Sim nieprzerwany":** literalnie osiągnięty (jeden sim, soft re-arm) — poprawka względem
   wstępnej wyceny RECON §d-1 (tam: konkatenacja z teleportem; runner uniknął teleportu przez
   ctick-reset).

## Eskalacja (L4 — decyzja człowieka)
L4 dolot terminalny nie domyka się w bounded ≤3 (deterministyczny NEAR). Opcje: (a) **akceptacja**
z uczciwym labelem „approach (near)" — korekta (sens L4) jest domknięta [rekomendacja]; (b) re-order
nóg (korekta wcześniej, mniej akumulacji); (c) skrócenie misji (bez L4-lotu, korekta jako refuse→admit
bez dolotu). **Rekomendacja (a).** To pozycja do **bramki wizualnej misji** (człowiek).

## Prowieniencja / higiena
Scena 49508 (`scene_sha256`), maska 45105 offset 4, obwiednia z cytatami frozen, subtitles z trace
(odtwarzalne), manifest misji (`mission.json`: trace/events/frame_at/admissions/results). Zero nowych
liczb pomiarowych. **STOP przed bramką wizualną — akceptację wizualną misji podejmuje człowiek.**
