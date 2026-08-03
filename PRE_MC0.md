# PRE_MC0 — pre-rejestracja fazy MC (mission cut: jedna ciągła misja)

**Data:** 2026-08-03. **Etap:** B1 (dokument zamrożony; kończy się STOP na ratyfikację scenariusza).
**Podstawa:** `RECON_MC.md`. **Charakter:** BUDOWA pokazowa, **nie pomiar** — żadna liczba pomiarowa
nie powstaje; banery/napisy wyłącznie z inwentarza liczb DP (RECON_DP §C) + zdarzeń trace. Zasady DP
bez zmian. `[PROPOZYCJA]` = do ratyfikacji człowieka.

> **STATUS:** OCZEKUJE NA RATYFIKACJĘ. Etap B2 (budowa runnera/nagrania) nie startuje bez adnotacji
> „RATYFIKOWANE" ręką człowieka.

## §1 Tożsamość
Misja = **opowieść demonstracyjna na zmierzonych klockach**: jedna scena K8, jedna rejestracja,
konsola + pamięć korekt + osłona APPLIED. Banery i napisy **wyłącznie** z inwentarza liczb DP i
**zdarzeń trace**. **Uczciwie (RECON §d-1):** misja jest **konkatenacją demo-legów** (reset-per-leg +
teleport carry-over), nie jednym literalnym nieprzerwanym simem; trace i obraz ciągłe. Nogi startujące
z pozycji poprzedniego celu są **poza rozkładem spawnu** i oznaczone w prowieniencji jako **demo-leg**.

## §2 Scenariusz [PROPOZYCJA — lista ZAMKNIĘTA, do ratyfikacji]

Scena **K8**, jedna rejestracja. **Wariant A (REKOMENDOWANY — z mitygacją transit, RECON §b/§d-2):**
każdą nogę LOTU poprzedza **skryptowy transit „return home"** (egzekutor → `[home_xy, z_hover, 0]`, BEZ
polityki), by lot startował **in-distribution** (smoke: spawn→cel = ARRIVED; carry-over = NEAR/MISS).

| # | segment | typ | oczekiwanie |
|---|---|---|---|
| L1 | start (spawn) → `fly to the red box` → dostarczenie → dwell | policy (in-dist) | SUCCESS |
| — | transit `return home` | skrypt egzekutor | dron w home |
| L2 | `fly to the blue sphere`, **burst L5 w połowie dolotu** → mostkowanie na ekranie → dwell | policy | SUCCESS |
| — | transit `return home` | skrypt | home |
| L3 | komenda na cel **relokowany poza geofence** → **REFUSE(GEOFENCE)** przy admisji (certyfikat P2 w napisie) | admisja | REFUSE(GEOFENCE) |
| — | transit `return home` | skrypt | home |
| L4 | `fly to the crimson box` → **NO_MATCH** → korekta aliasu (podpisany rekord) → `fly to the red box` → dostarczenie → dwell | policy + memory | SUCCESS |
| L5 | `return home` → lądowanie → plansza końcowa | skrypt | landed |

**Wariant B (bez transitu):** nogi lotu startują z poprzedniego celu; akceptacja **NEAR/MISS** z jawnym
labelem demo-leg (słabszy pokaz). **Rekomendacja: A.** Czas docelowy **90–180 s**. **Zero scen ponad listę.**

**Scena [PROPOZYCJA]:** pin seedu K8 regułą antyselekcyjną (ascending od 49500, pierwszy K8 zawierający
**red box + blue sphere** + obiekt do relokacji + dystraktory) — reguła zamrożona w aneksie MC przed
przeszukaniem (jak ANEKS_DP1). Alternatywa: komendy adaptowane do obiektów wylosowanej sceny K8
(mniej narracyjnie czyste). **Do ratyfikacji:** wariant sceny.

## §3 Napisy (subtitles)
Generowane **WYŁĄCZNIE z logu zdarzeń** trace (admisja, dostarczenie, LINK FROZEN, wejście w dwell,
HOLD, REFUSE+powód, korekta-alias, transit, landed). **Szablon per typ zdarzenia** + timestamp; **zakaz
napisów odręcznych poza szablonami**; język **EN**. Wyjście: `subtitles.vtt` **generowany skryptem z
trace** (nie pisany ręcznie) — odtwarzalny.

## §4 Nagranie
Osłona **APPLIED**. Limit **≤3 próby NA NOGĘ** (re-record od początku nogi, jeśli runner pozwala —
inaczej od początku misji, z licznikiem prób w manifeście). **Maska burstu przypięta w PRE:** seed
maski **45105** (rodzina G2) + **offset okna względem wejścia L2** ustawiony JAWNIE tak, by burst wypadł
w **środku dolotu** (nie na dwell-entry; lekcja 46507) — offset do wpisania w aneksie MC. **Flip nogi**
(noga nie domyka się w limicie) = **protokół antyselekcyjny** per ANEKS_DP1 (reguła deterministyczna,
aneks, raport odrzuconych).

## §5 Prowieniencja
**Manifest misji:** scena (seed + sha256 geometrii jak scene.json DP), seedy, maska (seed+offset),
**próby per noga**, **outcome per noga**, typ segmentu (policy/transit/admisja), demo-leg flag.
Napisy **odtwarzalne skryptem z trace** (`subtitles.vtt` generowany, nie pisany). Zamrożone nietknięte;
sweep 46600–46649 nietknięty; zero nowych liczb pomiarowych.

## §6 Ryzyka nazwane
1. **Niestabilność nóg z niestandardowych startów** (RECON §b, zmierzone NEAR/MISS) → mitygacja §2A
   (transit home przed nogami lotu) / §4 (bounded re-record ≤3/nogę).
2. **Burst nachodzący na dwell** (46507) → offset okna przypięty w PRE, burst w środku dolotu.
3. **Długość trace vs rozmiar playera** (RECON §d-4): ~1080–2160 tików × klatki base64 → budżet MB.
   Mitygacja: **klatki panelowe na niższym fps** (co 2–3 tik) przy zachowaniu **WSZYSTKICH zdarzeń** w
   logu napisów; widok 3D pełne fps (lekki). Budżet do wyceny w B2.
4. **„Sim nieprzerwany" nieliteralny** (RECON §d-1) → nazwane: konkatenacja demo-legów.
5. **Scope creep** → lista §2 **zamknięta**.

## §7 Budżet i kryterium
**Budżet: 1–2 sesje po ratyfikacji.** **Kryterium ukończenia:** misja odtwarza się w playerze w trybie
**„mission"** (obok trybu aktów DP — akty **nietknięte** jako widok alternatywny) z **napisami** i
**instrumentami W2**; manifest kompletny; **RAPORT_MC** krótki (co nagrano, próby per noga, odstępstwa).

## Decyzje do ratyfikacji
| # | decyzja | rekomendacja |
|---|---|---|
| wariant scenariusza | A (transit home) vs B (accept NEAR/MISS) | **A** — czyste nogi, `return home` w gramatyce |
| scena K8 | reguła ascending (red box+blue sphere) vs adaptacja komend | reguła ascending, aneks pre-search |
| transit return-home | skrypt egzekutor (nie policy) | tak — czysty, deterministyczny, bez frozen |
| burst L2 | seed 45105 + offset jawny (środek dolotu) | tak — offset w aneksie |
| budżet klatek | niższy fps klatek panelowych, wszystkie zdarzenia | tak, jeśli MB przekroczy próg |

---
*PRE_MC0 zamknięty. **STOP na ratyfikację scenariusza.** Bez „RATYFIKOWANE" etap B2 nie startuje.*
