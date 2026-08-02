# RECON_3D — rekonesans fazy 3d (read-only, ZERO kodu, ZERO pomiaru)

**Data:** 2026-08-02. **Etap:** R (rekonesans). **Charakter:** wyłącznie odczyt zamrożonego
repo. Nie napisano żadnego kodu, nie uruchomiono żadnego biegu (nawet smoke). Wynik R zasila
`PRE_3D0.md`; wszystkie rozbieżności prompt↔repo (§D) są **STOP-punktami do ratyfikacji w PRE**,
nie decyzjami własnymi. Zasada: MIERZĘ = RAPORTUJE.

Źródła przeczytane w kolejności promptu: `RAPORT_3B.md`, `RAPORT_S3B4.md`, `RAPORT_3C_MVP.md`,
`s3c1/shield.py`, `s3c1/measure_s1.py`, `ANEKS_3B_KANAL.md`, kanał celu w env/train, `ANEKS_3_KONSTRUKCJA_RDZENI.md`,
`ANEKS_4_PROCEDURA_TRENINGU.md`, `DECYZJE_3B.md`, `DECYZJE_3C.md`, `ANEKS_3C1_SEMANTYKA.md`,
`G2_GATE.md`, `F3_GATE.md`, `MANIFEST_F3.json`.

---

## A. Format i punkt wpięcia kanału celu w wejście polityki

### A.1 Kontrakt kanału (5-dim, FROZEN od S3b2-R)
Kanał = **5 wymiarów** `(cx, cy, w, h, age_n)`, znormalizowany; **conf USUNIĘTY z wejścia**
(ANEKS-3B; `models/policy_gc5.py:18` `TARGET_DIM=5`). Producent = `Tracker5` (`train/s3b2r.py:50-79`):

- **cx,cy,w,h** — box w kadrze 256², znormalizowany /256 (`train/s3b2r.py:69-70`).
- **age_n** = `min((k − k_src)·DT / AGE_MAX, 1.0)`, `DT = 1/12 s`, `AGE_MAX = 8.0 s`
  (`train/s3b2r.py:35,71`). Prawdziwy age w sekundach = `age_n · AGE_MAX`.
- **Dostarczenie (L_deliver):** źródło z ticku `k_src` staje się widoczne dopiero przy
  `k ≥ k_src + K_DEL`, `K_DEL = ceil(0.10/DT) = 2` (`train/s3b2r.py:36,64`).
- **ZOH:** przy braku nowego dostarczenia trzyma **najświeższe** dostarczone źródło
  `max(deliv, key=k_src)` (`train/s3b2r.py:68`).
- **No-lock:** brak jakiegokolwiek dostarczenia → wektor **`[0,0,0,0,1.0]`** (age_n=1.0 = sufit
  8 s = sygnatura braku locka, nie stary lock; `train/s3b2r.py:66-67`, DECYZJE_3B D3).
- **Kadencja:** grounder odpytywany **co 12. tick polityki** (`TICK_EVERY=12`,
  `s3b3/live_grounder.py:27`) → dostarczenia **~1 Hz**, podczas gdy polityka tyka **12 Hz**.
  Między dostarczeniami kanał jest **zamrożony (ZOH)** — to jest przestrzeń, w której mikro-filtr 3d
  ma interpolować/ekstrapolować.

### A.2 Punkt wpięcia (drop-in)
Polityka konsumuje kanał jako **ostatnie 5 z 83 wymiarów** wejścia rdzenia:
`x = cat([feat64, kin13, dt1, target5])` (`models/policy_gc5.py:38-39`, `IN_DIM=83` :19).
Ścieżka runtime w pętli ewaluacji (identyczna w `s3b4.py` i `measure_s1.py`):

```
target5 = tr.vector(k)                       # train/s3b4.py:78 ; s3c1/measure_s1.py:65
action, h = model.act(obs, target5, h, dev)  # train/s3b4.py:79 ; s3c1/measure_s1.py:66
```

**Wniosek dla 3d:** mikro-filtr jest czystym drop-inem **na `target5` tuż przed `model.act`**.
Zgodnie z PRE §3: filtr podmienia **`target5[0:4]` (cx,cy,w,h)** wygładzoną estymatą, a
**`target5[4]` (age_n) pozostaje NIETKNIĘTE** — osłona/semantyka age liczą prawdziwy wiek
(`s3c1/measure_s1.py:72` `age_s = target5[4]·AGE_MAX`). Przy no-lock (`[0,0,0,0,1.0]`) filtr nie ma
czego wygładzać — pass-through jest naturalną semantyką (decyzja do zapisania w PRE).

