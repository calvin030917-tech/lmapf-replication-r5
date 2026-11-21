"""English labels and notes for the tables in the Chinese R5 manuscript."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "manuscript_cn"))
from tables_cn import build_tables as source_tables
from tables_r4 import build_tables as shared_tables


def build():
    cn = source_tables("cn")
    tables = {key: value for key, value in shared_tables("en").items() if key in cn}

    def revise(key, title=None, headers=None, note=None, widths=None):
        t, h, rows, w, n, fs = tables[key]
        tables[key] = (title or t, headers or h, rows, widths or w, note or n, fs)

    def translated(key, title, headers, note, first=None, every=None, rows=None, widths=None):
        _, _, source, w, _, fs = cn[key]
        raw = [[str(c).replace("／", " / ") for c in row] for row in source]
        if first:
            for row in raw:
                row[0] = first[row[0]]
        if every:
            for row in raw:
                for column, value in enumerate(row):
                    for old, en in every.items():
                        value = value.replace(old, en)
                    row[column] = value
        tables[key] = (title, headers, rows if rows is not None else raw, widths or w, note, fs)

    translated("toy", "Table 3A. Joint reference and legacy sequential planning for fixed goals",
        ["Case", "Output source", "Conditions", "Finding or witness"],
        "The legacy routine makes the full team wait when full planning fails. The joint reference establishes feasibility for frozen goals under the indicated goal semantics.",
        rows=[
            ["S0", "Joint BFS", "Five-cell line, hold at first arrival", "Exhausts 10 configurations with no joint fixed-goal solution."],
            ["S0", "Legacy sequential full plan", "A first, cap 20", "No complete joint plan found. The team waits."],
            ["S1", "Joint BFS", "Retreat cell, depth 4 / 5", "Depth 4 cannot complete both tasks, with 20 expansions. Depth 5 finds a shortest solution with 29 expansions."],
            ["S2", "Joint BFS", "Six-cell 2D grid, hold at first arrival", "Completion in 3 steps with 15 expansions."],
            ["S2", "Legacy sequential full plan", "A first, cap 20", "A's first shortest route blocks B. The team waits. Another equally long route yields a solution."],
            ["S2", "Legacy sequential full plan", "B first, cap 3 / 20", "At cap 3 the routine cuts off and the team waits. At cap 20 it commits a 3-step plan."],
            ["S3", "Joint BFS", "Four-cell T, hold / release", "Goal holding exhausts 5 states. Release gives a 3-step witness."],
        ])
    translated("toy_actual", "Table 3B. First-round commitment and execution in Algorithm 1",
        ["Case", "Window W", "Cap", "Order", "Queries A / B", "Fallbacks",
         "Goal hits in plan", "Hits in 2 moves"],
        "Each robot with no returned candidate retains its safe seed. Arrival columns list A then B. Dashes indicate that no goal is reached in the observation window for that column.",
        every={"窗末":"Window", "截断":"Cutoff", "未启动":"Skipped", "穷尽":"Exhausted", "到达":"Goal"},
        widths=[.54,.72,.59,.69,1.50,.70,.96,1.00])
    revise("events", "Table 5. First-round actions and 32-step service events")
    caption, headers, rows, widths, note, fs = tables["policies"]
    tables["policies"] = (caption, headers, [
        [str(cell).replace("Other robots within Manhattan distance two, descending",
                           "Count of other robots within Manhattan distance two, descending") for cell in row]
        for row in rows
    ], widths, note, fs)
    revise("others", "Table 7. Capped completion-time differences and completion status of other robots by step 32")
    caption, headers, rows, widths, note, fs = tables["others"]
    tables["others"] = (caption, headers, [
        [str(r[0]).replace("Robot-pair Δ", "Capped robot-pair Δ")
                   .replace("Pairs with ≥2 delayed robots", "Pairs with ≥2 delayed other robots"), *r[1:]]
        for r in rows
    ], widths, note, fs)
    revise("descriptive", "Table 12. Descriptive results for seven priority orders with equal stratum weights",
           note="Rate is completions per 100 steps. Each stratum has 16 scenarios. Quantiles and longest spells are calculated within each run before aggregation.")
    revise("bounds", "Table 13. Primary policy comparisons and Bonferroni-adjusted bounds",
           headers=["Table 13\nLayout · N · cap", *tables["bounds"][1][1:]])
    translated("constructors", "Table A3. Other robots' completion status on new R4 synthetic layouts, by seed constructor",
        ["Constructor", "Snapshot pairs", "Both complete", "Original only / promoted only",
         "Neither completes", "Finish at 32, original / promoted"],
        "Robot-pair counts exclude the focal robot. Focal completions in the recursive cohort are 530/532 and 529/532, respectively, and 0/720 in both serial arms.",
        first={"递归":"Recursive","串行":"Serial"}, widths=[.88,.78,.92,1.49,1.00,1.63])
    translated("proxy", "Table 9. Planned observations and earlier completion on the same 460 snapshots",
        ["Planning criterion", "True +", "False +", "False −", "True −", "True + with other delay"],
        "The focal 32-step capped completion time decreases in 39 pairs. At least one other robot's capped time increases in 30 of those pairs.",
        first={"首步方向改善":"Better first-step heading","两步剩余距离改善":"Less remaining distance after two moves"})
    translated("mechanisms", "Table 10. Independent fixed-reservation reference for query-level mechanisms",
        ["Label", "Original positives", "Promoted positives", "Total", "False +", "False −"],
        "The 920 queries include two per pair. Labels can coexist. There are 31 multi-label queries and 3,680 distinct earliest-arrival checks across the four settings.",
        first={"B 预算":"B · budget","R 预留":"R · reservations","G 终点规则":"G · goal rule","W 窗长":"W · window length"})
    translated("public_cells", "Table 11. Service and promotion outcomes on the public layouts by stratum",
        ["Map · N · cap", "Mean rate", "Pairs", "E1 / E2 / E3", "Done, original / promoted",
         "E3 with shared edge", "E3 without shared edge"],
        "Each row contains 16 scenarios. Throughput is completions per 100 steps. Finishes exactly at step 32 count as completed. The shared-edge columns use the number of pairs in each group as denominator.")
    translated("more_policies", "Table B3. New-seed policy comparisons and aligned tasks on public layouts",
        ["Map · N · cap", "Rate change", "Overdue change (pp)", "Initial-task completion change (pp)",
         "Capped initial-task time change (steps)"],
        "Differences are two-stage minus remaining distance. Each stratum uses 16 new paired scenarios. Brackets give pointwise two-sided 95% intervals. Both arms issue the same initial tasks at step 0, with 64 steps of follow-up.")
    translated("workload", "Table C1. End-to-end SIPP round time and workload",
        ["Map · N · cap", "Time P50 / P95 (ms)", "Seed tests P50", "Interval-state expansions P50",
         "Neighbor-interval tests P50", "Reservation changes P50"],
        "One machine runs all scenarios serially. The workload uses seed 6101 and 96 post-warm-up rounds in each stratum. Time includes sorting, seed construction, search, reservations, and validity checks.")
    return tables


if __name__ == "__main__":
    cn = source_tables("cn")
    en = build()
    assert cn.keys() == en.keys()
    for key, (title, heads, rows, widths, note, fs) in en.items():
        assert len(heads) == len(widths)
        assert len(rows) == len(cn[key][2]), key
        assert all(len(row) == len(heads) for row in rows), key
