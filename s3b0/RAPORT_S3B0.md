# RAPORT_S3B0 — smoke groundera OFFLINE + throughput 256² (faza 3b)

**Data:** 2026-07-26. **Sesja:** S3b0 (PRE_3B0 D1–D8). **Zakres:** materiał do decyzji
**D1** (wybór groundera) i kalibracji **D2** (kamera 256² @1 Hz). **ZERO lotu, ZERO
treningu, ZERO zmian w `env/`.** MIERZĘ = RAPORTUJĘ. Decyzja D1 należy do Olgi — sesja
rekomenduje.

## Nienaruszalność (dotrzymana)
- Zapisy wyłącznie w `s3b0/` i `results/s3b0/`. `env/`, `expert/`, `models/`, `paper/`,
  `frozen_v1/` — nietknięte (tylko odczyt wzorców; nic nie importowane z `env/`).
- Osobny venv `s3b0/.venv_s3b0` (uv). Główny `.venv` treningowy nieużywany.
  Zależności: `s3b0/requirements_s3b0.txt` (torch 2.11.0+cu128, transformers 5.14.1,
  ultralytics 8.4.106, pybullet 3.2.7 — jak główny venv).
- Seedy scen **46900–46999** (A: 46900–46947, B: 46950–46957). Pule 46000–46649 nietknięte.
- Tuning promptów/progów **tylko na dev**; configy zamrożone w `results/s3b0/configs/`;
  liczby z **eval**.
- Latencja/VRAM przy wolnym GPU (`nvidia-smi` przed każdym kandydatem: 0 MiB).

## Instrument (T1–T2): zbiór atrybutowy
Generator `s3b0/scene_gen.py` (standalone, wzorzec `s0_scene_seg.py`): podłoga + K obiektów
z palety **kolor {red, green, blue} × kształt {box, sphere, cylinder}**; DOKŁADNIE jeden
obiekt pasuje do komendy `"fly to the {color} {shape}"`. Poziomy: **A0** (kolor wskazanego
unikalny), **A1** (kolor współdzielony ≥1 innym; kształt rozstrzyga). Kamera 256² wg ANEKS-1
(pitch −22.3°, FOV 60, TinyRenderer, shadow=1, light [0.4,0.4,1.0]), na osi podejścia (+x)
na dystansach **{2.0, 1.4, 0.9, 0.5} m**. GT: bbox z maski segmentacji per obiekt.

- **Wariant A (eval główny):** K∈{3,5,8} × A∈{A0,A1} × 8 seedów × 4 dyst = **192 klatki**;
  podłoga neutralna szara. **Split:** dev = 2 seedy/komórkę (**48 klatek**), eval (**144**).
- **Wariant B (informacyjny):** 8 scen × 4 dyst = **32 klatki**, podłoga teksturowana rodzina A.
- **Sanity:** wskazany widoczny @d=2.0 w **48/48** scenach. Frakcja widocznych obiektów per
  dystans (A): d2.0=1.00, d1.4=1.00, d0.9=0.96, d0.5=0.73 (peryferyjne uciekają z kadru przy
  zbliżeniu — GT to odnotowuje; martwe pole d<0.35 nie występuje).
- Determinizm: 2× ten sam seed → identyczny hash RGB.

## Kandydaci D1 (T3) — EVAL (144 klatki), IoU≥0.5, próg zamrożony na dev

| kandydat | model | prec@1 | A0 | A1 | wrong-obj | no-det | other-miss | latencja p95 | VRAM | Wariant B prec@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| **K2 OWLv2** | google/owlv2-base-patch16-ensemble | **0.958** | 0.986 | 0.931 | 0.042 | 0.000 | 0.000 | 642 ms | 780 MiB | 1.00 |
| **K1 YOLO-World** | yolov8s-worldv2 (ultralytics) | 0.868 | 0.875 | 0.861 | 0.083 | 0.035 | 0.014 | **26 ms** | **710 MiB** | 0.938 |
| **K3 LFM2.5-VL** | LiquidAI/LFM2.5-VL-450M | 0.139 | 0.125 | 0.153 | 0.007 | 0.000 | 0.854 | 336 ms | 897 MiB | 0.25 |

