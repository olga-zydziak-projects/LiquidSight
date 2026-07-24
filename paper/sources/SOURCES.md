# SOURCES.md — zrodla companion skopiowane do paper/sources/ (T0 przed W3)

**Data:** 2026-07-24. Kopie sa 1:1 (sha256 oryginalu = sha256 kopii). Zrodla
zewnetrzne (poza repo liquidsight) skopiowane wylacznie do odczytu na potrzeby
W3 (potwierdzenie liczb w prozie EN). Oryginaly nietkniete.

---

## 1. RAPORT_P0 (PDF) — ZNALEZIONY ✓

| pole | wartosc |
|---|---|
| kopia | `paper/sources/liquid_temporal_robustness_technical_report.pdf` |
| oryginal | `/mnt/c/Users/User/Downloads/liquid_temporal_robustness_technical_report.pdf` |
| sha256 oryginal | `0757744280932281667306676e0f707818c0b70586a0ccc862ab376f2cbb824a` |
| sha256 kopia | `0757744280932281667306676e0f707818c0b70586a0ccc862ab376f2cbb824a` |
| rowne? | **TAK** |
| bajtow | 230 595 |

Domyka **GAP-1**: liczby P0 w `NUMBERS.md T9` (obecnie `[P0:prompt]`) i w prozie
`DRAFT_EN.md` (`[TODO-src: P0 PDF]`) do zweryfikowania z tym PDF w W3
(Tab. 1-3 + par. 5).

---

## 2. RAPORT_E6 (onset detekcja) — NIE ZNALEZIONY ✗ (punkt otwarty)

**Nie znaleziono zadnego RAPORT_E6** (ani .md, ani .pdf). Przeszukane sciezki:

| # | sciezka / zrodlo | wynik |
|---|---|---|
| 1 | `~/projects/liquidwatch` | **katalog nie istnieje** |
| 2 | `find ~ -maxdepth 3 -type d -iname "*liquidwatch*"` | brak repo liquidwatch |
| 3 | `find ~ -iname "*E6*"` (home, bez ukrytych) | brak |
| 4 | `/mnt/c/Users/*/Downloads` (iname *E6*) | brak |
| 5 | `/mnt/c/Users/*/Documents` (iname *E6*) | brak |
| 6 | `/mnt/c/Users/*/Desktop` (iname *E6*) | brak |
| 7 | wnetrze `liquidwatch_backup_2026-07-04_nocubes.tar.gz` (Downloads) | zawiera tylko **RAPORT_E1.md** i **RAPORT_E2.md** (do E2; brak E6) |

Backup liquidwatch jest z **2026-07-04** i konczy sie na etapie E2; RAPORT_E6
(jesli powstal) jest pozniejszy i nie znajduje sie na tej maszynie w zadnej z
przeszukanych lokalizacji.

**Rozwiazanie (aneks T1b, W3): qualitative fallback.** Skoro raport pierwotny
niedostepny, rezim R2 (`DRAFT_EN.md §5.2` + wiersz mapy R2 w §5) przepisany na
forme **jakosciowa**: kierunek ujemny przy niskim FAR, **zrodlo wtorne = program
compendium** (`Portfolio_kompendium_pomiarow.docx`, Downloads), oznaczone w
prozie „as recorded in the program compendium; primary E6 report not preserved
in the project archive". Trzy sporne wartosci **wykluczone** z prozy; markery
`[E6:TODO-src]` usuniete. Rozdzielczosc mapy R2 = „qualitative (secondary
source)".

**⚠ Kompendium NIE skopiowane do sources/:** w Downloads sa **dwie wersje**
(`Portfolio_kompendium_pomiarow.docx` 2026-07-21 00:21 oraz
`Portfolio_kompendium_pomiarow (1).docx` 00:34) — nie kopiuje, by nie wybrac
niewlasciwej. Olga: wskaz wersje autorytatywna, jesli kopia ma trafic do
`sources/`. Cytat wtorny w prozie dziala bez kopii (nie podaje liczb).

**Do decyzji Olgi:** wskazac plik RAPORT_E6 pierwotny recznie → wtedy R2 do
formy ilosciowej.

---

## Podsumowanie

- Znalezione: **1/2** — P0 PDF (sha256 zgodne) → domyka GAP-1 (weryfikacja W3).
- E6: **qualitative fallback** (aneks T1b) — raport pierwotny niedostepny; R2
  jakosciowe ze zrodla wtornego (compendium). GAP-3 rozwiazany jakosciowo;
  promocja do formy ilosciowej tylko gdy Olga wskaze raport pierwotny.
