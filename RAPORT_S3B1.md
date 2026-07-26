# RAPORT_S3B1 — scena atrybutowa + kamera semantyczna + ekspert desygnowany

**Data:** 2026-07-26. **Sesja:** S3b1. **Zakres:** zamrożenie decyzji 3b (DECYZJE_3B.md),
addytywna implementacja env (scena atrybutowa + kamera semantyczna 256²), determinizm
nowej ścieżki, ekspert desygnowany. **ZERO treningu, ZERO groundera live, ZERO zmian
kanału wejść polityki.** MIERZĘ = RAPORTUJĘ.

## Nienaruszalność (dotrzymana)
- READ-ONLY: `frozen_v1/`, `~/projects/liquidflight/`, `paper/`, `models/`, parametry zadania
  (r_goal/z_hover/t_dwell — bez zmian), egzekutor i klif bezpieczeństwa — nietknięte.
- Rozszerzenia env **addytywne**: ścieżka 3a bez zmian (regresja `s1_env_det` **PASS**,
  hash 43100/T0 bit-w-bit z poprzednim biegiem tej maszyny).
- Wszystko z seeda; pule wg DECYZJE_3B D8; pule 3a i sondy 46900+ nietknięte.

## Decyzje z wartościami (pełne w DECYZJE_3B.md)
- **D1-live = YOLO-World** (`yolov8s-worldv2`, cfg S3b0). OWLv2 (0.958) = kandydat
  precyzja-first, **nieaktywny live** (1.6 s @1 Hz na tym sprzęcie).
- **D2:** kamera 256², ta sama poza co 64², **tick = 1.0 s (1 Hz)**, **L_deliver = 0.10 s**
  (mediana YOLO @1 Hz idle 63.1 ms, ceil do 0.05).
- **D3:** kanał (cx,cy,w,h,conf,age_s) znormalizowany, ZOH; age start = L_deliver = 0.10 s;
  brak locku → wektor zerowy + **AGE_MAX = 8.0 s**. Kontrakt od S3b2.
- **D4:** paleta 3×3, K∈{3,5,8}, A0/A1, `K={3,5,8}[seed%3]`, `A=A0 gdy (seed//3)%2==0`.

## Implementacja env (addytywna) — T2
- `env/scene_attr.py` (nowy): spawner atrybutowy — **port 1:1** palety/kształtów/logiki
  A0/A1 z `s3b0/scene_gen.py` (jeden generator, dwaj konsumenci; s3b0 nietknięty). Desygnowany
  w stożku czołowym +x (ANEKS-1), dystraktory w kadrze, min odstęp 0.35 m, podłoga neutralna szara.
- `env/liquidsight_env.py`: `reset(scene_seed, level, scene_type="3a")` — gałąź 3b buduje
  scenę atrybutową (K/A z mapowania D4). `step()` bez zmian dla **kanału polityki** (obs =
  rgb64/kin/dt). Kamera semantyczna 256² co 12. krok polityki (1 Hz), ta sama poza. `info`
  rozszerzone (3b): `designated_id`, `command`, `objects`, `rgb256`, `gt_bbox_256`, `gt_bbox_64`,
  `seg_mask` (na żądanie). Wrong-lock/no-arrival (D5) w kategoryzacji porażki (3b).
- `expert/expert.py`: `run_expert_episode(..., scene_type="3a")` — passthrough; logika najazdu
  bez zmian (ekspert celuje w GT `designated_id`).

## Wyniki determinizmu i eksperta — T3/T4

**Regresja 3a (`s1_env_det`) — PASS.** 43100/T0, 43149/T3, 43125/T2b: rgb/kin/setpoint
bit-w-bit w 2 przebiegach; **43100/T0 hash zgodny z poprzednim biegiem** (`74e1e20d…`).
Ścieżka 3a nietknięta.

**Determinizm 3b (`s3b_env_det`) — PASS (4/4 sceny).** Strumienie rgb64 / rgb256 / kin /
setpoint bit-w-bit w 2 przebiegach, 10 klatek semantycznych/epizod:

| seed | K | A | rgb64 | rgb256 | kin | setpoint | wynik |
|---|---|---|---|---|---|---|---|
| 46600 | 5 | A1 | ✓ | ✓ | ✓ | ✓ | success |
| 46648 | 5 | A1 | ✓ | ✓ | ✓ | ✓ | success |
| 46602 | 3 | A0 | ✓ | ✓ | ✓ | ✓ | success |
| 46601 | 8 | A1 | ✓ | ✓ | ✓ | ✓ | success |

*(46600/46648 → K5/A1 z formuły D4; etykiety promptu (K3/A0),(K8/A1) błędne — dodano
46602=K3/A0 i 46601=K8/A1 realizujące intencję. Rozbieżność odnotowana w DECYZJE_3B.)*

**Ekspert desygnowany (`s3b_expert_designated`, 100 ep, sceny eval 46500–46599) — 100%.**

