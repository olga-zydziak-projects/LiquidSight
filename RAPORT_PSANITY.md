# RAPORT_PSANITY — instrument GRU + pipeline BC/DAgger + bramka P-SANITY (I2)

**Data:** 2026-07-22
**Status:** **P1 FAIL • P2 FAIL • P3 PASS.** Bramka P-SANITY **niespełniona**. Rdzen CfC celowo nie powstal (przed F3_GATE).
**Werdykt nadrzedny:** instrument (ramie GRU) **nie osiaga zdolnosci P1** z powodu **problemu obserwowalnosci** kanalu percepcji (cel poza kadrem kamery przedniej w ~73% scen). Przyczyna jest **poza zakresem naprawy nominalnej** (dane/epoki/rundy/architektura) — wymaga **decyzji czlowieka** (rewizja D2 kamera / D1 cel / dodanie sterowania yaw). **MIERZĘ = RAPORTUJĘ** — wyniki podane niezaleznie od urody.

Zamrozenia (DECYZJE_F3.md, P_SANITY.md, config/env_f3.json, frozen_v1/, liquidflight/) **nietkniete**. Progi P1-P3 wg P_SANITY.md, bez zmian.

---

## 0. Maszyna i srodowisko

| pozycja | wartosc |
|---|---|
| CPU / GPU | Intel Ultra 9 275HX (24 wątki) / **NVIDIA RTX 5070 Ti Laptop** (CUDA) |
| platform | `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64` |
| Python | CPython 3.12.13 (uv 0.11.28) |
| torch | **2.11.0+cu128** (trening na CUDA) |
| pybullet / numpy / pillow | 3.2.7 / 2.5.1 / 12.3.0 |
| gym-pybullet-drones | 2.1.0, commit `e712698` (external/) |

Bit-determinizm kernelow CUDA **nieegzekwowany** (regula 4 — nie dotyczy kontraktu; env/render/sceny deterministyczne z seeda).

---

## 1. Parametry modeli (T1)

Skalowanie glowy: `pos_xy=2.0·tanh (±2.0 m)`, `pos_z∈[0.1,2.4] m`, `vel=1.0·tanh (±1.0 m/s)`.

| modul | parametry | uwaga |
|---|---|---|
| enkoder (4×conv k3s2 16/32/64/64 → flatten 1024 → Linear 64) | **126 112** | flatten, nie pooling (D2: gdzie jest cel) |
| **rdzen GRU (GRUCell 78→64)** | **27 648** | **referencja parytetu dla przyszlego CfC (±2%)** |
| glowa (Linear 64→6) | **390** | |
| **razem** | **154 150** | |

Wejscie rdzenia: `concat(feat 64, kin 13, dt 1) = 78`; tyk na klatce kamery (12 Hz), stan h przez epizod.

---

## 2. Hiperparametry, dane i log strojenia

**Dane BC (T2):** 300 epizodow eksperta na T0, sceny 44000-44299; **300/300 sukcesu eksperta**; probka na tik = (rgb, kin, dt) → setpoint eksperta; split 270 train / 30 val (monitoring, bez strojenia). Zbieranie: **110.9 s**.

**BC (T3):** sekwencyjnie pelnymi epizodami (120 tikow), batch 16, Adam lr 1e-3, grad clip 1.0, **15 epok**, seed treningu **45001** (pula REZERWOWA 45xxx; oś dropout niewykorzystana w F3 → 45001 wolny, odnotowane). train_mse 0.322→**0.0043**, val_mse 0.151→**0.0040** (val sledzi train — brak przeuczenia na poziomie MSE setpointu).

**DAgger ×3 (T4):** runda = 100 rolloutow polityki na T0 (44300-44399 / 44400-44499 / 44500-44599), etykieta eksperta na tiku, agregacja calego zbioru (BC train + rundy), dotrening 10 epok (te same hiperparametry), kontynuacja od wag BC.

**Log strojenia instrumentu (WYLACZNIE na T0 nominal; nigdy na T1-T3):**

| proba | dzwignia (sankcjonowana) | sukces T0 (100 ep) | rollout% (100 ep) | val_mse |
|---|---|---|---|---|
| BC | baseline | **0.0%** (100× dwell) | — | 0.0040 |
| +DAgger r1 | +100 danych, +1 runda | — | 0.0% | 0.0241 |
| +DAgger r2 | +100 danych, +1 runda | — | 2.0% | 0.0191 |
| +DAgger r3 (final) | +100 danych, +1 runda | **7.0%** (23 tilt, 70 dwell) | 0.0% | 0.0366 |

