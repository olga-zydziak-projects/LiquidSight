# RAPORT_S0 — smoke ścieżki krytycznej fazy 3a (render det • scena/seg • throughput)

**Data:** 2026-07-22
**Status:** **T2 PASS • T3 PASS** (warunek krytyczny determinizmu spełniony na tej maszynie); **T4 zmierzone** (bez bramki).
**Zakres:** zero treningu, zero integracji z gym-pybullet-drones, zero decyzji projektowych. **MIERZĘ = RAPORTUJĘ.**

Progi i logika skryptów `s0_render_det.py` / `s0_scene_seg.py` **nietknięte** — obie bramki i tolerancje takie, jak przyszły w archiwum sandboxowym.

---

## 0. Maszyna i środowisko

| pozycja | wartość |
|---|---|
| CPU | Intel(R) Core(TM) Ultra 9 275HX (1 socket, 24 rdzenie, 1 wątek/rdzeń) |
| nproc | 24 |
| RAM | 15 GiB total (≈14 GiB available w chwili pomiaru) |
| platform | `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` |
| Python | CPython **3.12.13** (uv-managed, nie systemowy) |
| venv | `/home/olga/projects/liquidsight/.venv` |
| menedżer | uv 0.11.28 (bez sudo/apt) |

**Wersje pakietów** (= `requirements.lock` zamrożonego repo; zweryfikowane odczytem):

| pakiet | wersja | uwaga |
|---|---|---|
| pybullet | **3.2.7** | wheel cp312 nie istnieje na PyPI → **build ze źródeł ~44 s** (pozwolony, wersji nie zmieniano); API `202010061` |
| numpy | **2.5.1** | |
| pillow | **12.3.0** | |

`pybullet API 202010061` jest identyczny jak w JSON-ach sandboxa — ten sam kod źródłowy renderera.

---

## 1. Relacja do frozen (`~/projects/liquidflight`, tag `liquidflight-v1.0`)

Repo zamrożone traktowane **READ-ONLY**. W tej sesji **czytano wyłącznie**:

- `requirements.lock` — źródło prawdy o wersjach (potwierdza pybullet 3.2.7 / numpy 2.5.1 / pillow 12.3.0);
- `MANIFEST.json` — wzór opisu środowiska (platform string, konwencja venv);
- `RAPORT_A1.md`, `RAPORT_C01.md` — wzór stylu i formy raportu.

**Zero zapisów, zero importów runtime, zero symlinków do frozen.** Warstwa wykonawcza (setpoint→DSL-PID) **nie była kopiowana** — wejdzie w sesji integracyjnej jako kopia bit-w-bit z sha256 w manifeście F3. Cała praca w nowym katalogu `~/projects/liquidsight`.

---

## 2. Testy krytyczne T2–T3

Skróty hashy = pierwsze 12 znaków SHA256. **FAIL byłby wyłącznie rozjazdem dwóch przebiegów NA TEJ maszynie** — rozjazd hashy vs sandbox (inna maszyna) **nie jest FAIL** (patrz §5).

### T2 — determinizm renderu TinyRenderer (DIRECT, CPU), 30 klatek, shadow=1

Dwa niezależne przebiegi (świeży klient DIRECT każdy), SHA256 osobno dla rgb/depth/seg.

| res | werdykt | rgb | depth | seg | rgb=depth=seg identyczne? |
|---|---|---|---|---|---|
| 64×64 | **PASS** | `b60bac62a81b` | `79bd776b0796` | `5ca35b80fb19` | tak (bit-w-bit) |
| 96×96 | **PASS** | `aaabd3c3e8a3` | `4743363cccf0` | `bd02a0639454` | tak (bit-w-bit) |

Wymagany PASS obu — **spełniony**. Ścieżka `shadow=0` (diagnostyczna) nie została uruchomiona, bo `shadow=1` przeszło. Pliki: `results/s0_render_det_64.json`, `results/s0_render_det_96.json`.

### T3 — scena z seeda + segmentacja + pule tekstur, 96×96

| sprawdzenie | wynik |
|---|---|
| werdykt | **PASS** |
| maska celu | **123 px** |
| \|centroid − proj(GT)\| | **0.93 px** (tol 4.0) |
| centroid maski | (60.67, 49.52) px |
| projekcja GT | (60.70, 50.45) px |
| pula powtarzalna (hash A == A) | OK — `951d776659cf` |
| pule różne (hash A != B) | OK — B `3763f6897009` |

Plik: `results/s0_scene_seg.json`.

---

## 3. Throughput A/B/C (pomiar, NIE bramka)

