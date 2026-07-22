# RAPORT_I1 — integracja środowiska zadaniowego fazy 3a (env • ekspert • smoke)

**Data:** 2026-07-22
**Status:** **T5 DONE • T5a DONE • T6 DONE (ekspert 100/100 T0) • T7 DONE (s1_env_det PASS oba seedy)**. Zero treningu, zero kodu modeli, zero P1/P2/P3. **MIERZĘ = RAPORTUJĘ.**
**Zamrożenia nietknięte:** `DECYZJE_F3.md`, `P_SANITY.md` — bez edycji. Progi i logika skryptów smoke **nietknięte** po zobaczeniu wyników.

> **Nocna sesja I1 została przerwana** po napisaniu kodu env (T4), z pustymi katalogami `frozen_v1/ config/ smoke/ expert/`. Osobna sesja audytu ustaliła: T1–T3 DONE, T4 PARTIAL (env napisany, untracked, nie importował się — czekał na `frozen_v1/`), T5–T9 MISSING, frozen czysty. **Ta sesja wznowiła od T5** (warstwa wykonawcza, od której zależy import env) i dokończyła I1.

---

## 0. Maszyna i środowisko

| pozycja | wartość |
|---|---|
| CPU | Intel(R) Core(TM) Ultra 9 275HX |
| nproc | 24 |
| RAM | 15 GiB total (≈14 GiB available w chwili pomiaru) |
| platform | `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` |
| Python | CPython **3.12.13** (uv-managed) |
| venv | `/home/olga/projects/liquidsight/.venv` |
| menedżer | uv **0.11.28** (bez sudo/apt) |

**Wersje pakietów** (zweryfikowane odczytem z `.venv`):

| pakiet | wersja | uwaga |
|---|---|---|
| pybullet | **3.2.7** | API `202010061` (identyczny jak S0) |
| numpy | **2.5.1** | |
| pillow | **12.3.0** | |
| gymnasium | **1.3.0** | |
| torch | **2.11.0+cu128** | zaimportowany tylko przez frozen (nieużywany w I1 runtime) |
| gym-pybullet-drones | **2.1.0**, commit `e712698` | `external/`, `-e --no-deps`; zgodny z pinem w `liquidflight/MANIFEST.json` |

---

## 1. Relacja do frozen (`~/projects/liquidflight`, `liquidflight-v1.0`)

Repo zamrożone **READ-ONLY**. W tej sesji **czytano** `src/task.py`, `src/c1_common.py` (analiza domiaru), `MANIFEST.json`, `RAPORT_S0.md` (wzór formy). **Zero zapisów, zero symlinków, zero importów runtime z frozen.** Kontrola:

- `git -C ~/projects/liquidflight status --porcelain` → tylko `M .claude/settings.local.json` + `?? ckpt/c1/`, **oba pre-datują sesję** (mtime 2026-07-20 23:53 i 2026-07-16); żaden plik frozen nie zmieniony przez tę sesję.
- `find ~/projects/liquidflight -newermt 2026-07-21` → **nic**.

### Kopia warstwy wykonawczej (T5) → `frozen_v1/` + `MANIFEST_F3.json`

| kopia | oryginał | sha256 (kopia == oryginał) | bajtów | verbatim |
|---|---|---|---|---|
| `frozen_v1/task.py` | `liquidflight/src/task.py` | `9ad8936353c9…d884c20` | 5789 | **tak (diff = 0)** |

`source: liquidflight-v1.0`, `source_commit: ce0d662…`. Bez `frozen_v1/__init__.py` (bare `import task` rozwiązuje się przez `sys.path` — jedna linia w env/expert; `task.py` nie ma importów wewnątrz frozen).

