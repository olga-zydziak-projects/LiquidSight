# RAPORT_DIAG_3B — dekompozycja G1-FAIL + skwantyfikowane opcje (diagnostyka)

**Data:** 2026-07-27. **Sesja:** DIAG-3B. **Cel:** rozłożyć stratę **88 pp** G1 (sufit
GT-fed 100% → live 12%) na źródła, zmierzyć realną obwiednię percepcji live i realne
sufity grounderów, i **skwantyfikować opcje aneksu** — **niczego nie naprawiając**.
Polityka (ckpt 45020), configi YOLO/OWLv2, env, ekspert, kontrakt D3 — **FROZEN**.
MIERZĘ = RAPORTUJĘ. Artefakty: `results/diag3b/`.

## Wynik nadrzędny (dekompozycja 88 pp)
| składowa | pp | metoda |
|---|---|---|
| **(i)** poza-FOV fałszywe locki | **0.0** | gate_infov(12%) − live(12%) |
| **(ii)** błędy groundera w FOV | **0.0** | oracle(12%) − gate_infov(12%) |
| **(iii)** conf-shift + polityka | **88.0** | sufit(100%) − oracle(12%) |

**Cała strata to (iii).** Nawet **oracle** (dostarczaj kanał TYLKO gdy wskazany w FOV
**i** grounder trafił w niego — czyli same idealne locki, lecz z **żywym conf ~0.02**)
daje wciąż **12%**. Dokładność groundera i widoczność **nie kontrybuują** — są
**zamaskowane** przez conf. **Test rozstrzygający:** ten sam oracle box + **conf wymuszony
1.0** → **80.0%** (skok **12→80%, +68 pp** z samej zmiany conf). Wniosek: **conf-shift jest
dominującym zabójcą (~68 pp)**; reszta (80→100, ~20 pp) to gęstość/jakość locków, widoczna
**dopiero po naprawie conf**.

> **Korekta interpretacji RAPORT_S3B3:** wcześniejsza hipoteza (rozjazd dystrybucji
> klatek + mylenie kształtu przy conf≈0) jako główne przyczyny — **obalona dowodowo**:
> te mechanizmy kontrybuują **0 pp**. Grounder jest dobry, gdy wskazany widoczny; problemem
> jest, że polityka trenowana na conf=1.0 nie działa na żywym conf ~0.02.

## T1 — audyt kanału GT: **FIZYCZNY**
Kod `env._render_semantic`: `gt_bbox_256 = bbox_from_mask(seg256, designated_id)`; poza FOV
seg ma 0 px → `None` → `TargetTracker.observe` pomija → **ZOH ostatniego widocznego locka**.
Sonda (500 tików): poza-FOV **396 tików, WSZYSTKIE (396) niosły ZOH ostatniego in-FOV boxa**,
0 no-lock, **0 pozycji poza-FOV**. **Werdykt: kanał FIZYCZNY** — sufit 100% z S3b2 mierzył
wykonawcę z *idealną wczesną desygnacją + pamięcią mostkującą martwe pole*, nie kanał
nadfizyczny. **Liczby wiersza odniesienia stoją; interpretacja doprecyzowana.**

## T2 — obwiednia widoczności live (lot eksperta, 50 ep sweep, seg≥3 px w 256²)
- **Frakcja tików z wskazanym w FOV: średnia 0.208** (min **0.20**, max **0.212**) —
  **jednorodna** po K×A (widoczność to geometria, nie trudność atrybutowa).
- **Profil vs dystans:** ≥0.5 m = **1.00**, <0.5 m (przy celu) = **0.015**. To **martwe pole
  terminalne ANEKS-1**: wskazany widoczny w dolocie, **znika gdy dron zawisa nad celem**.
  Większość tików to faza terminalna (dwell przy celu) → stąd 20.8% in-FOV.

