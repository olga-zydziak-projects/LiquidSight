# RAPORT_I3A — ramiona twin + parytet + smoke nominalny (I3a)

**Data:** 2026-07-23
**Status:** **F3_GATE zamrozony • parytet rdzeni PASS • smoke nominalny: KRYTYCZNE USTALENIE.** Oba ramiona CfC (A_NCP, A_CFC) **nie osiagaja zdolnosci nominalnej** w pipeline BC+DAgger przy OBU wartosciach siatki lr F3_GATE ({3e-4, 1e-3}): A_NCP 12%/19%, A_CFC 10%/18% — podczas gdy A_GRU (kontrola, ten sam harness) osiaga **100%**. **Zero ewaluacji OOD** (wylacznie T0/nominal). **MIERZĘ = RAPORTUJĘ.**

Konsekwencja: warunek zdolnosci nominalnej F3_GATE par.4 (>=90% per ramie) jest w smoke **niespełniony dla ramion CfC przy wyczerpanej siatce fallback** — bieg wiazacy I3b groziłby STOP par.4 („bez werdyktu tezy"). **Decyzja czlowieka wymagana przed I3b** (sekcja 6). F3_GATE **nietkniety** (zamrozony w tej sesji, par.2).

---

## 0. Maszyna i srodowisko

| pozycja | wartosc |
|---|---|
| GPU / CPU | NVIDIA RTX 5070 Ti Laptop (CUDA) / Intel Ultra 9 275HX |
| Python / uv | CPython 3.12.13 / uv 0.11.28 |
| torch | 2.11.0+cu128 |
| **ncps** | **1.0.1** (metadane dystrybucji = frozen requirements.lock) |
| pybullet / numpy / pillow | 3.2.7 / 2.5.1 / 12.3.0 |
| gym-pybullet-drones | 2.1.0, `e712698` (external/) |

### Incydent srodowiskowy (ncps) — falszywy alarm, bez naprawy
T0 zglosil pozornie `ncps 0.0.2` vs lock `1.0.1`. Diagnoza (mandat czlowieka, D1-D3):
- **D1** pelny `uv pip freeze` vs `requirements.lock`: **0 rozbieznosci** (55/55 pakietow, w tym ncps==1.0.1). Jedyna roznica: editable gpd → `external/` (oczekiwana, udokumentowana w RAPORT_I1).
- **Przyczyna**: `ncps.__version__` = stringu `"0.0.2"` zaszytego w zrodle ncps 1.0.1 (znany bug pakietu — nie zbumpowali). Metadane dystrybucji (`importlib.metadata.version`) = **1.0.1** = lock.
- **D2**: ncps niewzmiankowany w RAPORT_I1/S0 (niepotrzebny wtedy); zaden downgrade nie mial miejsca (metadane od zawsze 1.0.1).
- **D3**: `uv pip install ncps==1.0.1 --dry-run` → „Would make no changes".
- **Naprawa: zadna** (brak rozbieznosci). N1-N3 nieuruchamiane. T0 zaliczone.

---

## 1. Ramiona i dowod parytetu (T2)

Wspolne: enkoder jak P-SANITY (nowe instancje, zero wspoldzielenia wag), glowa Linear(rdzen→6) z tym samym skalowaniem, wejscie rdzenia 78, TwinPolicy. Native ts=None (dt zadania stale 12 Hz → bramka czasu stala; dt obecne jako cecha wejscia).

| ramie | konfiguracja rdzenia | rdzen param | delta% | pasmo [27095,28201] |
|---|---|---|---|---|
| A_GRU | GRUCell(78→64) | 27 648 | +0.00% | OK (ref) |
| **A_NCP** (orzekajace) | CfC(78, AutoNCP(units=64, out=6, seed=0)) | **27 571** | −0.28% | **OK** |
| **A_CFC** (opisowe) | CfC(78, units=53, backbone_layers=0) | **27 984** | +1.22% | **OK** |

Dowod przez automatyczne wyszukanie rozmiarow (najblizszy 27 648 w pasmie ±2%). `gate_arms` dopisane do MANIFEST_F3.json. Forward sanity (B,T,6) — OK dla wszystkich. Implementacja na ncps 1.0.1 (`ncps.torch.CfC`; dense oraz z okablowaniem `AutoNCP`).

---

## 2. Smoke nominalny (T3) — pipeline zdrowy, ramiona CfC niekompetentne

Pelny cykl BC(15 epok)+DAgger×3(10 epok) na seed 45010, ewaluacja **wylacznie nominal 43000-43099**. lr wg F3_GATE par.3 (3e-4 dla CfC); **informacyjnie** dodano lr 1e-3 (druga wartosc pre-rejestrowanej siatki fallback par.3) by odroznic „za niski lr" od „ramie nie trenuje"; oraz **kontrole A_GRU** (walidacja harnessu).

| ramie | lr | BC MSE (start→koniec) | DAgger rollout% (r1→r2→r3) | **nominal** | porazki (dwell/tilt) | cykl treningu |
|---|---|---|---|---|---|---|
| A_NCP | 3e-4 (gated) | 0.261 → 0.047 | 2 → 6 → 0 | **12.0%** | 77/11 | 675 s |
| A_NCP | 1e-3 (fallback) | 0.226 → 0.014 | 1 → 0 → 0 | **19.0%** | 75/6 | 662 s |
| A_CFC | 3e-4 (gated) | 0.223 → 0.0067 | 7 → 1 → 8 | **10.0%** | 65/25 | 544 s |
| A_CFC | 1e-3 (fallback) | 0.157 → **0.0020** | 1 → 3 → 3 | **18.0%** | 81/1 | 492 s |
| **A_GRU** (kontrola) | 1e-3 | 0.156 → 0.0013 | **2 → 57 → 100** | **100.0%** | — | 444 s |

**Interpretacja (twarda):**
1. **Harness poprawny.** A_GRU w TYM SAMYM harnessie (smoke_arm) osiaga 100% z DAgger 2→57→100 — identycznie jak P-SANITY R1. Wynik ramion CfC nie jest artefaktem pipeline'u.
2. **To nie brak pojemnosci imitacji.** A_CFC (lr 1e-3) osiaga BC MSE **0.0020** — niemal rownie nisko jak GRU (0.0013). Ramie CfC imituje trajektorie eksperta dobrze, ale **zawodzi w petli zamknietej**.
3. **DAgger nie ratuje ramion CfC.** Mechanizm, ktory podnosi GRU (2→57→100), na CfC jest plaski/kolapsuje (A_CFC 1→3→3; A_NCP 1→0→0). Korekta kowariancyjnego shiftu nie dziala dla rdzeni CfC w tym zadaniu.
4. **Porazki zdominowane przez „dwell"** (65-81 / ~82-90) — dron leci, ale nie utrzymuje precyzyjnie zawisu nad celem. Hipoteza (do diagnozy, nie naprawiana tu): pamiec CfC (ciagla, ts stale) nie trzyma pozycji celu po jego wyjsciu z kadru tak stabilnie jak stan GRU.
5. **Siatka fallback par.3 wyczerpana:** oba lr {3e-4, 1e-3} → nominal 10-19% ≪ 90%.

**Patologie par.3 (NaN / brak spadku straty / ~0% nominal):** literalnie **nie zaszly** (strata maleje monotonicznie, brak NaN, nominal >1%). Smoke jest informacyjny — nie zmieniono bramki, checkpointy smoke nie wchodza do I3b.

---

## 3. Czasy scienne (W5, jednostka kosztu I3b)

Pelny cykl treningu (BC+3×DAgger) per ramie, seed 45010:

| ramie | cykl treningu | uwaga |
|---|---|---|
| A_GRU | ~444 s (7.4 min) | zgodny z P-SANITY R1 (~420 s) |
| A_NCP | ~662-675 s (11.2 min) | per-step ncps CfC (wired) — launch-bound na GPU |
| A_CFC | ~492-544 s (8.7 min) | per-step ncps CfC (dense) |

Projekcja I3b (n=10 seedow × 3 ramiona), gdyby precondition spełniony: ≈ 10×(7.4+11.2+8.7) ≈ **4.6 h** treningu (bez ewaluacji sweep). **Uwaga:** ncps CfC per-step jest ~1.5× wolniejszy niz GRU (petla Pythona po 120 tikach).

---

## 4. Zero ewaluacji OOD — potwierdzenie

W calej sesji I3a **nie uruchomiono zadnej ewaluacji poza T0/nominal** (43000-43099). Sceny sweep (43100-43149) i poziomy T1-T3/T2a-T2c **nietkniete**. Zgodnie z regula 3 i par.4 (zakaz OOD przed spełnieniem precondition).

---

## 5. Zgodnosc z zakresem

F3_GATE zamrozony (par.2) i **nietkniety** po commicie. Parytet dowiedziony i w MANIFEST. Strojenie wylacznie na T0. Checkpoint sanity (P1) nietkniety, nie uczestniczy w twin. Frozen_v1/ i liquidflight/ nietkniete. Ramiona CfC nie byly „naprawiane" poza pre-rejestrowana siatka lr — glębsza zmiana (architektura/epoki/pipeline) bylaby modyfikacja frozen gate/instrumentu, poza zakresem I3a.

---

## 6. Decyzja czlowieka przed I3b (BLOKER)

**Ustalenie:** ramiona CfC (parytetowe, wierne ncps) nie osiagaja precondition par.4 (>=90% nominal) w pipeline BC+DAgger przy wyczerpanej siatce lr {3e-4, 1e-3}, gdy GRU w identycznym harnessie osiaga 100%. Bieg wiazacy I3b groziłby STOP par.4 dla A_NCP i A_CFC — **bez werdyktu tezy**.

**To wymaga decyzji czlowieka** (kazda opcja poza par.4-nominal jest zmiana frozen gate / instrumentu, wiec poza mandatem tej sesji):
- **(a) Diagnoza CfC** przed I3b: zbadac, czemu DAgger nie podnosi CfC i czemu „dwell" dominuje (hipoteza: pamiec/precyzja zawisu; ts, tryb CfC 'default' vs 'no_gate', normalizacja wejscia, liczba rund/epok DAgger). Rekomendacja techniczna — najtaniej rozstrzyga „czy CfC da sie w ogole wytrenowac na to zadanie".
- **(b) Rewizja par.3/par.4** (aneks do F3_GATE): np. szersza siatka lr / wiecej epok / wiecej rund DAgger dla ramion liquid — ale to zmiana zamrozonego budzetu treningu (rownosc budzetu vs zdolnosc — napiecie tezy).
- **(c) Uznac wynik** i uruchomic I3b ze swiadomoscia, ze precondition CfC prawdopodobnie FAIL → STOP par.4 (kosztowne ~4.6 h bez werdyktu). Nierekomendowane.

**Decyzje odroczone (po rozwiazaniu blokera):** poziom bramki T2b (zamrozony), n=10, dense-CfC vs AutoNCP — obie w twin (A_NCP orzekajace, A_CFC opisowe).

---

## STOP

F3_GATE zamrozony; parytet PASS (A_GRU 27648 / A_NCP 27571 / A_CFC 27984, wszystkie ±2%); smoke nominalny ujawnil, ze **ramiona CfC nie osiagaja precondition** (10-19%) przy obu lr fallback, podczas gdy A_GRU=100% (harness zwalidowany). Zero OOD. **Bloker I3b → decyzja czlowieka** (sekcja 6). Nic wiecej nie zmieniam.
