# FALSIFIER VERDICT — R15 HYDRO-FRANCIS-TRANSIENT-GOVERNOR

## HARNESS DIES

Exact dynamic programming on the declared lattice does not beat a tuned
multi-stage wicket-gate closing law, and — the sharper finding — it does not
beat a **myopic greedy on its own lattice** either, because on every
trajectory the plant actually takes, the two select the same action. No Rust
was written. This is the falsifier working.

The kill rule was frozen before the run:

> Replayed on the CONTINUUM plant (L22), the harness LIVES only if
> **K1** exact DP is violation-free and reaches handover on every panel;
> **K2** it beats the best violation-free tuned multi-stage law on ≥ 24 of
> 36 panels; **K3** it beats the myopic greedy on ≥ 24 of 36 panels.

**K1, K2 and K3 all fail, and K1 fails badly.** Measured over 36 seeded
panels (`falsifier/FALSIFIER-RUN.txt`):

| Kill criterion | Threshold | Measured |
|---|---|---|
| **K1** DP violation-free and reaching handover | 36/36 | **5/36** — 30 panels breach the draft-tube floor on the plant, 1 never reaches handover |
| **K2** DP beats the best tuned multi-stage law | ≥ 24/36 | **0/36** — median **1.55× slower**, mean 6.90 s against 4.38 s |
| **K3** DP beats the myopic greedy | ≥ 24/36 | **1/36** — and greedy beats DP on **4/36**; the two return *identical* times on **31/36** |

The mandated incumbent is genuinely good, as L1 required: the tuned two-stage
law beats the tuned single-stage law on 21 of 36 panels, so multi-stage
structure is doing real work and a naive linear close was never a contender.
A third stage adds essentially nothing (1 of 36) — which is itself a small
independent finding about where the value in a closing law sits.

---

## 1. What was on trial

A Francis unit on an elastic penstock, full load rejection. The control is
the quantized wicket-gate rate, held for one wave-reflection period. Two-sided
window: penstock overpressure at the spiral case is the ceiling, draft-tube
inlet pressure the floor, with unit overspeed as a third declared machine
limit and an L14 sustainability gate on the surge left in the column when the
gate arrives.

The entry condition from `model-stage-gate/VERDICT.md` was honoured: the
transported state is carried in **Lagrangian / method-of-characteristics**
form, never as an Eulerian zone vector. MOC at one reach, `dt = L/a`, decision
epoch `2L/a`. The carried state is the **pair of incoming characteristics**
for the epoch's two arrivals — an epoch contains exactly two, and the one
arriving now was emitted by the runner one reflection period ago.

Contenders: an oracle-tuned 1-, 2- and 3-stage closing law with continuous
rates (the mandated incumbent, L1); an oracle-tuned reactive pressure
controller; a myopic greedy on the same lattice with the same gates and no
lookahead (the L11 guard); and exact DP with hard gates excluded from the
Bellman max.

---

## 2. The scouting checks, run BEFORE the falsifier — and they PASSED

This harness is not an R8 or an R9. The L18 pre-checks that killed those two
came out **positive** here, which is what makes the death interesting.

| Check | Result | Read |
|---|---|---|
| **L18** gated Pareto frontier, computed AFTER the gates, progress vs surge handed on | **37.4% single-dominator** (1429 sampled states with a real choice) | Genuinely non-monotone. R8 and R9 both died at ~90%. The rulebook does **not** delete the interesting actions. |
| **L17** per-crossing motion of the carried states | surge bands move **5 bands** median (3.9% / 4.5% of legal crossings stay in-band); speed moves 1 band median, 40.1% stay in-band | No blindness anywhere. The accumulators are fully observable at this banding. |
| **L22** mechanism sign, by ablation | see §5e | Ablating the gates does **not** let DP pull ahead of greedy — they stay identical either way. |
| **L21** L8 gate slack per gated axis, budget < 10% | ceiling **15.4%** median / 17.5% worst; **draft floor 22.4% median / 29.6% worst**; speed 2.7% | **Two of three axes over budget, the binding one by 2–3×.** |

So the mechanism is present and observable, and the constraint tax is the
thing that is out of budget. That is the R17 signature, and it is why the
resolution and oracle studies in §4 were run before this verdict was written.

---

## 3. The L8 sense check — the assumption was measurably WRONG

The contract, the roadmap and ordinary hydraulic intuition all say the same
thing: a two-sided window has two gates with **opposite** worst-case
operating points, so gating one edge silently passes half the failures (R6
found exactly that). The sense was measured rather than asserted:

