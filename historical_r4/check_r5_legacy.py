"""Checks of R4 in the original solver, with one goal-rule intervention."""
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from heapq import heappop, heappush
from itertools import count
import argparse
import json
from pathlib import Path

from analyze import read
from diagnose import follow
from protocol import EXEC, LOOK, W
from simulator import (Case, Reservations, Search, State, advance, common_seed, goal_at,
                       order_for, paths_valid, replanning, scenario)
from small_cases import Tiny, grid


def release_variant(grid, reservations, start, goal, cap):
    """Original weighted queue with early goal arrival allowed only with a safe suffix."""
    if cap==0:
        return Search("not_started",0)
    d=grid.distance[goal]
    unique=count()
    fringe=[(2*d[start],d[start],next(unique),0,start)]
    previous={(0,start):None}
    expanded=0
    failed=set()
    exhausted_budget=False
    def legal(v,u,t):
        return u not in reservations.cells[t] and (v,u) not in reservations.edges[t]
    def append_suffix(t,v):
        nonlocal expanded,exhausted_budget
        if t==W:
            return (v,)
        if (t,v) in failed:
            return ()
        if expanded==cap:
            exhausted_budget=True
            return ()
        expanded+=1
        for u in (v,)+tuple(u for u in grid.moves[v] if u!=v):
            if legal(v,u,t+1):
                tail=append_suffix(t+1,u)
                if tail:
                    return (v,)+tail
                if exhausted_budget:
                    return ()
        failed.add((t,v))
        return ()
    while fringe:
        _,_,_,t,v=heappop(fringe)
        tail=()
        if v==goal:
            if all(goal not in reservations.cells[k] for k in range(t+1,W+1)):
                tail=(goal,)*(W-t+1)
            else:
                tail=append_suffix(t,v)
        if t==W or tail:
            x=(t,v)
            head=[]
            while x is not None:
                head.append(x[1])
                x=previous[x]
            path=tuple(reversed(head))+tail[1:]
            assert reservations.accepts(path)
            return Search("goal" if v==goal else "window",expanded,path)
        if exhausted_budget or expanded==cap:
            return Search("budget",expanded)
        expanded+=1
        for u in grid.moves[v]:
            if legal(v,u,t+1) and (t+1,u) not in previous:
                previous[t+1,u]=(t,v)
                h=d[u]
                heappush(fringe,(t+1+2*h,h,next(unique),t+1,u))
    return Search("exhausted",expanded)


def r4_case_b():
    archived=json.loads(Path("data/results.json").read_text())["examples"]["B"]
    case,state=scenario(archived["layout"],archived["n"],archived["multiplier"],archived["seed"])
    while state.time<archived["time"]:
        order=order_for(case,state,archived["source"])
        state=advance(case,state,replanning(case,state,order)[0])
    seed, _=common_seed(case,state)
    f=archived["focus"]
    g=goal_at(case,state,f)
    outcomes=[]
    for arm, field in (("baseline","order"),("treatment","promoted")):
        order=tuple(archived[field])
        paths,traces,stage=replanning(case,state,order,capture=True,seed_paths=seed)
        local,available=stage[f]
        for rule in ("hold", "release"):
            if rule=="hold":
                committed,readouts=paths,traces
            else:
                new=release_variant(case.grid,Reservations(local),state.pos[f],g,available)
                committed,readouts,changed=replanning(case,state,order,capture=True,seed_paths=seed,force=(f,new))
                assert changed[f]==stage[f]
                assert readouts[f]==new
            result,_=follow(case,state,archived["source"],committed,readouts)
            past=result["path"][f]
            assert next((t for t,v in enumerate(past) if v==g),None)==result["task"][f]
            if rule=="hold":
                assert result["task"]==archived[arm]["task"]
                assert result["path"]==archived[arm]["path"]
            outcomes.append(dict(arm=arm,rule=rule,focus=f,allowed=available,goal=g,
                                 reservations=local,seed=seed[f],query=asdict(readouts[f]),
                                 candidate_equals_seed=readouts[f].path==seed[f],
                                 focal_first=committed[f][:EXEC+1],candidate=committed,
                                 focal_finish=result["task"][f],every_finish=result["task"],trajectories=result["path"]))
    return {"case":{k:archived[k] for k in ("layout","n","multiplier","time","source","seed","focus")},
            "query_goal_occupancy_t2":outcomes[0]["goal"] in {p[2] for p in outcomes[0]["reservations"]},
            "runs":outcomes}