## T3 — realne sufity grounderów na dystrybucji z pozy drona (500 klatek)
| grounder | in-FOV (104): designated / other / no-det | poza-FOV (396): other(fałszywy lock) / no-det | conf med in-FOV |
|---|---|---|---|
| **YOLO-World** | **85.6%** / 9.6% / 4.8% | 11.1% / 88.9% | 0.017 |
| **OWLv2** | **99.0%** / 1.0% / 0.0% | 21.2% / 0.0% (bg 78.8%) | 0.177 |
YOLO in-FOV 85.6% ≈ offline 86.8% (spójne). OWLv2 in-FOV **99%**, ale **poza-FOV zawsze
zwraca box** (21.2% fałszywych locków vs YOLO 11.1%). **Sufity in-FOV: YOLO 85.6 / OWLv2 99.0.**

## T4 — audyt conf-pipeline
- **Próg YOLO (frozen) = 0.0** (top-1 zawsze). **Transform w kanale = RAW** (target[4] = surowy
  score, bez normalizacji/klipu).
- **conf median (wspólna skala):** trening GT-fed **1.0** · S3b0-offline YOLO **0.024** ·
  live YOLO in-FOV **0.017** · live OWLv2 in-FOV **0.177**.
- **Niska conf NIE psuje precyzji@1 groundera** (top-1 box bywa poprawny) — **psuje WEJŚCIE
  polityki**: kanał podaje conf ~50–100× mniejszy niż w treningu (1.0) → polityka OOD.

## Realne sufity (T5b): in-FOV vs all
| | YOLO in-FOV | OWLv2 in-FOV | uwaga |
|---|---|---|---|
| precision@1 | 85.6% | 99.0% | sufit percepcji, gdy wskazany widoczny |
| poza-FOV fałszywy lock | 11.1% | 21.2% | koszt niewidoczności |

## Opcje ANEKS-3B (skwantyfikowane; ŻADNYCH wdrożeń)
Kluczowe: strata to **(iii) conf-shift**; (i)+(ii) = 0 pp (zamaskowane). Stąd:

**(A) Rewizja obserwowalności** (stożek czołowy dla WSKAZANEGO / dla wszystkich K / szersze
FOV kamery): adresuje **widoczność → (i)+(ii)**. Z T2: mogłaby podnieść in-FOV z 20.8% ku
~100% (usuwając martwe pole). **ALE (i)+(ii)=0 pp** w obecnym potoku → **(A) SAMA odzyskuje
~0 pp** (oracle z pełną widocznością wciąż 12% przy żywym conf). Sens **dopiero po (B)**,
wtedy adresuje resztę ~20 pp.

**(B) Kanał live-fed w treningu** (conf/box z rozkładu T3 zamiast GT conf=1.0): **adresuje
(iii) = 88 pp** — jedyna opcja atakująca dominującą przyczynę. Dowód potencjału: oracle+conf1.0
= **80%**, więc polityka ucząca się ufać niskiej/zmiennej conf i mostkować martwe pole może
odzyskać większość 88 pp. **(B) jest KONIECZNA.**

**(C) OWLv2 live @0.5 Hz:** in-FOV precision **99%** (vs 85.6), conf **0.177** (vs 0.017, ~10×).
Ale conf wciąż ≪1.0 → **conf-shift trwa** → **(C) SAMA odzyskuje niewiele** (żywy conf dominuje;
oracle-live-conf = 12% niezależnie od jakości boxa). Dodatkowo poza-FOV **gorszy** (21.2%
fałszywych locków). Sens **dopiero po (B)** (lepszy grounder + wyższa conf pomogą reszcie).

**(D) Kombinacje:** **(B) obowiązkowa**; A/C addytywne **tylko po B**. B+A (conf + widoczność)
lub B+C (conf + lepszy grounder/wyższa conf) celują w pełne odzyskanie (~80–100%).

## STOP — rekomendacja (jedno zdanie)
**(B) kanał live-fed w treningu** jest jedyną ścieżką atakującą dominującą przyczynę
(conf-shift = 88 pp); (A) i (C) same odzyskują ~0 pp (zamaskowane przez conf) i mają sens
wyłącznie jako dodatek PO (B).

*(To diagnoza — nie aneks, nie wdrożenie. Decyzja o aneksie należy do człowieka.)*
Artefakty: `results/diag3b/{visibility,rebench,decompose,oracle_conf1,conf_audit}.json`,
`ticks.jsonl`, `gt_channel_audit.jsonl`, `frames/` (500).
