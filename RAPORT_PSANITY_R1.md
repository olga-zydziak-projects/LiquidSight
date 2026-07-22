# RAPORT_PSANITY_R1 — bramka P-SANITY po ANEKS-1 (I1R+I2R)

**Data:** 2026-07-23
**Status:** **P1 PASS (100%) • P3 PASS (100%) • P2 FAIL (1 poziom w pasmie).** Defekt obserwowalnosci z I2 **naprawiony**; instrument (ramie GRU) jest teraz **w pelni zdolny na T0** i oś OOD **rozdziela** (100/100/64/16). Bramka niespełniona **wylacznie** na kryterium P2 „≥2 poziomy w pasmie [30,85]" — do decyzji czlowieka (poziom posredni osi). Progi P_SANITY.md **nietkniete**.

Odwolanie: **ANEKS_1_OBSERWOWALNOSC.md** (Z1 kamera pitch −22.3°, Z2 spawn celu w stozku czolowym +x). Poprzedni **RAPORT_PSANITY.md** (P1 FAIL 7%) pozostaje bez zmian — historia FAIL jest czescia programu. Wyniki I2 zachowane (`results/*.json`, `*_pre_aneks1/`); wyniki R1 pod `results/*_r1.json`.

---

## 0. Maszyna i srodowisko

| pozycja | wartosc |
|---|---|
| GPU / CPU | NVIDIA RTX 5070 Ti Laptop (CUDA) / Intel Ultra 9 275HX |
| platform / Python | WSL2 Linux 6.18 / CPython 3.12.13 (uv 0.11.28) |
| torch | 2.11.0+cu128 (trening CUDA) |
| pybullet / numpy / pillow | 3.2.7 / 2.5.1 / 12.3.0 |
| gym-pybullet-drones | 2.1.0, commit `e712698` (external/) |

Determinizm env/render/seedy jak dotad; bit-determinizm CUDA niewymagany (regula 4).

---

## 1. Rewizja obserwowalnosci (ANEKS-1) i smoke po rewizji

**Zmiany env (jedyne, wg ANEKS-1):** Z1 `look = eye + R@[1,0,−0.41]` (pitch −22.3°); Z2 spawn celu: azymut wzgledem +x ∈ [−25°,+25°], dystans 1.0–2.0 m. **Realizacja konieczna:** heading +x (yaw=0) od t=0 i region startu w polowie −x (`start_x∈[−1.5,−0.3]`, `|start_y|≤0.85`) — „azymut wzgledem +x" wymaga headingu +x (brak yaw w akcji), a stozek 1–2 m w przod musi miescic sie w arenie (lim=1.7). **r_goal/z_hover/t_dwell BEZ ZMIAN.**

**s1_visibility (NOWA bramka, na stale; 100 ep eksperta, 43000-43099, T0; widocznosc = seg celu ≥3 px):**

| bramka | wynik | prog | werdykt |
|---|---|---|---|
| **G1** cel w kadrze w t=0 | **100 / 100** | 100/100 | **PASS** |
| **G2** mediana udzialu klatek z celem w dolocie (d>0.35 m) | **1.000** (srednia 0.997, min 0.938) | ≥0.90 | **PASS** |

`results/s1_visibility.json`. Pozostale smoke (po ANEKS-1, commit C2): **s1_env_det PASS bit-w-bit** (43100/T0, 43149/T3); **s1_expert 100/100, 0 katastrof**; **s1_axis_render** 16 nowych klatek (cel w kadrze; stare → `axis_preview_pre_aneks1/`).

**Diagnostyka widocznosci (results/p1_observability_r1.json), 100 scen 43000-43099:**

| metryka | I2 (przed) | **R1 (po ANEKS-1)** |
|---|---|---|
| sceny z celem w kadrze | 27/100 | **100/100** |
| klatek z celem / epizod (120) | mediana 0, śr. 2.6 | **mediana 17, śr. 18.8** |
| sukces dagger.pt przy widocznym / niewidocznym | 2/27 / 5/73 | **100/100 / 0** |

Sukces polityki jest teraz **idealnie skorelowany z widocznoscia** (100/100 sukcesow na scenach z celem w kadrze) — instrument rozwiazuje zadanie **przez percepcje**, nie przypadkiem.

---

## 2. Parametry modeli (bez zmian wobec I2)

| modul | parametry |
|---|---|
| enkoder (4×conv → flatten 1024 → 64) | 126 112 |
| **rdzen GRU (78→64)** | **27 648** (referencja parytetu CfC ±2%) |
| glowa (64→6) | 390 |
| razem | 154 150 |

Hiperparametry (identyczne jak I2, strojenie tylko na T0): BC 15 epok, batch 16 epizodow, Adam 1e-3, grad clip 1.0, seed 45001; DAgger ×3, po 100 rolloutow, dotrening 10 epok.

---

## 3. Czasy scienne — pelny cykl treningu (wejscie do decyzji n przy F3_GATE)

| etap | czas | sukces rollout (DAgger) |
|---|---|---|
| BC data collect (300 ep, 300/300 sukces eksperta) | 113 s | — |
| BC trening (15 epok, val_mse→0.0012) | 58.6 s | — |
| DAgger r1 (55+50) | 105 s | 2.0% |
| DAgger r2 (57+65) | 122 s | **35.0%** |
| DAgger r3 (58+77) | 135 s | **98.0%** |
| **DAgger x3 razem** | **362 s** | |
| **▶ PELNY CYKL TRENINGU (BC + 3×DAgger)** | **420.6 s ≈ 7.0 min** | |
| end-to-end na ramie (z data collect) | 533.6 s ≈ 8.9 min | |

