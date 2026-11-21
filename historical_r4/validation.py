"""Holdout simulation for the R4 diagnostic protocol."""
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from functools import cache, partial
from pathlib import Path
import argparse
import random

from diagnose import compare
from protocol import EXEC, LOOK, W
from run import write_jsonl
from simulator import (Case, Map, State, advance, age_rel, common_seed, goal_at,
                       order_for, paths_valid, replanning, scenario)

HOLDOUT_LAYOUTS = ("ladder", "offset")
MATCH_SEEDS = tuple(range(4101, 4117))
HOLDOUT_SEEDS = tuple(range(5101, 5113))
CONSTRUCTORS = ("recursive", "serial")
MATCH_TICKS = tuple(range(48, 161, 16))
HOLDOUT_TICKS = tuple(range(64, 289, 16))


class HoldoutMap(Map):
    def __init__(self, name):
        self.name = name
        self.width, self.height = 21, 13
        self.xy = tuple((x, y) for y in range(self.height) for x in range(self.width))
        strip = ({(x, y) for x in (9, 10, 11) for y in (2, 6, 10)}
                 if name == "ladder" else
                 {(9, 2), (11, 5), (9, 10), (11, 8)} | {(10, y) for y in range(2, 11)})
        shelves = ({(x, y) for x in (3, 4, 7, 13, 16, 17) for y in (3, 4, 8, 9)}
                   if name == "ladder" else
                   {(x, y) for x in (3, 4, 5, 14, 15, 16) for y in (1, 2, 3, 9, 10, 11)}
                   | {(7, y) for y in (5, 6, 7)} | {(13, y) for y in (4, 5, 6)})
        self.cells = tuple(v for v, (x, y) in enumerate(self.xy)
                           if ((x, y) in strip or x not in (9, 10, 11)) and (x, y) not in shelves)
        available = set(self.cells)
        w = self.width
        self.adj = {v: tuple(sorted(u for u in (v-w, v+w, v-1, v+1)
                                   if u in available and self.manhattan(u, v) == 1))
                    for v in self.cells}
        self.moves = {v: self.adj[v]+(v,) for v in self.cells}
        self.reverse = {v: tuple(reversed(self.adj[v]))+(v,) for v in self.cells}
        self.distance = {v: self.bfs(v) for v in self.cells}
        assert all(self.distance[self.cells[0]][v] >= 0 for v in self.cells)
        self.depots = tuple(tuple(v for v in self.cells if self.bank(v) == side
                                  and (self.xy[v][0] <= 2 or self.xy[v][0] >= 18))
                            for side in (-1, 1))

    def bank(self, v):
        x, _ = self.xy[v]
        return -1 if x <= 8 else 1 if x >= 12 else 0

    def bfs(self, v):
        d = [-1]*len(self.xy)
        d[v] = 0
        queue = deque([v])
        while queue:
            a = queue.popleft()
            for b in self.adj[a]:
                if d[b] < 0:
                    d[b] = d[a]+1
                    queue.append(b)
        return tuple(d)


@cache
def holdout_map(name):
    return HoldoutMap(name)


