# ANEKS-3B do DECYZJE_3B — kanal celu i zrodlo danych (2026-07-26)
Powod: G1 FAIL 12%; DIAG-3B (commit 1c5d469) dekomponuje strate
88 pp: 0 pp poza-FOV, 0 pp grounder w FOV, 88 pp conf-shift+polityka.
Dowod: oracle z zywym conf (~0.02) = 12%; oracle z conf=1.0 = 80%
(+68 pp z jednego wymiaru wejscia). Trening z conf=const 1.0 uczynil
ten wymiar mina OOD (zero wariancji w treningu -> niezdefiniowane
zachowanie przy zywych 0.01-0.05). Scena i grounder zdrowe
(widocznosc 100% w dolocie, ZOH fizyczny, YOLO in-FOV 85.6%).
Zmiany (jedyne):
Z1 kanal celu: (cx, cy, w, h, age_s) — 5 wymiarow, BEZ conf;
   wejscie rdzenia 78+5=83. conf pozostaje LOGOWANY per tick
   (results/*/conf_log) jako przyszly sygnal reguly admisyjnosci 3c
   — niepewnosc nalezy do oslony, nie do wykonawcy.
Z2 zrodlo danych treningowych: LIVE-FED — BC (300 ep, ekspert leci,
   kanal z zywego YOLO przez serwer .venv_s3b0 wg kontraktu tick/
   L_deliver/ZOH/no-lock) oraz rollouty DAgger (polityka z zywym
   kanalem, etykiety eksperta GT-designated). Train==test z
   konstrukcji; ticki bledne groundera (~14%) sa czescia rozkladu
   treningowego — odpornosc na nie jest pozadana wlasnoscia.
   [Z2' alternatywa konserwatywna, NIEAKTYWNA: GT-fed bez conf —
   aktywacja wymagalaby decyzji czlowieka.]
Bez zmian: reszta kontraktu D3 (tick 1 Hz, L_deliver 0.10 s,
AGE_MAX 8.0, ZOH, no-lock), procedura v2, seed 45020, pule scen,
progi i sceny G1, ekspert, env, konfiguracja YOLO.
Higiena: bramka G1 pozostaje zamrozona; naprawa motywowana wylacznie
diagnostyka nominalna+oracle (DIAG-3B), zero strojenia na sweep.
