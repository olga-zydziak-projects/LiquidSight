# RECON_DP — rekonesans fazy DP (demo-proof), read-only

**Data:** 2026-08-03. **Etap:** R. **Charakter:** wyłącznie odczyt zamrożonego repo; ZERO pomiaru,
ZERO kodu. Zasada nadrzędna: **TO NIE JEST FAZA POMIAROWA** — każda liczba na ekranie ma pochodzić
z zamrożonego raportu. Rozbieżności prompt↔repo (§F) = STOP-punkty do PRE_DP0, nie decyzje własne.

Źródła przeczytane: `RAPORT_3C_MVP.md`, `s3c1/shield.py` + `s3c1/test_shield.py`, `RAPORT_3D.md`,
`RAPORT_3B.md §4 (G2)`, `DEMO.md`, `demo/{record.py,build_player.py}`, kanał (`train/s3b2r.py
Tracker5`), env (`env/liquidsight_env.py`, `frozen_v1/task.py`, `config/env_f3.json`),
`models/policy.py` (`_scale_setpoint`), grounder (`s3b3/grounder_server.py`), `paper/NUMBERS.md`,
`paper/DRAFT_EN.md`. Solver stack sprawdzony w `.venv`.

---

## A. Automat osłony (z `s3c1/shield.py` — obiekt formalizacji P1/P5)

**Stany** (`shield.py:22`): `SEEKING`, `TRACKING`, `DWELL_GUARD`, `DONE`.
**Decyzje**: `ALLOW`, `HOLD`, `REFUSE(reason)`; **powody**: `NO_MATCH`, `STALE_AT_DWELL`,
`GEOFENCE`, `LOW_CONF_LOCK` (martwy w MVP). **Parametry** (`shield.py:29-37`, z DECYZJE_3C):
`arena_half=2.0`, `margin=0.2` → `geo_lim=1.8`; `near=0.5`; `theta_age_s=2.0`; `age_ceiling_s=6.0`;
`t_acq_s=t_hold_s=3.0`; `dt=1/12`.

**Przejścia (priorytet malejąco), z warunkami dokładnymi** (`shield.py:65-136`):

1. **Terminal latch** (`:66-68`): po REFUSE stan `DONE`, każdy kolejny tick zwraca ten sam
   REFUSE+powód (własność P1c: powód niepusty, latch trwały).
2. **R-C GEOFENCE** (`:70-78`, najwyższy priorytet, każdy stan): `max(|hover_x|,|hover_y|) > 1.8`
   (cel poza) **lub** `max(|pos_x|,|pos_y|) > 1.8` (trajektoria poza) → `REFUSE(GEOFENCE)`,
   `DONE`. **W tym samym ticku** (własność P1b).
3. **R-A/R-D NO_MATCH** (`:80-87`): `not has_lock`. Jeśli `k·dt ≥ t_acq (3.0 s)` → `REFUSE(NO_MATCH)`;
   inaczej `ALLOW`/`SEEKING`.
4. **R-B v2 admisja NA WEJŚCIU** (`:89-117`): lock aktywny. `old = (age_s > θ_age 2.0)`.
   - (a) pierwsze `dist < near (0.5)` (`:92-104`): jeśli `old` → `entry_hold_start_k=k`, `HOLD`,
     `DWELL_GUARD`; inaczej `admitted=True`, `ALLOW`, `TRACKING`. Poza martwym polem: `ALLOW`.
   - (a2) HOLD admisji (`:106-117`): świeży tick (`not old`) → `admitted`, `ALLOW`; `(k−start)·dt
     ≥ t_hold (3.0 s)` → `REFUSE(STALE_AT_DWELL)`; inaczej `HOLD`.
5. **R-B sufit twardy** (`:118-136`, po admisji): `over_ceiling = age_s > 6.0`. Pierwsze przekroczenie
   → `ceiling_hold_start_k=k`, `HOLD`; świeży (`≤6.0`) → `ALLOW` (sufit zwolniony); `(k−start)·dt ≥
   t_hold` → `REFUSE(STALE_AT_DWELL)`; inaczej `HOLD`. Poniżej sufitu: `ALLOW`/`TRACKING`.

**Księgowość** (`:139-156`): trójwynikowa SUKCES/ODMOWA/PORAŻKA; assert jednoznaczności
(`ODMOWA ⇔ terminal≠None`). **Pełne pokrycie przejść** potwierdzone testami `test_shield.py` (8/8):
no_match, geofence(cel/trajektoria), entry_fresh, entry_stale→readmit, entry_stale→timeout,
ceiling_starvation, clean_transparent. **Zgodność z RAPORT_3C_MVP:** pełna (reguły, wartości θ/T,
sufit — identyczne; RAPORT_3C §2 tabela = kod). **Rozbieżność kod↔RAPORT: BRAK.**

