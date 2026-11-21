"""One-time order intervention and the two local mechanism controls."""
from dataclasses import asdict
import hashlib
import random

from protocol import W, EXEC, WARM, END, LOOK, AT_MOST, MECH_PER_CELL
from simulator import (Reservations, Search, advance, age_rel, common_seed,
                       goal_at, low_search, order_for, paths_valid, replanning, scenario)


class Follow:
    def __init__(self, case, snapshot):
        n = len(snapshot.jobs)
        self.case, self.snapshot = case, snapshot
        self.completion = [None]*n
        self.exit = [None]*n
        self.entry = [None]*n
        self.zone = [None]*n
        self.first_entry = [None]*n
        self.loc = [[p] for p in snapshot.pos]
        self.initial_inside = [case.grid.bank(p) == 0 for p in snapshot.pos]
        self.destination = [case.grid.bank(goal_at(case, snapshot, i)) for i in range(n)]
        self.at_risk = [
            case.grid.bank(case.targets[i][snapshot.jobs[i]]) != self.destination[i]
            and case.grid.bank(v) != self.destination[i]
            for i, v in enumerate(snapshot.pos)
        ]
        for i, inside in enumerate(self.initial_inside):
            if inside and self.at_risk[i]:
                self.first_entry[i] = self.entry[i] = 0

    def visit(self, t, i, job, issued, p, arrived):
        t -= self.snapshot.time
        old_bank = self.case.grid.bank(self.loc[i][-1])
        new_bank = self.case.grid.bank(p)
        self.loc[i].append(p)
        if job != self.snapshot.jobs[i]:
            return
        if self.at_risk[i] and self.exit[i] is None:
            if new_bank == 0 and old_bank != 0:
                self.entry[i] = t
                if self.first_entry[i] is None:
                    self.first_entry[i] = t
            if old_bank == 0 and new_bank != 0:
                if new_bank == self.destination[i]:
                    self.exit[i] = t
                    self.zone[i] = (t-self.entry[i]
                                    if self.entry[i] is not None and self.entry[i] > 0 else None)
                else:
                    self.entry[i] = None
        if arrived:
            self.completion[i] = t

    def result(self):
        return dict(task=self.completion, gate=self.exit, gate_entry=self.first_entry,
                    zone=self.zone, path=self.loc)


def capped(t):
    return LOOK if t is None else t


def follow(case, snapshot, policy, first, traces, stop_at=LOOK, planner=replanning):
    result = Follow(case, snapshot)
    state = snapshot
    prefix = first
    assert paths_valid(case.grid, prefix)
    while state.time < snapshot.time + stop_at:
        if state.time > snapshot.time:
            prefix, _, _ = planner(case, state, order_for(case, state, policy))
            assert paths_valid(case.grid, prefix)
        state = advance(case, state, prefix, result.visit)
    return dict(**result.result(),
                first=[list(p[:EXEC+1]) for p in first],
                window=first,
                solver=[asdict(r) for r in traces],
                round_budget_cut=any(r.status in ("budget", "not_started") for r in traces),
                published=any(r.path for r in traces),
                fallback=not any(r.path for r in traces),
                seed_retained=[not bool(r.path) for r in traces]), result


