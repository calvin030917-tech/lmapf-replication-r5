"""Independent exploratory sample conditioned on observable bottleneck blocking."""
from concurrent.futures import ProcessPoolExecutor
import argparse
from diagnose import diagnose_run
from pathlib import Path
from run import write_jsonl
from protocol import LAYOUTS, BUDGET_MULTIPLIERS

GATE_SEEDS = tuple(range(3001, 3025))


def probe(spec):
    summary, pairs = diagnose_run(*spec, selection_mode="gate")
    summary["gate_conflict_cycles"] = summary.pop("overdue")
    return summary, pairs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    runs = [(*cell, seed, "congestion")
            for cell in [(m, 24, b) for m in LAYOUTS for b in BUDGET_MULTIPLIERS]
            for seed in GATE_SEEDS]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        result = list(pool.map(probe, runs))
    select, qp = zip(*result)
    pairs = [q for row in qp for q in row]
    out = Path("data")
    out.mkdir(exist_ok=True)
    write_jsonl(out/"gate_selection.jsonl", select)
    write_jsonl(out/"gate_pairs.jsonl.gz", pairs)
    print("Independent bottleneck probe:", len(select), "runs;", len(pairs), "pairs;",
          {k: sum(q[k] for q in pairs) for k in ("category1","category2","category3","co_burden_gate")})
