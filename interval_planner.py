"""Rolling safe-interval queries and independent joint seed construction."""
from collections import defaultdict
from dataclasses import dataclass
from functools import cache
from heapq import heappop, heappush
from itertools import count
from time import perf_counter_ns

from warehouse import W, priority


def safe(board, paths):
    for t in range(len(paths[0])):
        cells={p[t] for p in paths}
        assert len(cells)==len(paths) and all(v in board.adj for v in cells)
        if t:
            edges={(p[t-1],p[t]) for p in paths}
            assert all(a==b or b in board.adj[a] and (b,a) not in edges for a,b in edges)
    return True


def seed_paths(scene,state,goals):
    board = scene.board
    positions = state.cells
    n = len(positions)
    ds = tuple(board.distances(g) for g in goals)
    result = [[p] for p in positions]
    work = 0
    for layer in range(W):
        shift = (state.t+layer)%n
        order = sorted(range(n),key=lambda i:(state.issued[i],(i-shift)%n))
        occupant = {p:i for i,p in enumerate(positions)}
        booked, selected = set(), {}
        def reserve(i):
            nonlocal work
            u=positions[i]
            offset=(state.t+layer+i) % len(board.xy)
            for to in sorted((*board.adj[u],u),key=lambda v:(ds[i][v], (v-offset)%len(board.xy))):
                work+=1
                j=occupant.get(to)
                if to in booked or j is not None and i!=j and selected.get(j)==u:
                    continue
                selected[i]=to
                booked.add(to)
                if j is None or j in selected or reserve(j):
                    return True
                booked.remove(to)
                del selected[i]
            return False
        for i in order:
            if i not in selected:
                assert reserve(i)
        assert len(selected)==n
        positions=tuple(selected[i] for i in range(n))
        for i,p in enumerate(positions):
            result[i].append(p)
    return tuple(tuple(p) for p in result), work


class Reserved:
    def __init__(self, paths, window):
        self.w=window
        self.cell=defaultdict(set)
        self.edge=set()
        self.writes=0
        for p in paths:
            self.update(p, True)

    def update(self, path, add):
        for t,c in enumerate(path):
            if add:
                self.cell[c].add(t)
                if t:
                    self.edge.add((c,path[t-1],t))
            else:
                times=self.cell[c]
                times.remove(t)
                if not times:
                    del self.cell[c]
                if t:
                    self.edge.remove((c,path[t-1],t))
            self.writes+=1+bool(t)


@dataclass(frozen=True)
class Query:
    state: str
    expanded: int
    checks: int
    path: tuple = ()

    @property
    def arrival_state(self):
        return self.state == "goal"


class IntervalQueries:
    def __init__(self, board, reserved):
        self.board=board
        self.book=reserved
        self.w=reserved.w
        self.checks=0
        self.intervals=cache(self._intervals)

    def _intervals(self, cell):
        lo=0
        gaps=[]
        for blocked in sorted(self.book.cell.get(cell,())):
            if blocked>lo:
                gaps.append((lo,blocked-1))
            lo=blocked+1
        if lo<=self.w:
            gaps.append((lo,self.w))
        return tuple(gaps)

    def from_state(self, state, at):
        v, _, end = state
        for u in self.board.adj[v]:
            for low, high in self.intervals(u):
                self.checks += 1
                arrive=max(at+1,low)
                limit=min(end+1,high)
                while arrive<=limit and (v,u,arrive) in self.book.edge:
                    arrive+=1
                    self.checks+=1
                if arrive<=limit:
                    yield (u,low,high),arrive

    @staticmethod
    def build(previous, node, finish):
        segments=[(node[0][0],node[1])]
        while previous[node] is not None:
            node=previous[node]
            segments.append((node[0][0],node[1]))
        current,start=segments[-1]
        timeline=[current]
        for pos,t in reversed(segments[:-1]):
            timeline.extend([current]*(t-start-1))
            timeline.append(pos)
            current,start=pos,t
        return tuple(timeline+[current]*(finish-start))

    def suffix(self, start, t):
        """Construct any fixed-reservation continuation to the end of the window."""
        q=[(start,t)]
        witness={(start,t):None}
        times={start:t}
        for z,at in q:
            if times[z]!=at:
                continue
            if z[2]==self.w:
                return self.build(witness,(z,at),self.w)
            for next_node,nt in self.from_state(z,at):
                if nt<times.get(next_node,self.w+1):
                    times[next_node]=nt
                    witness[next_node,nt]=(z,at)
                    q.append((next_node,nt))
        return ()

    def solve(self, src, goal, cap=None, hold=True, goal_only=False):
        if cap==0:
            return Query("skipped",0,0)
        d=self.board.distances(goal)
        first=next(((src,a,b) for a,b in self.intervals(src) if a==0),None)
        if first is None:
            return Query("no_window",0,0)
        serial=count()
        heap=[(d[src],d[src],next(serial),0,first)]
        score={first:0}
        prev={(first,0):None}
        best, best_key=None, (self.w+10000,self.w+10000,self.w+10000)
        expanded=0
        result="exhausted"
        while heap:
            _,_,_,t,z=heappop(heap)
            if score[z]!=t:
                continue
            v,_,end=z
            if v==goal:
                if end==self.w:
                    return Query("goal",expanded,self.checks,self.build(prev,(z,t),self.w))
                if not hold:
                    continuation=self.suffix(z,t)
                    if continuation:
                        lead=self.build(prev,(z,t),t)
                        return Query("goal",expanded,self.checks,lead+continuation[1:])
            if not goal_only and end==self.w and (d[v],t,v)<best_key:
                best,best_key=(z,t),(d[v],t,v)
                if d[src]>self.w and d[v]==d[src]-self.w:
                    return Query("window",expanded,self.checks,self.build(prev,best,self.w))
            if t==self.w:
                continue
            if cap is not None and expanded==cap:
                result="cut"
                break
            expanded+=1
            for nxt,nt in self.from_state(z,t):
                u,_,ue=nxt
                if hold and u==goal and ue<self.w:
                    continue
                if nt<score.get(nxt,self.w+1):
                    score[nxt]=nt
                    prev[nxt,nt]=(z,t)
                    heappush(heap,(nt+d[u],d[u],next(serial),nt,nxt))
        if best is not None:
            return Query("cut_window" if result=="cut" else "window",expanded,self.checks,self.build(prev,best,self.w))
        return Query(result,expanded,self.checks)


def plan(scene,state,rule="density",order=None,prepared=None,focus=None):
    t0=perf_counter_ns()
    goals=scene.goals(state)
    if order is None:
        order=priority(scene,state,rule)
    orig, seed_cost=seed_paths(scene,state,goals) if prepared is None else prepared
    table=Reserved(orig,W)
    committed=list(orig)
    residual=scene.cap
    traces=[None]*len(orig)
    controls=None
    n_moves=0
    for i in order:
        table.update(committed[i],False)
        if i==focus:
            controls=dict(reservations=tuple(p for j,p in enumerate(committed) if j!=i),
                          allowance=residual, seed=orig[i])
        result=IntervalQueries(scene.board,table).solve(state.cells[i],goals[i],residual)
        residual-=result.expanded
        traces[i]=result
        if result.path:
            committed[i]=result.path
        n_moves+=result.checks
        table.update(committed[i],True)
    paths=tuple(committed)
    safe(scene.board,paths)
    cost=dict(seed_tests=seed_cost,interval_expanded=scene.cap-residual,edge_tests=n_moves,
              reservation_writes=table.writes,wall_ms=(perf_counter_ns()-t0)/1e6)
    return paths,tuple(traces),controls,cost
