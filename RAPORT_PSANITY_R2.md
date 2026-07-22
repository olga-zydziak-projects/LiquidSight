# RAPORT_PSANITY_R2 — drabina osi + powtorka P2 (ANEKS-2)

**Data:** 2026-07-23
**Status:** **P2R PASS • P3R PASS.** Po rozszerzeniu osi o drabine dystraktorowa (T2a/T2b/T2c) kryterium P2 „≥2 poziomy w [30,85]" jest **spełnione** (3 poziomy: T2, T2a, T2b). Bramka P-SANITY: **P1 PASS (100%, R1) • P2R PASS • P3R/P3 PASS (100% caly zakres)**. **Zero treningu** — ewaluacja istniejacego checkpointu z P1. Progi P_SANITY.md **nietkniete**.

Odwolanie: **ANEKS_2_DRABINA_OSI.md** (Z1: os parametryczna w K; T2=K0, T2a=K1, T2b=K2, T2c=K3, T3=K4). Raporty **RAPORT_PSANITY.md** (I2 FAIL) i **RAPORT_PSANITY_R1.md** (R1) — bez zmian. Checkpoint polityki (R1) **nietkniety**.

---

## 0. Maszyna i procedura

Maszyna/srodowisko jak R1 (RTX 5070 Ti, CUDA; Python 3.12.13; torch 2.11.0+cu128; pybullet 3.2.7; gpd `e712698`). **Ta sesja: WYLACZNIE ewaluacja** — polityka `ckpt/gru/dagger.pt` (z P1/R1) nie byla dotknieta (retrening po obejrzeniu OOD bylby strojeniem instrumentu na osi — zakazane). Determinizm env/render/seedy jak dotad.

**Smoke po nowej sciezce kodu (drabina):** `s1_env_det` scena 43125 / **T2b**, 2 niezalezne przebiegi — **PASS bit-w-bit** (rgb/kin/setpoint), obok zachowanych 43100/T0 i 43149/T3. Drabina zagniezdzona zweryfikowana: dla scene_seed 43125 cel identyczny na wszystkich poziomach, K=0/0/0/1/2/3/4.

---

## 1. Pelna krzywa drabiny — P2R (dagger.pt z P1, 50 ep/poziom, sceny 43100-43149)

| poziom | K dystr. | rodzina tla | sukces | katastrofy | pasmo [30,85] |
|---|---|---|---|---|---|
| T0 | 0 | A (pula tren.) | 100.0% | 0 | — (>85) |
| T1 | 0 | A (held-out) | 100.0% | 0 | — (>85) |
| T2 | 0 | B | 64.0% | 1 | **✓** |
| **T2a** | 1 | B | **46.0%** | 2 | **✓** |
| **T2b** | 2 | B | **36.0%** | 3 | **✓** |
| T2c | 3 | B | 24.0% | 3 | — (<30) |
| T3 | 4 | B | 16.0% | 3 | — (<30) |

**Poziomy w pasmie [30,85]: {T2, T2a, T2b} = 3 → P2R PASS** (wymagane ≥2). `results/psanity_p2r.json`.

Oś degraduje **monotonicznie i gladko** z K (100→100→64→46→36→24→16) — drabina dystraktorowa daje ciagla kontrole trudnosci OOD, dokladnie jak zakladal ANEKS-2 (uzupelnienie rozdzielczosci miedzy T2=64 a T3=16). Bez selekcji post hoc — wszystkie 7 poziomow raportowane.

**Zgodnosc z R1 (regula 2 aneksu):** poziomy T0/T1/T2/T3 w P2R = **100/100/64/16** — **identyczne z R1** (100/100/64/16). Determinizm sceny zachowany po zmianie sciezki kodu; **zero rozbieznosci**.

---

## 2. P3R — sufit eksperta na nowych poziomach (50 ep/poziom, te same sceny)