### A.3 Sygnały GT dostępne z env (do etykiet filtra) — DWA źródła
- **`info["gt_bbox_256"]`** — box celu w kadrze 256², **tylko na tickach semantycznych** (1 Hz) i
  **`None` gdy cel poza kadrem** (`env/liquidsight_env.py:227-228,253`; brama `if sem`). To dokładnie
  przestrzeń wyjścia filtra, ale rzadka i **znika w martwym polu** — czyli tam, gdzie leży problem
  (ściana B4).
- **`info["gt_target_pos"]`** — pozycja świata celu, **KAŻDY tick (12 Hz), zawsze obecna**, także
  poza kadrem (`env/liquidsight_env.py:246`). Gęsty sygnał, ale wymaga back-projekcji do (cx,cy,w,h),
  aby trafić w przestrzeń wejścia polityki.
- Gęsty box 256² per tick 12 Hz jest **osiągalny read-only** przez `drone_camera(...want_seg=True)` +
  `bbox_from_mask` (wzorzec `train/s3b4.py:102-103`, `s3b3/live_grounder.py:116-124`) — bez dotykania
  frozen; to procedura zbierania danych, nie zmiana env.

Ta dwoistość (image-box rzadki+znikający vs world-pos gęsty) jest **kluczową decyzją PRE §3/§4**
(przestrzeń filtra i źródło etykiety) — patrz **D-1**.

---

## B. Inwentarz pul seedów/masek + propozycja nowych (niekolidujących) zakresów 3d

