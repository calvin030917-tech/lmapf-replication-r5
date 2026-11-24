"""Opt-in R5 planner with shared safe intervals and fewer transition operations."""

from time import perf_counter_ns

from interval_planner import IntervalQueries, safe, seed_paths
from warehouse import W, priority


class RoundReservations:
    """Sparse reservations for the collision-free paths in one planning round."""

    def __init__(self, paths, window):
        self.w = window
        self.occupied = {}
        self.edge = set()
        self.writes = 0
        self._intervals_by_mask = {0: ((0, window),)}
        for path in paths:
            self.update(path, add=True)

    def update(self, path, add):
        occupied = self.occupied
        edges = self.edge
        previous = path[0]
        if add:
            for time, cell in enumerate(path):
                occupied[cell] = occupied.get(cell, 0) | (1 << time)
                if time:
                    edges.add((cell, previous, time))
                previous = cell
        else:
            for time, cell in enumerate(path):
                remaining = occupied[cell] ^ (1 << time)
                if remaining:
                    occupied[cell] = remaining
                else:
                    del occupied[cell]
                if time:
                    edges.remove((cell, previous, time))
                previous = cell
        self.writes += 2 * len(path) - 1

    def intervals(self, cell):
        mask = self.occupied.get(cell, 0)
        cached = self._intervals_by_mask.get(mask)
        if cached is not None:
            return cached

        remaining = mask
        low = 0
        gaps = []
        while remaining:
            blocked = (remaining & -remaining).bit_length() - 1
            if low < blocked:
                gaps.append((low, blocked - 1))
            low = blocked + 1
            remaining &= remaining - 1
        if low <= self.w:
            gaps.append((low, self.w))
        intervals = tuple(gaps)
        # A reservation update changes the mask key. Old keys stay valid for
        # all cells that still have the corresponding occupancy pattern.
        self._intervals_by_mask[mask] = intervals
        return intervals


class FastIntervalQueries(IntervalQueries):
    """Run the frozen SIPP search over a round's reusable interval cache."""

    def __init__(self, board, reserved):
        self.board = board
        self.book = reserved
        self.w = reserved.w
        self.checks = 0
        self.intervals = reserved.intervals

    def from_state(self, state, at):
        cell, _, end = state
        earliest, deadline = at + 1, end + 1
        edges = self.book.edge
        for neighbor in self.board.adj[cell]:
            intervals = self.intervals(neighbor)
            # Preserve R5's accounting for every neighbor interval, including
            # intervals that cannot intersect the transition's time range.
            self.checks += len(intervals)
            for low, high in intervals:
                if high < earliest:
                    continue
                if low > deadline:
                    break
                arrival = low if low > earliest else earliest
                last = high if high < deadline else deadline
                while (cell, neighbor, arrival) in edges:
                    self.checks += 1
                    arrival += 1
                    if arrival > last:
                        break
                else:
                    yield (neighbor, low, high), arrival


def plan(scene, state, rule="density", order=None, prepared=None, focus=None):
    """Plan one round using the frozen planner's arguments and result format."""
    started = perf_counter_ns()
    goals = scene.goals(state)
    if order is None:
        order = priority(scene, state, rule)
    seed, seed_cost = seed_paths(scene, state, goals) if prepared is None else prepared
    reservations = RoundReservations(seed, W)
    committed = list(seed)
    residual = scene.cap
    traces = [None] * len(seed)
    controls = None
    edge_tests = 0

    for robot in order:
        reservations.update(committed[robot], add=False)
        if robot == focus:
            controls = dict(
                reservations=tuple(path for i, path in enumerate(committed) if i != robot),
                allowance=residual,
                seed=seed[robot],
            )
        query = FastIntervalQueries(scene.board, reservations).solve(
            state.cells[robot], goals[robot], residual
        )
        residual -= query.expanded
        edge_tests += query.checks
        traces[robot] = query
        if query.path:
            committed[robot] = query.path
        reservations.update(committed[robot], add=True)

    paths = tuple(committed)
    safe(scene.board, paths)
    cost = dict(
        seed_tests=seed_cost,
        interval_expanded=scene.cap - residual,
        edge_tests=edge_tests,
        reservation_writes=reservations.writes,
        wall_ms=(perf_counter_ns() - started) / 1e6,
    )
    return paths, tuple(traces), controls, cost
