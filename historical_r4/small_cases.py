"""Exact fixed-goal references and matching short-window executions."""
from collections import deque
from itertools import product

def grid(cells):
    cells = set(cells)
    return {v: tuple(sorted(w for w in cells if abs(v[0]-w[0])+abs(v[1]-w[1]) == 1))
            for v in sorted(cells)}

def bfs(start, neighbors, goal, cap=None, depth=None):
    q = deque([start])
    prev, levels = {start: None}, {start: 0}
    expanded = 0
    while q:
        s = q.popleft()
        if goal(s):
            path = []
            while s is not None:
                path.append(s)
                s = prev[s]
            return 'goal', path[::-1], expanded
        if depth is not None and levels[s] == depth:
            continue
        if cap is not None and expanded == cap:
            return 'budget', [], expanded
        expanded += 1
        for nxt in neighbors(s):
            if nxt not in prev:
                prev[nxt] = s
                levels[nxt] = levels[s] + 1
                q.append(nxt)
    return 'exhausted', [], expanded

def joint(graph, starts, goals, budget=None, width=None):
    def next_steps(s):
        a,b=s
        aa = (a,) if a == goals[0] else (a,)+graph[a]
        bb = (b,) if b == goals[1] else (b,)+graph[b]
        for x,y in product(aa,bb):
            if x!=y and (x,y)!=(b,a):
                yield x,y
    return bfs(starts,next_steps,lambda s:s==goals,cap=budget,depth=width)

def distance(graph, goal):
    d = {goal:0}
    q = deque([goal])
    while q:
        s = q.popleft()
        for n in graph[s]:
            if n not in d:
                q.append(n)
                d[n] = d[s]+1
    return d

def high_shortest(graph,start,target):
    d=distance(graph,target)
    def rec(v):
        if v==target:
            yield [v]
        else:
            for n in graph[v]:
                if d[n]==d[v]-1:
                    for p in rec(n):
                        yield [v]+p
    return list(rec(start)) if start in d else []

def constrained_low(graph,start,target,high,cap=None):
    final=len(high)-1
    def next_steps(s):
        v,t = s
        nt=min(t+1,final)
        if v==target:
            candidates=(v,)
        else:
            candidates=graph[v]+(v,)
        for w in candidates:
            if w!=high[nt] and (v,w)!=(high[nt],high[t]):
                yield w,nt
    def reached(s):
        v,t=s
        return v==target and target not in high[t:]
    return bfs((start,0),next_steps,reached,cap=cap)

def greedy(graph,starts,goals,order=(0,1),budget=None):
    hi,lo=order
    status,p,used=bfs(starts[hi],lambda s:graph[s],lambda s:s==goals[hi],cap=budget)
    if status!='goal':
        return 'high '+status,p,[],used,False
    box=None if budget is None else budget-used
    status,q,n=constrained_low(graph,starts[lo],goals[lo],p,box)
    return 'low '+status,p,q,used+n,True

def validate_joint(graph,path):
    for (a,b),(x,y) in zip(path,path[1:]):
        assert x in (a,)+graph[a] and y in (b,)+graph[b]
        assert x!=y and (x,y)!=(b,a)
    return True


def release_at_goal(graph, starts, targets):
    def neighbors(past):
        (a, b), seen = past
        for x, y in product((a,)+graph[a], (b,)+graph[b]):
            if x != y and (x, y) != (b, a):
                yield (x, y), seen | (x == targets[0]) | (2*(y == targets[1]))
    mask = (starts[0] == targets[0]) | (2*(starts[1] == targets[1]))
    return bfs((starts, mask), neighbors, lambda s: s[1] == 3)


class Tiny:
    def __init__(self, g):
        self.moves = {v: g[v]+(v,) for v in g}
        self.distance = {v: distance(g, v) for v in g}


