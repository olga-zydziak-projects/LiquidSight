# ANEKS-1 do DECYZJE_F3 — rewizja obserwowalnosci (2026-07-23)
Powod: P-SANITY wykryla defekt instrumentu, nie tezy: kanal percepcji
nie zawiera celu (cel w kadrze w 27/100 scen; mediana 0 klatek/epizod;
sukces polityki nieskorelowany z widocznoscia; DAgger x3 <=7%). P3=100%
izoluje problem do geometrii percepcji. Przyczyny lacznie: kamera pitch
~-8.5 st. + yaw sztywno 0 + spawn celu w pelnym okregu azymutalnym.
Zmiany (jedyne):
Z1 kamera: look = eye + R@[1, 0, -0.41] (pitch ~-22.3 st.); pozostale
   parametry kamery bez zmian (offset, FOV 60, near/far, TinyRenderer,
   shadow=1, lightDirection).
Z2 spawn celu: azymut wzgledem +x w [-25 st., +25 st.], dystans poziomy
   od startu w [1.0 m, 2.0 m]; losowanie z seeda sceny jak dotad.
Uzasadnienie doboru: wysokosc kamery ~0.52 m, srodek celu z=0.08 ->
delta z ~0.44 m; pionowe pole widzenia przy pitch -22.3 st. pokrywa cel
od d=2.0 m (kat -12.4 st., margines do gornej krawedzi ~20 st.) do
d~0.35 m; stozek spawnu +-25 st. miesci sie w HFOV +-30 st. -> cel
w kadrze od t=0 przez caly dolot; martwe pole terminalne d<0.35 m
akceptowane jawnie — symetryczne dla obu przyszlych ramion, mostkowane
pamiecia rdzenia.
Co sie NIE zmienia: progi i procedury P_SANITY.md; akcja 6D bez yaw;
cel na podlozu (wyglad staly); definicja sukcesu/FAIL i geofence;
r_goal/z_hover/t_dwell; os T0-T3, pule tekstur i wszystkie pule seedow.
Higiena tezy: rewizja nastepuje PRZED zamrozeniem F3_GATE i przed
powstaniem CfC; motywacja wylacznie z T0 (P1) i P3 — zero wplywu
wynikow T1-T3. Wiernosc twierdzeniu [4]: zadanie testuje wizualny
poscig w petli zamknietej przy celu obserwowalnym — poszukiwanie
(active perception) nie jest przedmiotem tezy.
Odrzucone alternatywy: (b) yaw w akcji — luka imitacyjna (etykiety
eksperta koduja kierunek z GT nieobecny w pikselach przy celu poza
kadrem; skok zakresu w strone active perception); (c) podniesienie celu
— nie usuwa slepoty azymutalnej; (a-solo) sam pitch — j.w.
