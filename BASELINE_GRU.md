# BASELINE_GRU — charakteryzacja wykonawcy GRU (D7, baseline pod fazę 3b)

**Data:** 2026-07-26. **Sesja:** B1. **Cel:** kanoniczna charakteryzacja ramienia
wykonawczego **A_GRU** jako **baseline** dla fazy 3b (wiersz **D7** w DECYZJE_3B). Faza 3a
zamknięta (GRANICA); ta charakteryzacja NIE koliduje z 3b. **Zero nowych decyzji** — spec
wyłącznie przez referencję do dokumentów JUŻ ZAMROŻONYCH. MIERZĘ = RAPORTUJĘ.

## Specyfikacja (przez referencję — bez zmian)
- **Model / rdzeń:** A_GRU = `models/policy.Policy` (enkoder + GRU 64 + głowa Linear(64→6));
  ścieżka **3a** (`scene_type="3a"`, obserwacja **78** = feat 64 + kin 13 + dt 1; **BEZ kanału
  celu**). Fabryka: `models/arms.build_arm("A_GRU")`.
- **Procedura treningu:** **v2 (ANEKS-4)** — BC (runda 0) + **3× DAgger**, retrening OD ZERA
  na agregacie każdą rundę, best-val, **120 epok/etap**, batch 16, grad-clip 1.0
  (`train/procedure.run_cycle`). **lr = 1e-3** (F3_GATE par.4).
- **Zbiory / drabina:** BC = 300 ep (44000–44299, split 270/30; `data/bc/`); DAgger rundy
  44300–44399 / 44400–44499 / 44500–44599 (`train/procedure.ROUND_SEEDS`). **Nominal** =
  100 scen **43000–43099** (T0). **Drabina** = 7 poziomów {T0,T1,T2,T2a,T2b,T2c,T3} × 50 scen
  **43100–43149** (F3_GATE par.2, ANEKS-2).
- **Seedy:** **45010–45019** (10, sekwencyjnie).
- **Saliency IoU (F3_GATE par.6 W3):** `saliency = |grad(Σ|setpoint_6D|, rgb)|`, max po
  kanałach, binaryzacja **top-2%** pikseli; **IoU z maską seg celu**; klatki: co 4. klatka fazy
  dolotu (do pierwszego wejścia w r_goal), **max 15/epizod**, **pierwsze 10 epizodów sweep** per
  poziom per seed. Raport: **mean±sd IoU per poziom** (krzywa IoU vs K).

## Nienaruszalność (B1)
- **WYŁĄCZNOŚĆ GPU:** zero równoległych treningów/ewaluacji — czasy tego biegu = **kanoniczna
  jednostka kosztu**. Bieg **sekwencyjny solo** (seed po seedzie).
- **Wznawialność:** `results/baseline_gru/progress.jsonl` (append-only) + checkpoint per seed;
  restart pomija ukończone.
- Spec bez zmian; `paper/` i ścieżka 3b **nietykalne**; commity tylko
  `results/baseline_gru/` + `BASELINE_GRU.md` + `RAPORT_BASELINE_GRU.md`.

## Poza zakresem
Modele CfC, kanał celu, sceny 3b, zmiany env/spec, `paper/`, jakiekolwiek decyzje.
