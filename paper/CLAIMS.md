# CLAIMS.md — rejestr twierdzen preprintu (W1, faza 3)

**Data zestawienia:** 2026-07-24 (sesja W1). **Jezyk:** PL (proza EN powstaje w W2).
**Zasada:** kazde twierdzenie ma zrodlo (plik:sekcja lub commit) i liczby z
NUMBERS.md. **Zakaz liczb z pamieci.** Rozbieznosci miedzy zrodlami wypisane
jawnie (znacznik ⚠). Ranga: **glowne** / wtorne / footnote.

Legenda dowodu: `plik §sekcja` = dokument w repo liquidsight; `commit` = skrot.
Liczby kanoniczne — patrz `paper/NUMBERS.md` (tam pelna prowieniencja per komorka).

---

## C1 — teza OOD [4] NIETESTOWALNA przy parytecie w tym harnessie *(GLOWNE)*

**Tresc.** W harnessie vision-twin fly-to-target, przy parytecie rdzeni
(27 648 ±2%) i procedurze v2 (frozen C1), **zadne ramie CfC nie osiaga
precondition ≥90% sukcesu nominalnego** na calej dozwolonej siatce lr
{3e-4, 1e-3}. Poniewaz ramie orzekajace (A_NCP) nie spelnia precondition,
teza F3_PRE0 / [4] (liquid > GRU na przesuniecie percepcyjne) **nie jest
testowalna** w tym harnessie — **zero ewaluacji OOD** w calej fazie 3.

**Dowod.** Wszystkie 4 nogi FAIL (arytmetyka na zamrozonym kryterium):
A_NCP 3e-4=16,5% (k2), A_NCP 1e-3=72,2% (k4) / 75,3% (6 seedow),
A_CFC 3e-4=27,0% (k2), A_CFC 1e-3=55,3% (k3). `oper_lr = {}`,
`any_cfc_pass = False` → BRAMKA GRANICA.
Zrodla: `results/i3b/fazaA_wynik.json`; `RAPORT_F3.md §2, §8`;
kryterium `F3_GATE.md §4`; commit `e810195`.

**Ograniczenia.** To **nie falsyfikacja** F3_PRE0 — bez precondition testu nie
ma; wynik jest komorka mapy programu (granica), nie wyrokiem o tezie
(`RAPORT_F3.md §8`). Zakres: jeden harness, jeden budzet, parytet ~27k.

---

## C2 — podatek trenowalnosci przy parytecie *(GLOWNE)*

**Tresc.** Przy identycznych danych/budzecie/procedurze i parytecie rdzeni,
zdolnosc nominalna tworzy gradient: **GRU 100% (stabilnie) > CfC/AutoNCP
(„wired", szczyt 92%, srednie nog do 75,3%) > CfC dense (sufit 65%)**. Sam
parytet parametrow nie wystarcza — CfC placi „podatek trenowalnosci".

**Dowod.**
- GRU (kontrola, procedura v2, lr 1e-3, seed 45010): **100%**, dwell 0
  (`results/smoke_A_GRU_proc2.json`; `RAPORT_F3.md §6`).
- A_NCP (wired): szczyt **92%** (seed 45010 @1e-3), srednia nogi 1e-3 =
  72,2% (k4) / 75,3% (6 seedow); rozstep 49–92 (`RAPORT_F3.md §2-3`;
  `results/i3b/progress.jsonl`).
- A_CFC (dense): sufit **65%** (seed 45012 @1e-3), srednia nogi 1e-3 = 55,3%
  (`results/i3b/fazaA_wynik.json`; `progress.jsonl`).

**Footnote C2a (dominujaca porazka: dwell; tilt wyeliminowany).** Na lr 1e-3
**0 tilt** we wszystkich cyklach CfC; rezydualna porazka to **dwell**
(nieprecyzyjny zawis). Przed ANEKS-4 (procedura v1): **tilt 78/100** dla
A_CFC. Zrodla: `RAPORT_F3.md §4.2`; `RAPORT_I3AR.md §2-3`; `progress.jsonl`.

**Ograniczenia.** „Podatek" mierzony przy TYM budzecie treningu (BC-120 +
DAgger×3 od zera); wyzszy symetryczny budzet moze go zmniejszyc (hipoteza,
niezmierzona — `RAPORT_F3.md §8a`). ⚠ terminologia: „NCP-wired" = A_NCP;
„dense" = A_CFC (`F3_GATE.md §1`).

---

## C3 — granica jest WARIANCJA, nie srednia *(GLOWNE)*

**Tresc.** Niestabilnosc miedzy seedami jest obiektem pomiaru: A_NCP@1e-3 daje
**49–92% (rozstep 43 p.p.)** przy tej samej procedurze, gdy GRU = 100%
stabilnie. CfC przy parytecie nie „nie uczy sie" — uczy sie **niestabilnie i
dwell-limited, srednio ponizej 90%**.