**Dla P1 (BMC/indukcja):** stan automatu to skończona krotka `(state, entered, admitted,
entry_hold_start_k, ceiling_hold_start_k, terminal)` + wejścia dyskretne `(has_lock, age-bucket
{<2, [2,6], >6}, dist-bucket {<0.5, ≥0.5}, geo-bucket)`. Przestrzeń mała → **indukcja/BMC domykalne**
(z3 albo jawne wyliczenie osiągalnych stanów). Własności P1a–P1d wprost mapują się na §A.1–5.

---

## B. Stałe dynamiki do dowodu geofence (P2)

Z odsyłaczami do linii:
- **Takt polityki** `DT_OBS = 1/12 s` (`env:52`); osłona sprawdza pozycję **co tik polityki 12 Hz**
  (`shield.step` per k). Kontrola wykonawcza 48 Hz, `CAM_EVERY=4` (`env:48`), setpoint ZOH przez
  4 tiki (`env:144`).
- **Ograniczenie zadanej prędkości** `VEL_LIM = 1.0 m/s` per oś (`models/policy.py:24,32`,
  `_scale_setpoint`: `vel = VEL_LIM·tanh`). **Zadana pozycja xy** `XY_LIM = 2.0 m` (`policy:22,30`)
  — **równa arena_half** (uwaga: polityka MOŻE zadać setpoint na samym ogrodzeniu; gwarancja opiera
  się na kontroli pozycji przez osłonę + margines, nie na ograniczeniu setpointu — §F-D4).
- **Ekspert v_max = 1.0 m/s** (`config/env_f3.json ekspert`, `expert.py EXPERT_DEFAULTS`).
- **Position-hold** (`shield` HOLD → harness): `applied = [pos_x, pos_y, pos_z, 0, 0, 0]`
  (`record.py:195`, `measure_s1.py:77`) — setpoint = bieżąca pozycja, prędkość zadana 0.
- **Geofence env (katastrofa)** `|pos_x|>2.0 ∨ |pos_y|>2.0 ∨ pos_z>2.5` → `"geofence"`
  (`env:188-190`, `_check_cliff`); `is_catastrophe`. Osłona wyprzedza przy 1.8 m.
- **Model hamowania:** CF2X DSL-PID (`frozen_v1/task.py:13,98`), thrust-to-weight ~2 → decel
  osiągalny ≫ wymagany. **Szkic P2 (do formalizacji, założenia jawne):** przy prędkości ≤ VEL_LIM
  i kontroli pozycji co Δt=1/12 s, przekroczenie 1.8 m jest wykrywane w ≤1 tiku; naddatek =
  `VEL_LIM·Δt + VEL_LIM²/(2A)` = `0.083 + 0.5/A`. Dla `A ≥ 4.27 m/s²` naddatek `< 0.2 m` → dron nie
  opuszcza 2.0 m. **Założenia P2 (wypisać w PRE):** (i) |prędkość fizyczna| ≤ VEL_LIM (albo jawny
  bound tracking-overshoot), (ii) decel ≥ A_min (stała z modelu CF2X), (iii) osłona aktywna (APPLIED),
  (iv) pozioma projekcja. To jest **twierdzenie o modelu**, nie o pełnym PyBullet.

---

## C. Inwentarz liczb DOZWOLONYCH na banery (z zamrożonych raportów)

Tylko poniższe wolno pokazać; każda z prowieniencją:

| liczba | źródło (repo) |
|---|---|
| desygnacja **67% / wrong-lock 10%** | `RAPORT_3B §3`, `RAPORT_3C_MVP §2` (baza nogi A 67,0/10,0) |
| próg **85/8** (zamrożony, niespełniony) | `G1_GATE.md` |
| **GT-fed 100%** (sufit wykonalności) | `RAPORT_3B §9` (`results/s3b2/ceiling.json`) |
| **G2: 80 / 66 / 44 / 30** (p0/.25/.5/.75) | `RAPORT_S3B4`, `RAPORT_3B §4` |
| **L5 −4 pp vs p0.5 −36 pp** (asymetria) | `RAPORT_S3B4` (kotwica p0=80) |
| **noga B: SUKCES 15 / ODMOWA 22 / PORAŻKA 13; 16/28 porażek→abstynencja** | `RAPORT_3C_MVP §5` |
| **geofence 25/25** | `RAPORT_3C_MVP §6` |
| **obiekt-nieobecny limit 6/25** (uczciwie, nie ukryty) | `RAPORT_3C_MVP §6` |
| **werdykt 3d: inwersja, Δ=−5,8, NEGATYWNY** | `RAPORT_3D §2` |
| v1.0: **klif ~102 → ~779 ms**, **CfC-32 lata 500–1300 ms**, Δt **zero przewagi**, **τ≈35 ms** | `paper/NUMBERS.md:277-279`, `paper/DRAFT_EN.md:128` (źródła `RD`/`C01`, repo `liquidflight`) |

