# DECYZJE_3C — zamrożone decyzje MVP osłony (3c-MVP)

**Data:** 2026-07-31. **Status:** DECYZYJNY, zamrożony na czas pomiaru S3c1.
Prowieniencja parametrów empirycznych: kalibracja offline **S3c0** (commit `bdfa41e`,
`RAPORT_S3C0.md`, artefakty `results/s3c0/`). Wartości poniżej **nie podlegają strojeniu po
obejrzeniu wyników** (MIERZĘ = RAPORTUJE). Podstawa: `PRE_3C0.md` §2–§3.

Osłona jest czystym wrapperem nad zamrożoną polityką `ckpt/s3b2r/policy_gc5.pt` (granica
67%/10%). Zero zmian w polityce, kanale, env, percepcji, ekspercie.

| # | decyzja | wartość zamrożona | prowieniencja / uzasadnienie |
|---|---|---|---|
| **D1** | punkt pracy θ_conf (reguła R-A) | **brak progu conf** — R-A ograniczona do wariantu **NO_MATCH/timeout**; conf **logowany per tick** bez bramkowania | S3c0 (`bdfa41e`): ROC separacji conf poprawne-vs-błędne **AUC = 0.6496** zbiorczo (poniżej progu płaskości 0.65; per-bieg 0.60–0.72). Replay: progowanie conf net-negatywne (≈2 fałszywe odmowy sukcesu na 1 złapaną złą akcję). Zrealizowane ryzyko `PRE_3C0 §7` („ROC conf może być płaska"). Powód `LOW_CONF_LOCK` pozostaje w enumeracji, ale **nigdy nie odpala** w MVP. |
| **D2** | θ_age (reguła R-B) | **θ_age = 2.0 s** (0.25 znormalizowane, AGE_MAX=8.0) | S3c0 (`bdfa41e`): histogramy age-at-dwell-entry z G2 — sukcesy wchodzą w dwell z wiekiem <4 s (p95 = 2.0 s), porażki mają ogon 21 epizodów przy >6 s (kanał zamrożony). Próg 2.0 s nie dotyka żadnego epizodu czystej bazy (0/45), łapie ~38% porażek trybu „zamrożony kanał". |
| **D3** | timeouty | **T_acq = 3.0 s, T_hold = 3.0 s** | `PRE_3C0 §3` D3 (proste, jawne; do rewizji po S1). |
| **D4** | definicje wyników | **księgowość trójwynikowa**: SUKCES / ODMOWA / PORAŻKA. Odmowa ≠ sukces i ≠ porażka. **Wrong-action = porażka pierwszej klasy.** Asserty jednoznaczności wyniku epizodu. | `PRE_3C0 §1`, §3 D4. Obowiązuje od pierwszego pomiaru (bez podwójnego liczenia HOLD→ALLOW→sukces). |
| **D5** | zbiór pułapek S2 | pula **47400–47449** (addytywna, poza pulami pomiarowymi): **25 ep** komenda→obiekt NIEOBECNY w scenie (47400–47424), **25 ep** cel za geofencem (47425–47449). Oczekiwanie: 100% odmów z właściwym powodem (NO_MATCH / GEOFENCE). | `PRE_3C0 §3` D5. Generator wariantu w `s3c1/` (rozszerzenie testowe, addytywne). |

## Maszyna stanów osłony (wyprowadzenie z reguł R-A..R-D, `PRE_3C0 §2`)

- **SEEKING** — brak jakiegokolwiek locka. Polityka leci na wejściu no-lock (ALLOW akcji).
  Brak locka do **T_acq = 3.0 s** → **REFUSE(NO_MATCH)** (R-A/R-D; przy braku progu conf
  „no-match" = brak dostarczenia przez T_acq).
- **TRACKING** — lock aktywny, dron poza martwym polem lub kanał świeży → **ALLOW**.
- **DWELL-GUARD** — dystans do celu < 0.5 m (martwe pole) i age_s > **θ_age = 2.0 s** →
  **HOLD** (position-hold przez egzekutor v1.0: setpoint = [pozycja bieżąca, prędkość 0]).
  Świeży tick (age_s spada ≤ θ_age) w oknie **T_hold = 3.0 s** → powrót do **ALLOW**;
  timeout T_hold bez odświeżenia → **REFUSE(STALE_AT_DWELL)** (R-B).
- **GEOFENCE** — cel poza areną lub pozycja drona poza granicą (arena_half = 2.0 m,
  margines 0.2 m → próg 1.8 m), w **każdym** stanie → **REFUSE(GEOFENCE)** (R-C).

Decyzje deterministyczne (reguła + wartość + próg), logowane per tick do jsonl pod overlay
aktu 4 dema. Powody enumerowane: `NO_MATCH`, `STALE_AT_DWELL`, `GEOFENCE`, `LOW_CONF_LOCK`
(martwy w MVP wg D1).
