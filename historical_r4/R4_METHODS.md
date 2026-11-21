# R4 clock accounting and audit details

## Strip exit

For a cross-bank task with the robot outside its destination bank at the snapshot, parse its executed cells through first completion or the follow-up cap, whichever comes first. Mark F at first entry, or 0 if the robot is already in the strip. E is the first observed transition from the strip to the goal bank. A return to the origin bank closes an unsuccessful attempt. Track L as the last entry before E, or 0 for a robot that starts inside and exits on its initial attempt. On an observed exit the identity E = F + (L−F) + (E−L) holds per robot. L−F contains travel and requeueing. Only E−L measures the successful final segment. The breakdown in Table 6 has a common observed-exit denominator within each reported row. The aggregated paired outcomes use capped E at 32, with missing events retained explicitly.

## Planner mechanics

At each round construct one full-window safe seed from current locations and goals, with the recursive ordering fixed by issue time and ID. Its two action rules are nearest neighbor by static distance and collision-safe waits or inherited movements. During replacement, reserve all other robots' current paths, which may be old seed paths or new replacements for robots already queried. Remove a robot's own path from both reservation tables immediately before its query, then reinsert the accepted candidate or its original seed. The low-level cap charges nonterminal states only. It tests a popped state for goal or end of window before applying the residual budget check, unless the query starts with zero budget. A goal candidate can wait at its goal through the window. A complete reserved window reaching the boundary can also be submitted. Safety is checked before executing two irrevocable actions. The environment issues the next goal at the end of each arrival step, but the remaining committed action does not replan. The search code observes only the current assignment.

The case B hold/release reference enumerates a time layer for each of eight steps with the same focal query reservations. For release, the earliest prior arrival at a given (cell, time) dominates a later arrival or no arrival, since the suffix constraints depend only on cell and time. For holding, once a robot reaches the goal its subsequent action can only be waiting. Following the graph and reservations, the algorithm retains a complete feasible suffix and minimizes first arrival. The local reference has no R3 node cap. It is a finite feasibility test of the goal rule, separate from the live replanning circuits.

## Matched validation and inferences

At each prespecified tick in the 24-robot comparison, choose the focal robot prior to applying the opposing-traffic label. The data comprise eligible scheduled ticks. Historical per-trajectory sampling and the scheduled-tick populations differ. In the new comparison, the bootstrap keeps all ticks and both budget settings for a map and scenario together, with maps as strata. For the standardized rate difference, compute within layout × budget × rank cells containing both labels, weight by the original number of observed pairs in these cells, and report the number of bootstrap draws retaining both labels in every such cell. The conditional interval is secondary given incomplete support. The label is observational.

For the policy comparisons, the bootstrap draws paired scene records independently per stratum. Every primary bound uses tail area 0.05/32. For ratio bounds each bootstrap draw divides the two scenario-mean rates. Supplementary distance contrasts use a separate 0.05/16 family with uncorrected pointwise intervals also saved. The factorial contrasts are pointwise and exploratory. The input thresholds, comparator rules, and original 5% tolerance were set in the R3 policy protocol. Counts of resamples report numerical resolution and do not increase independent scenario counts.

## R4 audit entry points

- `revision_audit.py --historical-only` verifies the original data and derives tables before any new logs are present.
- Without the flag, the same program additionally computes the validation outcomes, same-snapshot seed controls, and all scenario and robot distributions.
- `verify_r4.py` tests both main validation splits, their coupling, legal execution, consistency of all recorded event flags, reported clock identities, and the primary threshold decision counts.
