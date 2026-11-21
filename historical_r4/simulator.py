"""Deterministic, reservation-safe rolling prioritized planning on a grid."""
from collections import deque
from dataclasses import dataclass
from functools import cache
from heapq import heappop, heappush
from itertools import count
import random
import time

from protocol import WIDTH, HEIGHT, W, EXEC, WARM, END, LOOK, TAUS, PROTECT


class Map:
    def __init__(self, name):
        self.name = name
        self.width, self.height = WIDTH, HEIGHT
        self.cells = tuple(y * WIDTH + x for y in range(HEIGHT) for x in range(WIDTH)
                           if not (x in (2, 3, 5, 6, 10, 11, 13, 14) and y in (1, 2, 7, 8))
                           and (not 7 <= x <= 9 or y in (0, 5)
                                or name == "bypass" and (y == 3 or (x, y) == (8, 4))))
        cells = set(self.cells)
        self.xy = tuple((v % WIDTH, v // WIDTH) for v in range(WIDTH * HEIGHT))
        self.adj = {v: tuple(sorted(u for u in (v-WIDTH, v+WIDTH, v-1, v+1)
                                   if u in cells and self.manhattan(u, v) == 1))
                    for v in self.cells}
        self.moves = {v: self.adj[v] + (v,) for v in self.cells}
        self.reverse = {v: tuple(reversed(self.adj[v])) + (v,) for v in self.cells}
        self.distance = {v: self.bfs(v) for v in self.cells}
        self.depots = tuple(tuple(v for v in self.cells if self.bank(v) == side
                                  and (self.xy[v][0] <= 2 or self.xy[v][0] >= 14))
                            for side in (-1, 1))
        assert all(self.distance[self.cells[0]][v] >= 0 for v in self.cells)

    def manhattan(self, a, b):
        x, y = self.xy[a]
        u, v = self.xy[b]
        return abs(x-u) + abs(y-v)

    def bank(self, v):
        x, _ = self.xy[v]
        return -1 if x <= 6 else 1 if x >= 10 else 0

    def bfs(self, v):
        d = [-1] * (WIDTH * HEIGHT)
        d[v] = 0
        q = deque([v])
        while q:
            a = q.popleft()
            for b in self.adj[a]:
                if d[b] == -1:
                    d[b] = d[a]+1
                    q.append(b)
        return tuple(d)


@cache
def layout(name):
    return Map(name)


@dataclass(frozen=True)
class Case:
    grid: Map
    targets: tuple
    lengths: tuple
    budget: int


@dataclass(frozen=True)
class State:
    time: int
    paths: tuple
    jobs: tuple
    issued: tuple

    @property
    def pos(self):
        return tuple(p[0] for p in self.paths)


def scenario(name, n, budget_multiplier, seed):
    grid = layout(name)
    run_rng = random.Random(seed * 1000 + n * 10 + (name == "bypass"))
    starts = run_rng.sample(grid.depots[0]+grid.depots[1], n)
    targets, lengths = [], []
    for start in starts:
        rng = random.Random(run_rng.getrandbits(64))
        goals, distances = [start], []
        for _ in range(END + LOOK + 1):
            previous = goals[-1]
            side = (grid.bank(previous) == 1) ^ (rng.random() < .80)
            choices = [v for v in grid.depots[side] if v != previous]
            g = rng.choice(choices)
            goals.append(g)
            distances.append(grid.distance[g][previous])
        targets.append(tuple(goals))
        lengths.append(tuple(distances))
    return (Case(grid, tuple(targets), tuple(lengths), budget_multiplier*n),
            State(0, tuple((v,)*(W+1) for v in starts), (0,)*n, (0,)*n))


def paths_valid(grid, paths):
    for t in range(len(paths[0])):
        cur = [p[t] for p in paths]
        if len(set(cur)) != len(cur):
            return False
        if t:
            edges = [(p[t-1], p[t]) for p in paths]
            es = set(edges)
            if any(v not in grid.moves[u] or (u != v and (v, u) in es) for u, v in edges):
                return False
    return True


class Reservations:
    def __init__(self, paths, horizon=W):
        self.cells = [set() for _ in range(horizon+1)]
        self.edges = [set() for _ in range(horizon+1)]
        for p in paths:
            self.change(p, True)

    def change(self, path, add):
        for t, v in enumerate(path):
            (self.cells[t].add if add else self.cells[t].remove)(v)
            if t:
                (self.edges[t].add if add else self.edges[t].remove)((v, path[t-1]))

    def accepts(self, path):
        return all(v not in self.cells[t] and (t == 0 or (path[t-1], v) not in self.edges[t])
                   for t, v in enumerate(path))


@dataclass(frozen=True)
class Search:
    status: str
    expanded: int
    path: tuple = ()

    @property
    def started(self):
        return self.status != "not_started"


def low_search(grid, reservations, start, goal, cap, reverse=False, horizon=W):
    if cap <= 0:
        return Search("not_started", 0)
    distance = grid.distance[goal]
    moves = grid.reverse if reverse else grid.moves
    num = count()
    h = distance[start]
    heap = [(2*h, h, next(num), 0, start)]
    previous = {(0, start): None}
    latest_block = max((t for t, vs in enumerate(reservations.cells) if goal in vs), default=-1)
    used = 0
    while heap:
        _, h, _, t, v = heappop(heap)
        if t == horizon or v == goal:
            s = (t, v)
            path = [v] * (horizon-t)
            while s is not None:
                path.append(s[1])
                s = previous[s]
            return Search("goal" if v == goal else "window", used, tuple(reversed(path)))
        if used == cap:
            return Search("budget", used)
        used += 1
        nt = t+1
        occupied, swapped = reservations.cells[nt], reservations.edges[nt]
        for u in moves[v]:
            ns = nt, u
            if ns in previous or u in occupied or (v, u) in swapped or (u == goal and nt <= latest_block):
                continue
            previous[ns] = (t, v)
            d = distance[u]
            heappush(heap, (nt+2*d, d, next(num), nt, u))
    return Search("exhausted", used)


def goal_at(case, state, i):
    return case.targets[i][state.jobs[i]+1]


def age_rel(case, state, i):
    return (state.time-state.issued[i])/case.lengths[i][state.jobs[i]]


def order_for(case, state, what):
    p = state.pos
    agents = range(len(p))
    if what == "fixed":
        return tuple(agents)
    if what == "age":
        return tuple(sorted(agents, key=lambda i: (state.issued[i], i)))
    if what == "relative":
        return tuple(sorted(agents, key=lambda i: (-age_rel(case, state, i), i)))
    if what == "distance":
        return tuple(sorted(agents, key=lambda i: (-case.grid.distance[goal_at(case, state, i)][p[i]], i)))
    counts = [sum(i != j and case.grid.manhattan(v, u) <= 2 for j, u in enumerate(p))
              for i, v in enumerate(p)]
    if what == "congestion":
        return tuple(sorted(agents, key=lambda i: (-counts[i], i)))
    if what in ("dual", "protect_fixed"):
        rel = [age_rel(case, state, i) for i in agents]
        return tuple(sorted(agents, key=lambda i:
                            (0, -rel[i], i) if rel[i] > PROTECT
                            else (1, -counts[i] if what == "dual" else 0, i)))
    raise ValueError(what)


def common_seed(case, state, horizon=W):
    """Build a safe window by deterministic one-step priority inheritance."""
    grid = case.grid
    positions = state.pos
    n = len(positions)
    metrics = [grid.distance[goal_at(case, state, i)] for i in range(n)]
    base = order_for(case, state, "age")
    planned = [[v] for v in positions]
    work = 0
    for _ in range(horizon):
        present = {v: i for i, v in enumerate(positions)}
        claimed = set()
        next_pos = [None] * n

        def assign(i):
            nonlocal work
            d, v = metrics[i], positions[i]
            for u in sorted(grid.moves[v], key=lambda u: (d[u], u == v, u)):
                work += 1
                j = present.get(u)
                if u in claimed or (j is not None and j != i and next_pos[j] == v):
                    continue
                claimed.add(u)
                next_pos[i] = u
                if j is None or next_pos[j] is not None or assign(j):
                    return True
                next_pos[i] = None
                claimed.remove(u)
            return False

        for i in base:
            if next_pos[i] is None:
                assert assign(i)
        positions = tuple(next_pos)
        for i, v in enumerate(positions):
            planned[i].append(v)
    return tuple(map(tuple, planned)), work


def replanning(case, state, order, capture=False, force=None, seed_paths=None, horizon=W):
    """Every replacement has been checked against current reservations of all other vehicles."""
    paths = list(common_seed(case, state, horizon)[0] if seed_paths is None else seed_paths)
    table = Reservations(paths, horizon)
    traces = [None]*len(paths)
    stages = {} if capture else None
    remaining = case.budget
    for i in order:
        table.change(paths[i], False)
        if capture:
            stages[i] = (tuple(p for j, p in enumerate(paths) if j != i), remaining)
        if force and force[0] == i:
            result = force[1]
            assert result.expanded <= remaining and table.accepts(result.path)
        else:
            result = low_search(case.grid, table, paths[i][0], goal_at(case, state, i),
                                remaining, horizon=horizon)
        traces[i] = result
        remaining -= result.expanded
        if result.path:
            paths[i] = result.path
        table.change(paths[i], True)
    return tuple(paths), tuple(traces), stages


def advance(case, state, paths, measure=None):
    # Plans already start at the snapshot positions. Execute only the next EXEC actions.
    jobs, issued = list(state.jobs), list(state.issued)
    for k in range(1, EXEC+1):
        t = state.time+k
        for i, path in enumerate(paths):
            job = jobs[i]
            arrived = path[k] == case.targets[i][job+1]
            if measure is not None:
                measure(t, i, job, issued[i], path[k], arrived)
            if arrived:
                jobs[i] += 1
                issued[i] = t
    continued = tuple(p[EXEC:] + (p[-1],)*EXEC for p in paths)
    return State(state.time+EXEC, continued, tuple(jobs), tuple(issued))


def percentile(data, p):
    if not data:
        return None
    d = sorted(data)
    k = (len(d)-1)*p
    i = int(k)
    return d[i]+(d[min(i+1, len(d)-1)]-d[i])*(k-i)


def length_bin(d):
    return 0 if d <= 8 else 1 if d <= 16 else 2


class FleetStats:
    def __init__(self, case, n):
        self.case = case
        self.n = n
        self.over = [[0]*n for _ in TAUS]
        self.runs = [0]*n
        self.longest = [0]*n
        self.censored_run = [0]*n
        self.cohort = [None]*n
        self.capped = []
        self.by_length = [[0, 0, 0] for _ in range(3)]
        self.completed = 0
        self.planning_ms = []
        self.budget_events = 0
        self.empty_plans = 0
        self.rounds = 0
        self.seed_tries = []

    def visit(self, t, i, job, issued, p, arrived):
        if t <= WARM:
            return
        d = self.case.lengths[i][job]
        age = t-issued
        for k, tau in enumerate(TAUS):
            self.over[k][i] += age > tau*d
        b = length_bin(d)
        bl = self.by_length[b]
        bl[0] += 1
        bl[1] += age > 3*d
        bl[2] += max(age-d, 0)
        if age > 3*d:
            self.runs[i] += 1
            self.longest[i] = max(self.longest[i], self.runs[i])
        else:
            self.runs[i] = 0
        if WARM <= issued <= END-LOOK and (arrived or age == LOOK):
            if self.cohort[i] != job:
                self.capped.append((b, min(age, LOOK), bool(arrived and age <= LOOK)))
                self.cohort[i] = job
        if arrived:
            self.completed += 1
            self.runs[i] = 0
        if t == END:
            self.censored_run[i] = self.runs[i]

    def plan(self, traces, elapsed, seed_tries):
        self.rounds += 1
        self.budget_events += any(r.status in ("budget", "not_started") for r in traces)
        self.empty_plans += not any(r.path for r in traces)
        self.planning_ms.append(elapsed)
        self.seed_tries.append(seed_tries)

    def summary(self):
        exp = END-WARM
        fi = [x/exp for x in self.over[TAUS.index(3)]]
        return dict(throughput=self.completed/exp*100,
                    completed=self.completed, f2=sum(self.over[0])/(self.n*exp),
                    f3=sum(fi)/self.n, f4=sum(self.over[2])/(self.n*exp),
                    vehicle_median=percentile(fi, .5), vehicle_q25=percentile(fi, .25),
                    vehicle_q75=percentile(fi, .75), vehicle_max=max(fi),
                    vehicle_steps_over=[list(a) for a in self.over],
                    longest=max(self.longest), per_car_longest=self.longest,
                    right_censored_run=self.censored_run, by_length=self.by_length,
                    tasks_capped=self.capped, plan_p95_ms=percentile(self.planning_ms, .95),
                    seed_tries_mean=sum(self.seed_tries)/len(self.seed_tries),
                    budget_rounds=self.budget_events, empty_plan_rounds=self.empty_plans, rounds=self.rounds)


def policy_run(case, init, policy):
    state = init
    stats = FleetStats(case, len(init.jobs))
    while state.time < END:
        start = time.perf_counter_ns()
        order = order_for(case, state, policy)
        seed_paths, seed_tries = common_seed(case, state)
        paths, traces, _ = replanning(case, state, order, seed_paths=seed_paths)
        if state.time >= WARM:
            stats.plan(traces, (time.perf_counter_ns()-start)/1e6, seed_tries)
        assert paths_valid(case.grid, paths)
        state = advance(case, state, paths, stats.visit)
    return stats.summary()
