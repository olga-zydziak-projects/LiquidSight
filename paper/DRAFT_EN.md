# Where Liquid Networks Help, Hurt, and Fail to Train: A Pre-Registered Boundary Map

*Olga Żydziak — Independent Research — 2026-07-24. Draft EN v1 (W2) + W3 revisions. Target venue: arXiv cs.LG/cs.RO (companion P0 as PDF/arXiv).*

> **Draft conventions.** Every quantitative value traces to `paper/NUMBERS.md` (canonical tables T1–T10). Fixed terminology (used throughout): **arms** (A_GRU, A_NCP = AutoNCP-wired CfC, A_CFC = dense CfC); **lr legs** (an arm evaluated at one learning rate); **gates** (frozen criteria: P-SANITY, F3-GATE); **annexes** (sanctioned, provenanced unfreezes, Annex 1–4); **fixes F1–F4** (the four recipe restorations that made a CfC trainable at all, §6 — distinct from the regime rows R1–R4 of the boundary map, §5); **stop rule** (Annex-4's rule ending instrumental annexes in phase 3a); **trainability tax** (the capability gradient observed at core-parameter parity). Effect differences are reported in **percentage points (pp)**. Figures are generated (`paper/figures/*.pdf`); captions are final.

---

## Abstract

*(~200 words)*

Liquid neural networks — continuous-time cores such as LTCs and their closed-form successor (CfC), wired with NCP/AutoNCP — are claimed to grant perception-and-control policies greater robustness under distribution shift. We subject that claim to a pre-registered measurement program spanning three task regimes at core-parameter parity and equal training budget: open-loop classification (companion P0, PASTIS), open-loop onset detection (companion E6), and closed-loop control (state-loop, LiquidFlight v1.0; vision-loop, this work). In the richest regime — a vision-in-the-loop fly-to-target twin with a perceptual-shift ladder — no CfC arm reaches our pre-registered nominal-capability precondition (mean ≥90% success at core parity of 27,648 ±2%) on either allowed learning rate, so the robustness claim is **untestable under our precondition** and we ran **zero out-of-distribution (OOD) evaluations**. Beneath that boundary we measure a **trainability tax**: at identical budget, a GRU control reaches 100% while the wired CfC peaks at 92% (per-leg means up to 75.3%, a 43 pp seed spread) and the dense CfC caps at 65%. We attribute trainability to wiring, localize a continuous-time Δt implementation dependency, and contribute a reusable gate/precondition methodology with an arithmetic early-stopping rule. A negative result, pre-registered, maps where the mechanism can and cannot be measured.

---

## 1. Introduction

*(~1 page)*

Continuous-time recurrent networks have become an attractive substrate for embodied perception and control. Liquid Time-Constant networks (LTCs) and their closed-form counterpart (CfC), especially when wired with Neural Circuit Policies (NCP/AutoNCP), have been reported to yield policies that generalize better under distribution shift than conventional gated recurrences such as GRUs. The most cited demonstration in the flight domain reports that a compact liquid policy attends to the task-relevant part of the visual scene and holds up under perceptual perturbation \citep{chahine2023flight}.

Two properties of that literature motivate this work. First, demonstrations are typically reported **without core-parameter parity** against a matched baseline and **without pre-registration** of the success criterion; a favorable curve is shown, but the counterfactual — a same-budget, same-data baseline under a criterion fixed in advance — is often absent. Second, the field does not report a **trainability layer**: whether the liquid core can be brought to competence at all, at parity, under a fixed budget, before any robustness question is even asked.

We take the claim seriously enough to try to falsify it under conditions it should survive. We build an honest twin — identical encoder, identical head, identical data and budget, cores matched to within ±2% — and we freeze the success criterion before measuring. This paper reports the vision-loop regime (phase 3) as the primary result and folds it into a portfolio-level **boundary map** with two companion regimes.

**Contributions**, mapped to our claim register (C1–C8):
- A pre-registered vision-loop twin in which the robustness claim is **untestable under our precondition** — the deciding arm never qualifies, and we hold to zero OOD evaluations (C1).
- A measured **trainability tax** at parity: GRU 100% vs wired-CfC (peak 92%, per-leg means up to 75.3%) vs dense-CfC (cap 65%), at identical budget (C2).
- The finding that the boundary is **variance, not mean** — seed instability is the object of measurement, echoing the companion P0 population spread (C3).
- A **wiring attribution**: AutoNCP makes the CfC trainable where the dense CfC caps (C4).
- Engineering findings on the continuous-time Δt path and DAgger procedure (C5, C6).
- A transferable **methodology**: gates, preconditions, annexes with a stop rule, and arithmetic early resolution (C7); plus an instrument characterization (C8).

---

## 2. Related Work

*(~0.4 page)*

**Liquid networks.** Liquid Time-Constant networks model the hidden state as a continuous-time dynamical system whose time constants are themselves input-dependent, giving the network a natively continuous notion of elapsed time \citep{hasani2021ltc}. Their closed-form successor, the CfC, replaces the numerical ODE solve with a closed-form update that preserves the continuous-time gate while removing solver cost, making the family practical at scale \citep{hasani2022cfc}. Neural Circuit Policies and their automatic wiring (AutoNCP) impose a sparse, structured connectivity on the recurrent core, inspired by biological circuits and reported to improve auditability and compactness \citep{lechner2020ncps}. The robustness claim we test derives largely from a flight-navigation demonstration in which a small wired liquid policy generalizes out of distribution and attends to task-relevant structure \citep{chahine2023flight}; we treat that claim as the hypothesis under test and its lineage as the object we reproduce at parity. Two of our arms — a wired CfC (A_NCP) and a dense CfC (A_CFC) — are chosen precisely to isolate the contribution of the wiring from that of the continuous dynamics.

**Continuous-time and state-space cousins.** Deep state-space models share the continuous-time framing: S4 parameterizes long-range dependencies through a structured state-space kernel \citep{gu2022s4}, Mamba adds input-dependent selectivity for linear-time sequence modeling \citep{gu2023mamba}, and Liquid-S4 connects the liquid formulation to this family \citep{hasani2023liquids4}. These situate our small recurrences within a broader continuous-time lineage; we do not evaluate them here.

**Pre-registration, reproducibility, and imitation learning.** Our methodology adopts the discipline of freezing success criteria before measurement and reporting honest baselines, in the spirit of the machine-learning reproducibility and pre-registration literature \citep{pineau2021reproducibility,sogaard2023preregistration}. Training uses behavioral cloning followed by DAgger, the canonical no-regret reduction of imitation learning to online learning \citep{ross2011dagger}; a central engineering finding of this work concerns the interaction between the DAgger update mode and continuous-time cores (§6). The vision harness is built on gym-pybullet-drones \citep{panerati2021gym}, and the companion open-loop regime uses the PASTIS satellite time-series benchmark \citep{garnot2021pastis}.

---

## 3. The Measurement Program

*(~1 page; C7)*

The program is a house methodology applied uniformly across regimes.

**Honest twin.** Each arm shares the same encoder, the same `Linear(64→6)` head with identical output scaling, the same training data and budget; cores are matched to a reference of 27,648 core parameters to within ±2% (Table T1). The only sanctioned inter-arm difference is the learning rate, whose provenance is documented.

**Frozen criteria; MEASURE = REPORT.** Success criteria are frozen in a gate document before any measurement; whatever is measured is reported, including nulls and boundaries. The vision-loop gate (F3-GATE) fixes the OOD level (T2b), the primary metric, the decision threshold, and n before a single OOD scene is rendered.

**Gates and preconditions.** A capability **precondition** (nominal success ≥90% per arm) must pass before the thesis metric is evaluated; the precondition is *not* the thesis. Failing it triggers a sanctioned, nominal-only repair (a learning rate from the pre-registered fallback grid — nothing else) and a full retrain, logged; exhaustion is a STOP for a human decision, not a verdict on the thesis.

**Annexes with a stop rule.** When the recipe diverges from a frozen, known-good reference, we unfreeze via an **annex** that cites the reference line-by-line and applies the change symmetrically to all arms. The stop rule (Annex-4) declares the last instrumental annex of phase 3a: if a CfC arm still fails the precondition afterward, FAIL becomes a reported **boundary**, not another annex.

**Arithmetic early resolution.** Because the precondition is a mean over 10 seeds, a leg can be resolved before all seeds run: after k seeds summing to S, if `S + (10 − k)·100 < 900` the leg cannot reach 90% and is declared FAIL. This is arithmetic on the frozen criterion, not a change to it. In phase 3 it reduced the run to **13 full cycles instead of 40** and left one four-seed batch never launched (Table T8).

**Determinism contract.** Environment, rendering, and seeding are bit-exact reproducible **within a single machine** (`s1_env_det`, two runs, rgb/kin/setpoint identical). Cross-machine hashes may differ and that is not a failure — determinism is a within-machine property (S0-NOTES), not a cross-machine guarantee.

---

## 4. Harnesses

*(~0.75 page)*

The portfolio uses three instruments, one per regime.

**4.1 PASTIS twin (P0).** Sentinel-2 crop classification of a phenologically confusable pair (soft winter wheat vs. corn) under test-time observation dropout, with a shared CNN encoder (28,752 parameters) and only the recurrent core swapped between CfC and GRU. Open-loop, day-scale. Companion; numbers in Table T9, verified against the companion report \citep{zydziak2026p0}.

**4.2 LiquidFlight (state-loop, v1.0).** A closed-loop drone flight twin (gym-pybullet-drones \citep{panerati2021gym}) with a setpoint→DSL-PID inner loop at 48 Hz, an observation-dropout OOD axis and a gap-length (latency) axis, and a time-constant (τ) inspection panel; CfC(32) vs. GRU at core parity, everything but the core bit-identical between arms. Frozen reference (Table T10). The vision-loop harness reuses this execution layer verbatim (sha256-pinned copies).

**4.3 LiquidSight (vision-loop, phase 3 — this work).** A fly-to-target task from a 64×64×3 forward camera plus kinematics: reach a ground marker and hold a hover within `r_goal` for the final dwell window. Physics at 240 Hz, control at 48 Hz, camera and policy tick at 12 Hz; the target lives only in pixels. A privileged DSL-PID expert supplies behavioral cloning (BC) labels; three DAgger rounds follow. The perceptual-shift axis is a distractor ladder T0–T3 (T2/T2a/T2b/T2c = K∈{0,1,2,3} distractors on structured backgrounds), with P-SANITY establishing that the axis resolves difficulty and that the expert ceiling is reachable at every level (§7). The gate level is T2b.

---

## 5. Results Across Regimes

The boundary map summarizes the direction and measurement resolution of the effect in each regime. No measurement crosses its pre-registered threshold.

| row | regime / harness | effect direction | verdict / resolution |
|---|---|---|---|
| R1 | open-loop classification, day-scale (P0) | weak positive under dropout | null (margin < pooled std); quantitative (Table T9, \citep{zydziak2026p0}) |
| **R2** | open-loop onset detection, low FAR (E6) | **negative** (unfavorable to the liquid core) | directional; **qualitative (secondary source)** |
| R3 | state-loop control, ms-scale (LiquidFlight v1.0) | zero (neither help nor harm from the core) | quantitative (Table T10) |
| R4 | vision-loop, this work (LiquidSight) | untestable under our precondition | precondition FAIL at parity; quantitative (NUMBERS.md T1–T8) |

### 5.4 Vision-loop (phase 3) — the primary result

*(~1.5 pages; C1–C4)*

**5.4a — The robustness claim is untestable under our precondition (C1).** After restoring the known-good recipe in full (core construction, Annex-3; training procedure, Annex-4) and exhausting the only sanctioned lever — the learning-rate grid {3e-4, 1e-3} — **no CfC arm reaches the pre-registered precondition** of mean ≥90% nominal success at core parity (Table T2). All four lr legs resolve to FAIL by arithmetic early resolution: A_NCP at 3e-4 = 16.5% (resolved at k=2), A_NCP at 1e-3 = **72.2% (k=4)**, A_CFC at 3e-4 = 27.0% (k=2), A_CFC at 1e-3 = 55.3% (k=3). Because the **deciding arm** (A_NCP, the AutoNCP-wired CfC faithful to the wiring in the cited claim) does not qualify, the thesis metric — a T2b margin of A_NCP over A_GRU with threshold `M > pooled_std`, n=10 — is **untestable under our precondition**. We therefore ran **zero OOD evaluations** in the entire phase: gate stages B (the A_GRU precondition sweep) and C (the OOD ladder) were skipped by the branch, so the pre-registered verdict remains untouched and unprejudiced.

This is deliberately *not* a falsification of the thesis. A test requires a qualifying deciding arm; without the precondition there is no test. The result is a cell in the boundary map, not a verdict on the mechanism.

[FIGURE b — *Per-seed nominal success for each lr leg.* Points show nominal success (100 scenes, level T0) for every trained seed across the four CfC lr legs (A_NCP and A_CFC × {3e-4, 1e-3}); horizontal bars mark per-leg means; a dashed rule marks the 90% precondition. The A_GRU control (100%) is shown for reference. The wired arm at 1e-3 spans 49–92% (43 pp); no leg mean crosses 90%.]

**5.4b — A trainability tax at parity (C2).** At identical data, budget, and procedure, and with cores matched to ±2%, nominal capability forms a gradient: **A_GRU 100%** (stable; dwell failures 0) > **wired CfC** (A_NCP; peak 92% at seed 45010/1e-3; per-leg mean 72.2% at k=4) > **dense CfC** (A_CFC; cap 65% at seed 45012/1e-3). Core-parameter parity alone does not buy capability; the continuous-time core pays a trainability tax at this budget. The dominant residual failure is **dwell** — the drone reaches the marker but does not hold the hover precisely — while catastrophic **tilt is eliminated** at 1e-3 (0 tilt across all CfC cycles, versus 78/100 for the dense CfC under the pre-Annex-4 procedure).

**5.4c — The boundary is variance, not mean (C3).** The wired arm at 1e-3 spans **49–92% across seeds — a 43 pp spread** — under one fixed procedure, while the GRU control is a stable 100%. Reporting only the k=4 mean (72.2%) understates the phenomenon; the **full six-seed characterization (75.3%, spread 43 pp)** shows the boundary is a property of the between-seed distribution, not a sample-size artifact. The CfC at parity does not "fail to learn"; it learns **unstably and dwell-limited, on average below 90%**. This mirrors the companion P0 result \citep{zydziak2026p0}, where the retention margin (+0.1127) and its pooled standard deviation (0.1759) are nearly invariant between n=3 and n=15 (Table T9) — population spread that does not shrink with n.

**5.4d — Wiring attribution (C4).** The contrast between arms attributes trainability to the wiring: the AutoNCP-wired CfC reaches a 92% peak and per-leg means up to 75.3%, whereas the dense CfC caps at 65%, across seeds and at the 1e-3 lever. The attribution holds on the 1e-3 lever; at 3e-4 the ordering inverts (dense 27.0% > wired 16.5%), so the wiring benefit is itself learning-rate dependent and we report it as such. A historical, single-seed diagnostic corroborates the readout dimension: reading the full state rather than six motor neurons raises reach from 8/50 to 26/50 (§6).

[FIGURE c — *DAgger rollout dynamics per round.* Success rate of on-policy rollouts across DAgger rounds r1→r2→r3 for each arm. The GRU control climbs 18→100→100; CfC arms stay low or flat (e.g., wired at 1e-3, seed 45010: 44→32→53; dense at 1e-3, seed 45012: 0→34→44), illustrating that the aggregate does not close for the continuous-time cores.]

### 5.1 Open-loop classification, day-scale (P0) — companion

*(~0.5 page, condensed; C3 linkage)*

The PASTIS twin gives a directional-but-null signal: at full cadence the GRU leads on macro-F1 (0.9073 ±0.0137 vs 0.8802 ±0.0121), but under observation dropout the CfC retains more — retention R(0.6) of 0.6415 ±0.1138 vs 0.5288 ±0.0622, a **+0.1127 margin against a pooled std of 0.1759, i.e. null** by the pre-registered rule. An absolute-F1 crossover appears at d=0.6 (CfC 0.5642 ±0.0985 above GRU 0.4798 ±0.0567, despite a −0.027 start), and the degradation slope is gentler for the CfC (−0.5095 vs −0.6936). Crucially, margin and pooled std are near-invariant from n=3 to n=15 — the boundary is population spread, not sampling noise. All P0 numbers are verified against the companion report \citep{zydziak2026p0} (Table T9).

### 5.2 Open-loop onset detection, low FAR (E6) — companion

*(~0.3 page; qualitative)*

The onset-detection regime contributes the **negative direction** of the map: at a low false-alarm-rate operating point the effect sign is **unfavorable to the liquid core**, as recorded in the program compendium; the primary E6 report is not preserved in the project archive. We therefore state this regime **qualitatively only** and report no numerical values for it — in particular the detection-delay delta, the sweep parameter, and the false-alarm-rate definition are not carried into the prose, since their primary source could not be verified. The regime enters the boundary map as a directional cell (§5, row R2), not as a quantitative result.

### 5.3 State-loop control, millisecond-scale (LiquidFlight v1.0) — companion

*(~0.4 page)*

In the state-loop regime the continuous-time lever (Δt) is not behaviorally load-bearing (Table T10). With a setpoint action abstraction the CfC-32 policy flies under 500–1300 ms observation gaps and the episode-failure cliff moves from ~102 ms (raw-RPM stabilization) to ~779 ms; the Δt mechanism is *visible* in the state dynamics (recovery after a gap) but yields **no behavioral edge** — ablating the Δt channel flies identically. The fitted time constants are short (median τ ≈ 35 ms, IQR 24–69 ms), so a 500 ms gap is ≈14× τ and the model does not bridge gaps with long memory; τ serves as an explainability handle, not a source of advantage. Under the A1 perturbation grid there were **0 tip-overs**. The regime contributes a **zero** to the map: neither help nor harm attributable to the liquid core at this horizon.

---

## 6. Engineering Findings

*(~1 page; C5, C6)*

Bringing a CfC to the point where it will run at all in this harness required restoring a known-good recipe in four provenanced steps (fixes **F1–F4**); each is an **engineering finding, established by single-seed controlled probes (diagnostic, not statistical)** — not a statistically powered ablation.

**F1 — Backbone.** The dense CfC built without a backbone under the parity constraint does not reach the target (reach 8/50); adding a frozen-style backbone restores it (35/50, ≈ GRU) (Annex-3).

**F2 — The Δt path and its units (C5).** The continuous-time core — the sole locus of the thesis mechanism — is load-bearing only after two corrections. First, the time-span scale sets the gate regime: with an explicit `ts` in **seconds** (0.0833 s per 12 Hz tick) reach is 39/50, versus 15/50 at ts=1.0 (ticks) and 9/50 at ts=4.0; the post-init gate drive `|t_a·ts|` scales accordingly (0.010 / 0.125 / 0.501), so a mis-scaled `ts` freezes or destabilizes the cell. Second, we found a **library bug**: `ncps.torch.CfC` rejects explicit `timespans` when the batch size exceeds one (scalar, `(B,1)`, and `(B,)` all raise; only `None`=1.0 works), which had trapped the arms at `ts=1.0`. We work around it by stepping the cell manually. The auxiliary thesis is therefore: **Δt is load-bearing implementationally, not advantageously** — in this harness we could not measure an advantage because the precondition was never met.

**F3 — Full-state readout.** Reading the wired core's full state rather than six motor neurons lowers BC error (0.0047 vs 0.0220) and raises reach (26/50 vs 8/50) (Annex-3, §S3).

**F4 — DAgger update mode (C6).** Continuous-time cells are sensitive to the DAgger update procedure. Under the gate's original v1 mode (continue from the previous weights + final-epoch checkpoint), the dense CfC becomes unstable (tilt 78/100) and the wired CfC collapses its rollouts (1→0→0); the dense CfC is stable after BC alone (0 tilt), so the instability is **induced by the procedure**, not the construction. Adopting the frozen-C1 mode symmetrically (retrain from scratch each round + best-validation checkpoint, 120 epochs per stage; Annex-4) removes the tilt (78→0 at 1e-3) and follows the canonical DAgger formulation \citep{ross2011dagger}. The **GRU is robust to both procedures** (100% either way).

A mechanistic signature accompanies this (C6a): for every CfC arm the best validation error after BC alone is low (~0.00012–0.0009) but **rises** after the DAgger aggregate (rounds r1–r3), and the best epoch moves early (e.g., wired at 1e-3, seed 45013: 119→41→26→37) — the core does not close the fit to the policy-visited distribution as well as it fits the clean expert. The GRU holds its best validation low across all rounds (.000168→.000112) — a different regime.

[FIGURE e — *Best-validation trend, BC vs aggregate.* Best validation error per stage (r0 = BC → r1→r2→r3 = DAgger aggregate) for the CfC arms (rising after aggregation, best epoch moving earlier) against the GRU control (monotonically low). Round-level (four points per cycle); full per-epoch curves are not persisted and would require re-measurement.]

---

## 7. Instrument Characterization and Protocol Economics

*(~0.75 page; C8, C7a)*

**Axis resolution and expert ceiling (C8).** The perceptual-shift axis resolves difficulty monotonically. The sanity policy degrades **100/100/64/46/36/24/16** across T0/T1/T2/T2a/T2b/T2c/T3 (50 scenes per level), placing three levels inside the pre-registered [30%, 85%] band and selecting **T2b (36%)** as the hardest in-band gate level. The privileged expert reaches a **100% ceiling at every level** (P3R), confirming that the distractors do not block physical reachability — the axis touches pixels only. Determinism is bit-exact **within a machine** (rgb/kin/setpoint identical across two runs; cross-machine equality is neither required nor claimed).

[FIGURE d — *Sanity ladder and expert ceiling.* Policy success across the distractor ladder (T0→T3: 100/100/64/46/36/24/16) with the [30,85] band shaded and the T2b gate level marked; the expert ceiling (100% at every level) overlaid.]

**Protocol economics (C7a).** The binding run comprised **13 full training cycles** (plus one GRU control), ~**57.1 h** of cumulative compute (sum of per-cycle wall time; parallel wall-clock was shorter but is not an authoritative per-arm cost — Table T7). Arithmetic early resolution spared a complete four-seed batch relative to the 40 cycles a full n=10 over four legs would have required.

---

## 8. Discussion

*(~1 page)*

**Synthesis.** Across the regimes we map, the sign of the effect depends on the task: a weak positive in sparse open-loop observation (P0), a negative under low-FAR onset detection (E6), a zero in state-loop control (LiquidFlight), and — in the richest regime, vision-in-the-loop — a question that never reaches the conditions of measurement, because the advantage is preceded by a trainability tax at parity. No measurement crosses its pre-registered threshold. The unifying reading is that **task construction decides whether the mechanism can reveal itself at all**: the continuous-time core needs a regime whose dependencies it is positioned to exploit, and at parity it must first be trainable there.

**Demonstration culture vs. falsification.** A pre-registered null carries evidential weight that a single favorable curve does not. Much of the liquid-network robustness literature is demonstrated rather than falsified: a favorable model is shown on a task chosen after the fact, without a same-budget parity baseline and without a criterion fixed in advance. Our program inverts that stance — it commits to a threshold, a level, and a seed count before any out-of-distribution scene is seen, and it reports whatever the instrument returns, including a boundary. The cost of this discipline is that we sometimes conclude "untestable" rather than "wins" or "loses"; the benefit is that the three cells we *can* state (weak-positive, negative, zero) are not artifacts of selective reporting. The map says where to look and where not to — it does not claim the mechanism is absent, only that under parity, fixed budget, and frozen criteria we did not measure it in these harnesses.

**When the twin re-arms.** The vision-loop cell would re-enter measurement under conditions that unlock trainability without breaking parity. The cleanest such condition is a **symmetric budget increase** for all arms — more epochs, more DAgger rounds, or more data applied identically to GRU and CfC — carried until the deciding arm (A_NCP) meets the precondition; the wired arm at 1e-3 is the natural starting point, already at 92% best seed and 75.3% mean. Because the increase is symmetric, the duel remains fair: if the GRU also improves, the parity contract is preserved. Two subsidiary questions gate the value of that rerun. First, the sensitivity of continuous-time cells to the DAgger update mode (F4) is an open research problem worth isolating on its own — why does retrain-from-scratch with best-validation selection stabilize a CfC that continuation destabilizes, when a GRU is indifferent to both? Second, whether the residual dwell failure reflects a precision limit of the continuous-time state under this readout, or merely under-training, is answerable only once the precondition is met. Until then, we resist reading the boundary as evidence about the mechanism itself.

**Next habitat.** The mechanism's most plausible next habitat is a regime with genuinely variable time steps or asynchronous/event-stream sensing, where the continuous-time gate has something to integrate — offered as a direction, not a promise.

---

## 9. Limitations

*(~0.5 page; C-scope + GAP-4)*

- **Simulation only.** PyBullet dynamics, no photorealism, no sim-to-real transfer.
- **One harness per regime.** A single fly-to-target task family at 64×64; results may not generalize across task families.
- **Parity at ~27k core parameters.** Findings are stated at this capacity; other capacities are untested.
- **n=10 with a finality rule.** Seeds 45010–45015 were used (early resolution); increasing n, or changing the level or threshold after seeing any OOD result, is forbidden by the gate.
- **No OOD measurement in the vision-loop regime.** This is a *consequence* of the unmet precondition, not a design choice.
- **Engineering findings are single-seed probes.** The four recipe restorations (fixes F1–F4) are diagnostic controlled probes (n=1 for most), illustrative rather than statistically powered (GAP-4).
- **Determinism is within-machine**, not cross-machine.
- **Fixed training budget.** The trainability tax is measured at BC-120 + DAgger×3; a higher symmetric budget is unmeasured.
- **Single-operator program**; one task family per regime.
- **Companion E6 primary report not preserved.** The onset-detection regime (R2) is stated qualitatively from a secondary source (program compendium); its primary report is absent from the project archive, so R2 carries no numerical values and its direction should be read as directional evidence, not a measured effect size.

---

## 10. Reproducibility and Artifacts

*(~0.3 page)*

We release the liquidflight v1.0 and liquidsight repositories (tags and gate commits), the frozen documents (F3_PRE0, DECYZJE_F3 and Annexes 1–4, P-SANITY, F3-GATE), sha256 manifests of the execution layer, the seed pools, the per-cycle logs (`results/i3b/progress.jsonl`), and the reports. The companion P0 ships as a separate PDF/arXiv artifact \citep{zydziak2026p0}. Instrument determinism is within-machine bit-exact (`s1_env_det`); bit-for-bit reproduction across different GPUs is not guaranteed (inherent to CUDA).

---

## 11. Conclusion

*(~0.5 page)*

We set out to test a robustness claim about liquid networks and, in the richest regime, found the claim **untestable under our pre-registered precondition**: at core parity and fixed budget, no continuous-time arm becomes reliably competent, so no out-of-distribution verdict can be earned. The first-order result is therefore a **boundary map** — where the mechanism helps (weakly), hurts, is neutral, and cannot yet be measured — together with a **trainability tax** that the field does not usually report: a same-budget capability gradient from a stable GRU (100%) through a wired CfC (peak 92%) to a dense CfC (cap 65%). The measurement methodology — gates, preconditions, provenanced annexes with a stop rule, and arithmetic early resolution — is the portable contribution. A negative result, pre-registered, is a map of where to measure next.

---

## Appendix A — Program timeline

[FIGURE a — *Gate and annex timeline.* The phase-3 program as a time axis (2026-07-22 to 07-24): frozen gates (P-SANITY, F3-GATE criterion, parity v1/v2) and annexes (A1 observability, A2 distractor ladder, A3 core construction, A4 training procedure), each with a one-sentence reason; "frozen" markers where criteria were locked.]

One-line reasons (from DECYZJE_F3 and annex preambles):
- **Annex-1 (observability).** Target spawned in the frontal cone; camera pitched −22.3° so the marker is in-frame.
- **Annex-2 (distractor ladder).** Axis extended with T2a/T2b/T2c (K=1/2/3) to fill resolution between T2 and T3.
- **Annex-3 (core construction).** Fixed three CfC construction defects vs frozen C1 (backbone, ts-in-seconds, full-state readout).
- **Annex-4 (training procedure).** Unified the training procedure with frozen C1 (from-scratch per round, best-val, 120 epochs), symmetrically; declared the stop rule.

## Appendix B — Frozen criteria (verbatim pointers)

- **P-SANITY** (P1 capability ≥90%; P2 axis resolution ≥2 levels in [30,85]; P3 expert ceiling ≥95%/level) — `P_SANITY.md`.
- **F3-GATE §4** (precondition: mean nominal success ≥90% per arm; fallback grid {3e-4, 1e-3}; no OOD before all arms pass).
- **F3-GATE §5** (primary metric M = mean_s succ(A_NCP,s) − mean_s succ(A_GRU,s), n=10; pooled_std = sqrt((sd(A_NCP)² + sd(A_GRU)²)/2); verdict M > pooled_std; binding at n=10).
- **Stop rule** (Annex-4): the last instrumental annex of phase 3a; a subsequent precondition FAIL becomes a reported boundary.

## Appendix C — Per-seed tables (binding run I3b)

*Generated from `results/i3b/progress.jsonl` (read, not measured). Columns: nominal % | failures | DAgger rollout r1→r2→r3 | best-val r0→r3 | best-epoch r0→r3 | cycle seconds.*

**A_NCP @ 1e-3** (best leg; mean 72.2% at k=4, 75.3% over six seeds, 43 pp spread)

| seed | nom% | failures | rollout | best-val r0→r3 | best-epoch | sec |
|---|---|---|---|---|---|---|
| 45010 | 92 | dwell 8 | 44→32→53 | .000174→.000735→.000773→.000587 | 117,109,49,65 | 18,889.3 |
| 45011 | 79 | dwell 21 | 43→37→52 | .000153→.000552→.000761→.000696 | 118,90,43,39 | 19,138.1 |
| 45012 | 69 | dwell 31 | 25→11→36 | .000169→.001639→.001851→.001187 | 118,30,29,115 | 19,441.2 |
| 45013 | 49 | dwell 51 | 9→1→13 | .000184→.0015→.001835→.001711 | 119,41,26,37 | 18,986.6 |
| 45014 | 86 | dwell 14 | 32→12→37 | .000121→.00076→.001057→.000878 | 119,47,44,50 | 19,471.4 |
| 45015 | 77 | dwell 23 | 25→38→23 | .000152→.000646→.000952→.000934 | 119,52,35,92 | 18,992.2 |

**A_NCP @ 3e-4** (mean 16.5%, resolved k=2)

| seed | nom% | failures | rollout | best-val r0→r3 | best-epoch | sec |
|---|---|---|---|---|---|---|
| 45010 | 22 | dwell 76, tilt 2 | 22→13→25 | .000566→.001791→.001973→.001843 | 115,46,47,34 | 8,742.0 |
| 45011 | 11 | dwell 89 | 12→0→12 | .000721→.002559→.002478→.002428 | 115,45,46,40 | 19,081.3 |

**A_CFC @ 1e-3** (mean 55.3%, resolved k=3; cap 65%)

| seed | nom% | failures | rollout | best-val r0→r3 | best-epoch | sec |
|---|---|---|---|---|---|---|
| 45010 | 44 | dwell 56 | 0→8→44 | .000648→.001095→.000926→.000965 | 113,81,97,86 | 13,107.9 |
| 45011 | 57 | dwell 43 | 2→14→40 | .000631→.000708→.001072→.001127 | 115,81,104,100 | 14,810.0 |
| 45012 | 65 | dwell 35 | 0→34→44 | .00047→.000735→.001421→.001041 | 116,107,118,115 | 12,839.9 |

**A_CFC @ 3e-4** (mean 27.0%, resolved k=2)

| seed | nom% | failures | rollout | best-val r0→r3 | best-epoch | sec |
|---|---|---|---|---|---|---|
| 45010 | 18 | dwell 70, tilt 12 | 8→0→6 | .000887→.005571→.003664→.002938 | 118,37,56,53 | 7,154.3 |
| 45011 | 36 | dwell 64 | 2→0→8 | .000889→.004062→.003624→.002709 | 99,45,55,100 | 15,056.7 |

**A_GRU control @ 1e-3** (procedure v2)

| seed | nom% | failures | rollout | best-val r0→r3 | best-epoch | sec |
|---|---|---|---|---|---|---|
| 45010 | 100 | — (dwell 0) | 18→100→100 | .000168→.000247→.000179→.000112 | 119,101,116,118 | 6,079.6 |

## Appendix D — Early-resolution formula and savings

For a per-arm precondition of mean ≥90% over 10 seeds, after k seeds with partial sum S the leg is declared FAIL when

  **S + (10 − k)·100 < 900.**

Applied to the four legs: A_NCP@3e-4 FAIL at k=2 (S=33; 833<900); A_NCP@1e-3 FAIL at k=4 (S=289; 889<900); A_CFC@3e-4 FAIL at k=2 (S=54; 854<900); A_CFC@1e-3 FAIL at k=3 (S=166; 866<900). Total executed: 13 cycles versus 40 for a full n=10 over four legs; one four-seed batch (45016–45019) was never launched. This is arithmetic on the frozen criterion, not a modification of it.

---

## TODO — items not closable inside the repository

Everything sourceable in-repo is closed. The following require an artifact or a human decision that does not live in this repository:

1. **E6 primary report (§5.2 / map row R2) — external artifact missing.** The primary RAPORT_E6 could not be located (T0: no liquidwatch repo; absent from home/Downloads/Documents/Desktop; the liquidwatch backup holds only E1/E2). R2 is stated qualitatively from the program compendium (secondary source), with no numerical values. *To close:* Olga supplies the primary E6 report → promote R2 to a quantitative cell.

2. **`panerati2021gym` bib field — `[BIB:verify]` on `pages`.** The IROS-2021 proceedings page range for gym-pybullet-drones could not be confirmed online; venue, year, authors, and arXiv id are verified. *To close:* confirm page numbers from the IEEE Xplore record.

*Closed in W3:* all P0 numbers verified against the companion PDF (Table T9, zero discrepancies); v1.0 numbers sourced from the frozen liquidflight reports (Table T10); title selected (candidate 2); bibliography written (`paper/latex/references.bib`, 13 entries). No `[TODO-src]` marker remains anywhere in the prose. All C1–C8 quantities are sourced in NUMBERS.md T1–T10.