**Decyzja domiaru — NIE skopiowano `c1_common.py`** (mimo że prompt spodziewał się „min. task.py i c1_common.py"). Uzasadnienie:
- Domknięcie importów env sterowane błędami importu = **`{task.py}`**. `env/` importuje wyłącznie prymitywy wykonawcze z `task` (`CTRL_DT, CTRL_FREQ, FAIL_TILT_DEG, FAIL_Z_MIN, make_expert, obs_kin, split_state`); wzorzec position-hold jest wbudowany wprost w `step()` (kompozycja `DSLPIDControl.computeControlFromState` + `env.step`).
- Cała reużywalna zawartość `c1_common.py` (`RampIntercept`, `rollout_expert_*`, `outage_mask`, `mask_seed`) jest **specyficzna dla zadania okręgu + outage** — `RampIntercept` wykrywa lukę i robi feedforward **ruchomej** referencji. Wciągnięcie tego do fly-to-target byłoby **przeciekiem logiki zadania**, który T5a każe zgłosić i zatrzymać.
- Prymityw gładkiej rampy, którego potrzebuje ekspert (`_smoothstep`, `3a²−2a³`), **jest w `task.py`**.

Zapisane w `MANIFEST_F3.json/NIE_kopiowano`. **To jedyne odstępstwo od literalnego brzmienia T5 — do wglądu człowieka.**

---

## 2. Poprawki przeglądu T5a (kod env był nowy i niecommitowany)

Przegląd env vs spec (kamera / takt / API / klif / sceny) — zgodność potwierdzona. **Jedyna zmiana kodu:**

1. **`env/liquidsight_env.py`**: usunięto martwy `import task as _task` (import **całego** modułu `task`, w tym logiki okręgu `reference`/`episode_init`/`CIRCLE_*`, nigdzie nieużywany — potencjalny przeciek). Zastąpiono komentarzem; zostały **wyłącznie** jawne importy prymitywów wykonawczych. Weryfikacja `grep` przed zmianą: 0 użyć `_task`.

Nic więcej nie zmieniono. Weryfikacja z kodu:
- **Kamera** (`scene_builder.drone_camera`): `eye=pos+R@[0.10,0,0.02]`, `look=eye+R@[1,0,−0.15]`, `up=R@[0,0,1]`, `FOV 60`, `near 0.05`, `far 6.0`, `ER_TINY_RENDERER`, `shadow=1`, `lightDirection=[0.4,0.4,1.0]` — zgodne co do znaku.
- **Takt**: fizyka 240 Hz, kontrola 48 Hz, kamera co 4. tik = 12 Hz, setpoint ZOH przez 4 tiki.
- **API**: `reset(scene_seed, level)` / `step(setpoint6, want_seg)` → obs `{rgb uint8 64×64×3, kin float32 (13,), dt float32 (1,)}`, info `{success, fail_type, gt_target_pos, seg_mask na żądanie}`.
- **Klif D1b**: crash z<0.05 m, tilt>60°, geofence |xy|>2.0 lub z>2.5, kontakt; sukces = dwell na końcowym oknie `t_dwell`.

**Dry-run T5a** (scene_seed 43100, T0, stały setpoint, bez eksperta): env żyje, kształty/typy kontraktowe OK, `dt=1/12`, kamera renderuje (rgb 32–255), `seg_mask` obecna (64×64 bool). Skokowy setpoint na 1.67 m wywołał klif **tilt** po 4 tikach — **oczekiwane**; potwierdza działanie klifu i motywuje rampę eksperta (D5).

---

## 3. Ekspert privileged — strojenie (T6)

Ekspert (`expert/expert.py`, `HoverExpert`): gładki najazd `start → [target_xy, z_hover]` profilem **smoothstep** (`frozen_v1/task.py::_smoothstep`) z pełnym feedforwardem prędkości; `T_ramp = max(t_ramp_min, 1.5·dystans/v_max)`. Privileged: zna GT pozycji celu, **pikseli nie widzi**.

Strojenie na **100 epizodach T0 (sceny 43000–43099)**, próg **≥95%**:

| cfg | sukces | katastrofy | brak-dolotu/dwell |
|---|---|---|---|
| r_goal=0.25, z_hover=0.5, t_dwell=2.0, v_max=1.0, t_ramp_min=2.0 | **100/100 = 100.0%** | 0 | 0 |

**Próg osiągnięty bez rozluźniania wartości startowych D1** (0.25/0.5/2.0). Strojono jedynie potwierdzająco parametry rampy — wartości startowe (v_max=1.0, t_ramp_min=2.0) dały 100% już na pierwszym pełnym przebiegu; nie było potrzeby zmiany. Zamrożone → `config/env_f3.json`, commit `b29fe85` „F3: konfiguracja zadania zamrozona po strojeniu eksperta".

---

## 4. Smoke (T7)

### s1_env_det — determinizm środowiska (bramka STOP)

Pełny env pod ekspertem, 2 niezależne przebiegi na seed, SHA256 strumieni. Skróty = 12 znaków.

| scene_seed | poziom | tików | wynik | rgb | kin | setpoint | bit-w-bit |
|---|---|---|---|---|---|---|---|
| 43100 | T0 | 120 | success | ✓ | ✓ | ✓ | **PASS** |
| 43149 | T3 | 120 | success | ✓ | ✓ | ✓ | **PASS** |

**WYNIK: PASS** — oba strumienie wszystkich buforów identyczne bit-w-bit w obu przebiegach, oba seedy. Ekspert dolatuje także na T3 (widzi GT, nie piksele). Plik: `results/s1_env_det.json`.

### s1_expert — obwiednia eksperta T0

| poziom | sukces | katastrofy | brak-dolotu/dwell | typy porażek |
|---|---|---|---|---|
| T0 (43000–43099) | **100/100 = 100.0%** | **0** | 0 | {} |

Oczekiwane ~0 katastrof — spełnione (0). Plik: `results/s1_expert.json`.

### s1_axis_render — podgląd osi OOD

16 klatek (4 poziomy × 4 sceny `[43100, 43112, 43125, 43137]`, te same sceny na każdym poziomie, snapshot tik 40) → `results/axis_preview/<level>_<seed>.png`.

Rozdzielność poziomów (średni |Δpiksela| 0–255, dla tego samego seeda):

| seed | T0–T1 | T1–T2 | T0–T2 | T2–T3 | czerwone px T2→T3 |
|---|---|---|---|---|---|
| 43100 | 22.9 | 37.4 | 36.7 | 3.2 | 0 → 137 |
| 43112 | 25.3 | 30.3 | 33.6 | 0.0 | 0 → 0 |
| 43125 | 27.8 | 41.2 | 39.9 | 0.0 | 0 → 0 |
| 43137 | 30.5 | 41.4 | 41.6 | 5.0 | 0 → 244 |

Odczyt (potwierdzony wizualnie): **T0/T1** = rodzina A (patchwork szumu niskoczęstotliwościowego, różne seedy → różne kolory); **T2** = rodzina B (strukturalne ukośne pasy) — wyraźnie rozdzielna od A; **T3** = to samo tło B **+ czerwone dystraktory**. **T3 różni się od T2 wyłącznie dystraktorami** (D6: T3 = T2 + K=4), więc T2–T3 jest ≈0, gdy dystraktory są poza przednim FOV (43112, 43125), i widoczne, gdy wpadają w kadr (43100: 137 px, 43137: 244 px). To poprawna semantyka osi — **nie** korygowano snapshotu, by wymusić różnicę.

---

## 5. Finalne parametry zadania (zamrożone w `config/env_f3.json`)

| grupa | parametr | wartość |
|---|---|---|
| env | res | 64 |
| | r_goal | 0.25 m |
| | z_hover | 0.5 m |
| | t_dwell | 2.0 s |
| | arena_half / arena_z | 2.0 / 2.5 m (geofence 4×4×2.5) |
| | start_half / start_z | 1.5 / 0.5 m |
| | min_target_dist | 1.0 m |
| | episode_s | 10.0 s |
| takt | pyb / ctrl / cam | 240 / 48 / 12 Hz |
| ekspert | profil | smoothstep (frozen_v1/task.py) |
| | v_max / t_ramp_min | 1.0 m/s / 2.0 s |

`env/liquidsight_env.py` `DEFAULTS` są lustrem tego pliku; smoke buduje env z `config/env_f3.json`.

---

## 6. Co zostaje do I2

- Wykonanie bramki **P-SANITY** (P1/P2/P3) — ramię GRU, wg `P_SANITY.md`. **Nie ruszane w I1.**
- Kod modeli (twin D4: primary end-to-end, secondary frozen encoder) — brak w I1.
- Trening: BC + 3× DAgger, dane wyłącznie T0 (D5); naprawy tylko na nominalu.
- Pule seedów treningowych 44xxx i rezerwa 45xxx — nietknięte.

---

## 7. Rozbieżności / uwagi

- **`c1_common.py` nieskopiowany** — jedyne odstępstwo od literalnego T5, w pełni uzasadnione domiarem importów i zakazem przecieku logiki okręgu (§1). Do akceptacji człowieka: jeśli wymagane jest kopiowanie „warstwy wykonawczej jako udokumentowanej całości" niezależnie od użycia, mogę dokopiować `c1_common.py` verbatim w osobnym kroku — ale env/expert go **nie importują**.
- **torch importowany tylko tranzytywnie przez frozen** (`c1_common` go używa) — w I1 runtime nieużywany; `task.py` (jedyna kopia) torcha nie importuje.
- **Wartości D1 nie rozluźnione** — ekspert osiągnął 100% na wartościach startowych; brak pokusy strojenia progu po zobaczeniu wyniku.
- **branch:** praca na `master` (jak S0 i commity F3), zgodnie z ustaloną konwencją tego repo.

---

## STOP

Po tym raporcie i commicie końcowym `I1: srodowisko zadaniowe + ekspert + smoke` sesja I2 (bramka P-SANITY) — osobny krok, decyzja człowieka. Otwarta kwestia do decyzji: kopiować `c1_common.py` do `frozen_v1/` mimo braku importu, czy zostawić domiar `{task.py}` (rekomendacja: zostawić — mniej powierzchni, zero przecieku).
