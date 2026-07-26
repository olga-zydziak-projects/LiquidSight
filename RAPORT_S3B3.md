# RAPORT_S3B3 — G1: grounder LIVE + werdykt (raport diagnostyczny + STOP)

**Data:** 2026-07-26. **Sesja:** S3b3. **Zakres:** grounder LIVE (YOLO-World @1 Hz) zamiast
GT-fed; bramka G1. **ZERO dropoutu (S3b4), ZERO treningu, ZERO re-tuningu groundera.**
MIERZĘ = RAPORTUJĘ. **Werdykt: G1-FAIL → STOP do decyzji człowieka** (zgodnie z G1_GATE pkt 6;
żadnych samodzielnych napraw).

## Werdykt G1 — **FAIL**
50 ep sweep 46600–46649 (TE SAME sceny co sufit S3b2 = 100% → porównanie sparowane),
polityka FROZEN (ckpt 45020), grounder LIVE (config FROZEN S3b0), kontrakt D3.

| metryka | wynik | próg G1 | werdykt |
|---|---|---|---|
| **sukces desygnacji** | **12.0%** (6/50) | ≥ 85% | ✗ |
| **wrong-lock** | **20.0%** (10/50) | ≤ 8% | ✗ |
| no-arrival | 62.0% (31/50) | — | — |
| dwell | 6.0% (3/50) | — | — |
| katastrofy | 0 | — | — |

**Strata vs sufit (sparowane): 88.0 pp** (sufit GT-fed 100% → live 12%). To **wkład
groundera** — cała różnica między idealną percepcją a live.

### Per-komórka (live vs sufit S3b2)
| K×A | live sukces | sufit | wrong-lock |
|---|---|---|---|
| K3_A0 | 12.5% | 100% | 1 |
| K3_A1 | 0.0% | 100% | 0 |
| K5_A0 | 0.0% | 100% | 4 |
| K5_A1 | 22.2% | 100% | 2 |
| K8_A0 | 37.5% | 100% | 1 |
| K8_A1 | 0.0% | 100% | 2 |
| **średnia** | **12.0%** | **100%** | 10 |

Zapaść we WSZYSTKICH komórkach (min 0% / max 37.5%). Brak zależności monotonicznej od K/A —
dominuje globalny defekt percepcji, nie trudność atrybutowa.

## Wskaźniki wtórne (audyt ticków)
- **tick-precision live:** designated **48.0%** / other **16.8%** / background 0.0% /
  no_detection **35.2%** (n=324 ticki). Box groundera pasuje do wskazanego tylko w połowie ticków.
- **flip-rate:** mediana **0** (mean 0.38) — lock rzadko zmienia tożsamość w epizodzie; polityka
  „commituje się" do tego, co złapała (dobrze → sukces; dystraktor → wrong-lock; nic → no-arrival).
- **rozkład conf live** (histogram, n=324): [0,0.1)=**302**, [0.1,0.2)=8, [0.2,0.3)=5, …
  **mediana conf = 0.013**. Trening: conf=1.0 zawsze → **skrajna rozbieżność** (channel OOD).
- **wall-latencja groundera:** mediana **25.4 ms**, p95 42.8 ms — **≪ L_deliver 100 ms**.
  **Walidacja L_deliver: OK na tym sprzęcie** (kontrakt czasowy spełniony; wall nie jest wąskim gardłem).

## Werdykt hipotezy odświeżania (S3b1) — **ODRZUCONA**
Hipoteza: odświeżanie 1 Hz kompensuje błędy pojedynczej klatki (offline 86.8%). **Live 12.0% ≪
86.8%** → **NIE kompensuje**. Powód: błędy live są **systematyczne, nie losowe** — odświeżanie
nie pomaga, gdy cel jest systematycznie poza kadrem lub mylony co do kształtu.

## Diagnoza (root cause; audyt + trace `results/s3b3/traces/`)
1. **Rozjazd dystrybucji klatek offline↔live.** Offline S3b0 (86.8%) mierzono na **statycznej
   osi podejścia** (cel wyśrodkowany, dystanse 2.0–0.5 m — korzystne). Live to **poza drona**:
   cel widoczny wcześnie (daleko), potem **wychodzi z kadru** (martwe pole terminalne, ANEKS-1) /
   przy obrocie drona. Median detekcji 8/10 ticków, ale tylko 48% to wskazany.
2. **Mylenie kształtu przy conf≈0.** Trace (46601 „blue cylinder"): k=0 box na blue cylinder
   (poprawnie, conf 0.00) → k=48 cel poza kadrem, grounder bierze **blue box** (dystraktor) →
   wrong-lock. YOLO-World przy conf≈0 nie rozróżnia cylinder vs box, tylko „coś niebieskiego".
3. **conf≈0 OOD dla polityki.** Polityka trenowana na conf=1.0; live conf med 0.013 → kanał celu
   w reżimie nigdy nie widzianym → polityka nie ufa/nie nawiguje → **no-arrival 62%**.
4. **Wynik:** systematyczny brak/błąd locka + conf OOD ⇒ polityka nie dolatuje (62%) lub goni
   dystraktor (20%). Katastrof 0 (klif bezpieczeństwa trzyma).

## Znane różnice train ↔ live (potwierdzone jako materialne)
- **conf 1.0 (GT) → live med 0.013.** Materialny rozjazd kanału (flagowany w S3b2 — potwierdzony).
- **GT bbox → live box** na **innej dystrybucji klatek** (statyczna oś podejścia vs poza drona).
  Offline benchmark 86.8% **nie jest reprezentatywny** dla percepcji live w pętli.

## STOP — punkty decyzyjne dla człowieka (NIE wykonane w tej sesji)
G1-FAIL zatrzymuje fazę. Naprawa wykracza poza mandat S3b3 (re-tuning groundera / OWLv2 live /
retrening / zmiana kontraktu/zadania = osobne decyzje z aneksem). Opcje do rozważenia:
1. **Re-benchmark groundera na dystrybucji live** (klatki z pozy drona, nie osi podejścia) —
   zmierzyć realny sufit percepcji przed dalszymi decyzjami.
2. **OWLv2 live** (offline 0.958 vs YOLO 0.868; ale 1.6 s @1 Hz → wymaga ticku 0.5 s / D2-fallback).
3. **Retrening polityki na kanale live-fed** (domain randomization conf/box; polityka uczy się
   nieufać niskiej conf i mostkować braki pamięcią) — najbliższe „kompensacji przez uczenie".
4. **Rewizja zadania/percepcji** (np. aktywna percepcja / inne kadrowanie, by cel nie znikał
   terminalnie) — zmiana zakresu tezy.

Rekomendacja sesji (do decyzji Olgi): najpierw **(1)** — bez realnego sufitu percepcji live
pozostałe opcje są ślepe. Żadnej z nich NIE uruchamiam samodzielnie.

## Reprodukcja
```
.venv/bin/python -m s3b3.eval_g1 unittest   # serwer vs S3b0 (IoU>=0.90) — PASS
.venv/bin/python -m s3b3.eval_g1 smoke       # 10 ep EVAL, plumbing — PASS (wall 26ms med)
.venv/bin/python -m s3b3.eval_g1 measure     # 50 ep sweep -> results/s3b3/g1.json (FAIL)
.venv/bin/python -m s3b3.eval_g1 traces      # 3 epizody -> results/s3b3/traces/
```
Artefakty: `results/s3b3/{g1,g1_episodes,smoke}.json`, `tick_audit.jsonl`, `traces/`.
Grounder = serwer-subprocess `.venv_s3b0` (izolacja); polityka/YOLO-config FROZEN.
