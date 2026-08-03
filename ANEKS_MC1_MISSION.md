# ANEKS_MC1 do PRE_MC0 — mechanika opcji 1 (per-leg launch + scena w obwiedni)

**Data:** 2026-08-03. **Charakter:** aneks mechaniki do `PRE_MC0.md §2` (ratyfikacja opcji 1).
**Reguły ZAPISANE PRZED przeszukaniem sceny** (anti-selection; ten commit poprzedza scene-search).
Wszystkie stałe z zamrożonych dokumentów; **zakaz rozszerzania obwiedni „na oko"**. MIERZĘ = RAPORTUJE.

## §A Obwiednia polityki (PRZYPIĘTA ze stałych zamrożonych, rider 1)
Stożek czołowy +x, w którym `gc5` dolatuje (poza nim — miss, ustalenie 3b):
- **azymut względem +x: ±25°** — `config/env_f3.json:15` (`spawn_azymut_deg: 25.0`),
  `ANEKS_1_OBSERWOWALNOSC.md:11` (Z2: „azymut względem +x w [−25°, +25°]"), `DECYZJE_3B D4`.
- **dystans poziomy: [1.0, 2.0] m** — `config/env_f3.json:16` (`spawn_dystans_m: [1.0, 2.0]`),
  `ANEKS_1:11`. **yaw = 0** (`config/env_f3.json:17`).
**Zakaz rozszerzania** tych wartości pod scenariusz.

## §B Reguła launch (deterministyczna, funkcja celu + obwiedni; rider 2)
`launch(T) = [clip(T_x − 1.5, −1.6, 1.6), clip(T_y, −1.6, 1.6), z_hover]` — cel dokładnie **+x-przed**
(azymut 0 ⊂ ±25°), dystans **1.5 m ⊂ [1,2]**. **Nie strojony ręcznie per noga.** `LAUNCH_R=1.5`
(środek [1,2]), clamp `1.6` (launch zostaje w arenie). Cel „w obwiedni" ⟺ po launchu az ⊂ ±25° ∧
dyst ⊂ [1,2] (clamp może zepsuć dla skrajnych pozycji → obiekt odrzucony w scene-search).
**Zwalidowane (seed 49502 K8, 8/8 obiektów): 6 ARRIVED, 2 NEAR (≤0.29 m); ciągły sim, zero teleportu.**

## §C Reguła scene-search (ascending; rider 3, aneks pre-search)
Od **seed 49500** rosnąco; **pierwszy** seed spełniający **wszystkie**:
1. `scene_params(seed)[0] == 8` (K8);
2. zawiera **red box** w obwiedni (§B);
3. zawiera **blue sphere** w obwiedni;
4. ≥1 inny obiekt (do relokacji L3).
Zostaje sceną misji. **Log odrzuconych** (seed + powód: `K≠8` / `brak red box` / `brak blue sphere` /
`obiekt poza obwiednią`) w manifeście. Reguła stopu: 30 kolejnych seedów bez trafienia → STOP/eskalacja.

## §D Segmenty i transit (opcja 1)
- **LEARNED-LEG:** lot polityki `gc5` z **launch(cel)** do celu, osłona **APPLIED** (in-distribution
  i in-cone → czysty).
- **SCRIPTED-TRANSIT (reposition to launch):** egzekutor + rampa `HoverExpert` leci dronem do
  `launch(następny cel)`; **BEZ polityki**, przelot **w kadrze** (rider 1: zero teleportu).
- Ciągły sim (soft re-arm liczników, `self.env`/dron nietknięte); trace globalny.

## §E Burst L2 (PRZYPIĘTY przed nagraniem; rider 5)
Seed maski **45105**, **offset = 4** (okno `[first_lock+4, first_lock+4+Lt)`). Uzasadnienie: w krótkiej
obwiedni (dolot ~2 s z 1.5 m) burst **przed dotarciem** jest niewykonalny (5 s > dolot); offset=4
umieszcza burst **w terminalnym dwellu** (dron już przy celu, link zamarza → **FROZEN**, dron trzyma
z pamięci → dwell domyka się) — dynamika **bridging** jak DP A2, **unika wejścia w dwell** (lekcja
46507). **Zwalidowane (49502 blue sphere): offset 3/4/5/6 = CLEAN BRIDGE (ARRIVED, zero REFUSE).**
Odstępstwo od „burst w trakcie dolotu": w obwiedni dolot jest za krótki na burst przed-dotarciowy;
klean bridging to burst w dwellu (bridging z pamięci) — nazwane, nie zmiękczone.

## §F Etykiety (rider 4)
Segmenty transit w napisach: **„reposition to launch (executor) — not the learned pilot"**. Przy
**pierwszym** transicie dodatkowy napis ramujący: **„midcourse by executor; terminal flight by the
learned pilot within its measured envelope (±25° frontal cone, 1–2 m — RAPORT_3B)"**. Typy segmentów
w manifeście: `LEARNED-LEG` / `SCRIPTED-TRANSIT` per odcinek (bez zmian).

## §G Higiena
Obwiednia = jedno zdanie w RAPORT_MC jako **znane ustalenie 3b** (bez nowych liczb). Smoke launch/burst
(49502, poza pulami) = feasibility, nie baner. Zamrożone nietknięte; sweep 46600–46649 nietknięty.
*Aneks zamknięty PRZED scene-search. Następny krok: bieg scene-search wg §C.*
