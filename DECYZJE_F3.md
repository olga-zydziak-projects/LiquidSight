# DECYZJE_F3 — D1-D7 zatwierdzone przez Olge, 2026-07-22
D1  zadanie: fly-to-target — dolot i zawis. Cel: czerwony box 0.08 m na
    podlozu, pozycja losowa w arenie (min 1.0 m od startu). Start: losowa
    pozycja w centralnych 3x3 m, z=0.5, losowy yaw. Sukces = pozycja drona
    w promieniu r_goal od punktu zawisu [target_xy, z_hover] nieprzerwanie
    przez koncowe t_dwell s epizodu (epizod 10 s). r_goal/z_hover/t_dwell
    strojone na ekspercie w I1 (start: 0.25 m / 0.5 m / 2.0 s), potem
    zamrozone w config/env_f3.json.
D1b FAIL: klif bezpieczenstwa v1.0 (z<0.05 m, tilt>60 st., kontakt) +
    geofence areny 4x4x2.5 m. Typy porazki raportowane rozdzielnie:
    brak-dolotu/dwell vs katastrofa (tilt/geofence/crash).
D2  obserwacja: rgb uint8 64x64x3 (kamera przednia z pozy drona) +
    obs_kin(13) float32 + dt(1) float32. Referencja trajektorii nie
    istnieje w wejsciu — cel wylacznie w pikselach.
D3  takt: fizyka 240 Hz, kontrola 48 Hz (5 substepow), kamera 12 Hz
    (co 4. tik kontroli); rdzen polityki tyka na klatce, setpoint ZOH
    miedzy klatkami; petla wewnetrzna PID zawsze 48 Hz.
D4  twin: primary end-to-end (wlasny enkoder per ramie, identyczna
    architektura i budzet, parytet parametrow rdzenia +-2%); secondary:
    wspolny enkoder frozen (pretrening supervised piksele -> wzgledna
    pozycja celu). Realizacja w I2+.
D5  nauczyciel: DSL-PID privileged (GT pozycji celu z sim) z gladkim
    najazdem bez skokow setpointu; BC + 3 rundy DAgger; naprawy treningu
    wylacznie na T0 (nigdy na podstawie OOD).
D6  os OOD primary — poziomy teksturowe (wyglad CELU staly przez wszystkie
    poziomy; os zmienia kontekst, nie cel):
    T0 = rodzina A, pula treningowa (seedy 41000-41049);
    T1 = rodzina A, held-out (41500-41519);
    T2 = rodzina B (42000-42019);
    T3 = T2 + K=4 dystraktorow o kolorze zblizonym do celu
         (rgba czerwien z jitterem +-0.1, rozmiar celu +-20%).
    Rodzina A: szum niskoczestotliwosciowy 8x8 -> kron do 128x128, paleta
    [0.2,0.8] (jak w s0_scene_seg). Rodzina B: wzory strukturalne — pasy /
    szachownica o losowej orientacji i skali, paleta [0.1,0.9].
    Osie wtorne (poza werdyktem 3a): oswietlenie, dropout klatek.
D7  nazwa projektu: liquidsight.
Pule seedow fazy 3 (rozlaczne z v1.0 i LiquidWatch): 40001-40003 S0
(zuzyte); 41xxx tekstury rodz. A; 42xxx rodz. B; 43000-43099 sceny eval
nominal; 43100-43149 sceny sweep osi (te same sceny na kazdym poziomie);
44xxx sceny treningowe; 45xxx rezerwa (maski dropout).
ANEKS-1 (2026-07-23): D1/D2 zrewidowane wg ANEKS_1_OBSERWOWALNOSC.md
— spawn celu w stozku czolowym, kamera pitch -22.3 st.; progi
P_SANITY bez zmian.
ANEKS-2 (2026-07-23): D6 zrewidowane wg ANEKS_2_DRABINA_OSI.md —
os rozszerzona o poziomy T2a/T2b/T2c (K=1/2/3 dystraktory); progi
P_SANITY bez zmian.
