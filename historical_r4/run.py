"""Run the independent continuous-task diagnostics and policy evaluations."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
from time import perf_counter

from diagnose import diagnose_run, mechanism_runs
from protocol import DIAG_SEEDS, POLICY_SEEDS, POLICIES, SOURCES, strata
from simulator import policy_run, scenario


def run_diagnostic(specification):
    return diagnose_run(*specification)


def run_policies(specification):
    m, n, b, seed = specification
    case, state = scenario(m, n, b, seed)
    return [dict(layout=m, n=n, multiplier=b, budget=case.budget, seed=seed,
                 policy=p, **policy_run(case, state, p)) for p in POLICIES]


def write_jsonl(out, rows):
    op = gzip.open if out.suffix == ".gz" else open
    with op(out, "wt", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":"))+"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--mode", choices=("diagnosis", "policies", "all"), default="all")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        if args.mode in ("diagnosis", "all"):
            runs, pairs = [], []
            runspecs = [(*cell, seed, source) for cell in strata() for source in SOURCES for seed in DIAG_SEEDS]
            for i, (selection, selected) in enumerate(pool.map(run_diagnostic, runspecs), 1):
                runs.append(selection)
                pairs.extend(selected)
                if i % 48 == 0:
                    print(f"Diagnostics {i}/{len(runspecs)} ({len(pairs)} pairs)", flush=True)
            write_jsonl(args.out/"selection.jsonl", runs)
            write_jsonl(args.out/"pairs.jsonl.gz", pairs)
            b, p = mechanism_runs(pairs)
            write_jsonl(args.out/"mechanism_budget.jsonl", b)
            write_jsonl(args.out/"mechanism_route.jsonl", p)
            print(f"Diagnostics done: {len(runs)} runs, {len(pairs)} pairs ({perf_counter()-start:.1f}s)", flush=True)
        if args.mode in ("policies", "all"):
            rows = []
            runspecs = [(*cell, seed) for cell in strata() for seed in POLICY_SEEDS]
            for i, r in enumerate(pool.map(run_policies, runspecs), 1):
                rows.extend(r)
                if i % 32 == 0:
                    print(f"Policy scenarios {i}/{len(runspecs)}", flush=True)
            write_jsonl(args.out/"policies.jsonl.gz", rows)
            print(f"Policies done: {len(rows)} runs ({perf_counter()-start:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
