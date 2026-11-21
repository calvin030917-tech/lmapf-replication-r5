"""Simulation design and seed splits. See PROTOCOL.md for estimands."""

WIDTH, HEIGHT = 17, 11
W, EXEC = 8, 2
WARM, END, LOOK = 48, 192, 32
AT_MOST = 5
TAUS = (2, 3, 4)
PROTECT = 2.5
MARGIN = 0.05
LAYOUTS = ("single", "bypass")
FLEETS = (12, 24)
BUDGET_MULTIPLIERS = (5, 14)
SOURCES = ("age", "congestion")
POLICIES = ("fixed", "age", "relative", "congestion", "distance", "dual", "protect_fixed")
DIAG_SEEDS = tuple(range(1001, 1013))
POLICY_SEEDS = tuple(range(2001, 2017))
BOOTSTRAPS = 50000
BOOT_SEED = 518031
MECH_PER_CELL = 3


def strata():
    return [(m, n, b) for m in LAYOUTS for n in FLEETS for b in BUDGET_MULTIPLIERS]
