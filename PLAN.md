# [QCEOM RL] Hydro Francis Transient Governor — Spec & Phased Plan

**Status: the falsifier killed this harness at P1. Nothing beyond P1 was
built.** This file records the specification the falsifier was written
against, unedited, so the death certificate in `FALSIFIER-VERDICT.md` can be
read against what was actually attempted.

## QCEOM-RL DOMAIN HARNESS SPEC — R15 HYDRO-FRANCIS-TRANSIENT-GOVERNOR

1. **DOMAIN & BUYER**: medium-head Francis hydro. Buyers are plant owners and
   governor integrators. The commercial unit is **seconds to a safe,
   restartable machine after a full load rejection**, at zero penstock
   overpressure and zero draft-tube cavitation.
2. **DECISION PROBLEM**: given a declared penstock and unit, choose the
   quantized wicket-gate closing rate, held for one wave-reflection period,
   that reaches the commanded gate opening and leaves the water column quiet
   in the least time, subject to a hard rulebook — solved offline per plant
   and deployed as a static lookup table to the governor.
3. **STATE ENCODER** (the part the model-stage gate constrained): method of
   characteristics at the wave-speed timestep, ONE reach, `dt = L/a`, decision
   epoch `= 2L/a`. State =
   `(gate-position band 0..12) × (speed band 0..13, non-uniform) ×
    (incoming-characteristic surge band A 0..15) × (surge band B 0..15)`
   = **46 592 states × 7 rate tiers**. The two surge bands are the exact
   Lagrangian carried state: an epoch contains exactly two characteristic
   arrivals, and the one arriving now was emitted by the runner one
   reflection period ago. A single epoch-mean scalar was tried first and
   reproduced the wave's MEAN while destroying its PEAK — L16 reappearing
   inside the harness built to respect it.
4. **CHARGE ENCODER**: repulsors on the high-surge rows, attractor on the
   closed-gate layer, shaping weight 0.0. Never reached — no kernel run.
5. **CONSTRAINT DECLARATIONS (the rulebook)**: hard gates —
   (a) **penstock overpressure**: spiral-case head ≤ 1.32 × gross head;
   (b) **draft-tube floor**: runner-exit piezometric head ≥ −8.0 m gauge, a
   declared guard above the ≈ −10 m vapour limit;
   (c) **overspeed**: ω/ω_r ≤ 1.55 against a runaway of 1.85;
   (d) **L14 sustainability**: the residual surge at the moment the gate
   arrives must be inside the band from which the FREE oscillation cannot
   breach the ceiling on its own.
   Authority: Allievi elastic water-hammer equations discretized by the
   method of characteristics (Streeter & Wylie), a normalized Francis
   characteristic in unit-quantity form, and a rigid-column draft tube.
6. **SCENARIO CORPUS**: seeded deterministic panel generator (gross head ×
   penstock length × wave speed × friction factor × load carried at the
   instant the breaker opens) via splitmix64, 36 panels. Every panel is a
   full load rejection.
7. **INCUMBENT BASELINE (mandated, L1)**: oracle-tuned 1-, 2- and 3-stage
   wicket-gate closing laws, grid-searched per panel with hindsight, with
   CONTINUOUS rates and oracle knowledge of that panel's plant; plus an
   oracle-tuned reactive pressure controller; plus a myopic greedy on the
   same lattice with the same gates (the standing L11 guard). Two- and
   three-stage closing laws are standard hydro practice and are genuinely
   good; a naive linear close was never a contender and no claim against one
   is made anywhere in this repository.
8. **ACCEPTANCE CRITERIA** — never reached. The P1 kill rule, frozen before
   the run, was: exact DP violation-free on every panel, beating the best
   violation-free tuned multi-stage law on ≥ 24 of 36 and the myopic greedy
   on ≥ 24 of 36, all measured on the CONTINUUM plant (L22).
9. **ENGINE CONFIG**: γ = 0.9999 (L10), shaping weight 0.0.
10. **DEPLOYMENT TIER**: would have been hybrid — hosted solve per plant, map
    packed into a `QCHF` provenance image, NOSTD twin on the governor
    controller. Not built.
11. **BOUNDARY**: synthetic panels only; single conduit, reservoir upstream,
    no surge tank; constant wave speed; quasi-steady friction plus a declared
    linear damping term; full load rejection only. No grid-code, certification
    or plant-suitability claim of any kind.
12. **PHASES**: P0 patent landscape (done, `PATENT-LANDSCAPE.md`) → P1
    falsifier (**done — HARNESS DIES**, `FALSIFIER-VERDICT.md`) → P2..P8 not
    started.

---

## What the falsifier was allowed to spend before it was believed

Four instrument defects were found and fixed BEFORE the verdict was
accepted, per the standing discipline that R9, R10 and R17 all established:

1. A single epoch-mean surge scalar aliased the returning wave's peak. Fixed
   by carrying the exact pair of incoming characteristics.
2. The L8 worst-case SENSE of the draft-tube floor was asserted from the
   two-sided-window intuition and MEASURED to be wrong. Fixed by evaluating
   every gate at every band corner, so no sense is assumed at all.
3. A wide bottom speed band put the band-centre transition half a band above
   the truth on every panel and walked the map into a dead cell on its first
   decision. Fixed with non-uniform speed bands, fine at both ends.
4. A piecewise-constant reconstruction of the incoming characteristic
   manufactured a draft-tube suction spike worth up to 3 m against a 6 m
   margin. Fixed with a piecewise-linear reconstruction — and the residual
   is the finding, not the fix.

A fifth change was a reformulation, not a defect fix: the uncontrolled
ring-down was moved out of the MDP and into an analytic terminal charge with
an L14 sustainability gate, because gating an epoch the action cannot
influence turns feasibility into reachability and fills the lattice with
dead states no action ever chose.
