"""Public-layout rolling experiments, paired diagnostics and serial timing."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from itertools import product
import gzip
import json
from pathlib import Path
import random
from statistics import median

from interval_planner import plan, seed_paths
from reference import caps, controlled, inspect_query, replay_events
from warehouse import CFG, E, H, W, age, priority, scenario

OUT=Path(__file__).resolve().parent/"data_r5"


def quantile(seq,k):
    ordered=sorted(seq)
    index=(len(ordered)-1)*k
    shift=int(index)
    return ordered[shift]+(index-shift)*(ordered[min(shift+1,len(ordered)-1)]-ordered[shift])


def choices(scene,state,order):
    goals=scene.goals(state)
    board=scene.board
    focals=[i for i in order[1:]
            if state.t-state.issued[i]>=2
            and board.distances(goals[i])[state.cells[i]]<=CFG["max_focal_static_distance"]
            and board.distances(goals[i])[state.cells[i]]>=board.distances(goals[i])[state.previous[i]]]
    if not focals:
        return None
    f=min(focals,key=lambda i:(-age(scene,state,i),i))
    steps=CFG["route_intent_lookahead"]
    intent=[board.greedy_edges(p,g,steps) for p,g in zip(state.cells,goals)]
    limit=CFG["max_opposed_entry_offset"]
    counterpart=[]
    for i,route in enumerate(intent):
        if i==f:
            continue
        for t,(u,v) in enumerate(intent[f],1):
            for k,edge in enumerate(route,1):
                if edge==(v,u) and abs(t-k)<=limit:
                    counterpart.append((i,u,v,t,k))
    return f, counterpart


def follow(scene,state,first,rule="density"):
    traces=[[p] for p in state.cells]
    initial_jobs=state.jobs
    finishes=[None]*len(traces)
    start=state.t
    def do(t,i,task,issue,arrive):
        if arrive and task==initial_jobs[i]:
            finishes[i]=t-start
    current=first
    while state.t<start+H:
        for p,s in zip(current,traces):
            s.extend(p[1:E+1])
        from warehouse import execute
        state=execute(scene,state,current,observer=do)
        if state.t<start+H:
            current=plan(scene,state,rule)[0]
    return tuple(tuple(s) for s in traces),tuple(finishes)


def direction(board,p,g):
    d=board.distances(g)
    x,y=board.xy[p[0]]
    u,v=board.xy[p[1]]
    diff=d[p[0]]-d[p[1]]
    return dict(heading=(u-x,v-y),relative=(diff>0)-(diff<0),progress_two=d[p[0]]-d[p[E]])


def comparison(scene,state,order,focus,matches,records,key):
    f=focus
    board=scene.board
    goals=scene.goals(state)
    prepared=seed_paths(scene,state,goals)
    promoted=(f,)+tuple(i for i in order if i!=f)
    arms={}
    for label,o in (("baseline",order),("promoted",promoted)):
        candidate,traces,local,_=plan(scene,state,order=o,prepared=prepared,focus=f)
        log, arrival=follow(scene,state,candidate)
        independently=replay_events(board,state.cells,goals,log)
        assert arrival==independently
        if label=="baseline":
            for dt in range(1,H+1):
                time=state.t+(dt-1)//E*E
                phase=(dt-1)%E+1
                assert [p[dt] for p in log]==[p[phase] for p in records[time]]
        probe=inspect_query(board,state.cells[f],goals[f],local["reservations"],W,traces[f])
        focal=asdict(traces[f])
        arms[label]=dict(ordered=o,commit=candidate,first_focal=candidate[f][:E+1],focal=local,
                         focal_query=focal, direction=direction(board,candidate[f],goals[f]),
                         observed=log,finish=arrival,controls=probe,
                         fallback=focal["path"]==(),candidate_same_seed=focal["path"]==local["seed"],
                         committed_same_seed=candidate[f]==local["seed"],
                         executed_same_seed=candidate[f][:E+1]==local["seed"][:E+1])
    original,treat=(arms[k] for k in ("baseline","promoted"))
    delta=tuple(caps(b)-caps(a) for a,b in zip(original["finish"],treat["finish"]))
    early=delta[f]<0
    others=[i for i,x in enumerate(delta) if i!=f and x>0]
    changed=original["first_focal"]!=treat["first_focal"]
    gained=original["focal_query"]["state"]=="skipped" and treat["focal_query"]["state"]!="skipped"
    direction_arms=[dict(kind=k,rank=v["ordered"].index(f)+1,order=v["ordered"],**v["direction"])
                    for k,v in arms.items()]
    rng=random.Random(f"order:{key}:{state.t}:{f}")
    for _ in range(CFG["direction_comparator_random_orders"]):
        shuffled=tuple(rng.sample(order,len(order)))
        p,_,_,_=plan(scene,state,order=shuffled,prepared=prepared)
        direction_arms.append(dict(kind="random",rank=shuffled.index(f)+1,order=shuffled,
                                   **direction(board,p[f],goals[f])))
    return dict(time=state.t,focus=f,rank=order.index(f)+1,issued=state.issued,jobs=state.jobs,
                positions=state.cells,goals=goals,match=bool(matches),matches=matches,
                start_remaining=board.distances(goals[f])[state.cells[f]],
                delta=delta,earlier=early,others_later=others,event1=gained and not changed,
                event2=changed and not early,event3=early and bool(others),
                proposed_direction=treat["direction"]["relative"]>original["direction"]["relative"],
                proposed_distance=treat["direction"]["progress_two"]>original["direction"]["progress_two"],
                order_comparison=direction_arms,**arms)


def generate(spec, diagnostics=False, policy="density", timing=False):
    from warehouse import execute
    m,n,b,seed=spec
    scene,state=scenario(*spec)
    meta=dict(layout=m,n=n,multiplier=b,cap=b*n,seed=seed,policy=policy)
    duration=CFG["duration"]
    warm=CFG["warmup"]
    tasks=[None]*n
    total_completed, not_timely = 0,0
    records={}
    by_label={False:[], True:[]}
    ticks=[]
    costs=[]
    def visit(t,i,j,issued,arrived):
        nonlocal total_completed, not_timely
        if j==0 and arrived:
            tasks[i]=t
        if t>warm:
            total_completed+=arrived
            not_timely+=t-issued > 3*scene.lengths[i][j]
    while state.t<duration:
        p,_,_,cost=plan(scene,state,rule=policy)
        if timing and state.t>=warm:
            costs.append(cost)
        if diagnostics:
            records[state.t]=p
            if state.t in range(CFG["first_landmark"],CFG["last_landmark"]+1,CFG["landmark_stride"]):
                order=priority(scene,state,policy)
                chosen=choices(scene,state,order)
                if chosen:
                    f,matches=chosen
                    by_label[bool(matches)].append((state,order,f,matches))
                    ticks.append(dict(**meta,time=state.t,focus=f,rank=order.index(f)+1,
                                      shared=bool(matches),matches=matches))
                else:
                    ticks.append(dict(**meta,time=state.t,focus=None,rank=None,shared=None,matches=[]))
        state=execute(scene,state,p,observer=visit)
    rate=total_completed/(duration-warm)*100
    observed_age=not_timely/(n*(duration-warm))
    result=dict(**meta,initiated=list(state.jobs),completions=total_completed,rate=rate,overdue=observed_age,
                job0_first=tasks,
                job0_initial_length=[seq[0] for seq in scene.lengths])
    if timing:
        samples={name:[k[name] for k in costs] for name in costs[0]}
        result["timing"]={name:[median(a),quantile(a,.95)] for name,a in samples.items()}
    if not diagnostics:
        return result
    r=random.Random(f"sample:{spec}")
    selected=[]
    whileby={}
    for label,candidates in by_label.items():
        chosen=r.sample(candidates,min(CFG["max_pairs_per_scene_and_resource_label"],len(candidates)))
        whileby[str(label)]=dict(eligible=len(candidates),sampled=len(chosen))
        for s,o,f,x in sorted(chosen,key=lambda a:a[0].t):
            selected.append(dict(**meta,**comparison(scene,s,o,f,x,records,spec),
                                 inclusion=len(chosen)/len(candidates)))
    result["selection"]=whileby
    return result,selected,ticks


def diagnostic(spec):
    return generate(spec,diagnostics=True)


def policy_test(spec):
    return tuple(generate(spec,policy=p) for p in ("dual","distance"))


def dump(path,rows):
    opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"wt",encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row,separators=(",",":"))+"\n")


def keys(split):
    start,end=CFG[split+"_seeds"]
    return list(product(CFG["maps"],CFG["fleets"],CFG["expansions_per_robot"],range(start,end+1)))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workers",type=int,default=8)
    ap.add_argument("--only",choices=("all","diagnostic","policy","timing","fixtures"),default="all")
    ap.add_argument("--out",type=Path,default=OUT)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"r5_fixtures.json").write_text(json.dumps(controlled(),indent=2))
    if a.only in ("all","diagnostic","policy"):
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            if a.only in ("all","diagnostic"):
                runs,pairs,ticks=[],[],[]
                for j,(rs,ps,ts) in enumerate(pool.map(diagnostic,keys("diagnostic")),1):
                    runs.append(rs)
                    pairs.extend(ps)
                    ticks.extend(ts)
                    if j%16==0:
                        print(f"diagnostic {j}, pairs {len(pairs)}",flush=True)
                dump(a.out/"r5_source_runs.jsonl",runs)
                dump(a.out/"r5_pairs.jsonl.gz",pairs)
                dump(a.out/"r5_ticks.jsonl.gz",ticks)
            if a.only in ("all","policy"):
                output=[]
                for j,v in enumerate(pool.map(policy_test,keys("policy")),1):
                    output.extend(v)
                    if j%32==0:
                        print(f"additional policy tests {j}",flush=True)
                dump(a.out/"r5_policy_runs.jsonl.gz",output)
    if a.only in ("all","timing"):
        scenarios=[s for s in keys("diagnostic") if s[3]==CFG["diagnostic_seeds"][0]]
        dump(a.out/"r5_work_timing.jsonl",[generate(s,timing=True) for s in scenarios])
        print("serial round timing completed",flush=True)


if __name__=="__main__":
    main()
