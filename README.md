# [QCEOM RL] Hydro Francis Transient Governor — **DECLINED AT THE FALSIFIER**

Wicket-gate closing-rate governance for a Francis turbine on an elastic
penstock, under a two-sided window: penstock overpressure as the ceiling and
draft-tube cavitation as the floor.

**This harness was killed by its own kill test before any Rust was written.**
That is the intended function of the QCEOM-RL factory's P1 phase, and it is
the fourth harness in the estate to end this way. The repository ships the
evidence, not a product.

- **Verdict and the numbers behind it:** [`FALSIFIER-VERDICT.md`](FALSIFIER-VERDICT.md)
- **What was specified before it was tested:** [`PLAN.md`](PLAN.md)
- **Landscape (written before any code, and it stands independently):**
  [`PATENT-LANDSCAPE.md`](PATENT-LANDSCAPE.md)
- **The experiment:** [`falsifier/falsifier.py`](falsifier/falsifier.py),
  measured output in `falsifier/FALSIFIER-RUN.txt`,
  `falsifier/ABLATION-RUN.txt` and `falsifier/ABLATION-OFF.txt`

---

## The one-paragraph result

On a full load rejection, exact dynamic programming on the declared lattice
returns **the same time as a myopic greedy on 31 of 36 seeded panels** — and
loses to it on 4 of the remaining 5 — while beating an oracle-tuned two-stage
wicket-gate closing law on **0 of 36**, at a median 1.55× slower. The
lookahead is genuinely present in the map (the policies differ on 11.4% of
live states that have a real choice, DP picking a strictly slower rate on
2158 of them) but it never binds, because the four hard gates the domain
forces you to build already encode "spending now removes headroom later".
Ablating those gates does not let DP pull ahead either. The governor is the
product; the optimizer is decoration.

Worse for the product than either: the solved map **breaks its own
draft-tube floor gate on 30 of 36 panels** when replayed on an eight-reach
plant, despite a declared guard already standing it 1.5 m back from the
limit. The cause is measured — that gate is on `dQ/dt`, whose time constant
is four times shorter than the characteristic step the method of
characteristics imposes on the governor's model. **A guard band can absorb an
unmodelled residual; it cannot absorb an unresolvable one.**

| Kill criterion (frozen before the run) | Threshold | Measured |
|---|---|---|
| K1 DP violation-free, reaching handover | 36/36 | **5/36** |
| K2 DP beats the best tuned multi-stage law | ≥ 24/36 | **0/36** |
| K3 DP beats the myopic greedy | ≥ 24/36 | **1/36** |

## Why the state has the shape it has — and the MOC requirement

R15 was registered behind a shared model-stage gate with R7, R16 and the HTC
slurry reactor. That gate has been run
(`model-stage-gate/VERDICT.md` in the core repo) and it **passed for exactly
one representation**: a coarse Eulerian zone vector missed all 11 real ceiling
breaches and admitted 10 forbidden actions into its safe set at every
resolution tested, while a Lagrangian representation passed everything with
four state elements. Carrying the transported state in Lagrangian /
method-of-characteristics form is therefore an **entry condition**, not a
preference.

For water hammer that is the natural form anyway: it is wave propagation on a
hyperbolic PDE, and the method of characteristics discretizes it exactly at a
timestep tied to the wave speed. This harness uses MOC at **one reach**,
`dt = L/a`, with the decision epoch equal to the reflection period `2L/a`. The
forward characteristic arriving at the runner during epoch `k+1` is exactly
what the runner emitted during epoch `k`, reflected off the reservoir:

```
CP(t) = 2·H0 − G(t − 2L/a) − friction,        G = H − B·Q,   B = a/(gA)
```

An epoch contains exactly **two** characteristic arrivals, so the exact
Lagrangian carried state is the **pair** of incoming characteristics, on top
of the gate position and the unit speed. The first version of the falsifier
carried a single epoch-mean scalar instead, and it reproduced the returning
wave's mean while destroying its peak — **L16 reappearing inside the harness
built to respect it**, measured against an eight-reach plant. That is recorded
because it is the same failure the model-stage gate measured, at a different
scale.

