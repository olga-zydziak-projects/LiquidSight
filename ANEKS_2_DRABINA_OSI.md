# ANEKS-2 do DECYZJE_F3 — drabina dystraktorowa osi (2026-07-23)
Powod: P2 (R1) formalnie FAIL — 1 poziom w pasmie [30,85] przy wymaganych
>=2 (T0 100, T1 100, T2 64, T3 16). Klauzule naprawcze P_SANITY nie
zachodza literalnie: "wszystko >85" — nie; klif ">85 -> <30 miedzy
sasiednimi" — nie (64 nie jest >85); wzmocnienie T3 — bezprzedmiotowe
(T3 juz <30). Intencja klauzuli klifu (uzupelnienie rozdzielczosci
miedzy sasiednimi poziomami przy przepasci przez dolna krawedz pasma)
zachodzi dla T2->T3 (64->16); aneks realizuje te intencje jawnie.
Zmiana (jedyna):
Z1 os rozszerzona do drabiny: miedzy T2 a T3 wchodza poziomy
   T2a (K=1), T2b (K=2), T2c (K=3) — tlo rodziny B (jak T2/T3) +
   K dystraktorow o parametryzacji IDENTYCZNEJ z T3 (kolor czerwien
   z jitterem +-0.1, rozmiar celu +-20%, placement z seeda sceny).
   Rownowaznie: T2 = K=0, T3 = K=4; os dystraktorowa staje sie
   parametryczna w K. Sceny sweep bez zmian (43100-43149, identyczne
   na kazdym poziomie). Wyglad celu, kamera, spawn, zadanie — bez zmian.
Procedura: ewaluacja ISTNIEJACEGO checkpointu z P1 (bez retrenowania)
na pelnej drabinie {T0, T1, T2, T2a, T2b, T2c, T3}; werdykt P2 wg
niezmienionego progu >=2 poziomy w [30,85] liczonego po pelnej drabinie;
P3 eksperta rozszerzone o nowe poziomy (>=95% kazdy). Wszystkie poziomy
raportowane.
Higiena tezy: przed F3_GATE, przed powstaniem CfC; kalibracja osi na
krzywej ramienia sanity (GRU z pre-rejestrowanego rzutu) jest elementem
projektu P-SANITY od F3_PRE0; polityka nie jest modyfikowana, wiec zero
strojenia instrumentu na OOD.
Wybor poziomu bramki (po PASS P2R): najciezszy poziom w pasmie [30,85]
— zapisywany w F3_GATE, nie tutaj.