Latencja: batch=1, warmup 10, 100 klatek, GPU wolne. VRAM = `torch.cuda.max_memory_allocated`.
**DNF: brak** (wszyscy trzej się uruchomili).

**Rozbicie per dystans (prec@1):**

| kandydat | d=2.0 | d=1.4 | d=0.9 | d=0.5 |
|---|---|---|---|---|
| K2 OWLv2 | 0.944 | 0.972 | 1.000 | 0.917 |
| K1 YOLO-World | 0.722 | 0.972 | 0.917 | 0.861 |
| K3 LFM2.5-VL | 0.000 | 0.056 | 0.500 | 0.000 |

**Rozbicie per K (prec@1):**

| kandydat | K=3 | K=5 | K=8 |
|---|---|---|---|
| K2 OWLv2 | 1.000 | 0.979 | 0.896 |
| K1 YOLO-World | 0.896 | 0.854 | 0.854 |
| K3 LFM2.5-VL | 0.208 | 0.125 | 0.083 |

**Interpretacja.**
- **K2 OWLv2** — najwyższa precyzja, **zero no-detection**, degradacja łagodna z K (0.90 @K=8)
  i z dystansem (najsłabszy narożnik d=0.5 = 0.92). A1 (współdzielony kolor) kosztuje ~5–6 pp
  vs A0 — atrybut kształtu rozróżniany dobrze. Cena: latencja p95 **642 ms** (wejście skalowane
  do 960²).
- **K1 YOLO-World** — solidna precyzja (0.87), **25× szybszy** (26 ms) i najmniejszy VRAM.
  Słaby narożnik: **d=2.0 = 0.72** (mały cel daleko) i wyższy wrong-object (0.083 — myli obiekt
  współdzielący kolor w A1). no-detection 0.035.
- **K3 LFM2.5-VL** — model **produkuje** boxy (0 no-detection), ale **lokalizuje zbyt zgrubnie**
  dla IoU≥0.5: dominuje other-miss 0.854; jedyny sensowny narożnik d=0.9 (0.50). Format wyjścia:
  bbox **znormalizowany [0,1]** `[x0,y0,x1,y1]` (potwierdzony na dev; prompt „shikra" wybrany na
  dev, dev prec@1 0.21 > where 0.17 > locate 0.19→0.19). Uwaga: literalny id **`LiquidAI/
  LFM2.5-VL-450M` istnieje** na HF (fallback do LFM2-VL nie był potrzebny). Wynik = zmierzona
  granica jakości lokalizacji tego 450M VLM na drobnych obiektach, nie DNF.

**Zamrożone configi** (`results/s3b0/configs/`): K1 `set_classes=["{color} {shape}"]`, próg conf 0.0
(top-1); K2 query `"{color} {shape}"`, próg score 0.0 (top-1); K3 prompt „shikra", próg 0.0.
Wszystkie: top-1 box, próg 0.0 wybrany na dev (usuwanie predykcji progiem nie poprawiało dev).

## Wariant B (informacyjny, podłoga teksturowana rodzina A) — sama prec@1
K2 = **1.00**, K1 = **0.938**, K3 = **0.25** (n=32). Tekstura tła rodziny A **nie pogorszyła**
K1/K2 względem szarej podłogi (małe n; sygnał: grounder odporny na teksturę tła w tym reżimie).

## Throughput renderu (T4) — czysty pybullet, 20 s @48 Hz kontroli (960 tików)

| konfiguracja | tik/s | x-realtime | narzut vs baza |
|---|---|---|---|
| baza: 64² @12 Hz | 2711 | 56.5× | 1.00× |
| **dual: 64² @12 Hz + 256² @1 Hz** | 1197 | **24.9×** | **2.27×** |
| awaryjna: 64² @12 Hz + 224² @0.5 Hz | 1788 | 37.3× | 1.52× |

