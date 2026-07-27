# RAPORT_S3B2R2 — DIAG-lite + ANEKS-3B-2 (dźwignie warunkowe) → L3 STOP

**Data:** 2026-07-27. **Sesja:** S3b2-R2. **Zakres:** DIAG-lite porażek PRECONDITION-R →
ANEKS-3B-2 z dźwigniami warunkowymi → (reguła L3) **STOP przed treningiem**. G1_GATE.md
**FROZEN**. MIERZĘ = RAPORTUJĘ. **Werdykt sesji: L3 STOP — bez retreningu, decyzja człowieka.**

## T1 — DIAG-lite: dekompozycja 33 porażek PRECONDITION-R (67% sukces)
**Uwaga metodyczna (jawnie):** istniejący `precond_R_audit_tick_audit.jsonl` nie zawierał
dystansu drona ani per-epizod fail_type (potrzebnych dla B3/B4). DIAG-lite wykonał **jeden
wzbogacony audyt na ZAMROŻONYM modelu** (zero treningu/strojenia; model/config/kanał/env/
ekspert bez zmian) — to pomiar diagnostyczny, nie „bieg" naprawczy.

| kubelek | mechanizm | epizody | pp |
|---|---|---|---|
| **B1** | nigdy-nie-zlockowane (brak designated-ticku) | 3 | **3.0** |
| **B2** | późno-zlockowane (>3 s) | 0 | **0.0** |
| **B3** | kradzież tożsamości w martwym polu (dist<0.7 m) | 3 | **3.0** |
| **B4** | **lock poprawny do końca, epizod PRZEGRANY** | **27** | **27.0** |

- Rozkład dystansu w momencie other-tickow: **mediana 0.168 m, 87% w martwym polu (<0.7 m)**
  — mechanizm kradzieży potwierdzony, ale marginalny (3 pp).
- **Dominuje B4 = 27 pp:** polityka ma poprawny lock przez cały epizod, a i tak nie dolatuje/
  nie utrzymuje. **Percepcja i kanał zdrowe** (locka wskazanego cały dolot); problem leży
  **w wykonawcy/warunkowaniu** przy szumnym-ale-poprawnym kanale — **nie w percepcji**.

## T2 — ANEKS-3B-2: dźwignie warunkowe (aktywacja wg arytmetyki na T1)
| dźwignia | reguła | ewaluacja T1 | status |
|---|---|---|---|
| **L1** FOV 60→90° | B3≥4 **lub** (B1+B2)≥6 | B3=3<4, B1+B2=3<6 | **NIEAKTYWNA** (bramka offline nieuruchomiona) |
| **L2** gating dostarczeń (IoU≥0.2 ∨ age>2.0) | B3≥2 | B3=3≥2 | reguła spełniona (aktywowałaby się) |
| **L3** STOP | (B4≥8 **lub** B1≥8) ∧ L1-nieaktywna | B4=27≥8 ∧ L1-nieakt. | **STOP WYZWOLONY** |

**Wynik bramki L1:** dźwignia L1 **nieaktywna** (reguła niespełniona) → jej bramka wejściowa
(offline probe FOV 90, sondy 46900-46959) **NIE była uruchamiana**.

## Werdykt: **L3 STOP** (bez treningu)
B4 (27 pp) — dominująca dziura — **nie jest adresowalna** przez L1 (FOV) ani L2 (gating): obie
dotykają **percepcji/kanału, a te są poprawne**. Zgodnie z regułą L3, przy dominującym B4 i
nieaktywnej L1, sesja **STOP po T2**: **żadnego retreningu**, **PRECONDITION-R2 i G1-R
NIEURUCHOMIONE**. Naprawa B4 wymaga dźwigni **spoza listy** (wykonawca / warunkowanie /
sygnał uczący — nie percepcja) = **decyzja człowieka** (kamera polityki, ekspert, progi,
scena — nietykalne; nowa dźwignia = nowy aneks).

## Kontekst i tabela (stan diagnozowany = PRECONDITION-R, S3b2-R)
Postęp naprawy: **12% (G1-FAIL) → 67% (S3b2-R, conf usunięty + live-fed)**. Reszta 33% =
B1 3 + B2 0 + B3 3 + **B4 27** pp. Per-komórka PRECONDITION-R (nie zmieniana w tej sesji):

| K×A | sukces | | K×A | sukces |
|---|---|---|---|---|
| K3_A0 | 64.7% | | K5_A1 | 50.0% |
| K3_A1 | 82.4% | | K8_A0 | 82.4% |
| K5_A0 | 76.5% | | K8_A1 | 43.8% |

A1 (kolor współdzielony) najsłabsze — spójne z resztkową kradzieżą (B3) + B4.

## Do decyzji człowieka (poza mandatem sesji)
B4 = 27 pp (lock poprawny, epizod przegrany) wskazuje na **wykonawcę/warunkowanie**, nie
percepcję. Kandydaci (nowy aneks, decyzja Olgi):
1. **Reward/kryterium dwell przy szumnym kanale** — polityka ma cel, ale traci precyzję
   zawisu; sprawdzić profil dwell w B4.
2. **Warunkowanie/pojemność rdzenia** — 5-dim kanał + GRU może nie utrzymywać celu w martwym
   polu tak stabilnie jak GT-fed (pamięć).
3. **L2 gating** (marginalny, 3 pp) — do rozważenia łącznie z powyższym, nie samodzielnie.
Rekomendacja sesji: **najpierw zdiagnozować B4** (profil dwell/no-arrival przy poprawnym
locku) — dopiero to wskaże właściwą dźwignię.

Artefakty: `results/s3b2r/{diag_lite,diag_lite_episodes}.json`. Bramka G1 — nietknięta.
Aneks: `ANEKS_3B2_PERCEPCJA.md` + linia w `DECYZJE_3B.md`.
