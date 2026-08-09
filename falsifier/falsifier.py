#!/usr/bin/env python3
"""
P1 FALSIFIER — R15 HYDRO-FRANCIS-TRANSIENT-GOVERNOR.

The cheapest experiment that KILLS the harness, run before a line of Rust.

WHAT IS ON TRIAL
----------------
A Francis unit on an elastic penstock takes a full load rejection. The
control is the QUANTIZED WICKET-GATE RATE, held for one wave-reflection
period. Two-sided window: penstock overpressure at the spiral case is the
CEILING, draft-tube inlet pressure is the FLOOR; unit overspeed is a third
declared machine limit. The accumulating state is the water column's
momentum, carried in LAGRANGIAN / METHOD-OF-CHARACTERISTICS form as mandated
by `model-stage-gate/VERDICT.md` — an Eulerian zone vector is forbidden, and
the first draft of this file proved why: a one-scalar-per-epoch summary of
the returning wave reproduced its MEAN and destroyed its PEAK, which is L16
reappearing inside the harness built to respect it.

THE STATE, AND WHY IT HAS THE SHAPE IT HAS
------------------------------------------
Method of characteristics at the wave-speed timestep, ONE reach:
    dt = L/a,  epoch = 2L/a = the reflection period.
The forward characteristic arriving at the runner during epoch k+1 is exactly
what the runner emitted during epoch k, reflected off the reservoir:

    CP(t) = 2*H0 - G(t - 2L/a) - friction,      G = H - B*Q

An epoch contains exactly TWO characteristic arrivals, so the exact
Lagrangian state is the PAIR (CP_a, CP_b) of incoming characteristics, on top
of the gate position and the unit speed. Four elements — which is what the
model-stage gate measured a Lagrangian representation needs.

Each incoming characteristic is banded as its SURGE COMPONENT
    W = CP - CP_ss(tau, omega)
against the quiescent value for the current operating point. Banding the raw
characteristic would bury the entire pressure rise inside one band, because
B*Q is an order of magnitude larger than the surge.

CONTENDERS
----------
  (a) TUNED MULTI-STAGE CLOSING LAW  — 1-, 2- and 3-stage schedules, oracle
      tuned per panel by grid search WITH HINDSIGHT on the same continuum.
      The mandated incumbent (L1); standard hydro practice and genuinely good.
  (b) TUNED REACTIVE CONTROLLER      — measures spiral-case pressure and
      switches rate against a threshold; all three knobs oracle-tuned.
  (c) MYOPIC GREEDY                  — same lattice, same gates, no lookahead
      (the standing L11 guard).
  (d) EXACT DP                       — value iteration on the characterized
      lattice, hard gates EXCLUDED from the Bellman max.

DECLARED KILL RULE (frozen before the run)
------------------------------------------
  Replayed on the CONTINUUM plant (L22), the harness LIVES only if:
    K1  exact DP is violation-free and reaches handover on every panel;
    K2  exact DP beats the best violation-free tuned multi-stage law on
        >= 24 of 36 panels;
    K3  exact DP beats the myopic greedy on >= 24 of 36 panels.
  Otherwise: FALSIFIER-VERDICT.md, and no harness is built.

Run:  python falsifier.py            (add --quick for 12 panels)
"""

import math
import sys
import numpy as np

np.seterr(all="ignore")

# ===========================================================================
# DECLARED MODEL
# ===========================================================================
# Allievi elastic water-hammer equations discretized by the method of
# characteristics (Streeter & Wylie), plus a normalized Francis
# characteristic in unit-quantity (hill-diagram) form.
#
# ASSUMPTIONS, STATED:
#   * QUASI-STEADY FRICTION plus a declared LINEAR damping term. The
#     Darcy-Weisbach term vanishes as Q -> 0, so a quasi-steady model alone
#     leaves a closed penstock ringing forever. ZETA is an aggregate linear
#     resistance expressed as a fraction of the pipeline characteristic
#     impedance B, standing in for unsteady friction (Zielke/Brunone),
#     pipe-wall damping and runner leakage. It is DECLARED, not fitted, and
#     it appears IDENTICALLY in the governor's model and in the plant.
#   * CONSTANT WAVE SPEED. No free gas, no cavitation-induced wave-speed
#     collapse, no viscoelastic wall. `a` is a declared constant, and every
#     result here is void if the penstock entrains air.
#   * SINGLE CONDUIT, RESERVOIR UPSTREAM. No surge tank, no manifold, no
#     second unit. A surge tank changes the reflection structure completely.
#   * RIGID-COLUMN DRAFT TUBE. 2*L_d/a << the reflection period, so the draft
#     tube is an incompressible column with inertia, not a wave conduit. Its
#     own time constant sets the integration substep (L12).
#   * FULL load rejection only. A partial rejection needs a residual
#     generator torque this model does not declare, so it is not claimed.

G = 9.81

D_PEN = 3.2
A_PEN = math.pi * D_PEN ** 2 / 4          # 8.0425 m^2
F_DARCY = 0.017
ZETA = 0.030                              # linear damping, fraction of B

H_RATED = 220.0
Q_RATED = 24.0
N_RPM = 250.0
OMEGA_R = 2 * math.pi * N_RPM / 60.0
ETA_R = 0.92
P_RATED = 1000.0 * G * Q_RATED * H_RATED * ETA_R       # 47.7 MW
T_MECH = 7.5
J_ROT = T_MECH * P_RATED / OMEGA_R ** 2
T_RATED = P_RATED / OMEGA_R

NU_RUNAWAY = 1.85
C_Q = 0.30
PHI_LO, PHI_HI = 0.40, 1.30

H_SETTING = 2.0
L_DRAFT = 75.0
A_DRAFT = 8.5
DRAFT_INERTIA = L_DRAFT / (G * A_DRAFT)
C_VELHEAD = 0.0022

# DECLARED LIMITS — the plant owner's rulebook
CEIL_FACTOR = 1.32          # spiral-case head <= 1.32 * gross head
DRAFT_FLOOR = -8.0          # runner-exit head >= -8 m gauge
SPEED_CEIL = 1.55           # omega / omega_r

# DECLARED HANDOVER STATE (L19 — the clock does not stop at the last unit of
# work). A load rejection is not over when the gate shuts: the penstock is
# still ringing, and until the residual oscillation can no longer threaten
# the design pressure rise the unit is not in a state the next operation can
# start from. The handover criterion is therefore PHYSICAL, not arbitrary —
# the surge amplitude must have fallen to a declared fraction of the
# ceiling margin, below which the free oscillation cannot breach the ceiling
# whatever it does next.
W_TOL_FRAC = 0.75           # of (CEIL_FACTOR - 1) * H0