**UWAGA prowieniencyjna (§F-D2):** „AutoNCP-20 **317** param" oraz „wynik P3" **nie są** liczbą-banerem
z raportu — to **artefakt dowodowy do wygenerowania** w module P3 (param count = fakt strukturalny
weryfikowalny przez zbudowanie sieci; bound P3 = wynik solvera). Traktować osobno od liczb §C.

---

## D. Reużywalność demo v1

| komponent v1 | werdykt DP |
|---|---|
| `demo/record.py` (pętla epizodu, `render_3d`, `save_jpg`, `saliency_overlay`, `draw_bbox256`, `burst_window`, integracja Shield, `trace.jsonl`, audyt GT) | **REUŻYĆ** jako baza recordera DP; dopisać: tryb APPLIED domyślny, licznik prób re-record, konsola komend/parser, rekordy podpisane HMAC |
| `demo/build_player.py` (single-file HTML EN, base64 inline JPEG, banery z prowieniencją, sha256, panel osłony) | **REUŻYĆ** jako baza playera DP; dopisać: dwie kolumny PROVED/MEASURED, panel certyfikatów, konsola NL, plansza mapy z komórką 3d |
| `demo/manifest.json` (pula/seed/maska/wynik per akt) | **REUŻYĆ** schemat; dodać licznik prób re-record + tryb osłony + hash certyfikatów |
| scenariusz `DEMO.md` (4 akty) | **BAZA**, ale DP ma 5 aktów + warstwa dowodowa; NIE modyfikować DEMO.md (v1 zamrożony) |

