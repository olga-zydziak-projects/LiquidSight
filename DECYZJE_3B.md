# DECYZJE_3B — decyzje fazy 3b (D1–D8, zamrożone)

**Data zamrożenia:** 2026-07-26. **Podstawa:** PRE_3B0 + smoke groundera offline
(RAPORT_S3B0) + sondy latencyjne S3b1 (R1/F1). **Zasada:** MIERZĘ = RAPORTUJĘ.
Zmiana wartości po tym commicie zabroniona (jak DECYZJE_F3). Faza 3b bada
percepcję desygnowaną (grounder → kanał celu → polityka) pod przesunięciem G2.

Skróty źródeł: `S0=RAPORT_S3B0.md`; `cfgK1=results/s3b0/configs/K1_yoloworld.json`;
`cfgK2=results/s3b0/configs/K2_owlv2.json`; sondy latencji: `results/s3b1/
k2_latency_regimes.json`, `k1_latency_regimes.json`.

---

## D1 — grounder (wybór + tryb live)
- **Kandydat precyzja-first (zmierzony, S0):** **OWLv2** `google/owlv2-base-patch16-ensemble`,
  konfiguracja zamrożona `cfgK2` (query = fraza komendy, top-1, próg 0.0).
  Precyzja@1 EVAL = **0.958** (A0 0.986 / A1 0.931), wrong-object 0.042.