### B.1 Pule ZAJĘTE (zweryfikowane grep-em po kodzie)
| pula | zakres | rola | źródło |
|---|---|---|---|
| 3a nominal | 43000–43099 | precondition F3 | F3_GATE §2; eval/psanity.py |
| 3a sweep | 43100–43149 | sweep T2b | F3_GATE §2 |
| 3a BC | 44000–44299 | BC twin | F3_GATE §2 |
| 3a DAgger | 44300–44599 | DAgger twin (3 rundy) | F3_GATE §2 |
| 3a init | 45010–45019 | init+shuffle seedy (n=10) | F3_GATE §2; train/baseline_gru.py |
| scene-builder wewn. | 41000–41520, 42000–42020 | wewn. generacja sceny | env/scene_builder.py:36-39 |
| 3b BC train | 46000–46270 | BC polityki S3b2-R | train/s3b2r.py:40 |
| 3b BC val | 46270–46300 | walidacja BC | train/s3b2r.py:41 |
| 3b DAgger r1/r2/r3 | 46300–46399 / 46400–46499 / 47000–47099 | rollouty DAgger | train/s3b2r.py:42 |
| 3b DAgger r4 (F3) | 47100–47199 | +1 runda (R4/R5) | train/s3b2r{3,4,5}.py |
| 3b hover-rich BC | 47200–47299 | R6 (szkodliwe) | train/s3b2r6.py:32 |
| 3b kurikulum GT-fed | 47300–47399 | R7 (neutralne) | train/s3b2r7.py:61 |
| **3b eval** | **46500–46599** | **ewaluacja G1/G2/S1 — NIETYKALNE** | DECYZJE_3B D8; s3b2r.py:43 |
| 3b G2 probe (T1) | 46550–46569 | sonda rozdzielczości (⊂ eval) | train/s3b4.py:193 |
| **3b sweep G1** | **46600–46649** | **CZYSTY — nietykalny (próg 85/8)** | DECYZJE_3B D8; G2_GATE |
| 3b sweep preview | 46600–46699 | smoke render 2/komórkę | smoke/s3b_axis_preview.py:15 |
| 3b init/split | 45020 (init), 45021 (split selekcji) | seed treningu polityki | s3b2r.py:39; s3b2r5.py:32 |
| **G2 maski** | **45100–45107, 45150–45151** | oś G2 (Bernoulli/burst/probe) | G2_GATE; train/s3b4.py:43-45 |
| S3b0 sondy | 46900–46999 | grounder offline (zużyte) | s3b0/*.py |
| **3c pułapki S2** | **47400–47449** | absent 47400–47424 / geofence 47425–47449 | DECYZJE_3C D5; measure_s2.py |
| stary BC/DAgger | 45001 | train_bc/dagger (3a) | train/train_bc.py:25 |

Mapa masek G2 (pula 45100+): p0=45100, p0.25=45101, **p0.50=45102**, p0.75=45103, L2=45104,
**L5=45105**, p0.90=45106, p0.10=45107, probe_p0.50=45150, probe_L5=45151 (`train/s3b4.py:43-45`).
Maska = `np.random.default_rng([mask_seed, seed_epizodu])` (`train/s3b4.py:72`; `measure_s1.py:53`).

### B.2 Pule WOLNE zweryfikowane
- **48000–49999** — **całkowicie dziewicze** (grep `4[89][0-9]{3}` = 0 trafień w całym repo).
- 46700–46899 — wolne, ale **46650–46699 dotknięte** smoke-preview (`s3b_axis_preview.py:15`,
  `range(46600,46700)`), tuż przy świętym sweepie → **odradzam** (bufor wokół 46600–46649).
- 45022–45039, 45040–45099, 45108–45149, 45152–45199, 45200–45999 — wolne w rodzinie 45xxx.

### B.3 PROPOZYCJA pul 3d (do ratyfikacji w PRE; wszystkie z B.2, rozłączne z zajętymi)
| pula 3d | proponowany zakres | rola | uzasadnienie rozłączności |
|---|---|---|---|
| **3d filtr-train sceny** | **48000–48299** (300 ep) | offline nadzorowane uczenie filtrów A2/A3 | 48xxx dziewicze; ≥ liczności BC 3b (300) |
| **3d filtr-val sceny** | **48300–48399** (100 ep) | wstrzymany zbiór: precondition P-3D + val | rozłączny z train; dziewiczy |
| **3d filtr-train maski** | **45200–45209** (rodzina 45100+, DISJOINT) | degradacja w treningu filtrów (ta sama rodzina co pomiar, inne seedy) | poza 45100–45107/45150–45151; PRE §4 wymóg „rozłączne seedy masek" |
| **3d filtr init/shuffle** | **45040–45044** (5 seedów, PAROWANE A2↔A3) | 5 seedów treningu per ramię uczone | analog par. F3 (45010–45019 parowane po indeksie) |
| pomiar sceny (PRESCRIBED, nie nowe) | **46500–46599** eval | ewaluacja zamkniętej pętli 3 nogi | prompt §6; NIE zmieniamy puli |
| pomiar maski (PRESCRIBED) | p0.5=**45102**, L5=**45105** (clean=brak) | maski nóg dropout, rodzina G2 | prompt §6 „te same co G2" |

Uwaga: pomiar **czyta** pulę eval 46500–46599 (read-only, jak G2/S1) — to nie jest „dotknięcie"
w sensie treningowym; sweep 46600–46649 **nie jest ruszany**.

---

## C. Zamrożone artefakty, których 3d dotyka WYŁĄCZNIE w trybie odczytu
- **Polityka:** `ckpt/s3b2r/policy_gc5.pt` (`models/policy_gc5.py`) — load+eval, zero zmian wag.
- **Kanał celu:** `Tracker5` (`train/s3b2r.py:50-79`), kontrakt D3 (DECYZJE_3B D3) — filtr wpina się
  **za** `tr.vector(k)`, nie modyfikuje trackera.
- **Env:** `env/liquidsight_env.py`, `env/scene_attr.py`, `env/scene_builder.py`, `frozen_v1/task.py`
  — reset/step/`gt_bbox_256`/`gt_target_pos`/`is_catastrophe`, wyłącznie odczyt.
- **Percepcja:** serwer YOLO-World `.venv_s3b0` + `s3b3/live_grounder.py`, `s3b3/grounder_server.py`
  — odpytywany jak w G2/S1, konfiguracja niezmieniona.
- **Osłona:** `s3c1/shield.py` — **niewpięta** w pomiar 3d (§6: harness BEZ osłony); czytana jako
  wzorzec księgowości/harnessu.
- **Recepta rdzeni/treningu (dla A3 CfC):** `models/core_cfc.py`, ANEKS-3 (CfCCell+backbone,
  ts w SEKUNDACH, krokowanie ręczne — obejście buga `ncps 1.0.1` timespans@batch>1;
  `ANEKS_3_KONSTRUKCJA_RDZENI.md:18-23`), ANEKS-4 (procedura). Recepta czytana, przenoszona do
  mikro-rdzenia ≤4000 param — nie modyfikuje rdzenia polityki.
- **Harness pomiarowy:** `s3c1/measure_s1.py` + `train/s3b4.py` — wzorce parowanego biegu,
  mapowania masek, księgowania; kopiowane/adaptowane do `s3d/`, oryginały nietknięte.
- **Bramki/decyzje:** G2_GATE, F3_GATE (formuła pooled_std §5), DECYZJE_3B/3C — odczyt.

---

## D. Rozbieżności prompt ↔ repo (STOP-punkty do wyjaśnienia w PRE_3D0)

**D-1 [KLUCZOWA] Przestrzeń filtra i źródło etykiety.** PRE §3 zakłada wyjście filtra w przestrzeni
**obrazu** (cx,cy,w,h), a §4 etykietę = „GT boxa celu". Ale RAPORT_3B (mandaty przyszłe,
`RAPORT_3B.md:250-252`) rekomenduje filtr w **przestrzeni ŚWIATA** (po back-projekcji) — właśnie
dlatego, że pixel-space zawiódł (F-3b-2, IoU≈0 przy dolocie). Repo daje oba sygnały (A.3):
`gt_bbox_256` (image, 1 Hz, `None` poza kadrem) i `gt_target_pos` (świat, 12 Hz, zawsze). **Decyzja
do ratyfikacji:** (a) filtr image-space (prosty drop-in, ale etykieta znika dokładnie w martwym polu
= tam, gdzie leży wartość), vs (b) filtr world-space + back-projekcja do (cx,cy,w,h) (gęsta etykieta,
ale dokłada komponent projekcji). Rekomendacja R: przedstawić w PRE oba warianty; skłon ku image-space
dla parytetu drop-inu z §3, z jawnym zapisem ograniczenia off-frame.

**D-2 Kadencja etykiety GT.** §4 „etykieta ... logowana per tick", ale env renderuje `gt_bbox_256`
tylko na tickach semantycznych (1 Hz; `env:253` brama `if sem`). Etykieta 12 Hz wymaga, by kolektor
offline sam renderował seg256 per tick (read-only, wzorzec `s3b4.py:102`) — to procedura zbierania
danych, nie zmiana frozen. Poza kadrem box = `None` → precondition RMSE liczone tylko na tickach z
istniejącą etykietą (albo world-pos wg D-1). Do zapisania jawnie w PRE §4/§5.

**D-3 N na nogę vs kotwica G2.** §6 chce **N=100/nogę** ORAZ „maski 45100+ te same co G2 dla
porównywalności z krzywą 80/66/44/30". Krzywa G2 mierzona na **50 ep** (46500–46549, maski 45102/45105);
pula eval ma 100 (46500–46599). Kotwicą werdyktu 3d jest i tak **parowane A0** w biegu (nie liczby G2 —
te są ~13 pp optymistyczne vs populacja, `RAPORT_S3B4.md:17-28`). **Do ratyfikacji:** (a) N=100 na
46500–46599, A0 jako kotwica parowana, G2 tylko referencja zewnętrzna [rekomendacja]; vs (b) N=50 na
46500–46549 dla dosłownego dopasowania do G2. n zamrażamy w PRE przed pomiarem.

**D-4 Maski nóg dropout — konkretne seedy.** `measure_s1.py:35` nogi B używa 45102 (p0.5). Dla nogi
burst L5 należy użyć **45105** (mapa G2, `s3b4.py:44`), a nie 45102. Zapisać jawnie w PRE §6, by
maski były z rodziny G2 (p0.5→45102, L5→45105, clean→brak maski).

**D-5 Harness „BEZ osłony" a `measure_s1`.** `measure_s1.py` jest sprzężony z `Shield` i księgowością
trójwynikową (SUKCES/ODMOWA/PORAŻKA). §6 3d żąda harnessu **bez osłony**, metryka pierwotna =
**czysty sukces env** (jak `s3b4.py:120` `info["success"]`). Nowy harness `s3d/` = szkielet z
`measure_s1` (parowanie, maski, pętla) **minus Shield**, plus drop-in filtra na `target5`. To budowa
nowego kodu w `s3d/`, nie zmiana frozen — nie jest sprzecznością, tylko notą projektową do PRE.

**D-6 pooled_std — formuła jawna.** F3-GATE §5 (`F3_GATE.md:55`): `pooled_std =
sqrt((sd_s(arm1)² + sd_s(arm2)²)/2)`, sd **po seedach** (rozrzut populacyjny, nie SEM). Werdykt 3d
(PRE §6) używa ramion **uczonych** A2 (GRU) i A3 (CfC): `pooled_std = sqrt((sd_s(A2)² + sd_s(A3)²)/2)`
po 5 seedach filtra. Wpisać dosłownie w PRE §6 (prompt to nakazuje).

Żadna z D-1…D-6 nie podważa przesłanki fazy (stan frozen jest spójny z promptem: polityka 5-dim,
kanał ZOH 1 Hz vs tick 12 Hz, wpięcie za `tr.vector`, pule rozłączne dostępne). Wszystkie idą do
`PRE_3D0.md` jako [PROPOZYCJA]/noty do ratyfikacji — bez decyzji własnej.

---

## E. Determinizm / higiena (pod PRE i M)
- Seedy jawne (B.3), maski `default_rng([mask_seed, ep])` (rodzina G2), init parowane A2↔A3.
- Artefakty 3d: kod `s3d/`, JSON `results/s3d/` z **sha256**, raport `RAPORT_3D.md` krosowany z JSON.
- WSL/GPU: po każdym biegu weryfikacja artefaktów (exit 144 / dxg ioctl −22 → retry, nie kontynuacja).
- Sweep G1 46600–46649 i próg 85/8 — **nietknięte**; eval 46500–46599 czytane read-only jak w G2/S1.

*Etap R zamknięty. Następny krok: `PRE_3D0.md` (dokument zamrożony, kończy się STOP na ratyfikację).*