Dzwignie sankcjonowane przez P_SANITY (dane / rundy DAgger) i T5 (epoki / architektura) **nie przekroczyly progu** — sufit ≤27% (patrz §4). Dalszej naprawy nominalnej (wiecej epok / inna architektura / wyzsza rozdzielczosc) **nie uruchomiono**: jest dowiedzione (§4), ze nie przekroczy sufitu obserwowalnosci — bylby to teatr, nie naprawa. Przyczyna lezy poza zakresem nominalnym.

---

## 3. Czasy scienne (wejscie do decyzji n przy F3_GATE)

| etap | czas |
|---|---|
| BC data collect (300 ep, jednorazowe) | 110.9 s |
| BC trening (15 epok) | 56.0 s |
| DAgger r1 (rollout 54.6 + trening 50.7) | 105.3 s |
| DAgger r2 (rollout 49.0 + trening 65.2) | 114.1 s |
| DAgger r3 (rollout 41.3 + trening 77.2) | 118.5 s |
| **DAgger x3 razem** | **337.9 s** |
| **▶ PELNY CYKL TRENINGU (BC + 3×DAgger)** | **393.9 s ≈ 6.6 min** |
| end-to-end na ramie (z data collect) | 504.8 s ≈ 8.4 min |

**Jednostka kosztu na 1 ramie ≈ 6.6 min treningu** (dane wspoldzielone lub +1.8 min zbierania na seed). Przy F3_GATE: koszt n seedow ≈ n × ten cykl. (Decyzja n — czlowiek; §7.)

---

## 4. Pierwotna przyczyna P1 FAIL: OBSERWOWALNOSC (results/p1_observability.json)

Zmierzone na tych samych 100 scenach co P1 (43000-43099, T0), widocznosc = ≥1 klatka z pikselami celu (seg) przy sterowaniu ekspertem:

| metryka | wartosc |
|---|---|
| sceny z celem kiedykolwiek w kadrze | **27 / 100 (27%)** |
| klatek z celem / epizod (120) | **mediana 0**, srednia 2.6, max 34 |
| sukces bc.pt: przy widocznym / niewidocznym | 0/27 / 0/73 |
| sukces dagger.pt: przy widocznym / niewidocznym | **2/27 / 5/73** |

**Wnioski (twarde):**
1. **Cel jest poza kadrem w 73% scen** i tylko ulotnie obecny w reszcie (mediana 0, srednia 2.6 klatki). Kamera przednia (`look = eye + R@[1,0,−0.15]`, ~8.5° w dol) patrzy niemal poziomo; cel na podlozu (z=0.08) wpada pod dolna krawedz FOV, gdy dron leci ku/nad punktem zawisu.
2. **Agent nie ma jak sprowadzic celu w kadr:** przestrzen akcji = setpoint6 (pos, vel) **bez yaw**; env liczy inner-PID z `target_rpy=0`, wiec dron ustawia heading→0 niezaleznie od kierunku do celu, a kamera jest sztywno zwiazana z headingiem.
3. **Sukces polityki jest nieskorelowany z widocznoscia** (dagger: 2/27 vs 5/73) — 7% to przypadkowe ladowania z priora ruchu, nie lokalizacja z percepcji. Instrument **nie rozwiazuje zadania przez wzrok**, bo sygnalu wzrokowego w wiekszosci nie ma.
4. **Sufit zdolnosci ≤27% ≪ 90%.** Zadna dzwignia nominalna (dane/epoki/rundy/architektura/rozdzielczosc) nie tworzy informacji, ktorej nie ma w wejsciu.

To NIE jest blad sceny ani eksperta: **P3 (§5) = 100% na kazdym poziomie** dowodzi, ze cel jest osiagalny, a scena/nagroda/klif poprawne. Problem jest wylacznie w **kanale percepcji** (D2 kamera przednia + brak yaw + D1 cel na podlozu).

---

## 5. Bramka P-SANITY (wg P_SANITY.md)

### P1 — zdolnosc (ramie GRU, T0, 100 ep, sceny 43000-43099)