**Dowod.** A_NCP@1e-3 seed-po-seedzie: 92, 79, 69, 49, 86, 77 (seedy
45010–45015); rozstep 43 p.p.; GRU=100% (`RAPORT_F3.md §4.3`;
`results/i3b/progress.jsonl`; `fazaA_wynik.json`).

**Ograniczenia / LUKA.** Lacznik z P0 („rozrzut populacyjny odporny na n")
jest w szkielecie i `RAPORT_F3` postulowany, ale **liczba P0 nie ma zrodla w
repo liquidsight** — RAPORT_P0 jest companionem poza tym repo. → **GAP-1**:
do domkniecia w W2 potrzebny cytat z RAPORT_P0 (patrz sekcja LUKI).

---

## C4 — atrybucja wiringu (AutoNCP) *(GLOWNE)*

**Tresc.** Okablowanie AutoNCP czyni CfC trenowalnym tam, gdzie dense CfC pada:
przy identycznym budzecie wired (A_NCP) osiaga szczyt 92% / srednia do 75,3%,
a dense (A_CFC) sufituje na 65% — na obu lr i wielu seedach.

**Dowod.** Zestawienie nog: A_NCP 3e-4=16,5% / 1e-3=75,3%(6s) vs
A_CFC 3e-4=27,0% / 1e-3=55,3%; szczyty 92 vs 65 (`RAPORT_F3.md §2`;
`results/i3b/fazaA_wynik.json`; `progress.jsonl`).
Historyczny dowod readoutu (readout pelnego stanu vs 6-motor): dolot 26/50 vs
8/50 (`RAPORT_DIAG_CFC.md §3 S3`).

**Ograniczenia.** Atrybucja przy parytecie ~27k i tym zadaniu; A_CFC ma
backbone (nie „goly" dense) — patrz C5/ANEKS-3. Na 3e-4 kolejnosc odwrocona
(A_CFC 27% > A_NCP 16,5%) — atrybucja trzyma na dzwigni lr 1e-3, nie na 3e-4.
⚠ do zaznaczenia w prozie: efekt wiringu jest lr-zalezny.

---

## C5 — Δt nosne implementacyjnie, nie przewagowo *(wtorne)*

**Tresc.** Native-Δt (jedyny mechanizm tezy [4]) jest w tej implementacji nosny
tylko po naprawie: skala `ts` steruje rezimem bramki czasu (maly ts = stabilny,
duzy = niestabilny), a wrapper `ncps.torch.CfC` **odrzuca jawne timespans przy
batch>1** (bug biblioteki) — obejscie przez manualne krokowanie komorki.

**Dowod.**
- Skala ts → dolot: sekundy(0,083)=**39/50**, tick(1,0)=15, 4,0=9
  (`RAPORT_DIAG_CFC.md §3 S1`; `ANEKS_3...md` Z2).
- Napęd bramki `|t_a·ts|` po init: 0,083→**0,010** / 1,0→0,125 / 4,0→**0,501**
  (std g: 0,038/0,053/0,147) (`RAPORT_DIAG_CFC.md §3 S2`; `ANEKS_3` pkt 2).
- Bug wrappera: scalar/`(B,1)`/`(B,)` → wyjatek, dziala tylko `None`=1,0;
  obejscie manualnym krokowaniem (`RAPORT_DIAG_CFC.md §1,§3 S1`;
  `MANIFEST_F3.json gate_arms_v2.opis`; `ANEKS_3` Z2).

**Ograniczenia.** Bug specyficzny dla ncps 1.0.1; „nosne, nie przewagowe" —
w tym harnessie przewagi nie zmierzono (precondition nieosiagniety, C1).
**Zakres (GAP-4):** engineering finding; sondy kontrolowane single-seed
(diagnostyczne, nie statystyczne) — `RAPORT_DIAG_CFC.md §3`.

---

## C6 — wrazliwosc komorek CT na procedure DAgger *(wtorne)*

**Tresc.** Komorki ciagloczasowe (CfC) sa wrazliwe na tryb DAgger:
**kontynuacja + checkpoint final-epoch** (procedura bramki v1) destabilizuje
je (A_CFC tilt 78/100, A_NCP kolaps rolloutow 1→0→0), a **retrening od zera +
best-val** (frozen C1, v2) usuwa tilt. **GRU odporny na obie procedury.**

**Dowod.**
- v1 (continue+final) po ANEKS-3: A_CFC tilt 78/100, A_NCP rollout 1→0→0;
  A_CFC stabilny po samym BC (0 tilt) → tilt indukowany DAgger
  (`RAPORT_I3AR.md §2-3`).
- v2 (od zera+best-val, ANEKS-4): tilt 78→0 na lr 1e-3
  (`RAPORT_F3.md §4.2, §5`; `progress.jsonl`).
- GRU odporny: 100% pod obiema procedurami (`RAPORT_I3A.md §2` v1;
  `smoke_A_GRU_proc2.json` v2).

**Footnote C6a (sygnatura mechanizmu: BC fituje, agregat DAgger nie domyka).**
Dla CfC best_val po samym BC (r0) jest niski (~0,00012–0,0009), ale po
agregacji DAgger **rosnie** (r1–r3), a best_epoch robi sie wczesny (np.
A_NCP@1e-3 s45013: 119→41→26→37). GRU trzyma best_val nisko przez wszystkie
rundy (.000168→.000112). Zrodla: `RAPORT_F3.md §4.1`; `progress.jsonl`;
`smoke_A_GRU_proc2.json`.

**Ograniczenia.** Wrazliwosc na DAgger-kontynuacje pozostaje otwartym problemem
badawczym (`SZKIELET_PREPRINT.md §8`); nie zmierzono, dlaczego best-val+od-zera
pomaga (mechanizm postulowany, nie izolowany osobnym ablacyjnym pomiarem).
**Zakres (GAP-4):** engineering finding; sondy kontrolowane single-seed
(diagnostyczne, nie statystyczne) — `RAPORT_DIAG_CFC.md §3` (dowod tilt-po-DAgger
z pojedynczych przebiegow BC-only vs BC+DAgger).

---

## C7 — metodologia jako wklad *(wtorne)*

**Tresc.** Program wnosi przenosna metodologie: bramki + precondition + aneksy z
**regula stopu**, **arytmetyczne wczesne rozstrzyganie** (13 cykli zamiast 40),
**zero kontaminacji OOD**, **cztery restauracje przepisu z dowodami**.

**Dowod.**
- Wczesne rozstrzyganie: `S+(10−k)·100 < 900 → FAIL`; nogi rozstrzygniete przy
  k=2/4/2/3; **13 pelnych cykli** wykonanych vs **40** dla pelnego n=10 na 4
  nogach; batch 45016–45019 nigdy nieuruchomiony
  (`RAPORT_F3.md §1-2`; `fazaA_wynik.json`; `progress.jsonl` = 13 rekordow).
- Cztery restauracje/fixes (F1 backbone / F2 ts=s / F3 readout pelny / F4 procedura)
  + dzwignia lr, kazda z prowieniencja frozen (`RAPORT_F3.md §5`;
  `ANEKS_3...md`; `ANEKS_4...md`; `RAPORT_DIAG_CFC.md`).
- Regula stopu: ANEKS-4 = ostatni aneks instrumentalny fazy 3a
  (`ANEKS_4...md §REGULA STOPU`; `DECYZJE_F3.md` ANEKS-4).
- Zero OOD: cala faza tylko nominal 43000–43099 + T0 (`RAPORT_F3.md §7`).

**Footnote C7a (ekonomia protokolu).** ~57,1 h skumulowanego compute (suma
`sec_cykl` 13 cykli = 205 711 s; `progress.jsonl`); reguła oszczedzila
kompletny batch 4 seedow (`RAPORT_F3.md §2-3`).

**Ograniczenia.** Program jednoosobowy; „4 restauracje" to bug-fixy przywracajace
frozen v1.0, nie nowa architektura (`ANEKS_3...md`; `RAPORT_DIAG_CFC.md §5`).

---

## C8 — charakteryzacja instrumentu *(wtorne)*

**Tresc.** Instrument jest scharakteryzowany: drabina GRU-sanity degraduje
monotonicznie **100/100/64/46/36/24/16** (T0..T3), **sufit eksperta 100% na
calej drabinie** (7 poziomow), determinizm env/render **bit-w-bit w obrebie
maszyny**.

**Dowod.**
- Drabina polityki (dagger.pt, 50 ep/poziom, 43100–43149): T0/T1/T2/T2a/T2b/
  T2c/T3 = 100/100/64/46/36/24/16 (`results/psanity_p2r.json`;
  `RAPORT_PSANITY_R2.md §1`). Poziom bramki = T2b (36%, najciezszy w [30,85]).
- Sufit eksperta: T2a/T2b/T2c=100% (nowe), T0–T3=100% (z R1) → 100% caly zakres
  (`results/psanity_p3r.json`; `RAPORT_PSANITY_R2.md §2`).
- Determinizm: `s1_env_det` PASS bit-w-bit (rgb/kin/setpoint), sceny 43100/T0,
  43125/T2b, 43149/T3, 2 przebiegi (`results/s1_env_det.json`;
  `RAPORT_I1.md §` (tab. det); `RAPORT_PSANITY_R2.md §0`).

**GAP-2 ROZWIAZANY (W2).** Wczesniej: szkielet twierdzil „determinizm bit-w-bit
(takze miedzy maszynami jako bonus)", czemu `S0_NOTES.md:51-53` przeczy (hashe
miedzy maszynami MOGA sie roznic i to NIE jest FAIL; FAIL = rozjazd dwoch
przebiegow na TEJ SAMEJ maszynie). **Poprawiono w W2:** `SZKIELET_PREPRINT.md`
i niniejsze C8 mowia teraz wylacznie **„bit-exact determinism within a machine"**
— twierdzenie cross-machine usuniete. Zrodlo: `S0_NOTES.md:51-53`;
`s1_env_det.json` (within-machine, 2 przebiegi PASS).

**Ograniczenia.** Drabina i sufit mierzone na ramieniu GRU z pre-rejestrowanego
rzutu moneta (`P_SANITY.md`); sceny sweep 43100–43149 (50), nie pelny nominal.

---

## LUKI (twierdzenia z niepelnym dowodem — do domkniecia w W2)

- **GAP-1 (C3 → P0) — ROZWIAZANY (W3).** Wszystkie liczby P0 (`NUMBERS.md T9`)
  **zweryfikowane CO DO CYFRY** wzgledem `paper/sources/liquid_temporal_robustness_
  technical_report.pdf` (Tab. 1-3 + §4-5) — zero rozbieznosci; margines retencji
  +0,1127 / pooled 0,1759 → null; stabilnosc n=3 vs n=15 potwierdzona. Znacznik
  `[P0:prompt]` usuniety; w prozie cytat `\citep{zydziak2026p0}`.
- **GAP-2 (C8 → determinizm cross-machine) — ROZWIAZANY (W2).** Poprawiono
  szkielet i C8 na „bit-exact determinism within a machine"; twierdzenie cross-
  machine usuniete (zrodlo `S0_NOTES.md:51-53`). Domkniete.
- **GAP-3 (R2/E6, spoza fazy 3) — ROZWIAZANY qualitative fallback (W3).**
  RAPORT_E6 pierwotny **niedostepny** (potwierdzone T0: brak repo liquidwatch;
  brak w home/Downloads/Documents/Desktop; backup liquidwatch ma tylko E1/E2).
  Per aneks T1b: §5.2 przepisane na forme **jakosciowa** (kierunek ujemny, niski
  FAR), zrodlo wtorne = **program compendium** (oznaczone wprost); trzy sporne
  wartosci (jednostka delty, parametr sweep, mianownik FAR) **nie wchodza** do
  prozy. Wiersz mapy R2 = werdykt kierunkowy, rozdzielczosc „qualitative
  (secondary source)". Markery `[E6:TODO-src]` usuniete. Opcjonalnie: gdy Olga
  wskaze raport pierwotny → R2 do formy ilosciowej.
- **GAP-4 (C5/C6/C7 „cztery restauracje/fixes" — kompletnosc dowodu F1–F4) —
  OZNACZONY (W2).** Efekty F1–F3 (backbone/ts/readout) dowiedzione sondami BC-8
  w DIAG; F4 (procedura) smoke'ami I3a-R vs I3a-R2. Wszystkie z prowieniencja, ale
  **pojedyncze sondy (n=1 seed dla wiekszosci)**. Zakres dopisany wprost do C5 i
  C6 („engineering findings; single-seed controlled probes, diagnostic not
  statistical") oraz do prozy §6/Limitations. Zrodlo: `RAPORT_DIAG_CFC.md §3`.

---

## PODSUMOWANIE REJESTRU

- Twierdzen glownych: **4** (C1–C4) — wszystkie z pelnym dowodem w repo; lacznik
  P0 dla C3 domkniety (GAP-1 zweryfikowany z PDF w W3).
- Twierdzen wtornych: **4** (C5–C8) — dowiedzione; **GAP-2 ROZWIAZANY** (C8 =
  within-machine), **GAP-4 OZNACZONY** (n=1 sondy, zakres dopisany do C5/C6).
- Kandydaci spoza C1–C8 znalezieni i zapisani jako **footnote**: C2a (dwell/
  tilt), C6a (sygnatura BC-vs-agregat), C7a (ekonomia ~57,1 h).
- Stan luk po W3: **GAP-1 ROZWIAZANY** (P0 PDF zweryfikowany), **GAP-2
  ROZWIAZANY** (within-machine), **GAP-3 ROZWIAZANY jakosciowo** (E6 fallback;
  raport pierwotny wciaz poza repo), **GAP-4 OZNACZONY** (sondy n=1). Jedyny
  otwarty marker w repo: `panerati2021gym` `pages` = `[BIB:verify]`.
