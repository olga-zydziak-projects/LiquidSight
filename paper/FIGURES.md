# FIGURES.md — inwentarz figur preprintu (W1, faza 3)

**Data:** 2026-07-24. **BEZ generowania** — tylko inwentarz: dla kazdej figury
dane zrodlowe (sciezka w repo), status eksportu, mapowanie na sekcje szkieletu.
Generowanie figur = W2/pozniej, poza mandatem W1. **Zero nowych pomiarow.**

Status legenda:
- **GOTOWE** — wszystkie dane w plikach `results/*.json` / `git log`, wystarczy
  narysowac (zero odczytu logow, zero pomiaru).
- **CZ. GOTOWE** — czesc danych obecna; dodatkowa warstwa wymagalaby odczytu
  logow/ponownego pomiaru (oznaczone, czego brakuje — NIE dostarczane w W1).

---

## Fig. (a) — Timeline bramek i aneksow programu

**Co:** os czasu 22–24 lipca: commity bramek (P-SANITY, F3_GATE, parytet v1/v2)
i aneksow (A1–A4), kazdy z jednozdaniowym powodem; znaczniki „frozen".
**Dane zrodlowe:**
- `git log --oneline` (24 commity; skroty i tytuly) — sekwencja i daty.
- `DECYZJE_F3.md` (linie ANEKS-1..4 z powodami) + preambuly:
  `ANEKS_1_OBSERWOWALNOSC.md`, `ANEKS_2_DRABINA_OSI.md`,
  `ANEKS_3_KONSTRUKCJA_RDZENI.md`, `ANEKS_4_PROCEDURA_TRENINGU.md`.
- Powody jednozdaniowe: patrz `paper/OUTLINE_MAP.md` (Appendix A) — juz zebrane.
**Status:** **GOTOWE** (dane w git + dokumentach; rysunek = uklad timeline).
**Mapowanie:** Appendix A szkieletu (`SZKIELET_PREPRINT.md §Appendices A`);
wspiera C7.

---

## Fig. (b) — Nominale seed-po-seedzie per noga *(figura glowna wyniku R4)*

**Co:** punkty sukcesu nominalnego per seed dla kazdej z 4 nog (A_NCP/A_CFC ×
{3e-4,1e-3}), z linia sredniej nogi i **poprzeczka progu 90%**. Kontrola
A_GRU=100% jako referencja.
**Dane zrodlowe:**
- `results/i3b/progress.jsonl` — `nominal_pct` per (arm, lr, seed).
- `results/i3b/fazaA_wynik.json` — srednie nog, k rozstrzygniecia.
- `results/smoke_A_GRU_proc2.json` — punkt kontroli 100%.
- Wartosci: NUMBERS.md T2 + T3 + T4.
**Status:** **GOTOWE** (wszystkie punkty obecne; 13 cykli + kontrola).
**Mapowanie:** `SZKIELET §5.4` (fig. b „nominale seed-po-seedzie z poprzeczka
90"); wspiera **C2, C3**.

---

## Fig. (c) — Dynamika rolloutow DAgger per runda per ramie

**Co:** trajektorie sukcesu rolloutow DAgger r1→r2→r3 dla ramion; kontrast
GRU (18→100→100) vs CfC (plaskie/niskie, np. A_NCP@1e-3 s45010 44→32→53;
A_CFC@1e-3 s45012 0→34→44).
**Dane zrodlowe:**
- `results/i3b/progress.jsonl` — pole `dagger_rollout` (r1,r2,r3) per cykl.
- `results/smoke_A_GRU_proc2.json` — `dagger[].rollout_succ_pct` kontroli.
- Wartosci: NUMBERS.md T3 (kolumna rollout) + T4 + T6.
**Status:** **GOTOWE** (rolloutty per runda w JSON).
**Mapowanie:** `SZKIELET §5.4/6` (fig. c „dynamika DAgger"); wspiera **C6** (+C2).

---

## Fig. (d) — Drabina GRU-sanity + sufit eksperta

**Co:** krzywa sukcesu polityki po drabinie osi (T0..T3: 100/100/64/46/36/24/16)
z pasmem [30,85] i wskazaniem poziomu bramki T2b; nalozony sufit eksperta
(100% na kazdym poziomie).
**Dane zrodlowe:**
- `results/psanity_p2r.json` — `sukces_pct` per poziom (polityka), pasmo, K.
- `results/psanity_p3r.json` — ekspert T2a/T2b/T2c=100%; T0–T3 z R1
  (`RAPORT_PSANITY_R2.md §2`).
- Wartosci: NUMBERS.md T5.
**Status:** **GOTOWE** (obie krzywe w JSON; T0–T3 eksperta cytowane z R1 w PR2).
**Mapowanie:** `SZKIELET §7` (C8 charakteryzacja); Appendix. Wspiera **C8**.

---

## Fig. (e) — Trendy best_val: BC vs agregat DAgger

**Co:** best_val per etap (r0=BC → r1→r2→r3=agregat) dla ramion CfC (rosnie po
agregacji, best_epoch wczesnieje) kontra GRU (monotonicznie nisko). Sygnatura
mechanizmu granicy (C6a).
**Dane zrodlowe:**
- `results/i3b/progress.jsonl` — `best_val_r` (4 punkty r0..r3) + `best_epoch_r`
  per cykl.
- `results/smoke_A_GRU_proc2.json` — `bc.best_val` + `dagger[].best_val` kontroli
  (.000168→.000247→.000179→.000112).
- Wartosci: NUMBERS.md T3 (best_val r0→r3) + T4.
**Status:** **CZ. GOTOWE** — best_val **per runda** (4 punkty r0..r3) obecny dla
wszystkich cykli → wersja round-level GOTOWA. **Brak:** pelne krzywe val po 120
epokach per etap (procedura je liczy, ale `progress.jsonl` zapisuje tylko
best_val/best_epoch per runda; `train_curve`/`val_curve` nie sa persystowane w
i3b). Pelna krzywa epokowa wymagalaby **ponownego pomiaru** (odpalenie z
checkpointu) → **poza zakresem W1** (zakaz nowych pomiarow). Rekomendacja: figura
(e) w wersji round-level (4 punkty), bez krzywej epokowej.
**Mapowanie:** `SZKIELET §6` (fig. e „best_val BC vs agregat"); wspiera **C6/C6a**.

---

## PODSUMOWANIE INWENTARZA

| figura | status | dane w repo | wspiera |
|---|---|---|---|
| (a) timeline | GOTOWE | git log + DECYZJE_F3 + aneksy | C7 |
| (b) nominale/noga | GOTOWE | progress.jsonl, fazaA_wynik.json, Gru2 | C2, C3 |
| (c) DAgger rollout | GOTOWE | progress.jsonl, Gru2 | C6, C2 |
| (d) drabina + sufit | GOTOWE | psanity_p2r.json, psanity_p3r.json | C8 |
| (e) best_val BC vs agregat | CZ. GOTOWE (round-level; brak krzywej epokowej) | progress.jsonl, Gru2 | C6, C6a |

**Gotowe do eksportu: 4** (a, b, c, d). **Czesciowo: 1** (e — round-level tak,
pelna krzywa epokowa wymaga ponownego pomiaru = poza W1).
Wszystkie dane zrodlowe sa w `results/` lub `git log` — **zadna figura nie
wymaga nowego treningu ani ewaluacji OOD**. Generowanie: W2.