| polityka | sukces | katastrofy | typy porazki | prog | werdykt |
|---|---|---|---|---|---|
| bc.pt | 0.0% | 0 | dwell×100 | ≥90% | FAIL |
| **dagger.pt (final)** | **7.0%** | 23 | tilt×23, dwell×70 | ≥90% | **FAIL** |

`results/psanity_p1.json`.

### P2 — rozdzielczosc osi (dagger.pt, 50 ep/poziom, sceny 43100-43149 identyczne)

| poziom | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| sukces | 8.0% | 2.0% | 4.0% | 2.0% |
| katastrofy | 13 | 16 | 13 | 31 |

Poziomy w pasmie [30%,85%]: **0** → **FAIL** (wymagane ≥2). Werdykt pasma **nieinformatywny** o odpornosci OOD — polityka jest niefunkcjonalna juz na T0 (nie ma czego rozdzielac na osi). Sciezki „wszystko>85" i „klif" **nie zachodza** (wszystkie poziomy <30%). `results/psanity_p2.json`.

### P3 — sufit (ekspert privileged, 50 ep/poziom, sceny 43100-43149)

| poziom | T0 | T1 | T2 | T3 | prog | werdykt |
|---|---|---|---|---|---|---|
| sukces | 100.0% | 100.0% | 100.0% | 100.0% | ≥95%/poziom | **PASS** |

`results/psanity_p3.json`. Ekspert (bez pikseli) dotyka sufitu na kazdym poziomie — **scena i oś skonstruowane poprawnie**; oś dotyka wylacznie pikseli, ktorych ekspert nie widzi.

---

## 6. Poziom osi dla F3_GATE

**Nieokreslony.** F3_GATE wymaga PASS P1-P3; P1/P2 FAIL. Poziom osi wskazywany przez P2 (pasmo [30,85]) **nie istnieje** — polityka niefunkcjonalna na wszystkich poziomach. **F3_GATE nieosiagalne** do czasu przejscia P1.

---

## 7. Decyzje czlowieka przed F3_GATE

**BLOKER nadrzedny (do rozstrzygniecia PRZED czymkolwiek innym):** kanal percepcji nie zawiera celu w ~73% scen. Naprawa jest **poza zakresem tej sesji** (zmiana env/D2). Opcje dla czlowieka (kazda wymaga rewizji zamrozenia i ponownego I1/env):
- **(a) Pochylic kamere w dol** (zwiekszyc pitch, np. `look` z −0.6…−1.0 zamiast −0.15) — cel na podlozu w kadrze; rewizja implementacji „kamera przednia" (D2).
- **(b) Dodac sterowanie yaw** do przestrzeni akcji (setpoint7 z target_yaw) — agent moze obrocic sie ku celowi; rewizja D2/D3 i eksperta.
- **(c) Podniesc cel** (np. slup/znacznik na wysokosci kamery) — rewizja D1.
- Rekomendacja techniczna: **(a)** najmniej inwazyjna (sama geometria kamery, bez zmiany akcji/eksperta), i najlatwiej re-zamrozic po sanity widocznosci.

**Decyzje odroczone (moot do czasu PASS P1) — wymienione dla kompletnosci T8:**
- **dense-CfC vs AutoNCP** dla rdzenia CfC: nierozstrzygalne — parytet liczy sie wzgledem rdzenia GRU (27 648 param), ale drugie ramie ma sens dopiero, gdy ramie P-SANITY przejdzie P1.
- **n seedow** przy F3_GATE: koszt jednostkowy zmierzony (§3, ~6.6 min/ramie), ale n bez sensu bez dzialajacego instrumentu.
- **potwierdzenie poziomu osi**: brak (P2 nieinformatywne).

**Zgodnosc z protokolem:** nie improwizowano naprawy poza P_SANITY (nie zmieniano env/kamery — poza zakresem), nie strojono na T1-T3, nie zamrazano F3_GATE. Sankcjonowane naprawy nominalne wyczerpano do granicy sufitu obserwowalnosci i udokumentowano ich dowiedziona bezskutecznosc.

---

## STOP

Bramka P-SANITY niespełniona (P1/P2 FAIL, P3 PASS). Diagnoza: obserwowalnosc kanalu percepcji. Dalszy ruch (rewizja D2/D1/D3 i powtorka I1→I2) — **decyzja czlowieka**. Nic wiecej nie zmieniam.
