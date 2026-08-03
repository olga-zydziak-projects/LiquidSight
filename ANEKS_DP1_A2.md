# ANEKS_DP1 do PRE_DP0 §2 — podmiana seedu aktu A2 (protokół antyselekcyjny)

**Data:** 2026-08-03. **Charakter:** aneks scenariuszowy do `PRE_DP0.md §2` (akt A2 „Łącze").
**Reguła selekcji ZAPISANA PRZED PRZESZUKANIEM** (anti-selection; ten commit poprzedza jakikolwiek
bieg wyszukiwania). MIERZĘ = RAPORTUJE.

## Powód
Seed **46507** przypięty w `PRE_DP0 §2` do A2 (burst L5, maska 45105) **flipuje pod APPLIED**:
zmierzone **3/3 próby → PORAZKA(dwell)** (`results/demo_proof` bieg 2026-08-03, log dp_rec).
Mechanizm: burst pokrył moment wejścia w dwell → osłona (R-B) HOLD-uje ślepy finisz → dron nie
domyka zawisu. To ten sam konserwatyzm, który na nodze dropout konwertuje 16/28 porażek w
abstynencję (RAPORT_3C_MVP §5). Zgodnie z F-D1 (PRE_DP0 §9.4) scena flipująca **wypada**; reguł
osłony **nie zmiękczamy**.

## Reguła selekcji nowego seedu A2 (ZAMROŻONA przed przeszukaniem)
1. **Przestrzeń kandydatów:** pula eval G2 **46500–46549** (ta sama, na której zmierzono krzywą
   G2/burst), maska **burst L5, mask_seed 45105** (bez zmian).
2. **Porządek:** **rosnący numer seedu** od 46500 (46500, 46501, 46502, …). Zero sortowania po
   jakości/estetyce.
3. **Kryterium:** pierwszy kandydat dający **SUKCES pod APPLIED** (osłona zastosowana) zostaje
   seedem A2. Limit **≤3 próby/kandydata** (F-D1; flip jest deterministyczny → 1 próba wystarcza,
   pozostałe 2 to zapas na pad WSL/GPU z weryfikacją artefaktów).
4. **Odrzucenie:** każdy kandydat z wynikiem ≠ SUKCES trafia na listę odrzuconych (seed + wynik)
   w manifeście A2 — jawnie, nie ukrywany.
5. **Reguła stopu:** jeśli **10 kolejnych** kandydatów nie przechodzi → **STOP i eskalacja**
   (sprzeczność z oczekiwaniem G2, że ~76% burst-L5 to SUKCES bez osłony; pod APPLIED spadek
   wymaga wyjaśnienia, nie obejścia).

## Zapis na planszy (obowiązkowy, uczciwość)
Obok banera G2 aktu A2: „seed przypięty w PRE (46507) poległ pod osłoną — burst pokrył wejście w
dwell, osłona zatrzymała ślepy finisz; ten sam konserwatyzm konwertuje 16/28 porażek w abstynencję
(MEASURED)". Baner G2 z **podpisem warunków pomiaru**: populacja 46500–46549, **bez osłony**
(krzywa G2 jest charakteryzacją bazy, nie systemu z APPLIED).

## Prowieniencja i higiena
Krzywa G2 (80/66/44/30; L5 −4 pp) — `RAPORT_S3B4`, mierzone **bez osłony** na populacji. Podmiana
seedu A2 nie tworzy nowej liczby pomiarowej (nagranie ≠ pomiar). Manifest A2 niesie seed finalny +
listę odrzuconych. Sweep 46600–46649 nietknięty.

*Aneks zamknięty PRZED przeszukaniem. Następny krok: bieg selekcji wg reguły powyżej.*
