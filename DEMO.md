# DEMO — scenariusz czteroaktowego pokazu (FROZEN przed budową)

**Data:** 2026-08-01. **Charakter:** MONTAŻ, nie pomiar. Epizody to **ilustracje ze zmierzonych
konfiguracji**; żadnych nowych twierdzeń liczbowych. Każda liczba na ekranie pochodzi z raportu
(odsyłacz w kolumnie „źródło"). System FROZEN (polityka/kanał/osłona/env). Sweep 46600–46649
nietknięty. Zapisy w `demo/` + `results/demo/`.

Ten dokument jest zamrożony przed budową recordera/playera — dobór epizodów i treść banerów nie
zmieniają się po obejrzeniu nagrań.

## Układ ekranu (wszystkie akty)

Cztery pola + panel:
- **Widok 3D** — kamera zewnętrzna śledząca drona (third-person), scena + obiekty + cel.
- **Kamera 256²** — wejście groundera; overlay: bbox dostarczonego locka + `conf` (liczba).
- **Surowe 64²** — wejście polityki (kamera drona); w akcie 2 przełącznik saliency.
- **Panel** (prawa kolumna):
  - `COMMAND:` treść komendy „fly to the {color} {shape}";
  - `LINK:` wskaźnik łącza semantycznego z `age_s` (zielony <2 s / żółty 2–6 s / czerwony >6 s /
    „FROZEN" gdy dropout); pokazuje ducha ZOH gdy brak dostarczeń;
  - `WRONG-LOCK:` licznik (0/1) — czy kanał wskazuje inny obiekt niż desygnowany (z audytu GT
    nagrania, nie nowy pomiar);
  - `SHIELD:` stan (SEEKING/TRACKING/DWELL-GUARD/DONE) + reguła (R-A..R-D) + decyzja
    (ALLOW/HOLD/REFUSE) + powód (NO_MATCH/STALE_AT_DWELL/GEOFENCE).

Styl: ciemny, liczby czytelne, zero ozdobników. Język ekranu: EN. Tempo: 12 kroków/s = realny
takt polityki (12 Hz); regulowane play/pause/krok/tempo.

## Akty — dobór epizodów i banery

Wszystkie epizody pochodzą ze zbiorów pomiarowych S3c1-R / G2 / S2 i są odtwarzane
deterministycznie (ten sam seed/maska co w pomiarze).

### AKT 1 — „the language" (desygnacja działa)
- **Epizod:** pula eval **46500–46599**, **seed 46513**, K5/A0, **bez maski** (clean),
  wynik **SUKCES** (noga A S3c1-R). Cel daleko w stożku +x, czysty dolot i dwell; osłona
  transparentna (ALLOW przez dolot; późny łagodny HOLD-sufit przy celu, jeśli wystąpi — opisany
  jako benign).
- **Baner (EN):** „designation **67%** / wrong-lock **10%** — measured envelope (pre-registered
  gate **85/8**: frozen, unmet, reported)".
- **Źródło liczb:** 67/10 → `RAPORT_3B` (granica G1) i `RAPORT_3C_MVP §2` (baza nogi A 67,0/10,0);
  próg 85/8 → `G1_GATE.md` (zamrożony, niespełniony).

### AKT 2 — „the distractors" (wabiki + saliency)
- **Epizod:** pula eval **46500–46599**, **seed 46505**, K8/A1, **bez maski**, wynik **SUKCES**
  (noga A). Overlay **saliency** (gradient wejścia 64², klatki dolotu) — przełącznik.
- **Baner (EN):** „attention↔target IoU **0.32 → 0.10** as distractors grow (K3→K8)".
- **Źródło liczb:** `RAPORT_BASELINE_GRU` (Saliency IoU, F3_GATE par.6 W3: T0 0.321 → T3 0.103).

### AKT 3 — „broken link" (zrywany strumień, mostkowanie)
- **Epizod:** pula **46500–46549**, **seed 46507**, K5/A0, **maska burst L=5 s** (pula masek
  45100+, `mask_seed 45105`, okno przerwy tiki 5–9), wynik **SUKCES** (G2). Bbox zamarza jako
  duch ZOH, `age_s` rośnie do ~5 s (czerwony), dolot i dwell domknięte mimo przerwy.
- **Inset:** krzywa G2 z zaznaczeniem **L5 = −4 pp** vs **p0.5 = −36 pp** (kotwica p0=80%);
  podpis „continuity is what matters".
- **Źródło liczb:** `RAPORT_S3B4` (G2: p0 80,0%; p0.50 44,0% = −36; burst L5 76,0% = −4).

### AKT 4 — „refusal, two faces" (odmowa z powodem)
- **(a) geofence:** pula pułapek **47400–47449**, **seed 47425** (wariant „cel za geofencem",
  generator `s3c1/traps.py`), wynik **REFUSE(GEOFENCE)** przy k=0. Cel oznaczony poza areną;
  panel: R-C GEOFENCE.
- **(b) stale:** pula **46500–46549**, **seed 46503**, K3/A1, **maska Bernoulli p=0.5** (dropout,
  `mask_seed 45102`), wynik **REFUSE(STALE_AT_DWELL)** (noga B). Dron wchodzi w martwe pole,
  łącze zabite (age>2 s, czerwony „FROZEN"), R-B: HOLD → T_hold 3 s → REFUSE.
- **Baner (EN):** „shield accounting (dropout leg): **16 of 28** base failures → safe abstention;
  success preserved **15/22**. uncertainty belongs to the shield".
- **Źródło liczb:** `RAPORT_3C_MVP §5` (noga B: baza 44/16 → SUKCES 15 / ODMOWA 22 / PORAŻKA 13;
  16/28 porażek → odmowa).

## PLANSZA KOŃCOWA
Cztery akty / cztery bramki / cztery liczby:

| akt | bramka | liczba (źródło) |
|---|---|---|
| 1 language | desygnacja | 67% / 10% (`RAPORT_3B`) |
| 2 distractors | saliency vs K | IoU 0.32→0.10 (`RAPORT_BASELINE_GRU`) |
| 3 broken link | mostkowanie | L5 −4 vs p0.5 −36 pp (`RAPORT_S3B4`) |
| 4 refusal | osłona | 16/28 porażek → abstynencja (`RAPORT_3C_MVP`) |

Podpisy (EN): „**thresholds frozen before measurement**". Linia roadmapy: „**next: state
continuity on public anti-UAV video (CT cores vs Kalman/GRU/Mamba)**".

## Tabela prowieniencji (kanoniczna — powtórzona w playerze i README)

| akt | pula | seed | maska | wynik | raport |
|---|---|---|---|---|---|
| 1 | eval 46500–46599 | 46513 | — (clean) | SUKCES | RAPORT_3C_MVP / RAPORT_3B |
| 2 | eval 46500–46599 | 46505 | — (clean) | SUKCES | RAPORT_3C_MVP / RAPORT_BASELINE_GRU |
| 3 | 46500–46549 | 46507 | burst L5 (45105) | SUKCES | RAPORT_S3B4 |
| 4a | pułapki 47400–47449 | 47425 | geofence (traps.py) | REFUSE(GEOFENCE) | RAPORT_3C_MVP |
| 4b | 46500–46549 | 46503 | Bernoulli p0.5 (45102) | REFUSE(STALE_AT_DWELL) | RAPORT_3C_MVP |

## Zasady nagrania (nie pomiar)
Recorder odtwarza deterministycznie te seedy/maski (identyczne z pomiarem) i zrzuca klatki +
`trace.jsonl`. Wynik każdego epizodu musi zgadzać się z etykietą prowieniencji powyżej; niezgodność
= STOP (nie podmieniamy epizodu na „ładniejszy" spoza zbiorów). `WRONG-LOCK` i `age` na ekranie
pochodzą z audytu GT nagrania (te same reguły dopasowania co w pomiarze), nie są nowym twierdzeniem.