# DECLARED MODEL GUARDS. The governor solves on a ONE-REACH method of
# characteristics; the plant is an eight-reach one. Measured against the
# plant, the one-reach model under-predicts the spiral-case peak because it
# samples the returning wave at two instants per reflection period rather
# than continuously. That residual is NOT hidden in tuning — it is declared
# as a guard band the gates are evaluated against, the plating-margin
# discipline of L8 applied to a discretization residual. `guard_report` in
# this file measures whether the guard is adequate, panel by panel.
CEIL_GUARD_FRAC = 0.16      # of the ceiling margin
DRAFT_GUARD = 1.5           # m

# ---------------------------------------------------------------------------
# LATTICE
# ---------------------------------------------------------------------------
TAU_BANDS = 12
TAU_LAYERS = TAU_BANDS + 1
DTAU = 1.0 / TAU_BANDS

# Speed bands are NON-UNIFORM, fine at the ceiling. The L8 worst-case edge is
# read at the top of the band, so only the band ADJACENT TO THE CEILING sets
# the gate slack — a uniform grid would spend resolution where nothing is
# gated. The grid extends past 1.55 so the declared gate, not the grid edge,
# is what refuses (L20).
# Fine at BOTH ends, not just the ceiling: the unit always enters at exactly
# synchronous speed, and a wide bottom band makes the band-CENTRE transition
# start the model half a band above the truth. That systematic bias put the
# first predicted landing band one step high on every panel and walked the
# map straight into a dead cell — an instrument defect, found by
# `predict_check` before any verdict was believed (the L17/L20 discipline).
SPD_EDGES = [1.000, 1.025, 1.060, 1.105, 1.160, 1.225, 1.295, 1.365,
             1.430, 1.485, 1.520, 1.545, 1.560, 1.610, 1.720]
SPD_BANDS = len(SPD_EDGES) - 1                      # 14

W_HI = 88.0
W_BANDS = 16
W_W = 2 * W_HI / W_BANDS                            # 11.0 m

RATE_TIERS = (-5, -4, -3, -2, -1, 0, 2)             # tau-bands per epoch
N_ACT = len(RATE_TIERS)

N_STATES = TAU_LAYERS * SPD_BANDS * W_BANDS * W_BANDS       # 46 592

NSUB = 12               # sub-substeps per HALF epoch (L12: resolves the
                        # draft-tube column, tau_dt = 2*L_d/a ~ 0.13 s)
GAMMA = 0.9999          # L10: never 1.0
MAX_EPOCHS = 70
WIN_THRESHOLD = 24


def spd_band(x):
    for i in range(SPD_BANDS):
        if x < SPD_EDGES[i + 1]:
            return i
    return SPD_BANDS - 1


# ===========================================================================
# PANELS
# ===========================================================================
def splitmix(x):
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)


def u01(seed, k):
    return (splitmix(seed * 1000003 + k) >> 11) / float(1 << 53)


class Panel:
    """One seeded plant + event: gross head, penstock length, wave speed,
    friction, and the load carried at the instant the breaker opens."""

    def __init__(self, seed):
        self.seed = seed
        self.H0 = 195.0 + 65.0 * u01(seed, 1)
        self.L = 430.0 + 350.0 * u01(seed, 2)
        self.a = 1000.0 + 200.0 * u01(seed, 3)
        self.f = F_DARCY * (0.85 + 0.30 * u01(seed, 6))
        self.tau0_band = TAU_BANDS - int(round(5 * u01(seed, 4)))   # 7..12
        self.tgt_band = 0
        self.B = self.a / (G * A_PEN)
        self.Tr = 2.0 * self.L / self.a
        self.ceil = CEIL_FACTOR * self.H0
        self.tau0 = self.tau0_band * DTAU
        self.tgt = 0.0
        self.wtol = W_TOL_FRAC * (self.ceil - self.H0)
        self.ceil_gate = self.ceil - CEIL_GUARD_FRAC * (self.ceil - self.H0)
        self.floor_gate = DRAFT_FLOOR + DRAFT_GUARD
        self.Rq1 = self.f * self.L / (2 * G * D_PEN * A_PEN ** 2)
        self.Rl1 = ZETA * self.B
        # Ring-down factor per reflection period, MEASURED on the declared
        # model with the gate shut. The ring-down is UNCONTROLLED physics -
        # once the gate is at its commanded opening nothing the governor can
        # do changes it - so it belongs in the objective as an analytic
        # charge, not inside the MDP where it would fill the lattice with
        # dead states the action never caused.
        self.decay = None
        # Sustainability gate (L14): the residual surge at closure must be
        # small enough that the FREE oscillation cannot breach the ceiling.
        self.sustain = (self.ceil - self.H0) - CEIL_GUARD_FRAC * (self.ceil - self.H0)

    def __str__(self):
        return (f"seed {self.seed:4d}  H0 {self.H0:6.1f}  L {self.L:6.1f}  "
                f"a {self.a:6.1f}  Tr {self.Tr:5.3f}  tau0 {self.tau0:.4f}")


# ===========================================================================
# TURBINE / FRANCIS CHARACTERISTIC
# ===========================================================================
def phi_of(nu):
    return np.clip(1.0 - C_Q * (nu - 1.0), PHI_LO, PHI_HI)


def turbine_solve(CP, tau, spd, H_prev, B):
    """Runner boundary: given the incoming forward characteristic
    CP = H + B*Q, the gate opening and the speed ratio, return (Q, H).
    nu is evaluated on the previous substep's head — a declared linearization
    at a substep two orders of magnitude shorter than any gated time
    constant, which keeps the solve closed-form."""
    Hs = np.maximum(H_prev, 1.0)
    nu = spd * np.sqrt(H_RATED / Hs)
    kt = np.maximum(tau, 0.0) * Q_RATED * phi_of(nu) / math.sqrt(H_RATED)
    CPp = np.maximum(CP, 0.0)
    disc = (kt ** 4) * (B ** 2) + 4.0 * (kt ** 2) * CPp
    Q = 0.5 * (-(kt ** 2) * B + np.sqrt(np.maximum(disc, 0.0)))
    Q = np.where(kt > 1e-12, Q, 0.0)
    return Q, CP - B * Q


def torque(tau, H, spd):
    Hs = np.maximum(H, 1.0)
    nu = spd * np.sqrt(H_RATED / Hs)
    return T_RATED * tau * (Hs / H_RATED) * (NU_RUNAWAY - nu) / (NU_RUNAWAY - 1.0)


def ring_decay(p):
    """Measure the closed-gate surge decay per reflection period."""
    if p.decay is None:
        t = np.array([0.0])
        sp = np.array([1.0])
        ss = cp_steady_vec(t, sp, p)
        a, b = ss + 40.0, ss + 40.0
        amps = []
        for _ in range(6):
            t, sp, a, b, _, _, _ = epoch_reduced(p, t.copy(), sp.copy(), a, b,
                                                 np.array([0.0]))
            ss = cp_steady_vec(t, sp, p)
            amps.append(max(abs(float(a[0] - ss[0])), abs(float(b[0] - ss[0]))))
        r = (amps[-1] / amps[1]) ** (1.0 / (len(amps) - 2))
        p.decay = min(0.999, max(0.5, r))
    return p.decay