def compare(case, state, order, focus, source, seed_paths, planner=replanning):
    promoted = (focus,) + tuple(i for i in order if i != focus)
    a, ta, _ = planner(case, state, order, seed_paths=seed_paths)
    b, tb, _ = planner(case, state, promoted, seed_paths=seed_paths)
    a, follow_obj = follow(case, state, source, a, ta, planner=planner)
    b, _ = follow(case, state, source, b, tb, planner=planner)
    task_delta = [capped(v)-capped(u) for u, v in zip(a["task"], b["task"])]
    gate_delta = [capped(v)-capped(u) if eligible else None
                  for u, v, eligible in zip(a["gate"], b["gate"], follow_obj.at_risk)]
    changed = a["first"][focus] != b["first"][focus]
    gained = not ta[focus].started and tb[focus].started
    others_later = [i for i, d in enumerate(task_delta) if i != focus and d > 0]
    others_earlier = [i for i, d in enumerate(task_delta) if i != focus and d < 0]
    return dict(focus=focus, rank=order.index(focus)+1, order=order, promoted=promoted,
                at_risk=follow_obj.at_risk, initial_inside=follow_obj.initial_inside,
                pre_distances=[case.lengths[i][k] for i, k in enumerate(state.jobs)],
                ages=[state.time-s for s in state.issued],
                goals=[goal_at(case, state, i) for i in range(len(state.jobs))],
                job_index=state.jobs, seed_paths=seed_paths,
                baseline=a, treatment=b, task_delta=task_delta, gate_delta=gate_delta,
                changed=changed, gained=gained, others_later=others_later, others_earlier=others_earlier,
                category1=gained and not changed,
                category2=changed and task_delta[focus] >= 0,
                category3=task_delta[focus] < 0 and bool(others_later),
                co_burden_gate=gate_delta[focus] is not None and gate_delta[focus] < 0 and bool(others_later))


def candidate_outcome(case, state, focus, reservation_paths, allowance):
    q = low_search(case.grid, Reservations(reservation_paths), state.pos[focus],
                   goal_at(case, state, focus), allowance)
    return asdict(q)


def budget_control(case, state, focal, stage):
    others, available = stage[focal]
    return dict(focal=focal, reservations=others, budget_before=available,
                first=candidate_outcome(case, state, focal, others, available),
                higher=candidate_outcome(case, state, focal, others, available+4*W),
                budget_after=available+4*W)


def score(grid, target, p):
    if target in p:
        return (0, p.index(target))
    return (1, grid.distance[target][p[-1]])


def candidate_control(case, state, order, focal, initial_paths, paths, trace, stage):
    for upper in order[:order.index(focal)]:
        old = trace[upper]
        if not old.path or old.expanded == 0:
            continue
        others, _ = stage[upper]
        target = goal_at(case, state, upper)
        alternative = low_search(case.grid, Reservations(others), state.pos[upper],
                                 target, old.expanded, reverse=True)
        if (not alternative.path or alternative.path == old.path
                or score(case.grid, target, old.path) != score(case.grid, target, alternative.path)):
            continue
        injected = Search(alternative.status, old.expanded, alternative.path)
        p2, t2, after = replanning(case, state, order, capture=True,
                                   force=(upper, injected), seed_paths=initial_paths)
        assert paths_valid(case.grid, p2)
        allowance = 4*W
        return dict(focal=focal, upper=upper, focal_cap=allowance,
                    round_cap=case.budget, order=order, score=score(case.grid, target, old.path),
                    path_old=old.path, path_alt=alternative.path,
                    old_reserved=stage[focal][0], alt_reserved=after[focal][0],
                    high_cost=old.expanded, alt_cost=alternative.expanded,
                    old_focal_budget=stage[focal][1], alt_focal_budget=after[focal][1],
                    old_focal=asdict(trace[focal]), alt_focal=asdict(t2[focal]),
                    old_exec=paths[focal][:EXEC+1], alt_exec=p2[focal][:EXEC+1],
                    old_local=candidate_outcome(case, state, focal, stage[focal][0], allowance),
                    alt_local=candidate_outcome(case, state, focal, after[focal][0], allowance))
    return None


def gate_focus(case, state, previous):
    p = state.pos
    grid = case.grid
    gs = [goal_at(case, state, i) for i in range(len(p))]
    side = [grid.bank(g) for g in gs]
    near = [i for i, v in enumerate(p)
            if 4 <= grid.xy[v][0] <= 12 and grid.bank(v) != side[i]
            and grid.bank(case.targets[i][state.jobs[i]]) != side[i]]
    blocked = [i for i in near if state.time-state.issued[i] >= 2
               and grid.distance[gs[i]][p[i]] >= grid.distance[gs[i]][previous[i]]
               and any(side[j] == -side[i] and grid.manhattan(p[i], p[j]) <= 4 for j in near)]
    return min(blocked, key=lambda i: (-age_rel(case, state, i), i)) if blocked else None


