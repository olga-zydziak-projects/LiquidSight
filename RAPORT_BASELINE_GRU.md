# RAPORT_BASELINE_GRU — charakteryzacja wykonawcy GRU (B1, wiersz D7)

**Data:** 2026-07-27. **Sesja:** B1. **Ramię:** A_GRU @ lr=1e-3, seedy **45010–45019**
(10), procedura v2 (ANEKS-4), ścieżka **3a** (obs 78, bez kanału celu). Bieg **sekwencyjny
solo** na wyłączność GPU. MIERZĘ = RAPORTUJĘ. Podstawa: `results/baseline_gru/progress.jsonl`,
`summary.json`.

## Nominal (precondition, 100 scen 43000–43099, T0)
**100.0 ± 0.0%** — **wszystkie 10 seedów po 100/100**. GRU jest w pełni kompetentnym
wykonawcą na T0 (potwierdza kontrolę z F3). DAgger domyka się klasycznie:
rollout r1 **25.1%** → r2 **99.4%** → r3 **99.9%** (mean po czystych seedach).

## Krzywa drabiny (7 poziomów, mean ± sd po 10 seedach; 50 scen 43100–43149/poziom)
| poziom | K wabików | sukces mean±sd |
|---|---|---|
| T0 | 0 | **100.0 ± 0.0** |
| T1 | 0 | **100.0 ± 0.0** |
| T2 | 0 | **75.8 ± 5.2** |
| T2a | 1 | **60.6 ± 4.7** |
| T2b | 2 | **46.2 ± 3.6** |
| T2c | 3 | **36.0 ± 4.8** |
| T3 | 4 | **24.2 ± 3.2** |

Monotoniczny spadek z liczbą wabików/rodziną tła. **T0/T1 (rodzina A) = 100%**; wejście
w rodzinę B (T2) i dokładanie wabików o kolorze zbliżonym do celu degraduje wykonawcę do
**24% na T3**. Poziom bramki **T2b = 46.2%**. (Sanity-policy P2R degradowała 100/100/64/46/36/24/16 —
trenowany GRU jest nieco wyżej, ta sama tendencja.)

## Saliency IoU (F3_GATE par.6 W3; top-2% pikseli, klatki dolotu, mean ± sd per poziom)
| poziom | IoU (uwaga↔cel) |
|---|---|
| T0 | 0.321 ± 0.050 |
| T1 | 0.329 ± 0.050 |
| T2 | 0.232 ± 0.029 |
| T2a | 0.161 ± 0.026 |
| **T2b** | **0.124 ± 0.018** |
| T2c | 0.104 ± 0.018 |
| T3 | 0.103 ± 0.019 |

**Krzywa IoU vs K malejąca:** uwaga wykonawcy pokrywa się z maską celu najlepiej bez wabików
(~0.33) i słabnie z rosnącym K (do ~0.10 na T3). Spadek IoU koreluje ze spadkiem sukcesu
drabiny — im więcej wabików zbliżonych kolorem, tym słabsze i rozproszone „patrzenie" na cel.
(Wartość odniesienia dla przyszłych ramion/kanałów; nieorzekająca.)

## Czasy solo (kanoniczna jednostka kosztu programu, constraint 1)
- **Kanoniczny cykl v2 (9 czystych seedów): 2458 ± 85 s = 41.0 min/seed.**
- **Czasy etapów (mean, czyste seedy):** BC (r0) train **371 s**; DAgger r1 rollout 59 + train 475 s;
  r2 rollout 60 + train 687 s; r3 rollout 63 + train 743 s (train rośnie z agregatem 270→570 ep).
- Nominal+drabina+saliency (eval) ≈ 250 s/seed dodatkowo.

### ⚠ Anomalia timingowa (jawnie, MIERZĘ=RAPORTUJĘ)
Podczas seeda **45013** maszyna (laptop) **spała ~3,5 h**; po wybudzeniu GPU chodziło na
obniżonych zegarach → cykl 45013 = **3608 s** (~+47% vs czyste). **45013 WYKLUCZONY z
kanonicznych czasów.** `perf_counter` (CLOCK_MONOTONIC) nie liczy czasu snu, a **wyniki
naukowe są niezależne od zegara GPU** — nominal/drabina/saliency 45013 **ważne i użyte**
(nominal 100%, T2b 50%). Zegary wróciły od 45014 (cykl 2381 s, najszybszy). Bieg wznawialny;
brak równoległych obciążeń (wyłączność GPU dotrzymana; sen to nie kontencja).

## Podsumowanie (wiersz D7)
- **Nominal 100.0 ± 0.0%**, drabina 100/100/75.8/60.6/46.2/36.0/24.2, IoU@T2b 0.124,
  koszt kanoniczny **41 min/seed** (cykl v2). Łączny czas biegu 10 seedów: **7.15 h**
  (z 45013 skażonym).
- Baseline gotowy jako **wiersz odniesienia D7** dla fazy 3b (wykonawca GRU bez kanału celu).

Artefakty: `results/baseline_gru/{progress.jsonl, summary.json}` (checkpointy w
`results/baseline_gru/ckpt/`, gitignored). Reprodukcja: `python -m train.baseline_gru run`
(wznawialny; GPU na wyłączność).