def holdout_scenario(name, n, multiplier, seed):
    grid = holdout_map(name)
    root = random.Random(f"LMAPF-R4:{name}:{seed}")
    starts = root.sample(grid.depots[0]+grid.depots[1], n)
    targets, lengths = [], []
    for start in starts:
        rng = random.Random(root.getrandbits(64))
        goals, distances = [start], []
        for j in range(321):
            origin = goals[-1]
            p = .65 if (j//4) % 2 == 0 else .35
            next_bank = (grid.bank(origin) == 1) ^ (rng.random() < p)
            g = rng.choice([v for v in grid.depots[next_bank] if v != origin])
            goals.append(g)
            distances.append(grid.distance[g][origin])
        targets.append(tuple(goals))
        lengths.append(tuple(distances))
    init = State(0, tuple((v,)*(W+1) for v in starts), (0,)*n, (0,)*n)
    return Case(grid, tuple(targets), tuple(lengths), n*multiplier), init


def serial_seed(case, state):
    """Grow a legal window without displacing an unprocessed robot."""
    grid = case.grid
    positions = state.pos
    order = order_for(case, state, "age")
    distances = [grid.distance[goal_at(case, state, i)] for i in order]
    paths = [[v] for v in positions]
    for _ in range(W):
        claimed = set(positions)
        edges = set()
        next_positions = list(positions)
        for i, distance in zip(order, distances):
            a = positions[i]
            claimed.remove(a)
            b = min((v for v in grid.moves[a] if v not in claimed and (v, a) not in edges),
                    key=lambda v: (distance[v], v))
            claimed.add(b)
            edges.add((a, b))
            next_positions[i] = b
            paths[i].append(b)
        positions = tuple(next_positions)
    out = tuple(map(tuple, paths))
    assert paths_valid(grid, out)
    return out


def serial_replan(case, state, order, seed_paths=None):
    initial = serial_seed(case, state) if seed_paths is None else seed_paths
    return replanning(case, state, order, seed_paths=initial)


def matched_focus(case, state, previous):
    g = case.grid
    goals = [goal_at(case, state, i) for i in range(len(state.jobs))]
    bank = [g.bank(v) for v in goals]
    left, right = (6, 14) if g.name in HOLDOUT_LAYOUTS else (4, 12)
    near = [i for i, v in enumerate(state.pos)
            if left <= g.xy[v][0] <= right and g.bank(v) != bank[i]
            and g.bank(case.targets[i][state.jobs[i]]) != bank[i]]
    candidates = [i for i in near if state.time-state.issued[i] >= 2
                  and g.distance[goals[i]][state.pos[i]] >= g.distance[goals[i]][previous[i]]]
    if not candidates:
        return None, None
    i = min(candidates, key=lambda j: (-age_rel(case, state, j), j))
    opposed = any(bank[j] == -bank[i] and g.manhattan(state.pos[i], state.pos[j]) <= 4 for j in near)
    return i, opposed


def validate_run(spec):
    map_id, b, seed, constructor = spec
    holdout = map_id in HOLDOUT_LAYOUTS
    make_case = holdout_scenario if holdout else scenario
    case, state = make_case(map_id, 24, b, seed)
    plan = serial_replan if constructor == "serial" else replanning
    ticks = HOLDOUT_TICKS if holdout else MATCH_TICKS
    full_length = 320 if holdout else 192
    scenario_id = dict(layout=map_id, n=24, multiplier=b, budget=case.budget, seed=seed,
                       source="congestion", constructor=constructor)
    selected, timeline, selection = [], {}, []
    previous = state.pos
    while state.time < full_length:
        order = order_for(case, state, "congestion")
        paths, traces, _ = plan(case, state, order)
        assert paths_valid(case.grid, paths)
        timeline[state.time] = (paths, [asdict(t) for t in traces], state)
        if state.time in ticks:
            focal, opposed = matched_focus(case, state, previous)
            rank = None if focal is None else order.index(focal)+1
            selection.append(dict(**scenario_id, time=state.time, focus=focal, rank=rank,
                                  opposed=opposed, selected=rank is not None and rank>1))
            if rank is not None and rank > 1:
                selected.append((state, order, focal, opposed))
        previous = tuple(p[EXEC-1] for p in paths)
        state = advance(case, state, paths)
    timeline[state.time] = (None, None, state)
    warm = ticks[0]
    first_jobs = timeline[warm][2].jobs
    completions = sum(state.jobs)-sum(first_jobs)
    source_summary = dict(**scenario_id, steps=full_length-warm, completions=completions,
                          throughput=100*completions/(full_length-warm))
    outcomes, same_snapshot = [], []
    for state, order, focal, opposed in selected:
        initial = serial_seed(case, state) if constructor == "serial" else common_seed(case, state)[0]
        q = compare(case, state, order, focal, "congestion", initial, planner=plan)
        source_paths, source_logs, _ = timeline[state.time]
        assert q["baseline"]["solver"] == source_logs
        assert q["baseline"]["window"] == source_paths
        for delta in range(1, LOOK+1):
            tick = state.time+(delta-1)//EXEC*EXEC
            expected = timeline[tick][0]
            assert [p[delta] for p in q["baseline"]["path"]] == [p[(delta-1)%EXEC+1] for p in expected]
        meta = dict(**scenario_id, time=state.time, opposed=opposed)
        outcomes.append(dict(**meta, **q))
        if holdout and constructor == "recursive":
            # compare() uses the supplied seed for the intervention cycle only.
            # The recursive source implementation resumes in both branches.
            alt = compare(case, state, order, focal, "congestion", serial_seed(case, state))
            same_snapshot.append(dict(**meta, **alt))
    return selection, outcomes, same_snapshot, source_summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, default=Path("data"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, specs in (
        ("matched", [(m,b,s,"recursive") for m in ("single","bypass") for b in (5,14) for s in MATCH_SEEDS]),
        ("holdout", [(m,b,s,c) for m in HOLDOUT_LAYOUTS for b in (5,14) for s in HOLDOUT_SEEDS for c in CONSTRUCTORS]),
    ):
        samples, logs, alternative, source_runs = [], [], [], []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for i, (s,p,a,source_run) in enumerate(pool.map(validate_run, specs), 1):
                samples.extend(s)
                logs.extend(p)
                alternative.extend(a)
                source_runs.append(source_run)
                if i % 16 == 0:
                    print(f"{name}: {i}/{len(specs)} runs, {len(logs)} pairs", flush=True)
        write_jsonl(args.out/f"{name}_source_runs.jsonl", source_runs)
        write_jsonl(args.out/f"{name}_selection.jsonl.gz", samples)
        write_jsonl(args.out/f"{name}_pairs.jsonl.gz", logs)
        if alternative:
            write_jsonl(args.out/"holdout_alternative_first_round.jsonl.gz", alternative)
        print(f"{name}: wrote {len(samples)} tick records, {len(logs)} pairs and {len(alternative)} first-round controls", flush=True)


if __name__ == "__main__":
    main()
