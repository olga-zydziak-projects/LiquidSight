# ANEKS-3B-5 do DECYZJE_3B — selekcja checkpointu (val-agregat) (2026-07-27)

Powód: S3b2-R4 — F3 pozytywny na rolloucie (55→72%), ale **wdrożenie 8%** (regresja z 67%)
przez **defekt selekcji checkpointu (ustalenie F-3b-3)**: walidacja selekcyjna była na
**val-BC-only** (30 ep eksperta), a agregat treningu przy r4 = 670 ep zdominowany przez
**DAgger** (polityka-szumne). Dowody R4: best-epoka r4 = **6** (r0–r3: 96–119); other-tick
dist median **0.55 m** (vs S3b2-R 0.17 m); rozjazd rollout(72%)/deploy(8%). BC-val minimalizuje
się wcześnie i rośnie → best-val wybiera niedotrenowany checkpoint.

## Zmiany (jedyne)
**Z1 — walidacja selekcyjna = STRATYFIKOWANY held-out z PEŁNEGO agregatu.**
- **8% epizodów KAŻDEJ rundy** (BC, r1, r2, r3, r4) odłączone od treningu do zbioru
  selekcyjnego; wspólny **deterministyczny seed splitu 45021**; identycznie na każdym etapie.
- best-val liczony na tym rosnącym, reprezentatywnym zbiorze (nie tylko BC).
- **Klasa zmiany: naprawa PROCEDURY treningu** (precedens: ANEKS-4 fazy 3a — best-val/split).
  **Żadnej nowej zdolności systemu.** Kamera/env/ekspert/kontrakt/percepcja — bez zmian.
- **Bezpośredni test F-3b-3:** oczekiwanie — best-epoki PÓŹNE także w r4 (jak r0–r3). Jeśli tak
  → F-3b-3 potwierdzone i naprawione; jeśli r4 nadal wczesne → F-3b-3 obalone (inny mechanizm).

**Z2 — hover-rich BC: PRE-SPECYFIKACJA, NIEAKTYWNE.** +100 ep eksperta z wydłużoną fazą zawisu
pod żywym kanałem (pula **47200-47299**, dopisana do D8 jako rezerwa). Aktywacja **WYŁĄCZNIE
po FAIL R5 i osobnej decyzji człowieka** (kolejny aneks).

**Z3 — STOP-warunek:** PRECONDITION-R5 FAIL → STOP (zero dalszych treningów); raport z opcjami
(aktywacja Z2 / pojemność rdzenia / granica systemowa) do decyzji człowieka.

Bez zmian: F2 OFF (0 odrzuceń), ROUNDS=4, kontrakt D3, procedura v2 (poza selekcją), seed 45020,
pule (r4 47100-47199), progi/sceny G1, ekspert, env, kamera, YOLO. Bramka G1 zamrożona.

## D8 — uzupełnienie (ANEKS-3B-5)
Rezerwa **47200-47299** (hover-rich BC, Z2, NIEAKTYWNA do decyzji człowieka).
