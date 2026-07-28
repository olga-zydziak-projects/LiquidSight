# ANEKS-3B-7 do DECYZJE_3B — kurikulum GT+live; klauzula końca (2026-07-28)

Powód: baza S3b2-R = 67%; dominujący brak B4 (precyzja dwell). Hover-rich (Z2) szkodliwy
(F-3b-4: szybki ekspert → rozjazd etykiet). Ta sesja testuje **Z2' — domieszkę GT-fed** —
i jest **OSTATNIĄ iteracją precondition w tym mandacie** (klauzula końca poniżej).

## Zmiany (jedyne — skład BC)
**Z2' AKTYWNE — BC = 400 ep = 300 live-fed + 100 GT-fed:**
- **300 live-fed** (46000-46299): kanał 5-dim, box źródłowy = **żywy YOLO** (kontrakt D3).
- **100 GT-fed** (NOWA pula **47300-47399**): kanał 5-dim wg **tego samego kontraktu D3**
  (co tick, L_deliver, ZOH, no-lock), box źródłowy = **gt_bbox_256** (dokładny), bez conf.
- **Ekspert STANDARDOWY** (v_max=1.0, t_ramp=2.0) w OBU + DAgger — **identyczny profil**
  (lekcja F-3b-4: żadnego szybkiego eksperta). **Hover-rich (Z2) ZDEZAKTYWOWANE.**
- **Mechanizm testowany:** spójność **etykieta↔kanał** w danych GT-fed uczy precyzyjnego
  podążania za zamrożonym boxem (dowód umiejętności: polityka GT-fed = 100%, S3b2); domieszka
  ma **przenieść umiejętność** na politykę żyjącą na żywym interfejsie.

## KLAUZULA KOŃCA (wiążąca)
**R7 = ostatnia iteracja precondition w tym mandacie.**
- **PASS (≥85% ∧ wrong-lock ≤8%) → G1-R** (sweep 46600-46649, G1_GATE.md niezmieniony).
- **FAIL → pomiar G1 zamyka się w stanie zmierzonym:** granica raportowana przy **NIETKNIĘTYM
  progu**; **sweep 46600-46649 pozostaje CZYSTY** (możliwe przyszłe ponowne uzbrojenie osobnym
  mandatem); program przechodzi do **G2 (na najlepszym modelu)** i **3c-MVP**. **Żadnych dalszych
  dźwigni precondition bez nowego mandatu człowieka.**

Bez zmian: przepis = S3b2-R + **Z1-selektor** (val stratyfikowany, seed 45021) + **ROUNDS=3**,
F2 OFF, kontrakt D3, seed 45020, pule DAgger, ekspert std, kamera, env, parametry, progi/sceny G1,
YOLO. Bramka G1 zamrożona.

## D8 — uzupełnienie (ANEKS-3B-7)
Pula **47300-47399** = **GT-fed BC** (Z2', AKTYWNA w tej sesji).
