#!/usr/bin/env python3
"""
L22 / L23 ABLATION — check the mechanism's sign by MEASUREMENT, never by
intuition. The factory has asserted a mechanism's direction from intuition
three times now and been wrong all three (R8's superlinear R_th, R9's dryout
cliff, and R15's own two-sided-window sense).

R15's registered mechanism is that the wave arriving at the runner NOW was
launched by the gate one reflection period ago, so the overpressure ceiling
that binds now was bought then. The gates that encode that story are the
spiral-case ceiling and the L14 sustainability gate on the surge left in the
column at closure — both in constraint slot 0.

L23 asks the question this ablation answers: does the gate you have to build
anyway ALREADY enforce the non-greedy story? Turn slot 0 off and re-measure
exact DP against the myopic greedy on the same lattice.

Run: python -u ablation.py
"""
import sys
import numpy as np
import falsifier as F

PANELS = [1000 + 7 * i for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 8)]


def score(gates):
    dp_better = gr_better = same = clean = 0
    for sd in PANELS:
        p = F.Panel(sd)
        r = F.run_panel(p, gates=gates)
        dp, gr = r["dp"], r["gr"]
        clean += dp["ok"] and not (dp["vH"] or dp["vD"] or dp["vS"])
        if abs(dp["t"] - gr["t"]) < 1e-9:
            same += 1
        elif dp["t"] < gr["t"]:
            dp_better += 1
        else:
            gr_better += 1
        print(f"    seed {sd}: DP {dp['t']:7.2f}  greedy {gr['t']:7.2f}",
              flush=True)
    return dp_better, gr_better, same, clean


print("=" * 74)
print("L22/L23 ABLATION - overpressure ceiling + L14 sustainability gate")
print("=" * 74)
WHICH = sys.argv[1] if len(sys.argv) > 1 else "both"
CASES = [("gates ON  (as declared)", (True, True, True)),
         ("gates OFF (slot 0 ablated)", (False, True, True))]
if WHICH == "on":
    CASES = CASES[:1]
elif WHICH == "off":
    CASES = CASES[1:]
for name, g in CASES:
    print(f"\n{name}")
    a, b, s, c = score(g)
    print(f"  -> DP strictly better {a}/8, greedy strictly better {b}/8, "
          f"identical {s}/8, DP clean {c}/8")
print("""
READ: if ablating the ceiling and the sustainability gate makes exact DP
pull AHEAD of the myopic greedy, then those gates were cannibalising their
own optimizer - the L23 signature, and the reason to call the governor the
product and the optimizer decoration. If it changes nothing, the lookahead
was never binding on any reachable trajectory in the first place.""")