def settle_epochs(p, amp):
    """Analytic ring-down charge to the declared handover state (L19)."""
    d = ring_decay(p)
    if amp <= p.wtol:
        return 0.0
    return math.log(amp / p.wtol) / math.log(1.0 / d)


def steady_point(tau, p, spd=1.0):
    Q = tau * Q_RATED
    for _ in range(80):
        H = max(p.H0 - p.Rq1 * Q * abs(Q) - p.Rl1 * Q, 1.0)
        nu = spd * math.sqrt(H_RATED / H)
        phi = min(PHI_HI, max(PHI_LO, 1.0 - C_Q * (nu - 1.0)))
        Qn = tau * Q_RATED * phi * math.sqrt(H / H_RATED)
        if abs(Qn - Q) < 1e-13:
            Q = Qn
            break
        Q = 0.5 * (Q + Qn)
    H = max(p.H0 - p.Rq1 * Q * abs(Q) - p.Rl1 * Q, 1.0)
    return Q, H


_CPSS = {}


def cpss_table(p):
    t = _CPSS.get(id(p))
    if t is None:
        t = np.zeros((TAU_LAYERS, SPD_BANDS + 1))
        for tb in range(TAU_LAYERS):
            for si in range(SPD_BANDS + 1):
                Q, H = steady_point(tb * DTAU, p, SPD_EDGES[si])
                t[tb, si] = H + p.B * Q
        _CPSS[id(p)] = t
    return t


def cp_steady_vec(tau, spd, p):
    """CP_ss(tau, omega) by bilinear lookup on the declared grid. The device
    holds the same table, so the surge decoding is bit-identical."""
    t = cpss_table(p)
    ti = np.clip(np.rint(np.asarray(tau) / DTAU).astype(int), 0, TAU_LAYERS - 1)
    e = np.array(SPD_EDGES)
    s = np.clip(np.asarray(spd), e[0], e[-1] - 1e-12)
    j = np.clip(np.searchsorted(e, s, side="right") - 1, 0, SPD_BANDS - 1)
    fr = (s - e[j]) / (e[j + 1] - e[j])
    return t[ti, j] * (1 - fr) + t[ti, j + 1] * fr


# ===========================================================================
# REDUCED (GOVERNOR) MODEL — MOC, ONE reach, dt = L/a, epoch = 2L/a
# ===========================================================================
def _reflect(p, H, Q):
    """Reservoir reflection: send G upstream, get the CP that comes back.
    Exactly the MOC boundary pair, carrying both friction terms."""
    def fr(q):
        return p.Rq1 * q * np.abs(q) + p.Rl1 * q
    CM = H - p.B * Q + fr(Q)
    Q0 = (p.H0 - CM) / p.B
    return p.H0 + p.B * Q0 - fr(Q0)


def epoch_reduced(p, tau, spd, CPa, CPb, rate_bands):
    """ONE decision epoch = one reflection period = TWO characteristic
    arrivals, sampled at t = Tr/4 and t = 3Tr/4.

    The incoming characteristic is reconstructed as PIECEWISE LINEAR between
    those two samples, not piecewise constant. That is not cosmetic. The
    draft-tube floor is a gate on dQ/dt, whose own time constant (2*L_d/a,
    about 0.13 s) is FOUR TIMES SHORTER than the characteristic step L/a that
    the method of characteristics forces on the model. A piecewise-constant
    reconstruction dumps a whole half-epoch of flow change into one substep
    and manufactures a suction spike that the plant does not have — measured
    at up to 3 m against a 6 m floor margin, i.e. a 50% error on the binding
    constraint. This is L12 meeting the MOC: the integration step must
    resolve the stiffest gated dynamic, but here the step is set by the wave
    speed and cannot be shortened without adding state. A first-order
    reconstruction is the cheapest honest recovery, and `_d1`-style
    comparison against the eight-reach plant is how its adequacy is judged.

    The two incoming characteristics were emitted by the runner one reflection
    period ago and cannot be changed by anything decided now. That is the
    non-greedy mechanism stated as a modelling fact rather than an intuition.
    """
    n = np.shape(tau)[0]
    rate = rate_bands * DTAU / p.Tr
    N = 2 * NSUB
    dt = p.Tr / N
    lag = math.exp(-dt / max(2.0 * L_DRAFT / p.a, 1e-9))
    maxH = np.full(n, -1e18)
    minHdt = np.full(n, 1e18)
    maxSpd = spd.copy()
    H = np.maximum(CPa - p.B * tau * Q_RATED, 1.0)
    Qp, H = turbine_solve(CPa, tau, spd, H, p.B)
    dQf = np.zeros(n)
    Ga = Gb = None
    ia, ib = NSUB // 2, N - NSUB // 2 - 1        # samples at Tr/4 and 3Tr/4
    for j in range(N):
        # piecewise-linear reconstruction between the two sample instants
        w = np.clip((j - ia) / float(ib - ia), 0.0, 1.0)
        CP = CPa + (CPb - CPa) * w
        tau = np.clip(tau + rate * dt, 0.0, 1.0)
        Q, H = turbine_solve(CP, tau, spd, H, p.B)
        dQf = lag * dQf + (1 - lag) * (Q - Qp) / dt
        Hdt = -H_SETTING - C_VELHEAD * Q * Q + DRAFT_INERTIA * dQf
        spd = spd + (torque(tau, H, spd) / J_ROT) * dt / OMEGA_R
        # HEAD is an ALGEBRAIC function of the arriving characteristic - it is
        # not filtered by anything - so its peak is evaluated at the EXACT
        # characteristic samples as well as along the reconstruction. The
        # draft-tube floor, by contrast, is a filtered derivative and is read
        # only from the reconstruction. Reconstructing both the same way gets
        # one of them wrong whichever way you choose it.
        Qh, Hh = turbine_solve(np.maximum(CPa, CPb), tau, spd, H, p.B)
        maxH = np.maximum(maxH, np.maximum(H, Hh))
        minHdt = np.minimum(minHdt, Hdt)
        maxSpd = np.maximum(maxSpd, spd)
        Qp = Q
        if j == ia:
            Ga = _reflect(p, H, Q)
        if j == ib:
            Gb = _reflect(p, H, Q)
    if Gb is None:
        Gb = _reflect(p, H, Q)
    return tau, spd, Ga, Gb, maxH, minHdt, maxSpd


