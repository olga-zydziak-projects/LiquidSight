# ANEKS-3B-4 do DECYZJE_3B — F2 off, czysty test F3 (2026-07-27)

Powód: S3b2-R3 (F2+F3) regresja **67% → 11%**. Audyt dowiódł, że **F2 (pixel-IoU-gating)
odrzucał LEGALNE aktualizacje** w dolocie (741 train / 133 eval; age-histogram przesunięty
w górę = locki zamrożone; detekcja groundera bez zmian, designated 20.6% ≈ 20.8%). Plateau F3
(rollout 57%) było **SKONFUNDOWANE** — mierzone pod zepsutym kanałem. Ta sesja izoluje F3.

## Zmiany (jedyne)
**Z1 — F2 DEZAKTYWOWANE na stałe (dostarczenia bez gatingu, jak w S3b2-R).**
- **Ustalenie inżynierskie F-3b-2:** pixel-IoU kolejnych boxów wskazanego **~0** przy dynamice
  dolotu 1 Hz (obiekt przesuwa się w kadrze 256 między tikami) → gating IoU≥0.2 odrzuca legalne
  re-lokalizacje → zamraża lock. Metryka pixel-IoU jest **nieadekwatna** dla ruchomej kamery.
- **Wariant gatingu w dystansie ŚWIATOWYM** (po back-projekcji) **JAWNIE ODŁOŻONY**: kradzież
  = 3 pp (B3), **nie uzasadnia** kolejnej dźwigni kanałowej przed czystym pomiarem F3.

**Z2 — F3 UTRZYMANE: +1 runda DAgger (r4, pula 47100-47199).**
- Cel: **czysty pomiar wartości budżetu** (jedna dodatkowa runda) na zdrowym kanale (S3b2-R).
  R3 nie jest dowodem plateau (kanał był zepsuty).

**Z3 — nic więcej.** Żadnych innych dźwigni (czystość atrybucji).

## STOP-warunek
**PRECONDITION-R4 FAIL → STOP DEFINITYWNY w mandacie** (zero dalszych treningów w sesji);
raport z opcjami **spoza listy** (hover-rich BC, pojemność rdzenia, world-gating) do **decyzji
człowieka**. Niezależnie od werdyktu: dekompozycja B1-B4 na porażkach (pomiar czystej wartości
r4 vs R: B4 27 → ?).

Bez zmian: kontrakt D3 (kanał 5-dim, tick 1 Hz, L_deliver 0.10, AGE_MAX 8.0, ZOH, no-lock),
procedura v2, seed 45020, pule (r4 47100-47199 z ANEKS-3B-3), progi/sceny G1, ekspert, env,
kamera polityki, konfiguracja YOLO. Bramka G1 zamrożona.
