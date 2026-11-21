"""Independent time-layer feasibility and execution-scoring references."""
from dataclasses import asdict
from collections import Counter

from interval_planner import IntervalQueries, Reserved
from warehouse import Board, CFG, H


def caps(t, horizon=H):
    return horizon if t is None else t


def explicit_layers(board, reserved, start, goal, window, hold):
    """Enumerate every reachable (cell,time) with its earliest first hit."""
    cells = [set() for _ in range(window+1)]
    reverse = [set() for _ in cells]
    for route in reserved:
        for t,p in enumerate(route):
            cells[t].add(p)
            if t:
                reverse[t].add((p,route[t-1]))
    if start in cells[0]:
        return None, ()
    infinity=window+1
    first=0 if start==goal else infinity
    layer={start:(first,(start,))}
    for t in range(1,window+1):
        new={}
        for a,(hit,trail) in layer.items():
            moves=(a,) if hold and a==goal else (a,*board.adj[a])
            for b in moves:
                if b in cells[t] or (a,b) in reverse[t]:
                    continue
                first=t if b==goal and hit==infinity else hit
                old=new.get(b)
                if old is None or first<old[0]:
                    new[b]=(first,trail+(b,))
        layer=new
    hits=[(t,p) for t,p in layer.values() if t<infinity]
    return min(hits,default=(None,()))


def verify_witness(board, witness, reservations, start, goal, width, mode):
    assert len(witness)==width+1 and witness[0]==start and goal in witness
    arrival=witness.index(goal)
    for t,x in enumerate(witness):
        assert all(path[t]!=x for path in reservations)
        if t:
            y=witness[t-1]
            assert x==y or x in board.adj[y]
            assert all((path[t-1],path[t])!=(x,y) for path in reservations)
    if mode:
        assert all(x==goal for x in witness[arrival:])
    return arrival


def mechanisms(online_state, hold, release, free, longer):
    return dict(
        budget=online_state in ("cut","cut_window","skipped") and hold is not None,
        reservation=release is None and free is not None,
        goal_rule=release is not None and (hold is None or release<hold),
        horizon=release is None and longer is not None)


def inspect_query(board, start, goal, reservations, window, outcome):
    big=window+CFG["reference_extension"]
    padded=tuple(p+(p[-1],)*(big-window) for p in reservations)
    cases=(
        ("hold",reservations,window,True),
        ("release",reservations,window,False),
        ("free_release",(),window,False),
        ("extended_release",padded,big,False),
    )
    found={}
    for label, paths, length, hold in cases:
        opt=IntervalQueries(board,Reserved(paths,length)).solve(start,goal,hold=hold,goal_only=True)
        t,witness=explicit_layers(board,paths,start,goal,length,hold)
        r_time=None if not opt.path else verify_witness(board,opt.path,paths,start,goal,length,hold)
        if witness:
            assert verify_witness(board,witness,paths,start,goal,length,hold)==t
        found[label]=dict(interval_earliest=r_time, reference_earliest=t, reference_path=witness)
    int_times=[r["interval_earliest"] for r in found.values()]
    ref_times=[r["reference_earliest"] for r in found.values()]
    return dict(probes=found, estimate=mechanisms(outcome.state,*int_times),
                reference=mechanisms(outcome.state,*ref_times))


def controlled():
    """Hand-labeled mechanism cases from explicit geometry, caps and reservations."""
    line=Board(["......."])
    branch=Board([".......","TT.TTTT"])
    tests=[
        ("budget",line,0,4,(),6,1,("budget",)),
        ("reservation",line,0,4,((2,)*7,),6,100,("reservation",)),
        ("goal_rule",line,0,1,((2,2,1,2,2,2,2),),6,100,("goal_rule",)),
        ("horizon",line,0,5,(),3,100,("horizon",)),
        ("clear",line,0,4,(),6,100,()),
        ("budget_goal_rule",line,0,1,((2,2,1,2,2,2,2),),6,0,("budget","goal_rule")),
        ("reservation_and_horizon",branch,0,4,((2,2,2,2,2,2,9),),6,100,("reservation","horizon")),
    ]
    out=[]
    for name,board,a,b,res,w,cap,tags in tests:
        query=IntervalQueries(board,Reserved(res,w)).solve(a,b,cap)
        x=inspect_query(board,a,b,res,w,query)
        expected={k:k in tags for k in x["reference"]}
        assert x["estimate"]==expected and x["reference"]==expected,(name,x)
        out.append(dict(case=name,map=[".......","TT.TTTT"] if board is branch else ["......."],start=a,goal=b,other_paths=res,
                        window=w,cap=cap,query=asdict(query),expected=expected,**x))
    return out


def replay_events(board, initial, goals, trace, horizon=H):
    """Check movement and derive first service independently of the simulator clock."""
    assert tuple(p[0] for p in trace)==tuple(initial)
    assert all(len(p)==horizon+1 for p in trace)
    verified_events=[]
    for i,trajectory in enumerate(trace):
        event=None
        for t in range(1,horizon+1):
            a,b=trajectory[t-1:t+1]
            x,y=board.xy[a]
            xx,yy=board.xy[b]
            assert b in board.adj and abs(x-xx)+abs(y-yy)<=1
            if b==goals[i] and event is None:
                event=t
        verified_events.append(event)
    for t in range(1,horizon+1):
        endpoints=[p[t] for p in trace]
        assert len(endpoints)==len(set(endpoints))
        moves={(p[t-1],p[t]) for p in trace}
        assert all(a==b or (b,a) not in moves for a,b in moves)
    return tuple(verified_events)
