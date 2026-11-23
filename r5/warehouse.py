"""Benchmark graphs and continuously issued, coupled navigation tasks."""
from array import array
from collections import deque
from dataclasses import dataclass
from functools import cache
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "protocol_r5.json").read_text())
W = CFG["window"]
E = CFG["executed_per_round"]
H = CFG["followup"]


class Board:
    """
    Builds a grid from map rows, recording traversable cells, valid neighbors, and positions within two Manhattan steps.
    """
    def __init__(self, rows):
        self.height = len(rows)
        self.width = len(rows[0])
        self.xy = tuple((x, y) for y in range(self.height) for x in range(self.width))
        self.cells = tuple(v for v, (x, y) in enumerate(self.xy) if rows[y][x] == ".")
        q = set(self.cells)
        self.adj = {
            v: tuple(u for u in (v-self.width, v-1, v+1, v+self.width)
                    if u in q and self.l1(v, u) == 1)
            for v in self.cells
        }
        self.nearby = {v: tuple(yy*self.width+xx for xx in range(max(0,x-2),min(self.width,x+3))
                                for yy in range(max(0,y-2),min(self.height,y+3))
                                if (xx != x or yy != y) and abs(xx-x)+abs(yy-y) <= 2)
                    for v in self.cells for x,y in (self.xy[v],)}

    def l1(self, a, b):#Computes the Manhattan distance
        x, y = self.xy[a]
        xx, yy = self.xy[b]
        return abs(xx-x)+abs(yy-y)

    @cache
    def distances(self, goal):# define BFS
        d = array("h", [-1])*len(self.xy)
        d[goal] = 0
        fringe = deque([goal])
        while fringe:
            v = fringe.popleft()
            for u in self.adj[v]:
                if d[u] == -1:
                    d[u] = d[v]+1
                    fringe.append(u)
        return d

    def greedy_edges(self, pos, goal, steps):
        d = self.distances(goal)
        edges = []
        for _ in range(steps):
            if pos == goal:
                break
            to = next((u for u in self.adj[pos] if d[u]+1 == d[pos]), None)
            if to is None:
                break
            edges.append((pos, to))
            pos = to
        return tuple(edges)


@cache
def load_map(name):
    desc = CFG["maps"][name]
    data = (ROOT / "benchmarks" / desc["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == desc["sha256"]
    header = data.decode("ascii").splitlines()
    rows = header[4:]
    assert len(rows) == int(header[1].split()[-1])
    assert all(len(row) == int(header[2].split()[-1]) for row in rows)
    board = Board(rows)
    mid, center = board.height//2, board.width//2
    wide = [y for y,row in enumerate(rows) if row.count(".") >= .8*board.width]
    pairs = []
    for sign in (-1,1):
        ys = sorted((y for y in wide if (y-mid)*sign > 2),key=lambda y:(abs(y-(mid+9*sign)),y))[:2]
        pool = tuple(y*board.width+x for y in sorted(ys) for x in range(center-11,center+12))
        assert all(v in board.adj for v in pool)
        pairs.append(pool)
    board.pools = tuple(pairs)
    return board


@dataclass(frozen=True)
class State:
    t: int
    cells: tuple
    jobs: tuple
    issued: tuple
    previous: tuple


@dataclass(frozen=True)
class Scene:
    board: Board
    targets: tuple
    lengths: tuple
    cap: int

    def goals(self, state):
        return tuple(self.targets[i][j+1] for i,j in enumerate(state.jobs))

"""
Uses a random seed to generate reproducible starts, goal sequences, and initial shortest-path lengths for n robots. 
Sets the per-round search budget to multiplier × n and returns the scene and initial state.
"""
def scenario(name, n, multiplier, seed):
    board = load_map(name)
    rng = random.Random(f"r5:{name}:{n}:{seed}")
    u,l = board.pools
    starts = tuple(rng.sample(u+l,n))
    results, lengths = [], []
    pools = [set(u),set(l)]
    for p in starts:
        r = random.Random(rng.getrandbits(64))
        sequence = [p]
        ds = []
        for _ in range(CFG["duration"]+H+1):
            prev = sequence[-1]
            side = int(prev in pools[1]) ^ (r.random() < .8)
            next_goal = r.choice([v for v in board.pools[side] if v != prev])
            sequence.append(next_goal)
            ds.append(board.distances(next_goal)[prev])
        results.append(tuple(sequence))
        lengths.append(tuple(ds))
    initial = State(0,starts,(0,)*n,(0,)*n,starts)
    return Scene(board,tuple(results),tuple(lengths),multiplier*n),initial

"""
Computes robot i’s relative task age by dividing elapsed steps 
since issue by the task’s initial shortest-path length.
"""
def age(scene, state, i):
    return (state.t-state.issued[i])/scene.lengths[i][state.jobs[i]]


def priority(scene, state, rule):#Returns the robot planning order
    cells = state.cells
    goals = scene.goals(state)
    density = {p:sum(v in occupied for v in scene.board.nearby[p])
            for occupied in [set(cells)] for p in cells}
    if rule == "distance":
        key = lambda i: (-scene.board.distances(goals[i])[cells[i]], i)
    elif rule == "dual":
        key = lambda i: (0,-age(scene,state,i),i) if age(scene,state,i)>2.5 else (1,-density[cells[i]],i)
    elif rule == "density":
        key = lambda i: (-density[cells[i]],i)
    else:
        raise ValueError(rule)
    return tuple(sorted(range(len(cells)),key=key))

"""
Executes the first E steps of the planned paths, currently two steps.
Checks for arrivals at each step, advances completed tasks to their next goals,
optionally reports events through observer, and returns the updated state.
"""
def execute(scene, state, paths, observer=None):
    jobs, issued = list(state.jobs), list(state.issued)
    for k in range(1,E+1):
        t = state.t+k
        for i,p in enumerate(paths):
            j = jobs[i]
            arrived = p[k] == scene.targets[i][j+1]
            if observer:
                observer(t,i,j,issued[i],arrived)
            if arrived:
                jobs[i] = j+1
                issued[i] = t
    return State(state.t+E,tuple(p[E] for p in paths),tuple(jobs),tuple(issued),
                tuple(p[E-1] for p in paths))