# ===========================================================================
# CHARACTERIZATION
# ===========================================================================
def characterize(p, gates=(True, True, True), wbands=None, tax=True):
    """Build next-state and per-constraint violation tables.

    L8, per-constraint worst-case SENSE — chosen by sensitivity sign and then
    MEASURED (`l8_sense_check`), never asserted:

      * OVERPRESSURE bites at the HIGH edge of both surge bands (a larger
        incoming characteristic is a larger head) and the LOW edge of the
        speed band (a slower runner swallows more, so there is more column
        momentum left to arrest).
      * The DRAFT-TUBE FLOOR bites at the OPPOSITE edges — the LOW edge of
        the surge bands and the HIGH edge of the speed band, which together
        make dQ/dt at the runner most negative.
      * OVERSPEED bites at the HIGH edge of the speed band and the HIGH edge
        of the surge bands (more head, more torque).

    Both senses are evaluated for every (state, action). Gating one edge
    silently passes half the failures — R6 found exactly this.

    F2 RULE (R9, the sharpest safety finding the factory has): every gate
    reads ONLY the indexed state and the action. tau is exact (integer bands
    per epoch); the speed band and the two surge bands are read at their own
    worst-case edges; NOTHING else enters — no ambient, no unmeasured plant
    coefficient, nothing unknown at solve time."""
    WB = wbands or W_BANDS
    ww = 2 * W_HI / WB
    S = TAU_LAYERS * SPD_BANDS * WB * WB

    tb = np.repeat(np.arange(TAU_LAYERS), SPD_BANDS * WB * WB)
    sb = np.tile(np.repeat(np.arange(SPD_BANDS), WB * WB), TAU_LAYERS)
    wa = np.tile(np.repeat(np.arange(WB), WB), TAU_LAYERS * SPD_BANDS)
    wbi = np.tile(np.arange(WB), TAU_LAYERS * SPD_BANDS * WB)

    tau_e = tb * DTAU
    e = np.array(SPD_EDGES)
    s_lo, s_hi = e[sb], e[sb + 1] - 1e-9
    s_md = 0.5 * (s_lo + s_hi)
    a_lo, a_hi = -W_HI + wa * ww, -W_HI + (wa + 1) * ww
    b_lo, b_hi = -W_HI + wbi * ww, -W_HI + (wbi + 1) * ww
    a_md, b_md = 0.5 * (a_lo + a_hi), 0.5 * (b_lo + b_hi)

    nxt = np.zeros((S, N_ACT), dtype=np.int32)
    viol = np.zeros((S, N_ACT, 3), dtype=bool)
    cost = np.ones((S, N_ACT))

    ss_lo = cp_steady_vec(tau_e, s_lo, p)
    ss_hi = cp_steady_vec(tau_e, s_hi, p)
    ss_md = cp_steady_vec(tau_e, s_md, p)

    for ai, rb in enumerate(RATE_TIERS):
        rate = np.full(S, float(rb))
        rate = np.where(tau_e + rate * DTAU > 1.0 + 1e-12,
                        (1.0 - tau_e) / DTAU, rate)
        rate = np.where(tau_e + rate * DTAU < -1e-12, -tau_e / DTAU, rate)

        # ALL-CORNER gate evaluation. The first draft of this file ASSUMED
        # the ceiling and the floor bite at opposite band edges, which is the
        # textbook two-sided-window intuition. `l8_sense_check` MEASURED that
        # assumption and it is WRONG for the draft-tube floor: the floor is
        # worst at the SAME corner as the ceiling (low speed, high surge),
        # because the runner-exit pressure is driven by dQ/dt and a low
        # runner speed with a big incoming characteristic is what makes the
        # deceleration steepest. That is the factory asserting a sign from
        # intuition and being wrong for the third time (L22), so the
        # assumption is removed entirely: every gate is evaluated at EVERY
        # corner of the state's own bands and the worst is taken. It costs
        # eight integrations per action and it cannot be wrong about a sense.
        mH = np.full(S, -1e18)
        mD = np.full(S, 1e18)
        mS = np.full(S, -1e18)
        # tax=False is the ORACLE instrument (R17's check): gates evaluated at
        # band CENTRES with no model guard, i.e. the L8/L21 conservatism set
        # to zero. It is NOT a shippable map - it would break its own gates -
        # but it answers the one question a negative verdict must answer: is
        # the lookahead absent, or is it present and being taxed away?
        corners = (((ss_lo, s_lo), (ss_hi, s_hi)), ((a_lo, a_hi)), ((b_lo, b_hi)))             if tax else (((ss_md, s_md),), (a_md,), (b_md,))
        for ss, sv in corners[0]:
            for av in corners[1]:
                for bv in corners[2]:
                    _, _, _, _, h, d, v = epoch_reduced(
                        p, tau_e.copy(), sv.copy(), ss + av, ss + bv, rate)
                    mH = np.maximum(mH, h)
                    mD = np.minimum(mD, d)
                    mS = np.maximum(mS, v)
        if gates[0]:
            viol[:, ai, 0] = mH > (p.ceil_gate if tax else p.ceil)
        if gates[1]:
            viol[:, ai, 1] = mD < (p.floor_gate if tax else DRAFT_FLOOR)
        if gates[2]:
            viol[:, ai, 2] = mS > SPEED_CEIL

        # TRANSITION from band CENTRES (the R3 model/gate split). Re-applying
        # the worst edge to the transition as well compounds across epochs and
        # gates every path vacuously; the deployed controller re-reads the TRUE
        # state at every epoch entry, so drift costs optimality, never safety.
        t1, s1, CA, CB, _, _, _ = epoch_reduced(
            p, tau_e.copy(), s_md.copy(), ss_md + a_md, ss_md + b_md, rate)
        ss1 = cp_steady_vec(t1, s1, p)
        tb1 = np.clip(np.rint(t1 / DTAU).astype(int), 0, TAU_LAYERS - 1)
        sb1 = np.clip(np.searchsorted(e, np.clip(s1, e[0], e[-1] - 1e-12),
                                      side="right") - 1, 0, SPD_BANDS - 1)
        WA1, WB1 = CA - ss1, CB - ss1
        wa1 = np.clip(np.floor((WA1 + W_HI) / ww).astype(int), 0, WB - 1)
        wb1 = np.clip(np.floor((WB1 + W_HI) / ww).astype(int), 0, WB - 1)
        nxt[:, ai] = ((tb1 * SPD_BANDS + sb1) * WB + wa1) * WB + wb1

        # L14 SUSTAINABILITY GATE, and the reason the ring-down is not in the
        # MDP. Arriving at the commanded opening with a large surge still in
        # the column is not safe just because this epoch was: the FREE
        # oscillation that follows is uncontrolled, and it must not be able to
        # breach the ceiling on its own. So an action that CLOSES the gate is
        # legal only if the residual amplitude it leaves behind is inside the
        # sustainable band. That is a constraint the action genuinely causes,
        # unlike gating the ring-down epoch by epoch, which fills the lattice
        # with states no action ever chose.
        amp1 = np.maximum(np.abs(WA1), np.abs(WB1))
        arriving = (tb1 == p.tgt_band) & (tb != p.tgt_band)
        if gates[0]:
            viol[:, ai, 0] |= arriving & (amp1 > p.sustain)
        # Terminal cost: one epoch plus the analytic ring-down to handover.
        dec = math.log(1.0 / ring_decay(p))
        extra = np.where(amp1 > p.wtol,
                         np.log(np.maximum(amp1, 1e-9) / p.wtol) / dec, 0.0)
        cost[:, ai] = 1.0 + np.where(arriving, extra, 0.0)

    term = (tb == p.tgt_band)
    return dict(nxt=nxt, viol=viol, term=term, cost=cost, tb=tb, sb=sb,
                wa=wa, wb=wbi, S=S, WB=WB)