def online_example(graph, starts, goals, window, budget=32):
    from dataclasses import asdict
    from simulator import Case, State, common_seed, paths_valid, replanning

    tiny = Tiny(graph)
    c = Case(tiny, tuple(zip(starts, goals)),
             tuple((tiny.distance[g][s],) for s, g in zip(starts, goals)), budget)
    state = State(0, tuple((s,)*(window+1) for s in starts), (0, 0), (0, 0))
    seed_path, work = common_seed(c, state, window)
    p, r, _ = replanning(c, state, (0, 1), seed_paths=seed_path, horizon=window)
    assert paths_valid(tiny, p)
    return dict(window=window, budget=budget, seed=seed_path, seed_work=work,
                solver=[asdict(x) for x in r], planner_submitted=any(x.path for x in r),
                budget_cut=any(x.status in ("budget","not_started") for x in r),
                retained_seed=[not x.path for x in r],
                fallback=not any(x.path for x in r), window_path=p,
                executed=[x[:3] for x in p])


def joint_record(graph, starts, goals, horizon=None):
    status,p,n = joint(graph,starts,goals,width=horizon)
    assert validate_joint(graph,p)
    return dict(status=status, expansions=n, path=p, horizon=horizon)


def order_record(graph, starts, goals, order=(0,1), budget=20):
    status,phigh,qlow,expanded,_ = greedy(graph,starts,goals,order,budget)
    plow = [x for x,t in qlow]
    joint_path = None
    if status == "low goal":
        horizon = max(len(phigh),len(plow))
        phigh = phigh + [phigh[-1]]*(horizon-len(phigh))
        plow = plow + [plow[-1]]*(horizon-len(plow))
        joint_path = list(zip(phigh,plow)) if order==(0,1) else list(zip(plow,phigh))
        assert validate_joint(graph,joint_path)
    return dict(status=status, expansions=expanded, budget=budget, order=order,
                high_plan=phigh, low_plan=plow, published=bool(joint_path),
                candidate=joint_path, executed=joint_path if joint_path else [starts]*3,
                fallback=None if joint_path else "team waits")


def main():
    import json
    from pathlib import Path
    line = grid((x,0) for x in range(5))
    refuge = grid(list(line)+[(2,1)])
    starts, goals = ((1,0),(3,0)), ((4,0),(0,0))
    s0 = dict(cells=list(line),starts=starts,goals=goals,exact=joint_record(line,starts,goals),
              legacy=order_record(line,starts,goals))
    s1 = dict(cells=list(refuge),starts=starts,goals=goals,by_window=[
        joint_record(refuge,starts,goals,4), joint_record(refuge,starts,goals,5)],
              online=[online_example(refuge,starts,goals,w) for w in (4,5)])
    witness = s1["by_window"][1]["path"][:5]
    assert validate_joint(refuge,witness)
    s1["w4_reference_witness"] = witness
    g = grid(product(range(2), range(3)))
    starts, goals = ((1,0),(0,0)), ((0,2),(0,1))
    hi = [(1,0),(1,1),(1,2),(0,2)]
    alt_status,qlow,alt_n = constrained_low(g,starts[1],goals[1],hi)
    lo = [x for x,t in qlow]
    alt_path = list(zip(hi,lo+[lo[-1]]*(len(hi)-len(lo))))
    assert validate_joint(g,alt_path)
    s2 = dict(cells=list(g),starts=starts,goals=goals,exact=joint_record(g,starts,goals),
              legacy=[order_record(g,starts,goals,(0,1),20),order_record(g,starts,goals,(1,0),3),
                      order_record(g,starts,goals,(1,0),20)],
              equal_path=dict(status=alt_status,low_expanded=alt_n,plan=alt_path))
    a,b,c,r = (0,0),(1,0),(2,0),(1,1)
    g = grid((a,b,c,r))
    starts, goals = (a,c),(b,a)
    flag,p,num = release_at_goal(g,starts,goals)
    assert flag == "goal" and validate_joint(g,[pos for pos,_ in p])
    s3 = dict(cells=list(g),starts=starts,goals=goals,stay=joint_record(g,starts,goals),
              release=dict(status=flag,expansions=num,path_with_arrival_flags=p))
    data=dict(config=dict(exact_coordinate_order="lexicographic", joint_wait="before moves",
                          single_dynamic_wait="after moves", rollout_execute=2),
              S0=s0,S1=s1,S2=s2,S3=s3)
    out = Path("data/small_cases.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name,s in [("S0",s0["exact"]),("S1",s1["by_window"]),("S2",s2["exact"]),("S3",s3)]:
        print(name,s)
    for s in s1["online"]:
        print("S1 online",s)


if __name__ == "__main__":
    main()