def diagnose_run(layout, n, multiplier, seed, source, selection_mode="overdue"):
    case, state = scenario(layout, n, multiplier, seed)
    targets = []
    counts = dict(eligible=0, periods=0, overdue=0, already_first=0)
    eligible_ranks = [0]*n
    states = {}
    ok = {}
    previous = state.pos
    while state.time < END:
        order = order_for(case, state, source)
        if WARM <= state.time <= END-LOOK:
            counts["periods"] += 1
            older = min(range(n), key=lambda i: (-age_rel(case, state, i), i))
            states[state.time] = state
            focus = older if age_rel(case, state, older) > 3 else None
            if selection_mode == "gate":
                focus = gate_focus(case, state, previous)
            if focus is not None:
                counts["overdue"] += 1
                rank = order.index(focus)+1
                if rank == 1:
                    counts["already_first"] += 1
                else:
                    counts["eligible"] += 1
                    eligible_ranks[rank-1] += 1
                    targets.append((state, order, focus))
        p, tr, _ = replanning(case, state, order)
        assert paths_valid(case.grid, p)
        ok[state.time] = tr
        previous = tuple(x[EXEC-1] for x in p)
        state = advance(case, state, p)
    stable_seed = f"{layout}:{n}:{multiplier}:{seed}:{source}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(stable_seed).digest()[:8], "big"))
    chosen = sorted(rng.sample(targets, min(AT_MOST, len(targets))), key=lambda row: row[0].time)
    out = []
    for state, order, focal in chosen:
        seed_paths, common_work = common_seed(case, state)
        q = compare(case, state, order, focal, source, seed_paths)
        original = ok[state.time]
        assert q["baseline"]["solver"] == [asdict(x) for x in original]
        for t in range(EXEC, LOOK+1, EXEC):
            if state.time+t in states:
                assert [p[t] for p in q["baseline"]["path"]] == list(states[state.time+t].pos)
        out.append(dict(layout=layout, n=n, multiplier=multiplier, budget=case.budget, seed=seed,
                        source=source, time=state.time, common_work=common_work, **q))
    return (dict(layout=layout, n=n, multiplier=multiplier, budget=case.budget,
                 seed=seed, source=source, picked=len(out), eligible_ranks=eligible_ranks, **counts), out)


def mechanism_runs(pairs):
    groups = {}
    for q in pairs:
        groups.setdefault((q["layout"], q["n"], q["multiplier"], q["source"]), []).append(q)
    budget_rows, route_rows = [], []
    for group in groups.values():
        sorted_group = sorted(group, key=lambda q: (q["seed"], q["time"]))
        budget_states = [q for q in sorted_group
                         if q["baseline"]["solver"][q["focus"]]["status"] in ("budget", "not_started")]
        wanted = [(q, "budget") for q in budget_states[:MECH_PER_CELL]] + [
            (q, "route") for q in sorted_group[:MECH_PER_CELL]]
        for q, experiment in wanted:
            key = {s: q[s] for s in ("layout", "n", "multiplier", "seed", "source", "time")}
            case, state = scenario(q["layout"], q["n"], q["multiplier"], q["seed"])
            for t in range(0, q["time"], EXEC):
                p, _, _ = replanning(case, state, order_for(case, state, q["source"]))
                state = advance(case, state, p)
            order = tuple(q["order"])
            initial_paths = tuple(map(tuple, q["seed_paths"]))
            f = q["focus"]
            p, tr, stage = replanning(case, state, order, capture=True, seed_paths=initial_paths)
            if experiment == "budget":
                budget_rows.append(dict(**key, **budget_control(case, state, f, stage)))
            else:
                route_rows.append(dict(**key, result=candidate_control(case, state, order, f, initial_paths, p, tr, stage)))
    return budget_rows, route_rows
