# S0_NOTES — prototypy smoke S0 zweryfikowane w sandboxie (2026-07-21)

## Co to jest

Dwa skrypty krytycznej sciezki S0 z `F3_PRE0.md` §3, napisane i **uruchomione
w sandboxie** na `pybullet==3.2.7` (wersja z Twojego `requirements.lock`),
zanim spalisz na to sesje na swojej maszynie:

- `s0_render_det.py` — determinizm renderu TinyRenderer (DIRECT, CPU):
  dwa niezalezne przebiegi tej samej sceny (fizyka + kamera na luku),
  SHA256 osobno dla rgb / depth / seg. PASS = bit-w-bit. Przy FAIL z
  shadow=1 automatyczna diagnoza shadow=0.
- `s0_scene_seg.py` — budowniczy sceny z seeda + pule tekstur (proceduralne
  PNG z seedowanego PRNG, zero zewnetrznych assetow) + maska segmentacji:
  (1) maska izoluje cel i centroid maski zgadza sie z projekcja GT srodka
  celu (view/proj -> piksele), (2) ta sama pula => identyczny obraz,
  (3) inna pula => inny obraz.

## Wyniki przebiegu sandboxowego (2026-07-21) — oba PASS

- `s0_render_det`: **PASS @ 64x64 i @ 96x96**, 30 klatek, shadow=1 —
  rgb / depth / seg **bit-w-bit identyczne** miedzy dwoma niezaleznymi
  przebiegami (fizyka + kamera na luku). Pliki: `s0_render_det.json`,
  `s0_render_det_96.json`.
- `s0_scene_seg`: **PASS @ 96x96** — maska celu 123 px,
  |centroid maski − projekcja(GT)| = **0.93 px** (tol 4.0);
  pula tekstur powtarzalna (identyczny hash), pule rozne (rozny hash).
  Plik: `s0_scene_seg.json`.

Srodowisko sandboxa (odnotowane uczciwie): CPython **3.11.15** (uv) +
oficjalny wheel manylinux `pybullet==3.2.7` (cp312 nie ma wheela na PyPI —
sdist buduje sie ~20+ min i nie zdarzyl w sandboxie), numpy 2.4.6.
Determinizm renderera zyje w skompilowanym C++ pybulleta (ten sam kod
zrodlowy 3.2.7), nie w wersji Pythona — ale dowod WIAZACY to powtorka
na Twojej maszynie, w Twoim uv (Python 3.12.13, Twoj zbudowany 3.2.7,
Twoj CPU). To pierwsze zadanie sesji S0 u Ciebie.

## Co sandbox rozstrzyga, a czego NIE

Rozstrzyga (wlasnosci implementacji, nie maszyny):
- czy TinyRenderer w DIRECT jest w ogole deterministyczny w obrebie maszyny
  (to jest warunek istnienia calego harnessu parowania),
- czy seg-buffer nadaje sie na GT maske celu (metryka IoU saliency w F3_GATE
  i sanity sceny w P-SANITY na tym wisza),
- czy koncept "pula tekstur z seeda" dziala powtarzalnie i separuje poziomy
  osi T0-T3,
- poprawnosc okablowania API (macierze widoku/projekcji, projekcja GT->px,
  flagi renderera).

NIE rozstrzyga (do powtorzenia u Ciebie, w srodowisku uv):
- determinizmu na TWOIM procesorze/glibc (inna maszyna = osobny dowod;
  hashe miedzy maszynami MOGA sie roznic i to nie jest FAIL — FAIL to
  rozjazd dwoch przebiegow na tej samej maszynie),
- `s0_throughput` — FPS sim+render na Twoim CPU przy 64^2/96^2 i kamerze
  12 Hz; od tego zalezy wiazace n seedow w F3_GATE (sandbox ma inny sprzet,
  pomiar tutaj bylby smieciem),
- integracji z `CtrlAviary` (kamera z pozy drona zamiast luku; te same
  wywolania `getCameraImage`, wiec ryzyko male, ale dowod nalezy do S0
  u Ciebie),
- Python 3.12.13 uv vs 3.12.3 sandboxa (kosmetyka, ale lock jest lockiem).

## Konwencje przeniesione z domu

- seedy z nowej puli 40000+ (scene_seed 40002, pule tekstur 41000/42000 —
  do wpisania do manifestu F3 przy adopcji),
- zadnych zaleznosci poza lockiem (numpy, pillow, pybullet, pybullet_data),
- wyniki do JSON, PASS/FAIL na stdout, zero stanu globalnego miedzy testami
  (swiezy klient DIRECT na przebieg).

## Znane niuanse (zapisane, zeby nie odkrywac dwa razy)

- `lightDirection` ustawione jawnie ([0.4, 0.4, 1.0]) — swiatlo domyslne
  nie jest czescia kontraktu determinizmu; w repo F3 kierunek swiatla
  stanie sie parametrem osi "oswietlenie" (os wtorna, poza werdyktem 3a).
- `shadow=1` w tescie celowo: cienie to najbardziej podejrzana sciezka
  renderera; jesli PASS z cieniami, PASS bez nich jest darmowy.
- seg-buffer przy domyslnych flagach zwraca body id per piksel — wystarcza,
  poki cel jest jednobrylowy; przy celu wielo-linkowym potrzebne
  ER_SEGMENTATION_MASK_OBJECT_AND_LINKINDEX (odnotowane, nieaktywne).
- depth hashowany jako float32 — jesli kiedys depth wejdzie do obserwacji
  polityki, hash float32 jest wlasciwym kontraktem (nie uint8 z wizualizacji).
- tekstury proceduralne (8x8 szum -> kron do 128^2) sa NA TERAZ; pula
  "rodzin" tekstur dla T0-T3 to decyzja tresci osi przy P-SANITY, nie
  infrastruktury.

## Adopcja do repo F3 (gdy powstanie, po D7)

1. `smoke/` <- oba skrypty bez zmian logiki; sciezki JSON -> `results/`.
2. Dopisac `s0_throughput.py` (pomiar u Ciebie; szkielet trywialny: petla
   step+render z zegarem, raport FPS i x-realtime dla 64/96 przy 12 Hz).
3. Przebieg S0 na Twojej maszynie => wyniki do `RAPORT_S0.md` -> dopiero
   wtedy domykanie i zamrozenie P-SANITY (progi z F3_PRE0 §4).
