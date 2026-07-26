# P-SANITY-3B — bramka zdrowia instrumentu 3b (zamrożona PRZED treningiem)

**Data zamrożenia:** 2026-07-26 (przed treningiem S3b2). **Zasada:** MIERZĘ = RAPORTUJĘ.
Progi zamrożone w tym commicie; po commicie **bez zmian**. Analog P_SANITY.md dla
percepcji desygnowanej (goal-conditioned). Cel: potwierdzić, że instrument 3b (scena
atrybutowa + kanał celu GT-fed + polityka warunkowana) jest **uczalny do kompetencji**
zanim uruchomimy sweep G1 / oś G2 — inaczej wynik G1/G2 byłby nierozstrzygalny.

## P1-3b — kompetencja polityki goal-conditioned (GT-fed) *(PRÓG)*
- **Reżim:** polityka warunkowana kanałem celu (D3), **źródło = GT** (`gt_bbox_256`
  wskazanego, `conf=1.0`), z kontraktem dostarczania (tick 12 klatek, L_deliver 0.10 s,
  age, no-lock) DOKŁADNIE wg DECYZJE_3B D3. **Bez groundera live, bez dropoutu.**
- **Miara:** % sukcesu na **100 epizodach eval 46500–46599** (mapowanie K/A z D4),
  deterministycznie.
- **PRÓG: sukces ≥ 90%.**
- **wrong-lock** raportowany **OSOBNO**, wymóg **< 2%**. Uzasadnienie: przy celu
  podanym z GT (dokładny bbox wskazanego) dwell przy INNYM obiekcie = **defekt kanału
  celu / warunkowania**, nie percepcji — nie wolno go tolerować na poziomie sanity.
- **no-arrival / katastrofy:** raportowane (bez osobnego progu; katastrofy oczekiwane ~0,
  klif bezpieczeństwa bez zmian).

**FAIL → naprawa WYŁĄCZNIE nominalna** (więcej danych BC / epok / rund DAgger — środki
z ANEKS-4), zalogowana, powtórka pomiaru. **Zakaz** pomiarów G1 (sweep) i G2 (dropout)
do osiągnięcia PASS. Zakaz strojenia na sweep 46600–46649 (konstytucyjnie — reguła 4).

## Charakteryzacja (BEZ progu) — sufit per-komórka
- **Sufit per-komórka K×A** na **sweep 46600–46649** (po **50 ep** wg mapowania D4):
  sukces + wrong-lock per komórka (K ∈ {3,5,8} × A ∈ {A0,A1}) + średnia.
- Rola: **wiersz odniesienia dla G1** (ile traci grounder live względem GT-fed).
  To charakteryzacja, **nie strojenie** — żadnych zmian modelu/przepisu po obejrzeniu.

## Zakres i higiena
- Strojenie (jeśli FAIL) **wyłącznie na nominalu** (eval 46500–46599); sweep 46600–46649
  **nietykany** do strojenia (tylko charakteryzacja po PASS).
- Kontrakt D3 **niezmienny po T2** (poza zakresem sesji). Znana różnica train/live:
  `conf=1.0` (GT) vs conf groundera live — **weryfikuje G1** (S3b3+).
- Parametry zadania (r_goal/z_hover/t_dwell), env 3a, ekspert, klif bezpieczeństwa —
  **bez zmian**.
