# RAPORT_I3AR — ramiona po ANEKS-3: parytet v2 + smoke nominalny

**Data:** 2026-07-23
**Status:** **Parytet v2 PASS • smoke nominalny FAIL (fix konieczny, ale NIEWYSTARCZAJACY).** ANEKS-3 naprawil KONSTRUKCJE rdzeni (backbone / ts=sekundy / readout) — BC-only jest teraz STABILNY — ale oba ramiona CfC nadal nie osiagaja precondition (4% nominal). Zlokalizowano pozostala przyczyne: **procedura DAgger bramki (continue + final-epoch) DESTABILIZUJE CfC** (A_CFC → tilt 78/100, A_NCP → kolaps rollout 1→0→0), czego aneks (z zalozenia konstrukcyjny) nie dotykal. **I3b NIE GOTOWE.** Zero OOD. **MIERZĘ = RAPORTUJĘ.**

---

## 0. Srodowisko
Maszyna/wersje jak I3a (RTX 5070 Ti, CUDA; Python 3.12.13; torch 2.11.0+cu128; **ncps 1.0.1**; pybullet 3.2.7; gpd `e712698`). Smoke: seed 45010, lr 3e-4 (F3_GATE par.3), wylacznie nominal (43000-43099). Warianty diag z RAPORT_DIAG_CFC nietkniete.

---

## 1. Parytet v2 (T2, po ANEKS-3) — PASS

| ramie | konfiguracja | rdzen | delta% | glowa |
|---|---|---|---|---|
| A_GRU | GRUCell(78→64) | 27 648 | +0.00% | 390 |
| A_NCP | CfC(78, AutoNCP(64,6,seed0)); readout stan pelny; ts=0.0833s manual | 27 571 | −0.28% | 390 |
| A_CFC | CfCCell(78, hidden=64, backbone=69); ts=0.0833s manual | 27 787 | +0.50% | 390 |

Rdzenie w pasmie ±2%; **glowy identyczne 390** (symetria twin). `MANIFEST_F3.gate_arms_v2` (poprzednia → `gate_arms_v1`). Uwaga: aneks Z1 proponowal A_CFC units=70/bb=64 (→glowa 426); zrealizowano hidden=64/bb=69 dla zachowania parytetu ORAZ symetrii glow Linear(64→6)=390 (Z3/T2) — rozbieznosc odnotowana.

---

## 2. Smoke nominalny pelnocyklowy (T3) — FAIL

BC-15 + DAgger×3, seed 45010, lr 3e-4, eval nominal 43000-43099.

| ramie | nominal | BC MSE (start→koniec) | DAgger rollout (r1→r2→r3) | porazki (dwell/tilt) | cykl |
|---|---|---|---|---|---|
| A_NCP | **4.0%** | 0.272 → 0.0085 | 1 → 0 → 0 | 82 / 14 | 691 s |
| A_CFC | **4.0%** | 0.248 → 0.0079 | 4 → 2 → 3 | 18 / **78** | 492 s |
| (A_GRU R1, ref) | 100% | 0.156 → 0.0013 | 2 → 57 → 100 | — | 444 s |

BC fituje lepiej niz przed aneksem (A_NCP 0.0085 vs 0.047; readout pelnego stanu dziala), ale **closed-loop nadal zawodzi**: A_NCP kolapsuje (DAgger 1→0→0, dwell), **A_CFC staje sie NIESTABILNY (tilt 78/100)** — nowy tryb porazki.

Patologia par.3 (NaN / brak spadku straty / ~0%): literalnie nie (strata maleje, 4%>1%), ale **cel precondition (≥90%) niespełniony** — smoke jest walidacja naprawy i **naprawa nie domknela precondition**.

---

## 3. Lokalizacja pozostalej przyczyny — procedura DAgger destabilizuje CfC

| konfiguracja (A_CFC) | dolot→r_goal | tilt | uwaga |
|---|---|---|---|
| BC-8 (diag, komorka frozen) | 39/50 | **0** | stabilny, dwell-only |
| BC-15 only (binding, bez DAgger) | 17/50 | **0** | **stabilny, zero tilt** |
| BC-15 + DAgger×3 (binding) | — | **78/100** | **niestabilny po DAgger** |

**Dowod:** A_CFC jest STABILNY po samym BC (0 tilt w obu probach BC-only), a **tilt 78 pojawia sie DOPIERO po DAgger**. Zatem instabilnosc jest **indukowana procedura DAgger** (continue od wag BC + 10 epok + final-epoch na zbiorze zdominowanym przez stany-porazki polityki), NIE konstrukcja ani przedluzonym BC. A_NCP analogicznie kolapsuje pod DAgger.

To pozostala rozbieznosc z zlotym przepisem frozen C1 (RAPORT_DIAG_CFC, tabela T1), ktorej ANEKS-3 z zalozenia nie ruszal (budzety/procedury par.3-4 „bez zmian"):
- frozen C1: **retrening OD ZERA co runde + wybor best-val checkpoint + 120 epok**;
- bramka F3_GATE: **continue + final-epoch + BC-15/DAgger-10** (robust dla GRU, destabilizuje CfC).

---

## 4. Gotowosc do I3b — NIE

Precondition par.4 (≥90% nominal per ramie) **niespełniony** dla obu ramion CfC (4%) mimo naprawy konstrukcji. Bieg wiazacy I3b groziłby STOP par.4 bez werdyktu tezy. **Blokada: procedura treningu (DAgger continue+final-epoch), nie konstrukcja.**

---

## 5. Decyzja czlowieka (bloker)
ANEKS-3 (naprawa konstrukcji) byl **konieczny, ale niewystarczajacy**. Pozostaly bloker to procedura DAgger bramki. Opcje (kazda to zmiana par.3/par.4 = poza mandatem I3a-R):
- **(A′) ANEKS-4 — procedura treningu wg frozen C1**: wybor best-val checkpoint (min.) i/lub retrening od zera co runde, i/lub wiecej epok — SYMETRYCZNIE dla wszystkich ramion (A_GRU retrenowany ta sama procedura, by budzet pozostal rowny). Rekomendacja: to bezposrednio adresuje zlokalizowana przyczyne i przywraca przepis, ktory dzialal w v1.0.
- **(B) mini-sweep** budzetu/procedury wszystkich ramion (precedens P0).
- Uwaga tezowa: zmiana musi byc SYMETRYCZNA (ten sam budzet/procedura dla GRU i CfC), inaczej narusza parytet budzetu treningu (rdzen tezy).

**Nie rekomendowane:** uruchamiac I3b na obecnym stanie (precondition FAIL pewny).

---

## 6. Zgodnosc z zakresem
ANEKS-3 zaimplementowany (Z1-Z3), parytet v2 dowiedziony. Zero OOD (tylko nominal). F3_GATE par.2-7 (poza zakresem aneksu), P_SANITY, env/expert/config/frozen_v1/checkpoint sanity **nietkniete**. Sondy lokalizacyjne w results/diag/. Nie zmieniano procedury treningu (to wymaga decyzji czlowieka).

---

## STOP
Parytet v2 PASS (rdzenie ±2%, glowy 390). Smoke FAIL: oba ramiona CfC 4% — naprawa konstrukcji konieczna, ale niewystarczajaca; **pozostala przyczyna zlokalizowana: procedura DAgger (continue+final-epoch) destabilizuje CfC** (A_CFC stabilny po BC, tilt dopiero po DAgger). I3b NIE gotowe → decyzja czlowieka (ANEKS-4: procedura treningu wg frozen C1, symetrycznie). Nic wiecej nie zmieniam.
