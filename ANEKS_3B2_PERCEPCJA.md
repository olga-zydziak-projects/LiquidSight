# ANEKS-3B-2 do DECYZJE_3B — percepcja i dostarczanie (2026-07-27)

Powod: PRECONDITION-R FAIL (67% / wrong-lock 10%). DIAG-lite (wzbogacony audyt,
1 przebieg na ZAMROZONYM modelu — bez treningu/strojenia) dekomponuje **33 porazki**
na kubelki:

| kubelek | opis | epizody | pp |
|---|---|---|---|
| **B1** | nigdy-nie-zlockowane (brak designated-ticku) | 3 | **3.0** |
| **B2** | pozno-zlockowane (pierwszy designated-tick > 3 s) | 0 | **0.0** |
| **B3** | kradziez tozsamosci w martwym polu (lock poprawny w dolocie, nadpisany other przy dist<0.7 m) | 3 | **3.0** |
| **B4** | lock poprawny do konca, epizod PRZEGRANY (dwell/no-arrival, kanal poprawny) | **27** | **27.0** |

Rozklad dystansu drona w momencie other-tickow: mediana **0.168 m**, **87% w martwym
polu (<0.7 m)** — potwierdza mechanizm kradziezy (ale to tylko 3 pp).

**Ustalenie:** dominuje **B4 = 27 pp** — polityka ma POPRAWNY lock przez caly epizod,
a i tak nie dolatuje/nie utrzymuje. To **nie problem percepcji ani kanalu** (te sa zdrowe:
locka wskazanego caly dolot); to wlasnosc wykonawcy/warunkowania przy szumnym-ale-poprawnym
kanale.

## Dzwignie warunkowe (aktywacja WYLACZNIE wg regul; arytmetyka na T1)
**L1 — FOV kamery semantycznej 60→90 st. (pitch bez zmian).**
- Regula aktywacji: `B3 >= 4 pp` LUB `(B1+B2) >= 6 pp`.
- Ewaluacja T1: B3=3.0 (<4), B1+B2=3.0 (<6) → **NIEAKTYWNA**.
- Bramka wejsciowa (offline probe FOV 90) **NIE uruchomiona** (dzwignia nieaktywna).

**L2 — gating dostarczen (logika kanalu): nowy box nadpisuje ZOH tylko gdy
`IoU(box, ostatni ZOH) >= 0.2` LUB `age_s > 2.0` (re-akwizycja); odrzucone logowane.**
- Regula aktywacji: `B3 >= 2 pp`.
- Ewaluacja T1: B3=3.0 (≥2) → **regula spelniona (aktywowalaby sie)**.

**L3 — reguła STOP: `B4 >= 8 pp` LUB `B1 >= 8 pp` przy NIEAKTYWNEJ L1 → STOP po T2**
(raport + decyzja czlowieka, **bez treningu**).
- Ewaluacja T1: B4=27.0 (≥8) ∧ L1 nieaktywna → **STOP WYZWOLONY**.

## Werdykt ANEKS-3B-2: **L3 STOP**
Dominujaca dziura (B4, 27 pp) **nie jest adresowalna** przez dostepne dzwignie
(L1 FOV / L2 gating dotykaja percepcji i kanalu — a te sa poprawne). L2 (3 pp B3)
i L1 (nieaktywna) sa marginalne wobec B4. Zgodnie z L3: **STOP po T2** — **zadnego
retreningu w tej sesji**; naprawa B4 wymaga dzwigni SPOZA listy (wykonawca/warunkowanie/
sygnal uczacy) = **decyzja czlowieka** (poza mandatem: kamera polityki, ekspert, progi,
scena — nietykalne; nowa dzwignia = nowy aneks).

Bez zmian: kontrakt D3 poza gatingiem (nieaktywny — STOP), procedura v2, seed 45020,
pule, progi/sceny G1, ekspert, env, konfiguracja YOLO. Bramka G1 pozostaje zamrozona.