| band corner | max spiral-case head | min draft-tube head | max speed |
|---|---|---|---|
| low speed, **high** surge | **377.0 m** | **−10.34 m** | 1.117 |
| high speed, low surge | 286.4 m | −8.07 m | 1.522 |
| low speed, low surge | 299.6 m | −9.08 m | 1.096 |
| high speed, high surge | 363.6 m | −9.33 m | **1.539** |

**The ceiling and the floor are worst at the SAME corner.** They are not an
opposite-sense pair at all. The draft-tube floor is a gate on `dQ/dt` at the
runner, and a low runner speed with a large incoming characteristic is
exactly what makes the deceleration steepest — the same corner that makes the
head highest. The factory has now asserted a mechanism's sign from intuition
three times and been wrong three times (R8's superlinear `R_th`, R9's dryout
cliff, and this). The characterization was rewritten to evaluate **every gate
at every band corner**, so no sense is assumed anywhere; it costs eight
integrations per action and it cannot be wrong about a direction.

---

## 4. Four instrument defects, found and fixed BEFORE the verdict was believed

R9's first verdict would have been *false* without its instrument check; R10
and R17 each found their first verdict was an artifact. The same discipline
was applied here, and it moved the harness a long way — from "the map cannot
close the gate at all" to "the map closes the gate cleanly and still loses".

1. **The wave's peak was being averaged away.** The first formulation carried
   a single epoch-mean surge scalar. Measured against the eight-reach plant it
   reproduced the MEAN and destroyed the PEAK — **L16 reappearing inside the
   harness built to respect it**. Fixed by carrying the exact pair of incoming
   characteristics, which makes the epoch transition exact for the model.
2. **The L8 sense was wrong** (§3). Fixed by all-corner evaluation.
3. **A wide bottom speed band biased every first decision.** The unit always
   enters at exactly synchronous speed, but the band-centre transition started
   the model half a band above the truth, put the first predicted landing band
   one step high on every panel, and walked the map straight into a dead cell.
   Fixed with non-uniform speed bands, fine at *both* ends. After the fix the
   predicted landing band matches the plant exactly on consecutive epochs.
4. **A piecewise-constant characteristic manufactured a suction spike.** The
   draft-tube floor is a gate on a filtered derivative whose time constant is
   `2·L_d/a ≈ 0.13 s`, four times shorter than the characteristic step `L/a`.
   Holding the incoming characteristic constant across a half-epoch dumps the
   whole flow change into one substep and invents up to **3 m** of suction
   against a **6 m** margin. Fixed with a piecewise-linear reconstruction, and
   the head evaluated at the exact characteristic samples (it is algebraic and
   unfiltered) while the floor is read from the reconstruction (it is not).

A fifth change was a reformulation rather than a defect fix: the uncontrolled
ring-down was moved **out of the MDP** into an analytic terminal charge plus
an L14 sustainability gate on the residual surge at closure. Gating an epoch
the action cannot influence turns feasibility into reachability and fills the
lattice with dead states no action ever chose — the dead-state fraction fell
from 53% to 43% and the map went from declining on its first or third
decision to completing every panel.

---

## 5. Why it dies — three measurements, in order of how much they matter

### 5a. On every reachable trajectory, exact DP and myopic greedy choose the same action

This is the decisive result and it is not a degenerate solve. Value iteration
converges in **10 sweeps**, values span 0 to −9 epochs, **21 539 of 46 592**
states are live, and the DP policy differs from the myopic greedy on
**11.4%** of live states that have a real choice — picking a strictly *slower*
rate on 2158 of them. The lookahead is genuinely in the map.

It never binds. Replayed on the continuum, DP and greedy return **identical
times on 31 of 36 panels** — and on the 5 where they differ, greedy wins 4.
The states where the policies disagree are not on any trajectory the plant
reaches, so the exact optimum and the myopic reflex are the same controller
in practice, and the exact one is marginally worse where they part company.

**This is L23 in its purest measured form.** The rulebook this domain forces
you to build — an overpressure ceiling, a draft-tube floor, an overspeed
ceiling and an L14 sustainability gate on the residual surge — *already*
encodes "spending now removes headroom later". Once those four gates are in
place there is one fastest legal action almost everywhere, and taking it is
what greedy does by definition. **The governor is the product; the optimizer
is decoration.**

### 5b. Even at ZERO conservatism, DP loses to a tuned two-stage law