**Tryb osłony w nagraniach — rozstrzygnięcie (rekomendacja):** v1 nagrywał akt1 i akt3 w
**`shadow`** (`record.py:48,52`) — osłona liczona, nie stosowana (problem ekranowy v1: panel osłony
pokazuje decyzje, których system nie wykonuje). **DP: tryb APPLIED wszędzie, gdzie panel osłony jest
na ekranie**, z bounded re-record (≤3 próby/scenę). Panel osłony pojawia się dopiero od aktu, w
którym działa w APPLIED — **konstrukcyjne rozwiązanie problemu shadow**. Ryzyko: konkretny seed dema
może zmienić wynik pod APPLIED (np. akt „łącze" pod sufitem 6 s → HOLD/REFUSE zamiast SUKCES);
bounded re-record, a po limicie scena wypada (nie zmiękczamy reguł) — §F-D1.

---

## E. Dostępność ProofGate / solverów (z `.venv`)

- **z3: NIEOBECNY**, ale **INSTALOWALNY** (`pip index versions z3-solver` → 5.0.0.0 dostępny; indeks
  osiągalny). → P1/P2/P5 realizowalne na z3.
- **onnx / CROWN / auto_LiRPA / Marabou: NIEOBECNE.** P3 (weryfikacja sieci) nie ma gotowego stacku.
- **hmac + hashlib: stdlib OBECNE** → rekordy podpisane (P4) i certyfikaty-hash bez zależności.
- **ProofGate kernel/packi: BRAK w repo** (grep zero); brak pakietu PCDL.

**Eskalacja (do PRE §9, ryzyko 2):**
- **P1/P2/P5 solver:** OPCJA A [rekomendacja] — `pip install z3-solver` (pin w PRE), BMC/indukcja na
  z3; OPCJA B — czysto-Pythonowy BMC (automat skończony, jawne wyliczenie osiągalnych stanów) +
  arytmetyka interwałowa dla P2, zero zależności, w pełni odtwarzalny. Rekomendacja: **A dla P1/P5**
  (standard, SMT), **A lub B dla P2** (interwały wystarczą; z3 jako weryfikator wtórny).
- **P3 sieci:** OPCJA A — `pip install` onnx + auto_LiRPA (CROWN), pełna weryfikacja; OPCJA B
  [rekomendacja MVP] — **czysto-numpy IBP** (interval bound propagation) przez jeden krok sieci
  (AutoNCP-20 317 param — minimum ratyfikowalne §3 P3), sound output-range, zero ciężkich zależności;
  gc5 (28,8k, GRU rekurencyjny) jako rozszerzenie. Rekomendacja: **B, jedna sieć (AutoNCP-20)**.
- **PCDL / ProofGate:** brak kernela → **lokalny minimalny moduł zgodny z PCDL** (schemat rekordu
  decyzji + podpis HMAC, `proofs/`), **dług integracyjny nazwany** w PRE (wariant integracji z
  ProofGate jako przyszły mandat). hmac/hashlib stdlib wystarczą.

---

## F. Rozbieżności prompt ↔ repo (STOP-punkty do PRE_DP0)

**F-D1 [tryb osłony w nagraniach].** v1 nagrywał akt1/akt3 w `shadow` (`record.py:48,52`) — dokładnie
„problem shadow-mode" z promptu. DP mandatuje APPLIED z bounded re-record. Ryzyko: seed dema może
flipnąć wynik pod APPLIED (osłona nie jest bit-transparentna: clean 67→63 zmierzone). Rekomendacja:
APPLIED + ≤3 próby/scenę; scena, która flipnie i nie wraca, wypada z aktu (reguł nie zmiękczamy).
Do ratyfikacji: które akty wymagają re-record vs pozostają clean-transparentne.

**F-D2 [AutoNCP-20 317 / P3 to artefakt, nie banner].** Prompt §c wpisuje „AutoNCP-20 317 param
(z wynikiem P3)" na eksponat v1.0. 317 nie występuje w raportach jako liczba zmierzona; to param-count
sieci **budowanej pod P3** (fakt strukturalny) + bound **generowany przez solver**. Rozdzielić:
liczby §C (cytowane) vs artefakty dowodowe (generowane, z hashem certyfikatu). Do ratyfikacji: czy
AutoNCP-20 jest budowany w DP (P3), czy pochodzi z liquidflight (jeśli tak — cytat źródła).

**F-D3 [ProofGate nieosiągalny].** Brak z3/onnx/CROWN/PCDL w repo. z3 instalowalny; reszta wymaga
instalacji albo wariantu minimalnego (§E). Do ratyfikacji: instalacja pakietów (z3 + ew. auto_LiRPA)
vs czysto-Pythonowy/numpy stack + lokalny PCDL z długiem integracyjnym.

**F-D4 [XY_LIM = arena_half].** `XY_LIM=2.0` = `arena_half` (`policy:22`): polityka może zadać
setpoint na ogrodzeniu, więc P2 NIE może opierać się na ograniczeniu setpointu — tylko na kontroli
pozycji przez osłonę (1.8 m) + margines 0.2 m + hamowanie. Założenia P2 (prędkość, decel) muszą być
jawne (§B). Nie sprzeczność, lecz warunek poprawności brzmienia P2.

**F-D5 [gramatyka ↔ grounder].** Grounder parsuje komendę naiwnie: `phrase = command.replace(
"fly to the ", "")` → `set_classes([phrase])` (`grounder_server.py:40-41`). Parser DP (§4) musi
produkować **dokładnie** ten format frazy dla zamrożonego groundera; alias-mapping (§5, „crimson"→
„red") wykonuje się PRZED budową frazy. Nie konflikt, lecz kontrakt do zapisania.

**F-D6 [DEMO.md v1 zamrożony].** DP ma 5 aktów + warstwę dowodową; DEMO.md (4 akty) pozostaje
nietknięty jako v1. DP pisze nowy scenariusz w PRE_DP0, nie edytuje DEMO.md.

Żadna z F-D1…F-D6 nie podważa przesłanki fazy (system frozen spójny; osłona = czysty automat gotów do
formalizacji; stałe dynamiki obecne; liczby-banery mają źródła). Wszystkie idą do PRE_DP0 jako
[PROPOZYCJA]/eskalacje do ratyfikacji — bez decyzji własnej.

---

## G. Higiena
- Zamrożone (polityka gc5, osłona v2, kanał, env, grounder, sweep 46600–46649, raporty, DEMO.md,
  paper/) — wyłącznie odczyt.
- DP nie tworzy nowych LICZB pomiarowych; nagrania to ilustracje ze zmierzonych konfiguracji
  (bounded re-record, licznik prób).
- Dowody odtwarzalne: `python -m proofs.verify` od zera vs certyfikat-hash w repo (zasada 3).
- UNSAT/UNPROVEN raportowane jawnie, brzmienie własności nieosłabiane po cichu (zasada 6).

*Etap R zamknięty. Następny: `PRE_DP0.md` (dokument zamrożony; kończy się STOP na ratyfikację).*
