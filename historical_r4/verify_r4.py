"""Verify holdout logs, timing definitions, and the primary decisions."""
from collections import Counter
import json
from pathlib import Path

from analyze import read
from revision_audit import crossing, grid_for, identity
from validation import HOLDOUT_SEEDS, MATCH_SEEDS
from verify import check_pair

DATA = Path("data")


def verify_selection(name, seed_range, planned_ticks, pair_count):
    ticks = read(f"{name}_selection.jsonl.gz")
    rows = read(f"{name}_pairs.jsonl.gz")
    assert len(ticks) == planned_ticks
    assert len(rows) == pair_count
    assert {q["seed"] for q in ticks} == set(seed_range)
    spec = lambda q: (*identity(q), q["constructor"])
    lookup = {spec(q): q for q in ticks}
    assert len(lookup) == planned_ticks
    assert len({spec(q) for q in rows}) == pair_count
    assert {spec(q) for q in rows} == {spec(q) for q in ticks if q["selected"]}
    for q in rows:
        chosen = lookup[spec(q)]
        assert all(q[k]==chosen[k] for k in ("rank","focus","opposed"))
        check_pair(q, grid_for(q["layout"]))
    return rows


def main():
    matched = verify_selection("matched", MATCH_SEEDS, 512, 445)
    table = Counter((q["opposed"], q["category3"]) for q in matched)
    assert (table[True,True],table[False,True]) == (11,4)
    holdout = verify_selection("holdout", HOLDOUT_SEEDS, 1440, 1252)
    first_round = read("holdout_alternative_first_round.jsonl.gz")
    subset = {identity(q):q for q in holdout if q["constructor"]=="recursive"}
    assert len(first_round) == len(subset) == 532
    for q in first_round:
        orig = subset.pop(identity(q))
        check_pair(q, grid_for(q["layout"]))
        assert all(q[k]==orig[k] for k in ("focus","rank","order","promoted","goals","job_index"))
    assert not subset
    gate = read("gate_pairs.jsonl.gz")
    totals=[]
    for arm in ("baseline","treatment"):
        by_start=Counter()
        for q in gate:
            i = q["focus"]
            f,l,e,_ = crossing(grid_for(q["layout"]),q[arm]["path"][i],q["goals"][i],q[arm]["task"][i])
            assert e == f + (l-f) + (e-l)
            by_start[q["initial_inside"][i]] += e
        totals.append((by_start[False],by_start[True]))
    assert totals == [(3028,1291),(2982,1279)]
    results = json.loads((DATA/"r4_results.json").read_text())
    d = results["decision"]
    assert [sum(row[f"rate_pass_{pct}"] for row in d) for pct in (0,5,10)]==[1,12,16]
    assert not any(row["overdue_pass"] or row["joint"] for row in d)
    print("Verified eligibility, safe trajectories, case clocks and the adjusted primary decisions.")


if __name__ == "__main__":
    main()