An oracle instrument (R17's check): gates evaluated at band centres with no
guard, i.e. the L8/L21 tax set to zero. Not shippable — it breaks its own
gates — but it answers whether the lookahead is absent or merely taxed away.

| panel | tuned law (continuous rates) | exact DP, zero tax | ratio |
|---|---|---|---|
| 1000 | 2.98 s | 6.94 s | 2.33 |
| 1007 | 4.13 | 6.88 | 1.67 |
| 1014 | 3.98 | 8.94 | 2.25 |
| 1021 | 4.26 | 5.68 | 1.33 |
| 1028 | 3.63 | 6.06 | 1.67 |
| 1035 | 5.25 | 6.56 | 1.25 |
| 1042 | 3.06 | 7.13 | 2.33 |
| 1049 | 5.01 | 4.17 | **0.83** |
| 1056 | 5.17 | 8.61 | 1.67 |
| 1063 | 5.24 | 7.86 | 1.50 |

Exact DP with **no conservatism at all** wins 1 of 10 and is a median 1.67×
slower. The tax is real and out of budget, but the tax is not what kills this.

### 5c. It is NOT R9's death — the deployment form carries the advantage fine

R9 died because its band-quantized artifact could not carry a real +23.76%
advantage. That explanation was tested here and **rejected**. The same tuned
multi-stage law was re-searched restricted to the *lattice's own quantized
rate tiers, switched only at epoch boundaries*:

| | continuous rates | lattice-quantized | ratio |
|---|---|---|---|
| 8 of 10 panels | — | — | **1.00** |
| seed 1007 | 4.13 s | 5.50 s | 1.33 |
| seed 1014 | 3.98 s | 4.97 s | 1.25 |

Quantization costs **nothing on 8 of 10 panels**. The lattice is expressive
enough to hold the good schedule; DP simply has nothing better to find.

---

### 5d. The solved map breaks its own draft-tube gate on 30 of 36 panels

This is the finding that would matter most commercially, and it is a safety
failure of the same family as R9's — different cause, same shape. The map's
own characterization declares every action it takes legal; replayed on the
eight-reach plant, the runner-exit head goes below the declared −8.0 m floor
on **30 of 36 panels**, despite a declared model guard already standing the
gate 1.5 m back from the limit.

The cause is measured, not conjectured (§6): the floor is a gate on `dQ/dt`
whose time constant is four times shorter than the characteristic step the
method of characteristics imposes on the governor's model. The model cannot
see the transient it is being gated on. **A guard band absorbs an unmodelled
residual; it cannot absorb an unresolvable one.**

### 5e. Mechanism sign, by ablation — and it is the strong form of L23

The registered mechanism is that the wave arriving at the runner now was
launched by the gate one reflection period ago, so the ceiling that binds
*now* was bought *then*. The gates encoding that story — the spiral-case
ceiling and the L14 sustainability gate on the surge left at closure — were
ablated together (`falsifier/ablation.py`, output in `ABLATION-RUN.txt` and
`ABLATION-OFF.txt`):

| | DP strictly better | greedy strictly better | identical | DP clean |
|---|---|---|---|---|
| gates ON, as declared | 0/8 | 0/8 | **8/8** | 2/8 |
| gates OFF (slot 0 ablated) | 0/5 | 0/5 | **5/5** | **0/5** |

**Removing the gates does not let exact DP pull ahead of the myopic greedy.**
They remain identical either way. That is the *stronger* of the two L23
readings: it is not merely that a well-built sustainability gate cannibalised
its own optimizer — the lookahead was never binding on any reachable
trajectory in the first place, gates or no gates.

The ablation does, however, show what the L14 gate is worth as a *governor*:
without it, DP is violation-free on **0 of 5** panels instead of 2 of 8, and
its time to handover gets worse on 3 of 5 (9.40 s against 4.96 s; 12.96 s
against 7.10 s) because it slams the gate shut and pays for the surge it
leaves ringing. The rulebook is doing all of the useful work here, and it is
doing it for the greedy controller exactly as well as for the exact one.

## 6. The binding constraint, and the new lesson it produces

Across every panel the incumbent rides the **draft-tube floor** exactly —
measured `−7.99 m`, `−7.98 m`, `−7.69 m` against a declared `−8.00 m` — while
sitting 20–40 m clear of the overpressure ceiling. The floor is what this
domain is actually about, and it is a gate on `dQ/dt`.

That is the problem, and it is structural rather than a tuning failure:

> **The method of characteristics fixes the integration step at `Δx/a`. A
> gated variable whose own time constant is shorter than that step cannot be
> resolved by the representation the wave forces on you.**

L12 says the integration step must resolve the stiffest gated dynamic. Here
it *cannot*, without adding reaches — and every added reach adds a carried
characteristic to the state, so the resolution needed to gate the floor
honestly is bought at the same exponential price R9 paid. The declared model
guard that covers the residual eats 25% of a 6 m margin before the band-edge
tax (22.4% median) is charged at all, and even with the guard the solved map
still breaks the floor on the eight-reach plant.

Meanwhile the incumbent pays none of it. This is L21's own corollary,
realised: *a domain whose carried state is cheaply MEASURABLE at decision
cadence and whose gates are all instantaneous gives the incumbent exact
arithmetic for free.* A hydro plant measures spiral-case pressure and gate
position directly at kHz rates, and a reactive controller reading them in
exact arithmetic can ride a limit that a banded, worst-corner-gated map must
stand 30% back from.

### Proposed L25 — the tax is charged against a BUDGET or against the MARGIN

L21 established that band width is a constraint tax. R15 measures *what the
tax is charged against*, and it is the difference between a viable harness
and a dead one:

- In an **accumulator** domain (Czochralski slip damage, IGT life meter, cryo
  heat load) the L8 worst-edge costs **one band width of a BUDGET**, once,
  non-cumulatively. Czochralski's proof at any resolution is exactly this.
- In a **wave** domain the carried state *is* the gated quantity. The worst
  edge is charged directly against the **whole competed margin**, on every
  gate, every epoch — and here twice over, because two carried characteristics
  both feed the same head.

**Scouting rule:** before registering a harness, ask whether the carried
state enters the gate as an *accumulated budget* or as *the gated quantity
itself*. If it is the gated quantity, the L21 gate-slack budget must be met
at the shipped state count or the harness has no room — and in a
wave-dominated domain that is a very hard test, because the representation's
timestep is fixed by physics rather than chosen by the engineer.

---

## 7. What was checked and did NOT rescue it

- **L19 (the objective stops measuring too early).** Applied from the start: a
  declared handover state charges the ring-down to a quiet penstock, so a
  controller that slams the gate shut and leaves the column ringing pays for
  it. It did not flip the verdict — because a well-tuned closing law already
  leaves very little surge, which is itself the point.
- **L20 (the grid boundary doing a gate's work).** The speed grid extends to
  1.72 against a 1.55 ceiling and the surge grid to ±88 m against a ≈70 m
  legal band, so the declared gate is always what refuses.
- **L11 shape check.** The gated frontier is non-monotone (37.4%), so this is
  not the concave-allocation trap.
- **Resolution.** Halving the tax (the oracle run) moves the dead-state
  fraction from 43% to 31% and improves DP, but leaves it losing.

---

## 8. Honest limits of this experiment

- **The plant is synthetic and declared.** Single conduit, reservoir upstream,
  no surge tank, constant wave speed, quasi-steady friction plus a declared
  linear damping term, rigid-column draft tube, normalized Francis
  characteristic rather than a measured hill chart. A real unit with a surge
  tank has a completely different reflection structure and this verdict says
  nothing about it.
- **The floor limit and the ceiling factor are declared design numbers**
  (−8.0 m gauge and 1.32 × gross head). They were chosen so both gates bind
  on a meaningful fraction of panels; a plant whose ceiling binds first rather
  than whose floor binds first is a different problem, and §6's argument would
  have to be re-measured there.
- **The eight-reach plant is not a converged reference.** It is eight times
  finer than the governor's model in the transport operator, which is what
  the L22 protocol needs, but no grid-convergence study was run on it. The
  §5c quantization result and the §5a DP-equals-greedy result do not depend on
  it; the size of the model guard in §6 does.
- **Only full load rejection was modelled.** A partial rejection needs a
  residual generator torque this model does not declare.

---

## 9. What survives

The **P0 landscape finding stands independently of the verdict**: optimising a
multi-stage guide-vane closing law against simultaneous pressure-rise and
speed-rise objectives is a published, mature research field with a decade of
multi-objective-optimisation papers behind it, and the live patent art around
it (GE Vernova/Woodward, Voith, Andritz, Hitachi Mitsubishi Hydro) is dense.
Any future hydro pitch has to start from that, not from a linear close.

The **falsifier itself survives** as the estate's first wave-domain harness
instrument, and §6 is the reason to keep it: it is the cheapest available test
of whether a hyperbolic-PDE domain can carry a banded governor at all.

## Reproduce

```bash
cd falsifier
python falsifier.py            # 36 panels, ~1 h -> FALSIFIER-RUN.txt
python falsifier.py --quick    # 12 panels
python -u ablation.py          # L22/L23 sign check
python tally.py                # recompute the verdict tallies from a run
```

Requires only `numpy`. Every run is deterministic — the panel corpus is
generated by splitmix64 bit-mixing from fixed seeds, and there is no RNG
anywhere in the model or the solver.