Each incoming characteristic is banded as its **surge component**
`W = CP − CP_ss(τ, ω)`, against the quiescent value for the current operating
point. Banding the raw characteristic would bury the entire pressure rise
inside one band, because `B·Q` is an order of magnitude larger than the surge.

## Assumptions the MOC formulation makes

Every one of these is declared in code and every result is void without them.

- **Quasi-steady friction, plus a declared linear damping term.**
  Darcy–Weisbach is evaluated on the instantaneous discharge. Unsteady
  friction (Zielke, Brunone) is **not** modelled. The quasi-steady term
  vanishes as `Q → 0`, so a closed penstock would ring forever; an aggregate
  linear resistance `ζ = 0.030` of the pipeline characteristic impedance `B`
  stands in for unsteady friction, pipe-wall damping and runner leakage. It is
  declared, not fitted, and it appears **identically** in the governor's model
  and in the plant it is graded on.
- **Constant wave speed.** No free gas, no cavitation-induced wave-speed
  collapse, no pipe-wall viscoelasticity. `a` is a declared constant per
  plant. If the penstock entrains air, every number here is void.
- **Single conduit, reservoir upstream.** No surge tank, no manifold, no
  second unit. A surge tank changes the reflection structure completely.
- **Rigid-column draft tube.** `2·L_d/a ≪` the reflection period, so the draft
  tube and tailrace are treated as an incompressible column with inertia
  rather than a wave conduit.
- **Normalized Francis characteristic** in unit-quantity (hill-diagram) form —
  discharge falling toward runaway and torque vanishing at it — not a measured
  hill chart for a specific runner.
- **Full load rejection only.** A partial rejection needs a residual generator
  torque this model does not declare.

## The gates, and the F2 audit

Four hard gates, all reward-neutral:

| # | Gate | Declared limit |
|---|---|---|
| 0 | penstock overpressure at the spiral case | ≤ 1.32 × gross head |
| 1 | draft-tube inlet piezometric head | ≥ −8.0 m gauge (guard above the ≈ −10 m vapour limit) |
| 2 | unit overspeed | ≤ 1.55 × rated, against a runaway of 1.85 |
| 3 | L14 sustainability at closure | residual surge inside the band from which the FREE oscillation cannot breach the ceiling |

**F2 rule (R9's finding, and the sharpest safety rule the factory has): every
hard gate must be evaluable from the indexed state and the action alone.**
Audited and satisfied here. The gate position is exact (integer bands per
epoch); the speed band and both surge bands are read at their own band
corners; nothing else enters — no ambient, no unmeasured plant coefficient,
no quantity unknown at solve time. The characterization evaluates every gate
at **every corner** of the state's bands rather than at an assumed worst
edge, because the assumed edge was measured to be wrong (see the verdict, §3).

## Evidence ladder

| Rung | Status |
|---|---|
| P0 patent landscape | **written**, before any code |
| P1 falsifier, 36 seeded panels, continuum replay | **run — HARNESS DIES** |
| P2 physics in Rust | not built |
| P3 MDP · P4 benchmark · P5 provenance | not built |
| P6 QEMU Cortex-M55 · P7 STM32N657 | not built |

No claim of certification, grid-code compliance, or suitability for any
specific unit is made anywhere in this repository.

## Reproduce

```bash
cd falsifier
python falsifier.py            # 36 panels  -> FALSIFIER-RUN.txt
python falsifier.py --quick    # 12 panels
python -u ablation.py          # L22/L23 mechanism sign check
python tally.py                # recompute the verdict tallies from a run
```

Requires only `numpy`. Every run is deterministic: the panel corpus is
generated by splitmix64 bit-mixing from fixed seeds, and there is no RNG
anywhere in the model or the solver.