| metryka | wartość |
|---|---|
| sukces | **100/100 = 100.0%** |
| wrong-lock (osobna kolumna, D5) | **0** |
| no-arrival | 0 |
| dwell | 0 |
| katastrofy (tilt/crash/geofence/contact) | 0 |
| per-cell (K×A) | K3A0 17/17, K3A1 17/17, K5A0 17/17, K5A1 16/16, K8A0 17/17, K8A1 16/16 |

Zgodne z oczekiwaniem: ekspert privileged (GT wskazanego) dolatuje jak w 3a; wrong-lock
**0 z konstrukcji** (nie celuje w inny obiekt). Sufit osi = 100% (percepcja nie limituje eksperta).

**Podgląd osi (`s3b_axis_preview`).** Siatka K×A, 2 sceny/komórkę = **12 klatek 256²** z bboxem
GT wskazanego (zielony) + komenda → `results/s3b1/preview/`. Wskazany widoczny z pozy startu
we wszystkich 12 (znacznik `_vis`); terminalnie znika pod dronem (martwe pole ANEKS-1,
mostkowane pamięcią — grounder locka wcześnie).

## Przepustowość env z dwiema kamerami — kontrola vs prognoza S3b0

| konfiguracja | x-realtime | uwaga |
|---|---|---|
| env 3b (dual: rgb64@12 Hz + rgb256@1 Hz + seg) | **8.2×** | pełny łańcuch: fizyka 240 Hz + ekspert + render |
| env 3a (single: rgb64@12 Hz) | 12.3× | narzut 3b/3a = **1.50×** |
| S3b0 prognoza (sam render dual) | 24.9× | bez fizyki — stąd env niżej |

Kamera semantyczna dokłada **1.50×** narzutu; env 3b nadal **8.2× realtime** (>1× z zapasem).
Kontrola `results/s3b1/env_throughput.json`.

## Latencja groundera: 0.56 s vs 1.6 s (materiał do noty RAPORT_3B)

RAPORT_S3B0 podał latencję OWLv2 **0.56 s** (mean, p95 0.64). Ten pomiar był **back-to-back
pod sustained load** (po ~200 inferencjach; zegary GPU wyśrubowane) z synchronizacją per-call —
**rig optymistyczny, niereprezentatywny** dla żywej pętli 1 Hz, gdzie 1 s przerwy między tickami
**zbija zegar** laptopowego GPU (SM 180 MHz idle vs 3090 MHz max).

**Sonda kadencyjna 1 Hz (R1, 30 wywołań, warmup 3), OWLv2:**

| reżim | mediana | p95 |
|---|---|---|
| (a) idle gap 1 s | 1607 ms | 1947 ms |
| (b) równoległe obciążenie polityki (~143k @12 Hz) | 1648 ms | 2161 ms |
| (c) keep-alive (ciągłe OWLv2 w przerwie) | 1613 ms | 2283 ms |

**Keep-alive NIE pomaga** — wszystkie reżimy ~1.6 s (thermal/zegar, nie brak rozgrzania).
Latencja (~1.6 s) **> tick 1 Hz** ⇒ OWLv2 @1 Hz niewykonalny na tym sprzęcie.

**Sonda YOLO-World (F1, te same warunki):** idle **63.1 ms**, policy-load **56.0 ms** (p95 ≤ 78 ms)
— ≪ 0.8 s. Stąd **D1-live = YOLO-World**, tick 1 Hz, L_deliver = 0.10 s. OWLv2 zostaje
zmierzonym kandydatem precyzja-first (nieaktywny live). Hipoteza: −9 pp precyzji offline
kompensowane odświeżaniem 1 Hz → **weryfikuje sweep G1** (S3b2+).
Artefakty: `results/s3b1/k2_latency_regimes.json`, `k1_latency_regimes.json`.

## Co zostaje do S3b2 (poza zakresem S3b1)
- Wpięcie **kanału celu (D3)** w wejście polityki (dodatkowy do rgb64/kin/dt; kontrakt age/ZOH).
- **Grounder live** (YOLO-World) w pętli @1 Hz + ZOH; walidacja L_deliver na sprzęcie docelowym.
- **Oś G2 (D6):** dropout p∈{0,.25,.5,.75} + burst L∈{2,5}s, maski 45100+; zamrożenie po sondzie.
- **Baseline B1 (D7):** RAPORT_BASELINE_GRU.
- **Sweep G1:** test hipotezy kompensacji błędnego locka odświeżaniem 1 Hz (YOLO 0.868 vs OWLv2 0.958).
- Trening polityki (sceny 46000–46299), eval 46500–46599.

## Reprodukcja
```
.venv/bin/python smoke/s1_env_det.py            # regresja 3a (PASS, hash 43100/T0)
.venv/bin/python smoke/s3b_env_det.py           # determinizm 3b (4 sceny, PASS)
.venv/bin/python smoke/s3b_expert_designated.py # ekspert desygnowany 100 ep
.venv/bin/python smoke/s3b_axis_preview.py      # siatka podgladow K x A -> preview/
```
Artefakty: `results/s3b1/{s3b_env_det,s3b_expert_designated,env_throughput,*latency*}.json`,
`results/s3b1/preview/*.png`.