| poziom | T2a | T2b | T2c | prog | werdykt |
|---|---|---|---|---|---|
| ekspert | 100.0% | 100.0% | 100.0% | ≥95%/poziom | **PASS** |

`results/psanity_p3r.json`. T0-T3 cytowane z R1 (100% kazdy). Ekspert (privileged, bez pikseli) dotyka sufitu na **calej drabinie** — konstrukcja nowych poziomow poprawna (dystraktory nie blokuja fizycznej osiagalnosci celu).

---

## 3. Bramka P-SANITY — stan zbiorczy

| bramka | wynik | werdykt |
|---|---|---|
| **P1** (zdolnosc, GRU T0, 100 ep) | 100.0% (R1) | **PASS** (≥90%) |
| **P2R** (rozdzielczosc osi, drabina 7 poziomow) | 3 poziomy w pasmie {T2,T2a,T2b} | **PASS** (≥2) |
| **P3 / P3R** (sufit, ekspert, 7 poziomow) | 100% kazdy | **PASS** (≥95%) |

**Bramka P-SANITY spełniona.** Instrument (ramie GRU z pre-rejestrowanego rzutu) jest zdolny (P1), oś rozdziela z zapasem dynamiki w ≥2 punktach (P2R), a sufit jest osiagalny na kazdym poziomie (P3). Droga do F3_GATE otwarta — po decyzjach czlowieka (§5).

---

## 4. Poziom osi wskazany dla F3_GATE

Zgodnie z ANEKS-2 („najciezszy poziom w pasmie [30,85]"): **T2b (K=2, 36.0%)**. Uzasadnienie: najnizszy sukces sposrod poziomow w pasmie → najwiekszy zapas dynamiki na margines CfC−GRU bez ryzyka podlogi/sufitu. Alternatywy w pasmie: T2a (46%), T2 (64%). Formalne zamrozenie poziomu → **F3_GATE**, nie tutaj (poza zakresem).

---

## 5. Czasy i decyzje czlowieka przed F3_GATE

**Koszt jednostkowy treningu ramienia (z R1, ta sesja nic nie trenowala):** pelny cykl **BC + 3×DAgger ≈ 7.0 min/ramie** (collect 113 s + BC 58.6 s + DAgger 362 s; end-to-end z data collect ~8.9 min). Rdzen GRU: **27 648** param (referencja parytetu ±2%).

**Decyzje czlowieka:**
- **Poziom bramki F3_GATE:** rekomendacja **T2b (36%)** (§4) — do potwierdzenia.
- **dense-CfC vs AutoNCP** dla rdzenia CfC: parytet wzgledem 27 648 param rdzenia GRU (±2%). Do wyboru przed budowa drugiego ramienia (poza ta sesja — CfC nie powstaje przed F3_GATE).
- **n seedow** przy F3_GATE: koszt n × ~7.0 min; wskaznik = margines CfC−GRU, prog = margines > pooled std (P_SANITY.md). Dobor n — czlowiek (z pomiaru czasu treningu P1, jak w P_SANITY).

**Zgodnosc z protokolem:** ANEKS-2 zaimplementowany 1:1 (os parametryczna w K, sceny sweep bez zmian); **zero treningu / checkpoint P1 nietkniety**; kamera/spawn/ekspert/parametry zadania/progi P_SANITY/frozen_v1 nietkniete; wszystkie 7 poziomow raportowane (bez selekcji post hoc); F3_GATE niezamrozony; CfC nie powstal. Raporty I2 i R1 nietkniete.

---

## STOP

Drabina osi domyka P2: **P2R PASS** (3 poziomy w pasmie: T2/T2a/T2b), **P3R PASS** (ekspert 100% na nowych poziomach). Bramka P-SANITY spełniona (P1+P2R+P3). Kandydat poziomu F3_GATE: **T2b (36%)**. Zamrozenie F3_GATE i decyzje (CfC dense vs AutoNCP, n seedow) — **czlowiek**. Nic wiecej nie zmieniam.
