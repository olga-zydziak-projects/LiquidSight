# LiquidSight — czteroaktowe demo (offline)

Pokaz złożony z **nagrań zmierzonych epizodów** (nie nowych pomiarów). Każdy epizod ma etykietę
prowieniencji (pula / seed / maska / wynik), a każda liczba na ekranie pochodzi z raportu fazy.
Scenariusz zamrożony przed budową: `../DEMO.md`.

## Jak odpalić

Podwójny klik na **`liquidsight_demo.html`** (albo otwórz w przeglądarce). Player jest
samowystarczalny — klatki i logi decyzji osadzone w pliku (base64), więc działa **offline z
`file://`**, bez serwera i bez sieci. Sterowanie: `play/pause` (spacja), `step` (→), suwak,
tempo `1×/2×/0.5×`, przełącznik `saliency` (akt 2), nawigacja aktów + plansza końcowa.

## Akty i prowieniencja (kanoniczne — zgodne z DEMO.md i manifestem nagrania)

| akt | pula | seed | maska | wynik | tryb osłony | raport |
|---|---|---|---|---|---|---|
| 1 — language | eval 46500–46599 | 46513 | — (clean) | SUKCES | shadow (transparentna) | RAPORT_3B, RAPORT_3C_MVP |
| 2 — distractors | eval 46500–46599 | 46505 | — (clean) | SUKCES | apply (he=0) | RAPORT_3C_MVP, RAPORT_BASELINE_GRU |
| 3 — broken link | 46500–46549 | 46507 | burst L5 (45105) | SUKCES | shadow (baza G2) | RAPORT_S3B4 |
| 4a — geofence | traps 47400–47449 | 47425 | geofence (traps.py) | REFUSE(GEOFENCE) | apply | RAPORT_3C_MVP §6 |
| 4b — stale | 46500–46549 | 46503 | Bernoulli p0.5 (45102) | REFUSE(STALE_AT_DWELL) | apply | RAPORT_3C_MVP §5 |

Nagranie odtwarza te seedy/maski deterministycznie; wynik każdego epizodu zgadza się z etykietą
(weryfikowane w `../results/demo/manifest.json`, pole `match`).

## Liczby na ekranie → źródło (bez nowych twierdzeń)

- Akt 1: **designation 67% / wrong-lock 10%**, próg **85/8** (frozen, niespełniony) —
  `RAPORT_3B` (granica G1), `RAPORT_3C_MVP §2` (baza nogi A), `G1_GATE.md` (próg).
- Akt 2: **attention↔target IoU 0.32 → 0.10** (K3→K8) — `RAPORT_BASELINE_GRU` (saliency, F3_GATE §6 W3).
- Akt 3: **burst L5 −4 pp vs p0.5 −36 pp** (kotwica p0 = 80%) — `RAPORT_S3B4` (G2).
- Akt 4: **16/28 porażek → bezpieczna abstynencja**, sukces zachowany **15/22** — `RAPORT_3C_MVP §5`;
  geofence **25/25** — `RAPORT_3C_MVP §6`.

## Budowa (odtworzenie)

1. `../.venv/bin/python -m demo.record` — nagrywa 5 epizodów → `../results/demo/<akt>/{3d,cam256,cam64}/` + `trace.jsonl` + `manifest.json`.
2. `../.venv/bin/python -m demo.build_player` — składa `liquidsight_demo.html` (osadza klatki + trace).

Recorder i player **nie dotykają systemu** (polityka/kanał/osłona/env/percepcja FROZEN); sweep G1
46600–46649 nietknięty; zapisy tylko w `demo/` i `results/demo/`.

## Integralność

- Player: `liquidsight_demo.html`
- sha256: `a2bb66df6cd103da759b0f8fa0c017968a5f4751aba50d4f1727f697f5211a12`
- rozmiar: `11M (11459040 B)`