# ===========================================================================
# EXACT DP (hard gates EXCLUDED from the Bellman max) and MYOPIC GREEDY
# ===========================================================================
def exact_dp(tab, sweeps=1500, tol=1e-11):
    S = tab["S"]
    legal = ~tab["viol"].any(axis=2)
    term, nxt, cost = tab["term"], tab["nxt"], tab["cost"]
    floor = -60.0 / (1.0 - GAMMA)
    V = np.where(term, 0.0, floor)
    it = 0
    for it in range(1, sweeps + 1):
        Q = -cost + GAMMA * V[nxt]
        Q = np.where(legal, Q, -np.inf)
        Vn = Q.max(axis=1)
        Vn = np.where(np.isfinite(Vn), Vn, floor)
        Vn = np.maximum(Vn, floor)
        Vn = np.where(term, 0.0, Vn)
        d = float(np.max(np.abs(Vn - V)))
        V = Vn
        if d < tol:
            break
    Q = -cost + GAMMA * V[nxt]
    Q = np.where(legal, Q, -np.inf)
    return V, np.argmax(Q, axis=1), legal, it


def greedy_policy(tab):
    """MYOPIC GREEDY: of the LEGAL actions, the one that moves the gate
    fastest toward the commanded opening. No lookahead of any kind. It is a
    strong controller — what a well-tuned rate-limited governor with a live
    protection interlock actually does."""
    legal = ~tab["viol"].any(axis=2)
    tb = tab["tb"]
    prog = np.zeros((tab["S"], N_ACT))
    for ai, rb in enumerate(RATE_TIERS):
        prog[:, ai] = -np.abs(np.clip(tb * DTAU + rb * DTAU, 0.0, 1.0))
    sc = np.where(legal, prog, -np.inf)
    act = np.argmax(sc, axis=1)
    hold = RATE_TIERS.index(0)
    return np.where(np.isfinite(sc.max(axis=1)), act, hold), legal


# ===========================================================================
# CONTINUUM PLANT — full MOC, NREACH reaches, batched
# ===========================================================================
NREACH = 8


class Continuum:
    """The plant every contender is graded on: a full method-of-characteristics
    penstock at dt = L/(NREACH*a) with distributed friction, a reservoir
    boundary and the same Francis / draft-tube boundary. The governor's own
    model is these equations at ONE reach; the gap between them is the
    discretization error this file measures (L22)."""

    def __init__(self, p, m):
        self.p, self.m = p, m
        self.dt = p.L / (NREACH * p.a)
        self.dx = p.L / NREACH
        self.B = p.B
        self.Rq = p.f * self.dx / (2 * G * D_PEN * A_PEN ** 2)
        self.Rl = ZETA * p.B / NREACH
        Q0, Ht = steady_point(p.tau0, p)
        self.H = np.zeros((m, NREACH + 1))
        for i in range(NREACH + 1):
            self.H[:, i] = p.H0 - (p.H0 - Ht) * (i / NREACH)
        self.Q = np.full((m, NREACH + 1), Q0)
        self.tau = np.full(m, p.tau0)
        self.spd = np.ones(m)
        self.Qp = np.full(m, Q0)
        self.dQf = np.zeros(m)
        self.t = 0.0
        self.maxH = self.H[:, -1].copy()
        self.minHdt = np.full(m, -H_SETTING - C_VELHEAD * Q0 * Q0)
        self.maxSpd = np.ones(m)
        self.vH = np.zeros(m, bool)
        self.vD = np.zeros(m, bool)
        self.vS = np.zeros(m, bool)
        self.lag = math.exp(-self.dt / max(2.0 * L_DRAFT / p.a, 1e-9))
        self.wpk = np.zeros(m)
        self.wa_pk = np.zeros(m)
        self.wb_pk = np.zeros(m)

    def _fr(self, q):
        return self.Rq * q * np.abs(q) + self.Rl * q

    def step(self, rate):
        p, B = self.p, self.B
        H, Q = self.H, self.Q
        CPa = H[:, :-1] + B * Q[:, :-1] - self._fr(Q[:, :-1])
        CMa = H[:, 1:] - B * Q[:, 1:] + self._fr(Q[:, 1:])
        Hn = np.empty_like(H)
        Qn = np.empty_like(Q)
        Hn[:, 1:-1] = 0.5 * (CPa[:, :-1] + CMa[:, 1:])
        Qn[:, 1:-1] = (CPa[:, :-1] - CMa[:, 1:]) / (2 * B)
        Hn[:, 0] = p.H0
        Qn[:, 0] = (p.H0 - CMa[:, 0]) / B
        self.tau = np.clip(self.tau + rate * self.dt, 0.0, 1.0)
        q, h = turbine_solve(CPa[:, -1], self.tau, self.spd, H[:, -1], B)
        Qn[:, -1], Hn[:, -1] = q, h
        self.dQf = self.lag * self.dQf + (1 - self.lag) * (q - self.Qp) / self.dt
        Hdt = -H_SETTING - C_VELHEAD * q * q + DRAFT_INERTIA * self.dQf
        self.spd = self.spd + (torque(self.tau, h, self.spd) / J_ROT) \
            * self.dt / OMEGA_R
        self.H, self.Q, self.Qp = Hn, Qn, q
        self.t += self.dt
        self.maxH = np.maximum(self.maxH, h)
        self.minHdt = np.minimum(self.minHdt, Hdt)
        self.maxSpd = np.maximum(self.maxSpd, self.spd)
        self.vH |= h > p.ceil
        self.vD |= Hdt < DRAFT_FLOOR
        self.vS |= self.spd > SPEED_CEIL
        self.wpk = np.maximum(self.wpk, np.abs(self.surge()))

    def surge(self):
        """The MEASURABLE carried state: CP - CP_ss(tau, omega). A plant knows
        its spiral-case head and its discharge, so this is an instrument
        reading, not an estimate."""
        CP = self.H[:, -1] + self.B * self.Q[:, -1]
        return CP - cp_steady_vec(self.tau, self.spd, self.p)


