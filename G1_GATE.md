# G1_GATE — bramka desygnacji end-to-end z grounderem LIVE (zamrożona)

**Data zamrożenia:** 2026-07-26 (przed pomiarem). **Zasada:** MIERZĘ = RAPORTUJĘ.
Progi zamrożone w tym commicie; po commicie **bez zmian**. G1 mierzy, czy polityka
goal-conditioned z S3b2 (FROZEN) działa z **grounderem LIVE** (YOLO-World @1 Hz)
zamiast idealnego GT-fed — czyli jaki jest koszt realnej percepcji w pętli.

## Pomiar
- **Sceny:** 50 ep **sweep 46600–46649** (mapowanie D4) — **TE SAME** sceny co wiersz
  sufitu w S3b2 (100% wszędzie) ⇒ **porównanie sparowane** (strata = wkład groundera).
- **Polityka:** deterministyczna, `ckpt/s3b2/policy_gc.pt` (seed 45020) — **FROZEN, zero treningu**.
- **Grounder:** YOLO-World LIVE, konfiguracja **FROZEN** z `results/s3b0/configs/K1_yoloworld.json`
  (`set_classes=["{color} {shape}"]`, top-1, próg 0.0) — **zero re-tuningu** (zmiana = aneks).
- **Kontrakt kanału (D3, jak trening):** tick co 12 klatek; dostarczenie w **czasie
  symulowanym** `t_zrodla + L_deliver` (0.10 s → k_del=k_src+2); **conf = LIVE score YOLO**
  (znana różnica vs trening conf=1.0 — to mierzymy); no-detection ticku → brak dostarczenia
  (kanał starzeje się ZOH; nigdy nie było locka → no-lock). **Sim NIE czeka na wall-clock**;
  wall-latencja per wywołanie logowana osobno (walidacja L_deliver na sprzęcie).

## Metryka pierwotna + PROGI (zamrożone)
- **% sukcesu desygnacji** ogółem + **per komórka K×A**.
- **wrong-lock %** raportowany **OSOBNO** (zawsze).
- **G1-PASS ⟺ sukces ogółem ≥ 85% ORAZ wrong-lock ≤ 8%.**

## Wskaźniki wtórne (raportowane, NIEORZEKAJĄCE)
1. **tick-precision live** (z audytu jsonl): udział ticków, których box pasuje (IoU≥0.5) do
   GT wskazanego / innego obiektu / niczego.
2. **flip-rate:** mediana liczby zmian tożsamości dostarczonego locka na epizod.
3. **strata vs sufit** (100%, sceny sparowane) = wkład groundera.
4. **porównanie z offline 86.8%** (RAPORT_S3B0 K1 precision@1): live **> 86.8%** ⇒ odświeżanie
   1 Hz **KOMPENSUJE** błędy pojedynczej klatki (hipoteza z S3b1) — **werdykt hipotezy wprost**.
5. **rozkład conf live** (histogram) vs trening conf=1.0.

## Determinizm / audyt
- Kontrakt bit-w-bit dotyczy **env** (rgb64/rgb256/kin). Wyjścia groundera na GPU **nie są
  hashowane** — **logowane per tick** (jsonl: `t, box, conf, obiekt dopasowany wg GT-IoU`) jako audyt.

## FAIL → STOP
- G1-FAIL → **diagnostyka per komórka + audyt ticków**, **STOP do decyzji człowieka**.
  Żadnych samodzielnych napraw (re-tuning groundera / zmiana kontraktu = poza mandatem).

## Izolacja / higiena
- Grounder = **serwer-subprocess** z `.venv_s3b0` (localhost); klient w głównym `.venv`.
  Zero instalacji w głównym `.venv`. Polityka, YOLO-config, env, ekspert, parametry,
  DECYZJE_3B — **nietykalne**. Dropout/G2 — poza zakresem (S3b4).