Render 256² @1 Hz podwaja (≈2.27×) czas ściany renderu, ale pipeline nadal biegnie **24.9×
szybciej niż realtime** — z dużym zapasem. (Pojedyncza klatka 256² = 16× pikseli 64²; 20 klatek
256² ≈ podwaja koszt vs 240 klatek 64².)

## REKOMENDACJA D1
**Prymarnie: K2 OWLv2** (precyzja-first). Uzasadnienie:
- Najwyższa **designation-precision@1 = 0.958** (A0 0.986), **0 no-detection**, najniższy
  wrong-object przy skali (K=8: 0.90), najlepsza odporność na dystans.
- Latencja p95 **642 ms** mieści się w budżecie **1 Hz** (grounder wołany ≤1×/s wg D2, próg 1 s) —
  z zapasem 36%. VRAM 780 MiB — nieproblematyczne.
- **Fallback low-latency: K1 YOLO-World** — jeśli integracja wymaga groundingu <100 ms lub
  częstotliwości >1 Hz (albo równoległości z pętlą 48 Hz bez blokowania), K1 daje 26 ms p95 i
  710 MiB kosztem ~9 pp precyzji i słabszego d=2.0. Rozsądny kompromis, gdy latencja krytyczna.
- **K3 LFM2.5-VL: nie rekomendowany** jako grounder bbox w tym reżimie — precyzja 0.139 zbyt
  niska dla desygnacji IoU≥0.5 (lokalizacja zgrubna). Ewentualnie do dalszego zbadania z
  natywnym formatem/promptem grounding modelu, poza budżetem smoke.

Decyzja końcowa (precyzja vs latencja vs VRAM) — Olga.

## Kalibracja D2
**256² @1 Hz MIEŚCI SIĘ** — narzut 2.27× nad bazą, ale 24.9× realtime (>> 1×). Rekomendacja:
**256² @1 Hz** bez potrzeby degradacji. Awaryjnie (gdyby żywy pipeline z groundera K2 + trening
obciążył GPU/CPU): **224² @0.5 Hz** (narzut 1.52×, 37.3× realtime). Latencja groundera (K2 642 ms
p95, K1 26 ms) mieści się w oknie 1 Hz.

## Galeria
`results/s3b0/gallery/` — 16 klatek eval (mix K/A/dystans), box GT (zielony) + predykcja
najlepszego kandydata **K2 OWLv2** (pomarańczowy) + komenda w nagłówku.

## Reprodukcja
```
cd s3b0
.venv_s3b0/bin/python scene_gen.py --selftest      # sanity generatora
.venv_s3b0/bin/python export_frames.py             # 192 (A) + 32 (B) klatki + gt.jsonl
.venv_s3b0/bin/python cand_k1_yoloworld.py         # K1  -> metrics/K1_yoloworld.json
.venv_s3b0/bin/python cand_k2_owlv2.py             # K2  -> metrics/K2_owlv2.json
.venv_s3b0/bin/python cand_k3_lfm2vl.py            # K3  -> metrics/K3_lfm2vl.json
.venv_s3b0/bin/python throughput_dual.py           # T4  -> throughput.json
.venv_s3b0/bin/python make_gallery.py              # T5  -> gallery/*.png
```
Artefakty: `results/s3b0/{frames/,gt.jsonl,configs/,metrics/,throughput.json,gallery/}`.
Metryki zbiorcze: `results/s3b0/metrics/summary.json`.

**Uwaga repro:** K1 (ultralytics YOLO-World) dociąga enkoder tekstowy CLIP `ViT-B-32.pt`
do cache'a `weights/clip/` w korzeniu repo (~338 MB, odtwarzalne). Nie jest artefaktem
sesji — po biegu K1 można usunąć (`rm -rf weights/`); nie wchodzi do commita.
```
