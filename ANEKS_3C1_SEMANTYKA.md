# ANEKS_3C1_SEMANTYKA — R-B v2: admisja na wejściu + sufit twardy

**Data:** 2026-08-01. **Sesja:** S3c1-R. **Charakter:** bug-fix do zamrożonej semantyki
`PRE_3C0 §2` reguły R-B + dodatek o pre-istniejącej prowieniencji. Zmiana **wyłącznie** w
semantyce R-B; polityka, kanał, env, percepcja, wartości θ (θ_age = 2.0 s), T_acq/T_hold = 3.0 s —
bez zmian. MIERZĘ = RAPORTUJE.

## Skąd poprawka (iter-1 jako historia)

`PRE_3C0 §2` definiuje R-B jako **„admisję wejścia w dwell"** — kontrolę wieku kanału w chwili
przekroczenia progu martwego pola, nie predykat trwały. W iteracji 1 (S3c1, commit `980160c`)
zaimplementowałem R-B jako **predykat CIĄGŁY**: `dist < 0.5 ∧ age_s > θ_age` sprawdzany na
**każdym** ticku. Efekt zmierzony na czystej bazie (100 ep): **83/100 odmów `STALE_AT_DWELL`,
sukces 67% → 9%**. Mechanizm: końcowy „ślepy" finisz z natury wchodzi w martwe pole (cel opuszcza
kadr 256², grounder milczy), więc age rośnie liniowo przez całą fazę zawisu; predykat ciągły łapał
ten wzrost w każdym epizodzie i zamrażał drona ~0.3 m od celu — dławiąc dokładnie ten kompetentny
ślepy finisz, który daje 67% sukcesów. To był rozjazd implementacji z PRE, nie własność zadania.
Iter-1 pozostaje w historii (git `980160c`, sekcja raportu finalnego); pomiar był parowany i wierny
(ramię bez osłony odtworzyło 67/10 co do liczby).

## R-B v2 (obowiązująca semantyka)

**(a) ADMISJA NA WEJŚCIU (jednorazowa).** W chwili **pierwszego** przekroczenia `dist < 0.5 m`
w epizodzie (przy aktywnym locku) osłona sprawdza wiek kanału **dokładnie raz**:
- `age_s ≤ θ_age (2.0 s)` → **admisja przyznana** natychmiast;
- `age_s > θ_age` → **HOLD** (position-hold); świeży tick obniżający `age_s ≤ θ_age` w oknie
  `T_hold = 3.0 s` → ponowna próba admisji (przyznana); timeout `T_hold` bez odświeżenia →
  **REFUSE(STALE_AT_DWELL)**.

Po przyznaniu admisji **dwell biegnie bez dalszych kontroli age** poniżej sufitu (b). To jest sedno
poprawki: świeży kanał w chwili wejścia oznacza, że dron wie, gdzie jest cel — pozwalamy mu domknąć
ślepy finisz z pamięci, nie karząc go za naturalny wzrost age w martwym polu.

**(b) SUFIT TWARDY (ciągły).** Niezależnie od admisji, jeśli `age_s > 6.0 s` w **dowolnym**
momencie po admisji → **HOLD** → świeży tick `≤ 6.0 s` w `T_hold` → powrót ALLOW; timeout →
**REFUSE(STALE_AT_DWELL)**. Sufit jest bezpiecznikiem na skrajnie zamrożony kanał (zabite łącze),
którego pamięciowy finisz już nie uratuje.

**Prowieniencja sufitu 6.0 s:** G2 (`RAPORT_S3B4`, `results/s3b4/measure.json`) — **zero sukcesów
przy age > 6 s** przy wejściu w dwell (histogramy age-at-dwell-entry: sukcesy wyłącznie w binach
< 4 s). Odmowa powyżej 6 s nie kosztuje więc żadnego mierzalnego sukcesu; to darmowy bezpiecznik.

## Niezmienniki

θ_age = 2.0 s (D2), T_acq = T_hold = 3.0 s (D3), martwe pole 0.5 m, geofence 1.8 m, R-A bez progu
conf (D1), R-C i R-D — **bez zmian**. Zmienia się wyłącznie tryb stosowania θ_age w R-B: z ciągłego
na jednorazowy-przy-wejściu + sufit 6.0 s. Testy jednostkowe R-B v2: `s3c1/test_shield.py`
(przypadki wejścia świeżego, wejścia starego z odświeżeniem, wejścia starego z timeoutem,
zagłodzenia do sufitu).