def r4_table_case(graph,starts,goals,order,horizon,cap):
    tiny=Tiny(graph)
    case=Case(tiny,tuple(zip(starts,goals)),tuple((tiny.distance[g][s],) for s,g in zip(starts,goals)),cap)
    state=State(0,tuple((s,)*(horizon+1) for s in starts),(0,0),(0,0))
    orig,_=common_seed(case,state,horizon)
    p,trace,_=replanning(case,state,order,seed_paths=orig,horizon=horizon)
    assert paths_valid(tiny,p)
    return dict(window=horizon,order=order,budget=cap,seed=orig,committed=p,
                executed=[v[:EXEC+1] for v in p],trace=[asdict(t) for t in trace],
                fallback_count=sum(not t.path for t in trace),
                hits_in_committed_window=[
                    next((i for i,x in enumerate(path) if x==g),None) for g,path in zip(goals,p)],
                hits_in_executed_prefix=[
                    next((i for i,x in enumerate(path[:EXEC+1]) if x==g),None) for g,path in zip(goals,p)])


def r4_small():
    raw=json.loads(Path("data/small_cases.json").read_text())
    new={}
    for key in ("S0","S1","S2","S3"):
        c=raw[key]
        graph=grid(tuple(p) for p in c["cells"])
        start,goal=[tuple(tuple(v) for v in c[k]) for k in ("starts","goals")]
        specs={
            "S0":[((0,1),8,20)],
            "S1":[((0,1),4,32),((0,1),5,32)],
            "S2":[((0,1),8,20),((1,0),8,3),((1,0),8,20)],
            "S3":[((0,1),8,20)]}[key]
        rows=[r4_table_case(graph,start,goal,*k) for k in specs]
        new[key]=dict(archived=c,algorithm1=rows)
    return new


def verified_source(job):
    key,qs=job
    m,n,b,seed,policy=key
    case,state=scenario(m,n,b,seed)
    end=max(v["time"]+LOOK for v in qs)
    original={}
    while state.time<end:
        order=order_for(case,state,policy)
        paths,tr,_=replanning(case,state,order)
        original[state.time]=(paths,tr,state)
        state=advance(case,state,paths)
    counts=0
    for pair in qs:
        t=pair["time"]
        res=pair["baseline"]
        orig,trace,st=original[t]
        assert [goal_at(case,st,i) for i in range(n)]==pair["goals"]
        assert json.loads(json.dumps(orig))==res["window"]
        assert json.loads(json.dumps([asdict(x) for x in trace]))==res["solver"]
        for dt in range(1,LOOK+1):
            tick=t+(dt-1)//EXEC*EXEC
            phase=(dt-1)%EXEC+1
            assert [p[dt] for p in res["path"]]==[p[phase] for p in original[tick][0]]
        counts+=1
    return counts


def check_rows():
    data=[]
    for name,files in (
        ("overdue","pairs.jsonl.gz"),("exploratory","gate_pairs.jsonl.gz"),
        ("matched","matched_pairs.jsonl.gz"),("new_layout","holdout_pairs.jsonl.gz")):
        rows=read(files)
        splits=("recursive","serial") if name=="new_layout" else (None,)
        for mode in splits:
            group=[r for r in rows if r.get("constructor")==mode] if mode else rows
            for k in ("baseline","treatment"):
                f=lambda x:x["focus"]
                data.append(dict(sample=name,constructor=mode,arm=k,n=len(group),
                    focal_no_candidate=sum(x[k]["seed_retained"][f(x)] for x in group),
                    focal_candidate_equals_seed=sum(x[k]["solver"][f(x)]["path"]==x["seed_paths"][f(x)] for x in group),
                    focal_committed_equals_seed=sum(x[k]["window"][f(x)]==x["seed_paths"][f(x)] for x in group),
                    focal_prefix_equals_seed=sum(x[k]["first"][f(x)]==x["seed_paths"][f(x)][:EXEC+1] for x in group),
                    focal_finished=sum(x[k]["task"][f(x)] is not None for x in group),
                    focal_finish_exact32=sum(x[k]["task"][f(x)]==LOOK for x in group)))
    return data


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    histories=[("overdue",read("pairs.jsonl.gz")),("exploratory",read("gate_pairs.jsonl.gz"))]
    results={}
    with ProcessPoolExecutor(max_workers=6) as pool:
        for lab,rows in histories:
            groups=defaultdict(list)
            for q in rows:
                k=tuple(q[x] for x in ("layout","n","multiplier","seed","source"))
                groups[k].append(q)
            results[lab]=sum(pool.map(verified_source,groups.items()))
            assert results[lab]==len(rows)
    result=dict(full_replay=results,case_b=r4_case_b(),small=r4_small(),candidate_status=check_rows())
    (a.out/"r5_historical_checks.json").write_text(json.dumps(result,indent=2))
    print("verified every historical original action:",results)
    print("case B:",[(x["arm"],x["rule"],x["allowed"],x["query"]["expanded"],x["focal_finish"])
          for x in result["case_b"]["runs"]])
    for k,x in result["small"].items():
        print(k,[(r["order"],r["window"],r["budget"],[q["status"] for q in r["trace"]],
                  r["hits_in_committed_window"],r["hits_in_executed_prefix"]) for r in x["algorithm1"]])


if __name__=="__main__":
    main()
