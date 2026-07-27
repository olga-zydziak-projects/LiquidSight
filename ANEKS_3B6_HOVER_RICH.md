# ANEKS-3B-6 do DECYZJE_3B — hover-rich BC (2026-07-28)

Powód: S3b2-R = 67% (baza); dominujący brak = **B4 (precyzja dwell, ~27-33 pp)** — lock
poprawny cały epizod, ale zawis nietrzymany w r_goal przy **wysokim age żywego kanału**
(martwe pole terminalne → brak świeżego locka w fazie dwell). Budżet rund (F3) nie domknął B4
(R5: 4 rd 58% < 3 rd 67%). Ta sesja: **JEDNA dźwignia — hover-rich BC** — precyzja dwell
**u źródła danych**.

## Zmiany (jedyne — skład BC)
**Z2 AKTYWNE — BC rozszerzone do 400 ep:**
- **300 standardowych** (46000-46299): ekspert standardowy (smoothstep, v_max=1.0, t_ramp=2.0).
- **100 hover-rich** (pula **47200-47299**): ekspert **dolatuje bez zwłoki i TRZYMA ZAWIS do
  końca epizodu** — **maksymalna gęstość stanów zawisu pod wysokim age żywego kanału**.
- Zbieranie **live-fed identycznie** jak reszta (żywy YOLO, kontrakt D3, kanał 5-dim, F2 OFF).
- **Cel mechanizmu:** kubełek **B4** (precyzja dwell) — więcej stanów „trzymaj zawis gdy kanał
  stary" w danych → polityka uczy się utrzymania.

**Realizacja hover-rich (jawnie):** ta sama klasa `HoverExpert` (logika `_smoothstep`
NIETKNIĘTA), lecz szybszy najazd — parametry rampy **v_max=2.0, t_ramp_min=0.5** WYŁĄCZNIE dla
100 epizodów hover-rich (augmentacja danych). Ekspert **standardowy** (config: v_max=1.0,
t_ramp=2.0) — używany do **DAgger, standardowego BC, ewaluacji** — **BEZ ZMIAN**. Env, kamera,
kontrakt, parametry zadania (r_goal/z_hover/t_dwell) — nietknięte.

**Z2' — kurikulum mieszane GT+live: wariant odwodowy, NIEAKTYWNY.** (transfer umiejętności
zawisu z reżimu GT-fed, który dowodnie jej uczy). Aktywacja **wyłącznie osobna decyzja człowieka**.

**STOP-warunek:** PRECONDITION-R6 FAIL → STOP (zero dalszych treningów); raport z rozmową o
**granicy systemowej** i o **ścianie wrong-lock jako odrębnym problemie** (dekompozycja w T4).

Bez zmian: przepis = S3b2-R + **Z1-selektor** (val stratyfikowany z agregatu, seed 45021) +
**ROUNDS=3**, F2 OFF, kontrakt D3, seed 45020, pule DAgger, progi/sceny G1, YOLO. Bramka G1 zamrożona.

## D8 — uzupełnienie (ANEKS-3B-6)
Pula **47200-47299** = **hover-rich BC** (Z2, AKTYWNA w tej sesji).
