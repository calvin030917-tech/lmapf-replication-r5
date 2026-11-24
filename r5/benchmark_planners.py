"""Compare the frozen and optimized R5 planners on paired rolling rounds."""

import argparse
from itertools import product
import json
import platform
from statistics import median

from interval_planner import IntervalQueries, Reserved, plan, seed_paths
from interval_planner_fast import FastIntervalQueries, RoundReservations, plan as fast_plan
from reference import controlled
from run_r5 import quantile
from warehouse import Board, CFG, E, execute, priority, scenario


def check_fixtures():
    """Compare paths, query status and work counts on the controlled cases."""
    checks = 0
    for case in controlled():
        board = Board(case["map"])
        other_paths = case["other_paths"]
        window = case["window"]
        extra = CFG["reference_extension"]
        extended = tuple(path + (path[-1],) * extra for path in other_paths)
        settings = (
            (other_paths, window, case["cap"], True, False),
            (other_paths, window, None, True, True),
            (other_paths, window, None, False, True),
            ((), window, None, False, True),
            (extended, window + extra, None, False, True),
        )
        for paths, width, cap, hold, goal_only in settings:
            original = IntervalQueries(board, Reserved(paths, width)).solve(
                case["start"], case["goal"], cap, hold, goal_only
            )
            optimized = FastIntervalQueries(board, RoundReservations(paths, width)).solve(
                case["start"], case["goal"], cap, hold, goal_only
            )
            if original != optimized:
                raise AssertionError(f"Fixture mismatch in {case['case']}: {cap=}, {hold=}, {width=}")
            checks += 1
    return checks


def verify_round(original, optimized, label):
    original_paths, original_queries, original_controls, original_costs = original
    optimized_paths, optimized_queries, optimized_controls, optimized_costs = optimized
    if original_paths != optimized_paths:
        raise AssertionError(f"Committed paths differ at {label}")
    if original_queries != optimized_queries:
        raise AssertionError(f"Query results differ at {label}")
    if original_controls != optimized_controls:
        raise AssertionError(f"Focal controls differ at {label}")
    if any(value != optimized_costs[key] for key, value in original_costs.items() if key != "wall_ms"):
        raise AssertionError(f"Work counters differ at {label}")


def sample_scenario(spec, rule, warmup, rounds):
    scene, state = scenario(*spec)

    # Verify the alternate entry point used for promoted-order diagnostics.
    ordered = priority(scene, state, rule)
    focus = ordered[-1]
    promoted = (focus,) + ordered[:-1]
    prepared = seed_paths(scene, state, scene.goals(state))
    explicit = dict(order=promoted, focus=focus, prepared=prepared)
    verify_round(plan(scene, state, **explicit), fast_plan(scene, state, **explicit), (spec, rule, "promoted"))

    frozen_times, fast_times = [], []
    for index in range(warmup + rounds):
        # Both methods receive the same state, with their execution order
        # alternating to reduce systematic timing bias.
        if index % 2:
            optimized = fast_plan(scene, state, rule=rule)
            original = plan(scene, state, rule=rule)
        else:
            original = plan(scene, state, rule=rule)
            optimized = fast_plan(scene, state, rule=rule)
        verify_round(original, optimized, (spec, rule, state.t))
        if index >= warmup:
            frozen_times.append(original[3]["wall_ms"])
            fast_times.append(optimized[3]["wall_ms"])
        state = execute(scene, state, original[0])

    return frozen_times, fast_times


def timing_summary(frozen_times, fast_times):
    frozen_p50, fast_p50 = median(frozen_times), median(fast_times)
    frozen_p95, fast_p95 = quantile(frozen_times, .95), quantile(fast_times, .95)
    return dict(
        measured_round_pairs=len(frozen_times),
        frozen_p50_ms=frozen_p50,
        optimized_p50_ms=fast_p50,
        p50_reduction_pct=100 * (1 - fast_p50 / frozen_p50),
        frozen_p95_ms=frozen_p95,
        optimized_p95_ms=fast_p95,
        p95_reduction_pct=100 * (1 - fast_p95 / frozen_p95),
    )


def print_table(report):
    environment = report["environment"]
    print(f"{environment['system']} {environment['architecture']} · Python {environment['python']}")
    print(
        f"Parity: {report['fixture_checks']} fixture queries, "
        f"{report['rolling_rounds_checked']} rolling rounds and "
        f"{report['promoted_rounds_checked']} promoted-order rounds"
    )
    print("Times are end-to-end milliseconds per round, including seed and safety checks.")
    print(f"Warm-up per scenario and policy: {report['warmup_rounds']} rounds")
    print(f"{'Scenario':<34} {'P50 frozen → fast':>19} {'P50 ↓':>8} {'P95 frozen → fast':>19} {'P95 ↓':>8}")
    for row in [*report["scenarios"], report["pooled"]]:
        descriptor = row.get("scenario", "Pooled rounds")
        print(
            f"{descriptor:<34} "
            f"{row['frozen_p50_ms']:8.3f} → {row['optimized_p50_ms']:7.3f} "
            f"{row['p50_reduction_pct']:7.1f}% "
            f"{row['frozen_p95_ms']:8.3f} → {row['optimized_p95_ms']:7.3f} "
            f"{row['p95_reduction_pct']:7.1f}%"
        )


def main():
    warmup = CFG["warmup"] // E
    limit = CFG["duration"] // E - warmup
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=limit, help="timed rounds per scenario and policy")
    parser.add_argument("--seeds", nargs="+", type=int, default=[CFG["diagnostic_seeds"][0]])
    parser.add_argument("--policies", nargs="+", choices=("density", "distance", "dual"), default=["density"])
    parser.add_argument("--json", action="store_true", help="write machine-readable results to standard output")
    args = parser.parse_args()
    if not 1 <= args.rounds <= limit:
        parser.error(f"--rounds must be between 1 and {limit}")

    fixture_checks = check_fixtures()
    scenarios, all_frozen, all_fast = [], [], []
    combinations = product(CFG["maps"], CFG["fleets"], CFG["expansions_per_robot"], args.seeds, args.policies)
    for layout, fleet, multiplier, seed, policy in combinations:
        frozen_times, fast_times = sample_scenario(
            (layout, fleet, multiplier, seed), policy, warmup, args.rounds
        )
        summary = timing_summary(frozen_times, fast_times)
        scenario_label = f"{layout} n={fleet} ×{multiplier} {seed} {policy}"
        scenarios.append(
            dict(scenario=scenario_label, layout=layout, fleet=fleet, cap=fleet * multiplier, seed=seed, policy=policy,
                 **summary)
        )
        all_frozen.extend(frozen_times)
        all_fast.extend(fast_times)

    report = dict(
        environment=dict(system=platform.system(), architecture=platform.machine(), python=platform.python_version()),
        warmup_rounds=warmup,
        fixture_checks=fixture_checks,
        rolling_rounds_checked=len(scenarios) * (warmup + args.rounds),
        promoted_rounds_checked=len(scenarios),
        scenarios=scenarios,
        pooled=timing_summary(all_frozen, all_fast),
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_table(report)


if __name__ == "__main__":
    main()
