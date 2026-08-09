# P0 GATE-ZERO — Patent & prior-art landscape

**R15 HYDRO-FRANCIS-TRANSIENT-GOVERNOR.** Written before any code, per the
factory protocol. Scope of the scan: wicket-gate / guide-vane closing laws,
hydro turbine governors, penstock surge and water-hammer protection, and
draft-tube cavitation / column-separation protection.

**Headline finding, stated first because it is the one that constrains the
build: this space is crowded, old, and — unusually — crowded on the
*academic* side more dangerously than on the patent side.** Optimising a
multi-stage guide-vane closing law against simultaneous pressure-rise and
speed-rise objectives is an established, published research field with a
decade of multi-objective-optimisation papers behind it. Anything this
harness claims must be stated against that literature, not against a naive
linear close.

---

## 1. Live claim clusters

### 1a. Turbine governors (the incumbent product)

| Holder | Cluster | Read |
|---|---|---|
| **GE Vernova** (owner of the entire legacy **Woodward** hydro governor IP, acquired 2000 via Nexus Controls) | electro-hydraulic and digital speed-governing systems for hydro turbines; PID/PIID speed loops, gate limit and rate-limit logic, servomotor control | The governor *product* is theirs and has been for a century. We do not build a governor loop. |
| **Voith Hydro** | wicket-gate mechanisms, servomotors, locking and shear-protection devices (e.g. US3920351A, automatic locking device for hydraulic turbine wicket gates); shut-off valve control | Mechanism and actuator claims. We command an existing actuator; we do not claim one. |
| **Hitachi Mitsubishi Hydro** | **US7092795B2** — turbine apparatus and governor, priority 2002-10-04. Independent claim: a governor whose derivative / integral / proportional gain *ratios shift as a function of speed-error magnitude*, to stabilise a pump-turbine operating in its S-characteristic region. | A **gain-scheduled PID**. Directly adjacent, and a good example of what the incumbent art actually claims: online closed-loop regulation of speed. |
| **Andritz Hydro** | pump-turbine and guide-vane apparatus (e.g. US11649798, reversible pump turbine and guide vane); digital governor products | Apparatus and hydraulic-design claims, not policy claims. |
| Multiple | **estimator-driven closure**: "close the guide-vane assembly at a rate determined by an *estimated* penstock pressure rise, estimated from rotational frequency, acceleration, head and gate position" | **This is the closest live art to anything we might do, and it is exactly the form we must not take.** It is an *online model-based estimator inside the closure loop*. |

### 1b. Surge / water-hammer protection

Surge tanks, air chambers, pressure-relief valves (synchronous bypass
valves), one-way surge tanks, air-inlet valves. These are **hardware**
mitigations with long, mature patent families and, more importantly, long
expired ones. The Allievi elastic water-hammer equations (1902–1913) and
the method of characteristics as applied to pipelines (Streeter & Wylie,
1967) are open literature and unencumbered.

### 1c. Draft-tube cavitation / column separation

Predominantly **academic**, not patented: numerical simulation of draft-tube
cavitation at off-design conditions, 1D–3D coupled simulation of water-column
separation in pump-turbine draft tubes after load rejection, and occurrence
criteria for column separation (the pressure at the draft-tube inlet
remaining below vaporisation pressure for a sustained interval). Hardware
patents exist for *suppression* geometry (J-groove draft tubes, air
admission). Nothing found claims a **control policy** that treats the
draft-tube minimum pressure as an executable hard constraint on the gate
rate.

## 2. The crowding that actually matters — published prior art

This is the honest part, and it is more constraining than the patents.

**Optimisation of two-stage and three-stage guide-vane closing schemes is a
solved and published problem.** The literature includes multi-objective
formulations that trade unit speed rise against water-hammer pressure using
metaheuristics (enhanced multi-objective gravitational search, NSGA-family
GAs), asynchronous / desynchronised guide-vane closure to cut pressure rise,
step-by-step closure control laws presented as a partial substitute for a
surge tank, and closing schemes derived specifically from the pump-turbine
S-shaped region.

Consequences the factory must accept:

1. **"We optimise the closing law" is not a claim.** It is the state of the
   art. Reporting a win over a *naive linear close* would be worthless, which
   is why the roadmap mandated a **tuned multi-stage closing law** as the
   incumbent (L1). This harness competes against a schedule that has been
   grid-searched with hindsight on each panel.
