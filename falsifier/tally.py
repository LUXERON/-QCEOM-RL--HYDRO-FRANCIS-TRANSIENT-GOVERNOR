#!/usr/bin/env python3
"""Recompute the verdict tallies from a FALSIFIER-RUN.txt panel table."""
import re, statistics as st, sys

rows = []
for line in open(sys.argv[1] if len(sys.argv) > 1 else "FALSIFIER-RUN.txt",
                 encoding="utf-8"):
    m = re.match(r"\s*(1\d{3})\s+(.*)$", line)
    if not m:
        continue
    toks = re.findall(r"(\d+\.\d+)([A-Zx]*)", m.group(2))
    if len(toks) >= 6:
        rows.append([(float(a), b) for a, b in toks])

dp = [r[0][0] for r in rows]
gr = [r[1][0] for r in rows]
best = [min(r[2][0], r[3][0], r[4][0]) for r in rows]
fin = [i for i in range(len(rows)) if dp[i] < 100]
print(f"panels                                   : {len(rows)}")
print(f"DP violation-free AND reaching handover  : "
      f"{sum(1 for r in rows if r[0][1] == '')}/{len(rows)}")
print(f"  draft-floor breaches                   : "
      f"{sum(1 for r in rows if 'C' in r[0][1])}")
print(f"  never reached handover                 : "
      f"{sum(1 for r in rows if 'x' in r[0][1])}")
print(f"DP beats the best tuned multi-stage law  : "
      f"{sum(1 for i in range(len(rows)) if rows[i][0][1] == '' and dp[i] < best[i])}"
      f"/{len(rows)}")
print(f"DP beats the myopic greedy               : "
      f"{sum(1 for i in range(len(rows)) if dp[i] < gr[i] - 1e-9)}/{len(rows)}")
print(f"greedy beats DP                          : "
      f"{sum(1 for i in range(len(rows)) if gr[i] < dp[i] - 1e-9)}/{len(rows)}")
print(f"DP and greedy IDENTICAL                  : "
      f"{sum(1 for i in range(len(rows)) if abs(dp[i]-gr[i]) < 1e-9)}/{len(rows)}")
print(f"median DP / best-incumbent               : "
      f"{st.median([dp[i]/best[i] for i in fin]):.2f}x")
print(f"mean time: DP {st.mean([dp[i] for i in fin]):.2f} s   "
      f"incumbent {st.mean([best[i] for i in fin]):.2f} s")
print(f"tuned 2-stage beats tuned 1-stage on     : "
      f"{sum(1 for r in rows if r[3][0] < r[2][0] - 1e-9)}/{len(rows)}")
print(f"a 3rd stage helps on                     : "
      f"{sum(1 for r in rows if r[4][0] < r[3][0] - 1e-9)}/{len(rows)}")