Progresja rollout 2%→35%→98% to podpis dzialajacego DAgger (korekta kowariancyjnego shiftu, mozliwa dopiero gdy cel jest w kadrze). **Jednostka kosztu ≈ 7.0 min/ramie** — przy F3_GATE koszt n seedow ≈ n × ten cykl.

---

## 4. Bramka P-SANITY (progi wg P_SANITY.md)

### P1 — zdolnosc (GRU, T0, 100 ep, 43000-43099)

| polityka | sukces | katastrofy | prog | werdykt |
|---|---|---|---|---|
| **dagger.pt (final)** | **100.0%** | 0 | ≥90% | **PASS** |

`results/psanity_p1_r1.json`. (Dla porownania I2: 7.0% FAIL — patrz RAPORT_PSANITY.md.)

### P2 — rozdzielczosc osi (dagger.pt, 50 ep/poziom, 43100-43149 identyczne)

| poziom | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| sukces | 100.0% | 100.0% | **64.0%** | 16.0% |
| katastrofy | 0 | 0 | 1 | 3 |

Poziomy w pasmie [30,85]: **{T2}** (1) → **FAIL** (wymagane ≥2). `results/psanity_p2_r1.json`.

Sciezki specjalne P_SANITY — **zadna nie zachodzi literalnie:** „wszystko >85" nie (T2=64, T3=16); „skok >85→<30 miedzy sasiednimi" nie (T1→T2 = 100→64: 64 nie <30; T2→T3 = 64→16: 64 nie >85). Oś **rozdziela monotonicznie** (100/100/64/16), ale ma tylko **jeden** punkt w pasmie dynamiki — T0/T1 przy suficie (100), T3 przy dnie (16).

### P3 — sufit (ekspert, 50 ep/poziom, 43100-43149)

| poziom | T0 | T1 | T2 | T3 | prog | werdykt |
|---|---|---|---|---|---|---|
| sukces | 100.0% | 100.0% | 100.0% | 100.0% | ≥95%/poziom | **PASS** |

`results/psanity_p3_r1.json`. Sufit dotkniety na kazdym poziomie — scena i oś poprawne (ekspert pikseli nie widzi).

---

## 5. Poziom osi dla F3_GATE

Formalnie **nieustalony**: P2 nie przeszedl kryterium ≥2-w-pasmie. Jedyny poziom w pasmie [30,85] to **T2 (64%)** — naturalny kandydat na poziom pomiaru F3_GATE (jedyny z zapasem dynamiki CfC−GRU; T0/T1 nasycone przy 100%, T3 przy 16%). Aby uzyskac ≥2 punkty w pasmie, oś potrzebuje **poziomu posredniego miedzy T2 (64%) a T3 (16%)** — to zmiana osi, **niesankcjonowana po C2** (regula 2 dopuszcza po C2 wylacznie wzmocnienie T3, ktore czyniloby T3 TRUDNIEJSZYM, a wiec pogarszalo pasmo). Decyzja nalezy do czlowieka (§6).

---

## 6. Decyzje czlowieka przed F3_GATE

**Rozstrzygniecie P2 (bloker gate'u):** oś rozdziela, ale ma 1 poziom w pasmie zamiast ≥2. Opcje:
- **(a)** dodac poziom posredni miedzy T2 a T3 (np. rodzina B z K=2 dystraktorow, lub mieszanka A/B) i powtorzyc P2 — **wymaga rewizji osi = nowy aneks / poza regula 2**; rekomendacja techniczna, bo najczysciej domyka kryterium.
- **(b)** zaakceptowac T2 jako jedyny poziom pomiaru F3_GATE mimo <2-w-pasmie — oslabia moc porownania (1 punkt dynamiki), do rozwazenia tylko jako fallback.
- Wzmocnienie T3 (jedyna sankcjonowana po C2 zmiana osi) **nie pomaga** — T3 jest juz <30%.

**Decyzje pozostale (odblokowane — instrument dziala):**
- **dense-CfC vs AutoNCP** dla rdzenia CfC (parytet wzgledem 27 648 param rdzenia GRU, ±2%): teraz sensowna — ramie P-SANITY przeszlo P1/P3. Do wyboru przez czlowieka przed budowa drugiego ramienia.
- **n seedow** przy F3_GATE: koszt jednostkowy zmierzony (§3, **~7.0 min/ramie**); n × cykl. Dobor n — czlowiek.
- **potwierdzenie poziomu osi**: patrz P2 wyzej (T2 lub +poziom posredni).

**Zgodnosc z protokolem:** ANEKS-1 zaimplementowany 1:1; env zamrozone po C2 (regula 2) — zero pozniejszych zmian env; strojenie treningu wylacznie na T0; progi P_SANITY nietkniete; F3_GATE niezamrozony; CfC nie powstal.

---

## STOP

Instrument naprawiony: **P1 100% PASS, P3 100% PASS**; **P2 FAIL** na kryterium ≥2-w-pasmie (oś rozdziela: 100/100/64/16, jedyny poziom w pasmie = T2). Domkniecie osi (poziom posredni T2–T3) i decyzje F3_GATE — **czlowiek**. Nic wiecej nie zmieniam.