2. **"We use MOC / Allievi" is not a claim.** Open literature since 1902.
3. **"We add a draft-tube pressure constraint" is a modelling choice**, not
   an invention; the phenomenon and its criterion are published.

## 3. Design-around posture (what this harness deliberately is *not*)

The posture is structural, not a drafting trick, and it is checkable in the
shipped artifact:

- **No online estimator, and no capacity for one.** The scanned governor
  claims read on an *online, in-transient, adaptive* loop: a hydraulic or
  thermal model that runs while the machine is rejecting load and rewrites
  the schedule from what it observes. The deployable artifact here is a
  **pre-solved lookup table** plus a fail-closed validator. The NOSTD device
  path takes **no floating-point operation at all** — band selection is
  integer comparison on decimetre-scale fixed point. *A device that cannot
  multiply two floating-point numbers cannot run a water-hammer estimator.*
- **Not a speed-regulation loop.** We do not close a speed loop, schedule PID
  gains, or regulate frequency. The unit's governor keeps doing that. We
  supply the **rate command envelope** for a transient event.
- **Not an open-loop schedule either.** A closing *law* is a function of
  time-since-trip. This is a function of **measured state** — gate position,
  unit speed, and the measured spiral-case pressure from which the incoming
  characteristic is reconstructed. That distinction is the only thing here
  with any chance of being non-obvious, and it is deliberately *not*
  argued in this file (see §5).
- **Constraints are declared, not learned.** The penstock ceiling, the
  draft-tube floor and the overspeed ceiling are numbers the plant owner
  writes down. We enforce them; we do not infer them.

## 4. Standing FTO gate

Before any commercial engagement on this harness:

1. A professional FTO search on the **specific** control-policy formulation,
   in the jurisdictions of the target plant, covering GE Vernova/Woodward,
   Voith, Andritz, Hitachi Mitsubishi Hydro, Toshiba, Sulzer and the Chinese
   pumped-storage institutes (which hold much of the recent guide-vane
   closing-scheme work).
2. A literature novelty review against the guide-vane closing-scheme
   optimisation corpus specifically. The patent search alone is **not
   sufficient** here — the published corpus is the tighter constraint.
3. No claim of certification, compliance with any grid code, or suitability
   for a specific unit. Model-fidelity risk sits with the engagement (thesis
   §7): the hard gates enforce the *declared* rulebook faithfully, and a
   mis-declared penstock is enforced faithfully and uselessly.

## 5. Boundary on this document

Per factory doctrine, **no assessment of our own potential novelty appears in
any published file.** Any such assessment lives in `NOVELTY-PRIVATE.md`,
which is gitignored before the first commit and is not part of the shipped
repository.

## Sources consulted (open web, 2026-08-09)

- US3920351A — Automatic locking device for hydraulic turbine wicket gates (Voith Hydro).
- US7092795B2 — Turbine apparatus and governor for turbine (Hitachi Mitsubishi Hydro; priority 2002-10-04).
- US11649798 — Reversible pump turbine and guide vane for the reversible pump turbine.
- US3536431A — Control device for wicket gates of a turbine installation.
- CA1099806A — Electro-hydraulic governor employing duplex digital controller system.
- GE Vernova, Hydro Turbine Speed Governing System (product literature; Woodward hydro IP ownership).
- Lei et al., *Optimization and decision making of guide vane closing law for pumped storage hydropower system*, 2023.
- *Optimization of Guide Vane Closing Schemes of Pumped Storage Hydro Unit Using an Enhanced Multi-Objective Gravitational Search Algorithm*, Energies 10(7):911, 2017.
- *Guide-Vane Closing Schemes for Pump-Turbines Based on Transient Characteristics in S-shaped Region*, J. Fluids Eng. 138(5):051302, 2016.
- *Wicket Gate Closure Control Law to Improve the Transient of a Water Turbine*, Adv. Mater. Res. 732–733:451.
- *Water column separation in pump-turbine after load rejection: 1D-3D coupled simulation*, Renewable Energy, 2021.
- *Evolution mechanism of water column separation in pump turbine: model experiment and occurrence criterion*, Energy, 2023.