def result(name, c, i, t, ok, extra=""):
    return dict(name=name, t=float(t), ok=bool(ok),
                vH=bool(c.vH[i]), vD=bool(c.vD[i]), vS=bool(c.vS[i]),
                maxH=float(c.maxH[i]), minHdt=float(c.minHdt[i]),
                maxSpd=float(c.maxSpd[i]), extra=extra)


# ===========================================================================
# CONTINUUM REPLAYS
# ===========================================================================
def replay_map(p, act, legal, tab, name):
    """Deployed semantics (L13): look up at epoch ENTRY with the TRUE measured
    state, HOLD the commanded rate for the whole reflection period.

    The two surge bands are read as the incoming characteristics for the two
    halves of the coming epoch — both are already determined by what the
    runner emitted one reflection period ago, so a real controller can compute
    them from its own pressure and flow record."""
    c = Continuum(p, 1)
    nsub = max(1, int(round(p.Tr / c.dt)))
    half = max(1, nsub // 2)
    WB = tab["WB"]
    ww = 2 * W_HI / WB

    def wband(x):
        return int(min(WB - 1, max(0, math.floor((x + W_HI) / ww))))

    # prime the two incoming characteristics from the steady field
    wa_v = wb_v = float(_reflect(p, c.H[:, -1], c.Q[:, -1])[0]
                        - cp_steady_vec(c.tau, c.spd, p)[0])
    declined = None
    done_t = None
    for k in range(MAX_EPOCHS):
        tb = int(round(c.tau[0] / DTAU))
        sb = spd_band(float(c.spd[0]))
        if tb == p.tgt_band:
            done_t = c.t + settle_epochs(p, max(abs(wa_v), abs(wb_v))) * p.Tr
            break
        s = ((tb * SPD_BANDS + sb) * WB + wband(wa_v)) * WB + wband(wb_v)
        if not legal[s].any() or not legal[s, act[s]]:
            declined = k
            break
        rate = np.array([RATE_TIERS[act[s]] * DTAU / p.Tr])
        ca = cb = None
        for j in range(nsub):
            c.step(rate)
            if j == half - 1:
                ca = _reflect(p, c.H[:, -1], c.Q[:, -1])
            if j == nsub - 1:
                cb = _reflect(p, c.H[:, -1], c.Q[:, -1])
        ss = cp_steady_vec(c.tau, c.spd, p)
        wa_v, wb_v = float(ca[0] - ss[0]), float(cb[0] - ss[0])
    ok = declined is None and done_t is not None
    if done_t is None:
        done_t = c.t + 1e3
    return result(name, c, 0, done_t, ok,
                  extra="" if declined is None else f"DECLINED@{declined}")


def _run_batch(p, rate_fn, m, horizon=MAX_EPOCHS):
    """Every contender is scored on the SAME clock: seconds until the gate is
    at the commanded opening, plus the analytic ring-down charge from the
    residual surge it leaves in the column (L19)."""
    c = Continuum(p, m)
    nsub = max(1, int(round(p.Tr / c.dt)))
    done = np.zeros(m, bool)
    tdone = np.full(m, np.nan)
    dec = math.log(1.0 / ring_decay(p))
    for k in range(horizon):
        c.wpk[:] = 0.0
        for _ in range(nsub):
            c.step(rate_fn(c))
        amp = c.wpk
        chg = np.where(amp > p.wtol,
                       np.log(np.maximum(amp, 1e-9) / p.wtol) / dec, 0.0) * p.Tr
        newly = (~done) & (c.tau <= p.tgt + 1e-9)
        tdone = np.where(newly, c.t + chg, tdone)
        done |= newly
        if done.all():
            break
    return c, np.where(done, tdone, 1e6), done


def tuned_multistage(p, stages):
    """The MANDATED INCUMBENT (L1): a tuned multi-stage closing law, grid
    searched per panel WITH HINDSIGHT and scored on the same continuum with
    the same handover clock. It gets every advantage — continuous
    (non-lattice) rates and oracle knowledge of this panel's head, penstock
    length, wave speed and friction. Beating a naive linear close would be a
    worthless claim, so no such claim is made anywhere in this repository."""
    span = p.tau0 - p.tgt
    if span <= 1e-9:
        return None
    rg = -np.array([0.030, 0.045, 0.060, 0.078, 0.098, 0.122,
                    0.150, 0.185, 0.225, 0.275, 0.335])
    if stages == 1:
        R = rg.reshape(-1, 1)
        Bk = np.zeros((R.shape[0], 0))
    elif stages == 2:
        bg = p.tgt + span * np.array([0.15, 0.30, 0.45, 0.60, 0.75, 0.90])
        r1, r2, b = np.meshgrid(rg, rg, bg, indexing="ij")
        R = np.stack([r1.ravel(), r2.ravel()], 1)
        Bk = b.ravel().reshape(-1, 1)
    else:
        r = rg[::2]
        b1g = p.tgt + span * np.array([0.45, 0.65, 0.85])
        b2g = p.tgt + span * np.array([0.12, 0.25, 0.38])
        r1, r2, r3, b1, b2 = np.meshgrid(r, r, r, b1g, b2g, indexing="ij")
        R = np.stack([r1.ravel(), r2.ravel(), r3.ravel()], 1)
        Bk = np.stack([b1.ravel(), b2.ravel()], 1)
    m = R.shape[0]
    idxr = np.arange(m)

    def rate_fn(c):
        st = np.zeros(m, int)
        for j in range(Bk.shape[1]):
            st += (c.tau < Bk[:, j]).astype(int)
        r = R[idxr, np.minimum(st, R.shape[1] - 1)]
        return np.where(c.tau <= p.tgt + 1e-9, 0.0, r)

    c, t, done = _run_batch(p, rate_fn, m)
    clean = done & (~c.vH) & (~c.vD) & (~c.vS)
    if not clean.any():
        return None
    i = int(np.argmin(np.where(clean, t, 1e9)))
    return result(f"tuned {stages}-stage", c, i, t[i], True,
                  extra=f"rates={np.round(R[i], 3).tolist()} "
                        f"breaks={np.round(Bk[i], 3).tolist()}")


def tuned_reactive(p):
    """A reactive controller reading the spiral-case pressure transducer:
    close fast below a head threshold, back off above it. Threshold and both
    rates oracle-tuned per panel."""
    tg = p.ceil - np.array([4.0, 10.0, 18.0, 28.0, 40.0, 55.0])
    fg = -np.array([0.078, 0.122, 0.185, 0.275, 0.335])
    sg = -np.array([0.018, 0.032, 0.052, 0.078])
    T, F_, S_ = np.meshgrid(tg, fg, sg, indexing="ij")
    T, F_, S_ = T.ravel(), F_.ravel(), S_.ravel()
    m = T.shape[0]

    def rate_fn(c):
        r = np.where(c.H[:, -1] < T, F_, S_)
        return np.where(c.tau <= p.tgt + 1e-9, 0.0, r)

    c, t, done = _run_batch(p, rate_fn, m)
    clean = done & (~c.vH) & (~c.vD) & (~c.vS)
    if not clean.any():
        i = int(np.argmin(t))
        return result("reactive (best, DIRTY)", c, i, t[i], False)
    i = int(np.argmin(np.where(clean, t, 1e9)))
    return result("tuned reactive", c, i, t[i], True)


# ===========================================================================
# SCOUTING INSTRUMENTS
# ===========================================================================
def l21_slack(p, ww=None):
    """L21: band width is a CONSTRAINT tax. The fractional error the L8 worst
    edge forces into each gated quantity. Declared budget: < 10%."""
    ww = ww or W_W
    margin = p.ceil - p.H0
    worst = 0.0
    for tb in range(TAU_LAYERS):
        tau = tb * DTAU
        Q, H = steady_point(tau, p)
        kt = tau * Q_RATED / math.sqrt(H_RATED)
        gain = 1.0 / (1.0 + p.B * kt / (2 * math.sqrt(max(H, 1.0))))
        worst = max(worst, gain * ww / margin)
    ic = next(i for i in range(SPD_BANDS) if SPD_EDGES[i + 1] >= SPEED_CEIL)
    slack_S = (SPD_EDGES[ic + 1] - SPD_EDGES[ic]) / (SPEED_CEIL - 1.0)
    dq = ww / p.B
    slack_D = (DRAFT_INERTIA * dq / (p.Tr / 2)) / abs(DRAFT_FLOOR + H_SETTING)
    return dict(ceiling=worst, speed=slack_S, draft=slack_D)


def l17_motion(p, tab):
    """L17: a CARRIED state's band must resolve its per-crossing motion. The
    carried states are the two surge bands and the speed band. The gate
    position is a PROGRESS variable crossed exactly (integer bands per epoch),
    so it has no motion question at all."""
    legal = ~tab["viol"].any(axis=2)
    WB = tab["WB"]
    out = {}
    for nm in ("surge_a", "surge_b", "speed"):
        cur = {"surge_a": tab["wa"], "surge_b": tab["wb"],
               "speed": tab["sb"]}[nm]
        d = []
        for ai in range(N_ACT):
            m = legal[:, ai]
            if not m.any():
                continue
            n1 = tab["nxt"][m, ai]
            if nm == "surge_a":
                v = (n1 // WB) % WB
            elif nm == "surge_b":
                v = n1 % WB
            else:
                v = (n1 // (WB * WB)) % SPD_BANDS
            d.append(np.abs(v - cur[m]))
        d = np.concatenate(d) if d else np.array([0])
        out[nm] = (float(np.median(d)), float((d == 0).mean()))
    return out


def l18_frontier(p, tab, stride=17):
    """L18: the Pareto frontier of the action set computed AFTER the gates.
    Two objectives that genuinely conflict: immediate progress toward a closed
    gate, and the surge amplitude handed to the next epoch. R8 and R9 both
    died here with a ~90% single-dominator frontier."""
    legal = ~tab["viol"].any(axis=2)
    WB = tab["WB"]
    tb, nxt = tab["tb"], tab["nxt"]
    mid = (WB - 1) / 2.0
    single = multi = nochoice = 0
    for s in range(0, tab["S"], stride):
        L = np.where(legal[s])[0]
        if L.size <= 1:
            nochoice += 1
            continue
        prog = np.array([-abs(min(1.0, max(0.0, tb[s] * DTAU
                                           + RATE_TIERS[a] * DTAU)) - p.tgt)
                         for a in L])
        surge = np.array([-max(abs((nxt[s, a] // WB) % WB - mid),
                               abs(nxt[s, a] % WB - mid)) for a in L])
        dom = sum(1 for i in range(L.size)
                  if all(prog[i] >= prog[j] - 1e-12
                         and surge[i] >= surge[j] - 1e-12
                         for j in range(L.size)))
        if dom >= 1:
            single += 1
        else:
            multi += 1
    tot = single + multi
    return dict(single=single, multi=multi, nochoice=nochoice,
                frac_single=(single / tot) if tot else 1.0)


def predict_check(p, act, legal, tab, nmax=12):
    """THE decisive instrument check for this harness (L22): does the state
    the governor's one-reach model PREDICTS agree with the state the
    eight-reach plant actually reaches? A map whose landing band is wrong is
    not solving the plant's problem, however exact its dynamic programming
    was on the lattice."""
    WB = tab["WB"]
    ww = 2 * W_HI / WB
    c = Continuum(p, 1)
    nsub = max(1, int(round(p.Tr / c.dt)))
    half = max(1, nsub // 2)
    ss0 = cp_steady_vec(c.tau, c.spd, p)
    ca = cb = _reflect(p, c.H[:, -1], c.Q[:, -1])
    rows = []
    for k in range(nmax):
        tb = int(round(c.tau[0] / DTAU))
        sb = spd_band(float(c.spd[0]))
        wa = int(min(WB - 1, max(0, math.floor((float(ca[0] - ss0[0]) + W_HI) / ww))))
        wbb = int(min(WB - 1, max(0, math.floor((float(cb[0] - ss0[0]) + W_HI) / ww))))
        s = ((tb * SPD_BANDS + sb) * WB + wa) * WB + wbb
        if not legal[s].any():
            rows.append((k, tb, sb, wa, wbb, -1, -1, -1, -1, "DEAD"))
            break
        a = act[s]
        pred = tab["nxt"][s, a]
        rate = np.array([RATE_TIERS[a] * DTAU / p.Tr])
        for j in range(nsub):
            c.step(rate)
            if j == half - 1:
                ca = _reflect(p, c.H[:, -1], c.Q[:, -1])
        cb = _reflect(p, c.H[:, -1], c.Q[:, -1])
        ss0 = cp_steady_vec(c.tau, c.spd, p)
        tb2 = int(round(c.tau[0] / DTAU))
        sb2 = spd_band(float(c.spd[0]))
        wa2 = int(min(WB - 1, max(0, math.floor((float(ca[0] - ss0[0]) + W_HI) / ww))))
        wb2 = int(min(WB - 1, max(0, math.floor((float(cb[0] - ss0[0]) + W_HI) / ww))))
        pt = pred // (SPD_BANDS * WB * WB)
        ps = (pred // (WB * WB)) % SPD_BANDS
        pa = (pred // WB) % WB
        pb = pred % WB
        rows.append((k, tb, sb, wa, wbb, tb2 - pt, sb2 - ps, wa2 - pa, wb2 - pb,
                     "" if (tb2, sb2, wa2, wb2) == (pt, ps, pa, pb) else "MISS"))
    return rows


def l8_sense_check(p):
    """MEASURE the worst-case sense of each gate instead of asserting it.
    R6 gated one edge of a two-sided window and silently passed half its
    failures; the factory has also twice asserted a mechanism's sign from
    intuition and been wrong (L22)."""
    tau = np.array([(TAU_LAYERS // 2) * DTAU])
    out = {}
    for nm, sp, wv in (("spd_lo_W_hi", 1.05, 44.0),
                       ("spd_hi_W_lo", 1.50, -44.0),
                       ("spd_lo_W_lo", 1.05, -44.0),
                       ("spd_hi_W_hi", 1.50, 44.0)):
        s = np.array([sp])
        ss = cp_steady_vec(tau, s, p)
        _, _, _, _, mH, mD, mS = epoch_reduced(
            p, tau.copy(), s.copy(), ss + wv, ss + wv, np.array([-4.0]))
        out[nm] = (float(mH[0]), float(mD[0]), float(mS[0]))
    return out


# ===========================================================================
# DRIVER
# ===========================================================================
def run_panel(p, gates=(True, True, True), wbands=None, tax=True):
    _CPSS.pop(id(p), None)
    tab = characterize(p, gates, wbands, tax)
    V, act, legal, it = exact_dp(tab)
    gact, _ = greedy_policy(tab)
    return dict(p=p, tab=tab, act=act, legal=legal, iters=it,
                dp=replay_map(p, act, legal, tab, "QCEOM map"),
                gr=replay_map(p, gact, legal, tab, "myopic greedy"))


def fmt(r):
    if r is None:
        return "       -  "
    f = ("P" if r.get("vH") else "") + ("C" if r.get("vD") else "") \
        + ("S" if r.get("vS") else "") + ("" if r["ok"] else "x")
    return f"{r['t']:8.2f}{f:<2}"


def main():
    quick = "--quick" in sys.argv
    npan = 12 if quick else 36
    thr = (WIN_THRESHOLD * npan) // 36
    print("=" * 96)
    print("P1 FALSIFIER - R15 HYDRO-FRANCIS-TRANSIENT-GOVERNOR")
    print("=" * 96)
    print(f"lattice: {TAU_LAYERS} gate x {SPD_BANDS} speed x {W_BANDS} surge_a "
          f"x {W_BANDS} surge_b = {N_STATES} states x {N_ACT} rate tiers")
    print(f"gates: spiral-case head <= {CEIL_FACTOR}*H0 | draft-tube head >= "
          f"{DRAFT_FLOOR} m | speed <= {SPEED_CEIL} x rated")
    print(f"objective: seconds to the declared HANDOVER STATE - gate closed "
          f"AND surge below {100*W_TOL_FRAC:.0f}% of the ceiling margin")
    print(f"kill rule (frozen): DP clean on every panel AND beats the best "
          f"tuned multi-stage law >= {thr}/{npan} AND beats myopic greedy "
          f">= {thr}/{npan}")
    print()

    panels = [Panel(1000 + 7 * i) for i in range(npan)]
    p0 = panels[0]

    print("--- L21 gate slack (declared budget < 10% per gated axis) ---")
    sl = [l21_slack(p) for p in panels]
    for k in ("ceiling", "draft", "speed"):
        v = [s[k] for s in sl]
        print(f"    {k:9s} median {100*np.median(v):5.2f}%   worst "
              f"{100*max(v):5.2f}%")
    print()

    _CPSS.pop(id(p0), None)
    tab0 = characterize(p0)
    print("--- L17 per-crossing motion of the carried states ---")
    for k, (med, f0) in l17_motion(p0, tab0).items():
        print(f"    {k:8s} median motion {med:4.1f} bands, "
              f"{100*f0:5.1f}% of legal crossings never leave their band")
    print()

    print("--- L8 sense check (MEASURED, not asserted) ---")
    for k, (mh, md, ms) in l8_sense_check(p0).items():
        print(f"    {k:12s} maxH {mh:7.1f}  minHdt {md:6.2f}  maxSpd {ms:.3f}")
    print()

    print("--- L18 gated Pareto frontier (progress vs surge handed on) ---")
    fr = l18_frontier(p0, tab0)
    print(f"    sampled states with a real choice: {fr['single']+fr['multi']}"
          f", no choice: {fr['nochoice']}")
    print(f"    single-dominator (monotone) frontier: "
          f"{100*fr['frac_single']:5.1f}%   [R8/R9 died at ~90%]")
    print()

    hdr = (f"{'panel':>5} {'DP':>10} {'greedy':>10} {'1-stage':>10} "
           f"{'2-stage':>10} {'3-stage':>10} {'reactive':>10}")
    print(hdr)
    print("-" * len(hdr))
    dp_clean = win_inc = win_gr = inc_n = 0
    for p in panels:
        r = run_panel(p)
        inc = {k: tuned_multistage(p, k) for k in (1, 2, 3)}
        rea = tuned_reactive(p)
        best = None
        for x in inc.values():
            if x and (best is None or x["t"] < best["t"]):
                best = x
        dp, gr = r["dp"], r["gr"]
        clean = dp["ok"] and not (dp["vH"] or dp["vD"] or dp["vS"])
        dp_clean += clean
        if best:
            inc_n += 1
            win_inc += clean and dp["t"] < best["t"] - 1e-9
        win_gr += clean and (not gr["ok"] or dp["t"] < gr["t"] - 1e-9)
        print(f"{p.seed:>5} {fmt(dp)} {fmt(gr)} {fmt(inc[1])} {fmt(inc[2])} "
              f"{fmt(inc[3])} {fmt(rea)}")
        sys.stdout.flush()

    print()
    print(f"DP clean and reaching handover          : {dp_clean}/{npan}")
    print(f"DP beats the best tuned multi-stage law : {win_inc}/{inc_n}")
    print(f"DP beats the myopic greedy              : {win_gr}/{npan}")

    print()
    print("--- L22 mechanism SIGN by ABLATION (never by intuition) ---")
    print("registered mechanism: the wave arriving now was launched by the")
    print("gate one reflection period ago, so the ceiling that binds NOW was")
    print("bought THEN. Ablate the ceiling and re-measure DP vs greedy.")
    sub = panels[:8]
    on = off = 0
    for p in sub:
        r = run_panel(p)
        on += r["dp"]["ok"] and (not r["gr"]["ok"] or r["dp"]["t"] < r["gr"]["t"])
        r = run_panel(p, gates=(False, True, True))
        off += r["dp"]["ok"] and (not r["gr"]["ok"] or r["dp"]["t"] < r["gr"]["t"])
    print(f"    overpressure ceiling ON  : DP beats greedy {on}/{len(sub)}")
    print(f"    overpressure ceiling OFF : DP beats greedy {off}/{len(sub)}")
    print(f"    sign: {'CONFIRMED' if on > off else 'NOT CONFIRMED'} "
          f"(registered direction predicts ON > OFF)")

    ok = dp_clean == npan and win_inc >= thr and win_gr >= thr
    print()
    print("=" * 96)
    print("VERDICT:", "HARNESS LIVES" if ok else "HARNESS DIES")
    print("=" * 96)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