Konfiguracja: klient DIRECT, timestep 1/240, tik kontroli = 5× `stepSimulation` (**48 Hz**), seed sceny **40003**, bez GUI. 20 s symulacji = **960 tików**; warmup 2 s (96 tików) nienotowany; **2 przebiegi + mediana**. B/C: `getCameraImage` co 4. tik (**12 Hz nominalnie**), TinyRenderer, shadow=1, `lightDirection=[0.4,0.4,1.0]` — identycznie jak `s0_render_det`.

| pomiar | res | przebieg | wall [s] | tik/s | ×realtime | camera-FPS (osiągn.) |
|---|---|---|---|---|---|---|
| **A** baseline | — | 1 | 0.010 | 95 789 | 1995.6 | — |
| | | 2 | 0.010 | 98 007 | 2041.8 | — |
| | | **mediana** | **0.010** | **96 898** | **2018.7** | — |
| **B** render | 64×64 | 1 | 0.200 | 4 796 | 99.91 | 1199.0 |
| | | 2 | 0.200 | 4 790 | 99.79 | 1197.5 |
| | | **mediana** | **0.200** | **4 793** | **99.85** | **1198.2** |
| **C** render | 96×96 | 1 | 0.423 | 2 268 | 47.25 | 567.1 |
| | | 2 | 0.407 | 2 359 | 49.15 | 589.8 |
| | | **mediana** | **0.415** | **2 314** | **48.20** | **578.5** |

**camera-FPS** to *osiągnięta* przepustowość renderu (klatki/wall), nie nominalne 12 Hz — sim biegnie znacznie szybciej niż realtime, więc 240 klatek renderuje się w ułamku sekundy. Nominalne 12 Hz jest w `config`.

**Narzut renderu** (mediana wall, spowolnienie vs A): **B/A = 20.2×**, **C/A = 41.9×**.

### Wyprowadzenia (etykieta: *przykładowy budżet demonstracji, nie decyzja*)

| wielkość | B (64²) | C (96²) |
|---|---|---|
| czas ściany 1 epizodu 10 s | **0.10 s** | **0.21 s** |
| projekcja na 300 epizodów | **30.0 s (0.5 min)** | **62.2 s (1.0 min)** |

Plik: `results/s0_throughput.json`.

---

## 4. Wnioski dla F3_GATE (n seedów)

Same liczby, bez interpretacji:

- Render 64² kosztuje **20.2×** baseline, 96² kosztuje **41.9×**; mimo to obie konfiguracje biegną **powyżej realtime** (99.85× i 48.20×).
- Budżet ściany na 1 sparowany epizod 10 s: **0.10 s (64²)** / **0.21 s (96²)** — bez uwzględnienia forward-passu polityki (CfC/GRU), którego tu nie ma.
- Projekcja liniowa 300 epizodów: **~30 s (64²)** / **~62 s (96²)** czasu renderu+sim, na tym CPU.
- camera-FPS osiągnięty przy 12 Hz nominalnym: **1198 (64²)** / **578 (96²)** klatek/s.

**Decyzja o n należy do człowieka po tym raporcie.**

---

## 5. Rozbieżności / uwagi (wolno odnotować; różnic hashy między maszynami NIE interpretuję jako FAIL)

- **Python:** sesja na CPython **3.12.13** (uv), sandbox raportował 3.11.15/3.12.3 — lock jest lockiem, różnica kosmetyczna dla determinizmu C++ renderera.
- **pybullet z buildu ze źródeł** (cp312 bez wheela) — czas budowy ~44 s; wersja i API (`202010061`) zgodne z sandboxem, nie zmieniano.
- **Zgodność hashy vs sandbox (obserwacja, nie kryterium):** hash rgb 64² na tej maszynie (`b60bac62a81b…`) jest **identyczny bit-w-bit** z JSON-em sandboxa — cross-machine reprodukowalność ponad wymagane minimum. To miły sygnał, nie warunek: kontraktem PASS jest wyłącznie zgodność **dwóch przebiegów na tej samej maszynie**, i ta jest spełniona dla wszystkich buforów przy 64² i 96².
- **T3** odtwarza sandbox co do liczby (123 px, 0.93 px) — ten sam scene_seed 40002 (domyślny), pule 41000/42000.
- **`unzip` niedostępny** (bez sudo/apt) — archiwum rozpakowano `python -m zipfile`; efekt identyczny (skrypty + notatki + JSON-y sandboxa), zawartość zacommitowana jako stan wejściowy.
- Seed sceny throughput **40003** (z puli 40000+, konwencja domu) — do wpisania do manifestu F3 przy adopcji, wraz z 40001/40002/41000/42000.

---

## STOP

Po zapisaniu tego raportu i commicie sesja S0 się kończy. Domknięcie i zamrożenie P-SANITY (progi z `F3_PRE0` §4) — osobny krok, decyzja człowieka.