- **Grounder LIVE 3b (D1-live) = YOLO-World** `yolov8s-worldv2`, konfiguracja zamrożona
  `cfgK1` (set_classes=[„{color} {shape}"], top-1, próg 0.0). Precyzja@1 EVAL = **0.868**.
  **Powód zamiany:** latencja live OWLv2 @1 Hz na tym sprzęcie ≈ **1.6 s** (R1: trzy
  reżimy 1607/1648/1613 ms, **keep-alive nieskuteczny**) — **niewykonalna** przy ticku
  1 Hz. YOLO-World @1 Hz = **63 ms** (F1). 
- **OWLv2: NIEAKTYWNY live** w 3b na tym sprzęcie (1.6 s @1 Hz). Adnotacja: różnica
  **−9 pp precyzji offline** (0.868 vs 0.958); **hipoteza kompensacji odświeżaniem 1 Hz**
  (błędny lock koryguje się w kolejnym ticku) — **weryfikuje sweep G1**. Gdyby sprzęt
  docelowy udźwignął OWLv2 @1 Hz, powrót do OWLv2 jest zmianą D1-live (nowa decyzja).

## D2 — kamera semantyczna + tick + L_deliver
- Kamera **256×256**, **ta sama poza** co 64² (D3 ANEKS-1), render co 12. krok polityki.
- **tick = 1.0 s (1 Hz)** — YOLO-World (63 ms) mieści się z zapasem (>15×).
- **L_deliver = 0.10 s.** Źródło: mediana latencji YOLO-World @1 Hz-kadencja (F1, 30 wywołań,
  warmup 3): idle **63.1 ms**, policy-load **56.0 ms**; wartość konserwatywna (idle)
  **zaokrąglona w górę do 0.05 s** → 0.10 s. Data pomiaru 2026-07-26, GPU RTX 5070 Ti Laptop.
  (Artefakt: `results/s3b1/k1_latency_regimes.json`.)
- Przepustowość env z dwiema kamerami: **8.2× realtime** (pełny łańcuch; kontrola
  `results/s3b1/env_throughput.json`) — >1× z zapasem; awaryjnie D2 dopuszcza 224²/0.5 Hz
  (S0), niepotrzebne.

## D3 — kanał celu (kontrakt od treningu S3b2)
- Wektor **(cx, cy, w, h, conf, age_s)** znormalizowany; **ZOH** między tickami (1 Hz).
- **age_s** = sekundy od KLATKI ŹRÓDŁOWEJ ticku; **start = L_deliver = 0.10 s**, rośnie
  liniowo do następnego dostarczenia (do ~L_deliver + tick).
- **brak locku** (grounder nie zwrócił boxu ≥ progu) → **wektor zerowy** + **age_s = AGE_MAX**.
- **AGE_MAX = 8.0 s** (sufit normalizacji age; F3). Uzasadnienie: pokrywa oś G2
  (burst do 5 s) + okres ticku + L_deliver + bufor, tak by żaden realny age „ważnego"
  locku nie osiągnął sufitu (sufit = sygnatura braku locku, nie stary lock).
- Kontrakt obowiązuje **od treningu S3b2** (polityka trenuje na tym, co zobaczy na żywo).
  W S3b1 kanał NIE jest wpięty w politykę (poza zakresem).

## D4 — scena atrybutowa
- Paleta **3 kolory × 3 kształty** (RGBA/wymiary przeniesione 1:1 z `s3b0/scene_gen.py`
  → `env/scene_attr.py`): red `(0.85,0.05,0.05)` / green `(0.05,0.6,0.05)` /
  blue `(0.1,0.2,0.85)` × box (half 0.08) / sphere (r 0.08) / cylinder (r 0.06, h 0.16).
- **K ∈ {3,5,8}**; poziomy **A0** (kolor wskazanego unikalny) / **A1** (kolor współdzielony,
  kształt rozstrzyga). Komenda `"fly to the {color} {shape}"`; **DOKŁADNIE 1 dopasowanie**.
- **Mapowanie deterministyczne seed→parametry:**
  `K = {3,5,8}[seed % 3]`; `A = A0 gdy (seed//3) % 2 == 0, inaczej A1`.
- Desygnowany spawnowany w stożku czołowym +x (ANEKS-1 Z2) — ekspert dolatuje jak w 3a.
  Podłoga **neutralna szara** (jak Wariant A S0; grounder S3b2 widzi to samo tło).

## D5 — sukces / porażki
- **sukces** = dolot + dwell (t_dwell) przy **WSKAZANYM** (r_goal, z_hover — bez zmian).
- **wrong-lock** = dwell przy INNYM obiekcie (osobna kolumna ZAWSZE).
- **no-arrival** = nigdy nie wszedł w r_goal wskazanego; **dwell** = wszedł, nie utrzymał.
- **Klif bezpieczeństwa bez zmian** (v1.0 + geofence + kontakt; `is_catastrophe`).

## D6 — oś G2 (przesunięcie percepcyjne)
- Dropout **Bernoulli p ∈ {0, .25, .5, .75}** + **burst L ∈ {2, 5} s**; maski z puli **45100+**.
- Poziomy **zamrażane po sondzie** (jak drabina osi 3a). **Poza zakresem S3b1** (deklaracja).

## D7 — baseline
- Tabela **B1** = referencja **RAPORT_BASELINE_GRU** (po biegu). **Poza zakresem S3b1**.

## D8 — pule seedów
| pula | zakres | rola |
|---|---|---|
| trening | **46000–46299** | trening polityki (S3b2) |
| eval | **46500–46599** | ewaluacja (T3 ekspert desygnowany tutaj) |
| sweep G1 | **46600–46649** | sweep (det/preview S3b1 tutaj) |
| maski dropoutu | **45100+** | oś G2 (D6) |
| sondy | **46900–46999** | S3b0 (zużyte) |

Pule 3a (43000–43149, 41000+, 42000+, 45010–45019) i sondy 46900+ **nietknięte**.

### D8 — uzupełnienie (S3b2, 2026-07-26, addytywne)
Rundy DAgger polityki 3b (retrening od zera na agregacie, ANEKS-4):
| runda | pula rolloutów |
|---|---|
| DAgger r1 | **46300–46399** |
| DAgger r2 | **46400–46499** |
| DAgger r3 | **47000–47099** |

**Seed treningu polityki 3b = 45020** (init modelu + shuffle; rozłączny z 45010–45019
używanymi w fazie 3a). Pule treningu BC (46000–46299) i eval (46500–46599) — bez zmian.

---

## Rozbieżności odnotowane (jawnie)
1. **Latencja OWLv2 0.56 s vs 1.6 s.** S0 podał 0.56 s (mean) mierzone **back-to-back pod
   sustained load** (zegary GPU wyśrubowane) — **niereprezentatywne** dla żywej pętli 1 Hz.
   Sonda kadencyjna 1 Hz (R1) daje ~1.6 s we wszystkich reżimach (idle/policy-load/keep-alive).
   → D1-live przełączone na YOLO-World (F1/F2). Szczegóły: RAPORT_S3B1 „Latencja groundera".
2. **Etykiety seedów T4 promptu.** Prompt oznaczył 46600=(K3/A0), 46648=(K8/A1); formuła D4
   mapuje **oba na K=5/A1**. Formuła jest wiążąca; s3b_env_det uruchomiono na 46600/46648
   (realne K5/A1) **oraz** 46602 (K3/A0) i 46601 (K8/A1) realizujących intencję etykiet.

**ANEKS-3B (2026-07-26):** D3 zrewidowane — conf usuniety z wejscia polityki, dane live-fed; wg ANEKS_3B_KANAL.md.
**ANEKS-3B-2 (2026-07-27):** DIAG-lite dekomponuje porazki PRECONDITION-R (B4=27 pp dominuje: lock poprawny, epizod przegrany); dzwignie L1 nieaktywna / L2 marginalna → reguła L3 STOP (bez treningu); wg ANEKS_3B2_PERCEPCJA.md.
**ANEKS-3B-3 (2026-07-27):** DIAG-B4 — B4 (27 pp) to precyzja dwell (near-miss 96%, box dokladny ~0.5px, korelacja Δbox↔Δhover 0.22); dzwignie F1 nieaktywna, F2 gating + F3 (+1 runda DAgger, pula 47100-47199) aktywne; wg ANEKS_3B3_PRECYZJA.md.
