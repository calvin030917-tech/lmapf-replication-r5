"""Reconstruct R4 tables and verify case replay from raw simulator trajectories."""
from collections import Counter, defaultdict
from dataclasses import asdict
import argparse
import json
from pathlib import Path

import numpy as np

from analyze import (ADJ, P, avg, band, clipped, first_stats, key, pair_ci, quant,
                     rank_group, read, run_key, write_csv)
from diagnose import compare
from protocol import EXEC, LOOK, MARGIN, W, strata
from simulator import Reservations, advance, common_seed, goal_at, layout, order_for, paths_valid, replanning, scenario
from validation import HOLDOUT_LAYOUTS, holdout_map

DATA = Path("data")
BRANCHES = ("baseline", "treatment")
CASE_KEYS = ("layout", "n", "multiplier", "seed", "source", "time")


def identity(q):
    return tuple(q[k] for k in CASE_KEYS)


def selected_metadata(q):
    return {k:q[k] for k in (*CASE_KEYS, "budget", "focus", "rank")}


def grid_for(name):
    return holdout_map(name) if name in HOLDOUT_LAYOUTS else layout(name)


def crossing(grid, path, goal, completed):
    bank = tuple(map(grid.bank, path))
    destination = grid.bank(goal)
    first = last = 0 if bank[0] == 0 else None
    retreats = 0
    for t in range(1, (LOOK if completed is None else completed)+1):
        if bank[t-1] != 0 and bank[t] == 0:
            last = t
            if first is None:
                first = t
        if bank[t-1] == 0 and bank[t] == destination:
            assert last is not None and first is not None
            return first, last, t, retreats
        if bank[t-1] == 0 and bank[t] not in (0, destination):
            retreats += 1
    return first, None, None, retreats


def gate_audit(rows):
    entries = []
    for q in rows:
        i = q["focus"]
        assert q["at_risk"][i]
        for arm in BRANCHES:
            r = q[arm]
            f,l,e,n = crossing(grid_for(q["layout"]), r["path"][i], q["goals"][i], r["task"][i])
            assert (f,e) == (r["gate_entry"][i], r["gate"][i])
            assert (e-l if e is not None and l > 0 else None) == r["zone"][i]
            assert e is not None
            entries.append(dict(**selected_metadata(q), arm=arm, inside=q["initial_inside"][i],
                                first_entry=f, successful_entry=l, exit=e, retreats=n,
                                before_first=f, entry_to_entry=l-f, final_segment=e-l,
                                first_to_exit=e-f))
    write_csv("r4_gate_clocks_all.csv",entries)
    groups=[]
    for branch in BRANCHES:
        all_arm=[r for r in entries if r["arm"]==branch]
        for area, rs in (("outside",[r for r in all_arm if not r["inside"]]),
                         ("inside",[r for r in all_arm if r["inside"]]), ("total", all_arm)):
            sums={col:sum(r[col] for r in rs) for col in (
                "before_first","entry_to_entry","final_segment","first_to_exit","exit")}
            assert sums["before_first"]+sums["entry_to_entry"]+sums["final_segment"]==sums["exit"]
            groups.append(dict(arm=branch, location=area, n=len(rs), with_retreat=sum(r["retreats"]>0 for r in rs),
                               **{f"{k}_sum":v for k,v in sums.items()},
                               **{f"{k}_mean":v/len(rs) for k,v in sums.items()}))
    write_csv("r4_gate_reconstruction.csv",groups)
    deviations=[]
    for q in rows:
        i=q["focus"]
        if q["gate_delta"][i] != q["task_delta"][i]:
            deviations.append(dict(**selected_metadata(q), gate_delta=q["gate_delta"][i],
                                   task_delta=q["task_delta"][i], baseline_gate=q["baseline"]["gate"][i],
                                   treatment_gate=q["treatment"]["gate"][i],
                                   baseline_task=q["baseline"]["task"][i],
                                   treatment_task=q["treatment"]["task"][i]))
    write_csv("r4_gate_vs_task_deltas.csv",deviations)
    return groups,deviations


def other_impact(rows):
    counts=[]; deltas=[]; positives=[]; statuses=Counter()
    nonearly=0
    exact_at_cap=Counter()
    for q in rows:
        i=q["focus"]
        a,b=q["baseline"]["task"],q["treatment"]["task"]
        late=0
        for j in range(len(a)):
            if j==i:
                continue
            x,y=a[j],b[j]
            status=("done" if x is not None else "open")+"_"+("done" if y is not None else "open")
            statuses[status]+=1
            exact_at_cap["baseline"]+=x==LOOK
            exact_at_cap["treatment"]+=y==LOOK
            dx=clipped(y)-clipped(x)
            deltas.append(dx)
            if dx>0:
                late+=1
                positives.append(dx)
        assert late==len(q["others_later"])
        counts.append(late)
        nonearly+=bool(late and q["task_delta"][i]>=0)
    return dict(pairs=len(rows), any_later=sum(c>0 for c in counts),
                focus_not_earlier_others_later=nonearly, pairs_two_or_more=sum(c>=2 for c in counts),
                slow_n_p50=quant(counts,.5), slow_n_p90=quant(counts,.9), slow_n_max=max(counts,default=None),
                positive_n=len(positives), negative_n=sum(d<0 for d in deltas), zero_n=sum(d==0 for d in deltas),
                slow_time_p50=quant(positives,.5), slow_time_p90=quant(positives,.9),
                slow_time_max=max(positives,default=None), signed_time_mean=avg(deltas),
                both_done=statuses["done_done"], baseline_only=statuses["done_open"],
                promotion_only=statuses["open_done"], both_open=statuses["open_open"],
                baseline_exact32=exact_at_cap["baseline"], promotion_exact32=exact_at_cap["treatment"])


def impact_tables(named):
    row_table=[]; pair_table=[]; vehicle_table=[]; scene_table=[]
    for name, qs in named.items():
        row_table.append(dict(sample=name,layout="all",n="",multiplier="",source="all",constructor="all",
                              **other_impact(qs)))
        groups=defaultdict(list)
        scenes=defaultdict(list)
        for q in qs:
            constructor=q.get("constructor","recursive")
            groups[(*key(q),q["source"],constructor)].append(q)
            scenes[(*key(q),q["source"],constructor,q["seed"])].append(q)
            others=[j for j in range(q["n"]) if j!=q["focus"]]
            pair_table.append(dict(sample=name,**selected_metadata(q),constructor=constructor,
                                   n_later=len(q["others_later"]),n_earlier=len(q["others_earlier"]),
                                   focus_delta=q["task_delta"][q["focus"]],
                                   max_other_delta=max(q["task_delta"][j] for j in others)))
            for j in others:
                u,v=(q[a]["task"][j] for a in BRANCHES)
                vehicle_table.append(dict(sample=name,**selected_metadata(q),constructor=constructor,robot=j,
                                          original_completion=u,promoted_completion=v,
                                          original_done=int(u is not None),promoted_done=int(v is not None),
                                          cap_delta=q["task_delta"][j]))
        for (m,n,b,s,c),rs in sorted(groups.items()):
            row_table.append(dict(sample=name,layout=m,n=n,multiplier=b,source=s,constructor=c,
                                  **other_impact(rs)))
        for (m,n,b,s,c,seed),rs in sorted(scenes.items()):
            scene_table.append(dict(sample=name,layout=m,n=n,multiplier=b,source=s,constructor=c,seed=seed,
                                    **other_impact(rs)))
    write_csv("r4_interference_summary.csv",row_table)
    write_csv("r4_interference_by_pair.csv",pair_table)
    write_csv("r4_interference_by_vehicle.csv",vehicle_table)
    write_csv("r4_interference_by_scenario.csv",scene_table)
    return row_table


def summarize_cells(named):
    out=[]
    for name,rows in named.items():
        grouped=defaultdict(list)
        for q in rows:
            group=(q["layout"],q["multiplier"],q.get("constructor","recursive"))
            rank=rank_group(q["rank"])
            label=q.get("opposed","all")
            for m,b,c,rr in (("all",0,"all","all"),(*group,"all"),(*group,rank)):
                grouped[(m,b,c,rr,label)].append(q)
        for (m,b,c,rr,label),qs in sorted(grouped.items()):
            f=first_stats(qs)
            out.append(dict(sample=name,layout=m,multiplier=b,constructor=c,rank=rr,opposed=label,
                            pairs=f["pairs"],e1=f["category1"],e2=f["category2"],e3=f["category3"],
                            gate_tradeoff=f["co_burden_gate"], task_delta=f["focus_delta"],
                            gate_delta=f["gate_delta"], n_gate=f["gate_pairs"],
                            any_other_slow=sum(bool(q["others_later"]) for q in qs)))
    write_csv("r4_same_conditions.csv",out)
    return out


def validation_cells(rows, selection):
    summaries=[]
    for m in ("all",*HOLDOUT_LAYOUTS):
        for b in ((0,) if m=="all" else (5,14)):
            for c in ("recursive","serial"):
                rs=[q for q in rows if q["constructor"]==c and
                    (m=="all" or (q["layout"],q["multiplier"])==(m,b))]
                ticks=[q for q in selection if q["constructor"]==c and
                       (m=="all" or (q["layout"],q["multiplier"])==(m,b))]
                stats=first_stats(rs)
                summaries.append(dict(layout=m,multiplier=b,constructor=c,ticks=len(ticks),
                                      first_rank=sum(q["rank"]==1 for q in ticks),
                                      no_focal=sum(q["rank"] is None for q in ticks),
                                      n_scenarios=len({(q["layout"],q["multiplier"],q["seed"]) for q in ticks}),
                                      pairs=len(rs),e1=stats["category1"],e2=stats["category2"],
                                      e3=stats["category3"], task_delta=stats["focus_delta"],
                                      n_gate=stats["gate_pairs"],gate_delta=stats["gate_delta"],
                                      any_other_slow=sum(bool(q["others_later"]) for q in rs)))
    write_csv("r4_holdout_cells.csv",summaries)
    return summaries


def matched_interval(rows, selection):
    # Keep both budgets and all ticks from the same (map, seed) together.
    strata_present=sorted({(q["layout"],q["multiplier"],rank_group(q["rank"])) for q in rows})
    a=np.zeros((P,len(strata_present),2,2))
    observed=np.zeros_like(a[0])
    rng=np.random.default_rng(518042)
    for m in ("single","bypass"):
        seeds=sorted({q["seed"] for q in selection if q["layout"]==m})
        x=np.zeros((len(seeds),*a.shape[1:]))
        for q in rows:
            if q["layout"]!=m:
                continue
            i=seeds.index(q["seed"])
            j=strata_present.index((m,q["multiplier"],rank_group(q["rank"])))
            x[i,j,int(q["opposed"])]+=[q["category3"],1]
        observed+=x.sum(axis=0)
        ids=rng.integers(len(seeds),size=(P,len(seeds)))
        a+=x[ids].sum(axis=1)
    def diff(tot):
        return tot[...,1,0]/tot[...,1,1]-tot[...,0,0]/tot[...,0,1]
    den=observed[...,1]>0
    summary={}
    for name in ("raw","standardized"):
        if name=="raw":
            sample=a.sum(axis=1)
            outcome=observed.sum(axis=0)
            valid=(sample[...,1]>0).all(axis=1)
            summary[name]=dict(rate_difference=float(diff(outcome)),interval=band(diff(sample[valid])),
                               valid_draws=int(valid.sum()),covered_pairs=int(outcome[...,1].sum()))
        else:
            overlap=den.all(axis=1)
            sample=a[:,overlap]
            outcome=observed[overlap]
            valid=(sample[...,1]>0).all(axis=(1,2))
            weights=outcome[...,1].sum(axis=1)
            summary[name]=dict(rate_difference=float(np.average(diff(outcome),weights=weights)),
                               interval=band(np.average(diff(sample[valid]),axis=1,weights=weights)),
                               valid_draws=int(valid.sum()),covered_pairs=int(weights.sum()),
                               covered_cells=int(overlap.sum()),all_cells=len(overlap))
    return summary


def check_same_snapshot(main, alternative):
    a={identity(q):q for q in alternative}
    out=[]
    for q in main:
        if q["constructor"]!="recursive":
            continue
        alt=a.pop(identity(q))
        assert all(q[k]==alt[k] for k in (
            "focus","rank","order","promoted","at_risk","initial_inside","pre_distances","ages","goals","job_index"))
        assert all(p[0]==r[0] for p,r in zip(q["seed_paths"],alt["seed_paths"]))
        out.append(dict(**selected_metadata(q),seed_diff=q["seed_paths"]!=alt["seed_paths"],
                        **{f"event{i}_{label}":x[f"category{i}"] for i in (1,2,3)
                           for label,x in (("recursive",q),("serial",alt))}))
    assert not a
    write_csv("r4_same_snapshot_seed_comparison.csv",out)
    summary={"n":len(out),"seed_different":sum(r["seed_diff"] for r in out)}
    for i in (1,2,3):
        m=Counter((r[f"event{i}_recursive"],r[f"event{i}_serial"]) for r in out)
        summary[f"e{i}"]={label:m[ab] for label,ab in (
            ("both",(True,True)),("recursive_only",(True,False)),
            ("serial_only",(False,True)),("neither",(False,False)))}
    return summary


def decision_tables(original, rows):
    primary=[]
    for e in original["contrasts"]:
        lo=e["rate_ratio_lower"]
        primary.append(dict(**e, overdue_pass=e["f3_upper"]<0,
                            **{f"rate_pass_{pct}":lo is not None and lo>1-pct/100 for pct in (0,5,10)}))
    write_csv("r4_joint_bounds.csv",primary)
    rng=np.random.default_rng(518041)
    by_cell=defaultdict(lambda:defaultdict(list))
    for r in rows:
        by_cell[key(r)][r["policy"]].append(r)
    secondary=[]
    for m,n,b in strata():
        g=by_cell[m,n,b]
        a,h=[sorted(g[code],key=lambda r:r["seed"]) for code in ("dual","distance")]
        assert [r["seed"] for r in a]==[r["seed"] for r in h]
        ns=len(a)
        ids=rng.integers(ns,size=(P,ns))
        df=np.array([100*(x["f3"]-y["f3"]) for x,y in zip(a,h)])
        ar,hr=(np.array([r["throughput"] for r in q]) for q in (a,h))
        rate=(ar[ids].mean(axis=1)/hr[ids].mean(axis=1))
        abs_diff=(ar-hr)
        tail=.05/(2*len(strata()))
        upper=quant(df[ids].mean(axis=1),1-tail)
        lower=quant(rate,tail)
        secondary.append(dict(layout=m,n=n,multiplier=b,n_seeds=ns,
                              overdue_pp=avg(df),overdue_ci=band(df[ids].mean(axis=1)),overdue_upper=upper,
                              rate_ratio=ar.mean()/hr.mean(),rate_ci=band(rate),rate_lower=lower,
                              absolute_rate_diff=avg(abs_diff),absolute_rate_ci=band(abs_diff[ids].mean(axis=1)),
                              this_control=upper<0 and lower>1-MARGIN))
    write_csv("r4_distance_contrasts.csv",secondary)
    return primary,secondary


def earliest_candidate(grid, reserved, start, goal, rule):
    assert rule in ("hold","release")
    res=Reservations(reserved)
    frontier={start:(None,(start,))}
    visited=0
    for t in range(1,W+1):
        next_layer={}
        for a,(arrival, path) in frontier.items():
            visited+=1
            for v in (a,) if rule=="hold" and a==goal else grid.moves[a]:
                if v in res.cells[t] or (a,v) in res.edges[t]:
                    continue
                hit=t if arrival is None and v==goal else arrival
                candidate=(LOOK if hit is None else hit,path+(v,))
                old=next_layer.get(v,(LOOK+1,()))
                if candidate<old:
                    next_layer[v]=candidate
        frontier={v:(None if hit==LOOK else hit,p) for v,(hit,p) in next_layer.items()}
    chosen=min(((t,p) for t,p in frontier.values() if t is not None),default=(None,()))
    if chosen[1]:
        assert res.accepts(chosen[1])
    return dict(earliest=chosen[0],path=chosen[1],expanded=visited,rule=rule)


def full_case_trace(q):
    case,state=scenario(q["layout"],q["n"],q["multiplier"],q["seed"])
    timeline={}
    while state.time<q["time"]+LOOK:
        order=order_for(case,state,q["source"])
        paths,tr,_=replanning(case,state,order)
        timeline[state.time]=(state,order,paths,tr)
        state=advance(case,state,paths)
    snap,order,source_window,source_tr=timeline[q["time"]]
    seed,work=common_seed(case,snap)
    assert json.loads(json.dumps(seed))==q["seed_paths"]
    assert work==q["common_work"]
    assert list(order)==q["order"]
    live=compare(case,snap,order,q["focus"],q["source"],seed)
    assert all(json.loads(json.dumps(live[k]))==q[k] for k in live)
    assert json.loads(json.dumps(source_window))==q["baseline"]["window"]
    assert json.loads(json.dumps([asdict(r) for r in source_tr]))==q["baseline"]["solver"]
    for dt in range(1,LOOK+1):
        t=q["time"]+(dt-1)//EXEC*EXEC
        assert [p[dt] for p in q["baseline"]["path"]]==[p[(dt-1)%EXEC+1] for p in timeline[t][2]]
    rounds={}; goal_match={}; focal=q["focus"]
    for arm,k in zip(BRANCHES,("order","promoted")):
        tested=tuple(q[k])
        paths,traces,stage=replanning(case,snap,tested,capture=True,seed_paths=seed)
        assert paths_valid(case.grid,paths)
        rounds[arm]=[dict(robot=i,residual_before=stage[i][1],reserved=stage[i][0],
                          search=asdict(traces[i]),executed=paths[i][:EXEC+1])
                     for i in tested]
        res,left=stage[focal]
        goal=goal_at(case,snap,focal)
        p=seed[focal]
        valid=Reservations(res).accepts(p)
        arrival=p.index(goal) if goal in p else None
        hold=valid and (arrival is None or all(x==goal for x in p[arrival:]))
        goal_match[arm]=dict(seed_arrival=arrival,seed_legal_under_release=valid,
                             seed_legal_under_hold=hold,residual=left,
                             exact_release=earliest_candidate(case.grid,res,p[0],goal,"release"),
                             exact_hold=earliest_candidate(case.grid,res,p[0],goal,"hold"))
    return dict(**selected_metadata(q), state=asdict(snap),active_goals=q["goals"],
                seed_paths=seed,seed_candidate_checks=work,original=q["order"],promoted=q["promoted"],
                first_round=rounds,paths_32={arm:q[arm]["path"] for arm in BRANCHES},
                arrivals_32={arm:q[arm]["task"] for arm in BRANCHES},
                exits_32={arm:q[arm]["gate"] for arm in BRANCHES},
                replays_all_source_actions=True, matched_goal_rule=goal_match)


def mechanism_counts(rows, budget, route):
    out=[]
    for m,n,b in strata():
        for source in ("age","congestion"):
            h=[q for q in rows if (*key(q),q["source"])==(m,n,b,source)]
            selected=[q for q in h if q["baseline"]["solver"][q["focus"]]["status"] in ("budget","not_started")]
            q1=[q for q in budget if (*key(q),q["source"])==(m,n,b,source)]
            q2=[q for q in route if (*key(q),q["source"])==(m,n,b,source)]
            assert [identity(q) for q in q1]==[identity(q) for q in sorted(selected,key=lambda q:(q["seed"],q["time"]))[:3]]
            assert [identity(q) for q in q2]==[identity(q) for q in sorted(h,key=lambda q:(q["seed"],q["time"]))[:3]]
            out.append(dict(layout=m,n=n,multiplier=b,source=source,sampled=len(h),budget_eligible=len(selected),
                            budget_tested=len(q1),route_tested=len(q2),route_alt=sum(q["result"] is not None for q in q2)))
    write_csv("r4_mechanism_selection.csv",out)
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--historical-only",action="store_true")
    args=parser.parse_args()
    original=json.loads((DATA/"results.json").read_text())
    pairs,gate=read("pairs.jsonl.gz"),read("gate_pairs.jsonl.gz")
    reconstruct,deviations=gate_audit(gate)
    primary,secondary=decision_tables(original,read("policies.jsonl.gz"))
    traces={label:full_case_trace(q) for label,q in original["examples"].items()}
    (DATA/"r4_case_replays.json").write_text(json.dumps(traces,ensure_ascii=False),encoding="utf-8")
    mechanisms=mechanism_counts(pairs,read("mechanism_budget.jsonl"),read("mechanism_route.jsonl"))
    rng=np.random.default_rng(518044)
    gi=pair_ci(read("gate_selection.jsonl"),gate,rng)
    r3subset=[q for q in pairs if q["n"]==24 and q["source"]=="congestion"]
    impacts=dict(R3_overdue=pairs,R3_gate=gate)
    comparison=dict(R3_overdue_same_fleet=r3subset,R3_gate=gate)
    extra={}
    if not args.historical_only:
        matched,match_ticks=read("matched_pairs.jsonl.gz"),read("matched_selection.jsonl.gz")
        holdout,hold_ticks=read("holdout_pairs.jsonl.gz"),read("holdout_selection.jsonl.gz")
        alternative=read("holdout_alternative_first_round.jsonl.gz")
        impacts.update(R4_matched=matched,R4_holdout=holdout)
        comparison["R4_matched"]=matched
        extra=dict(matched_interval=matched_interval(matched,match_ticks),
                   match_ticks={"total":len(match_ticks),"no_focal":sum(q["rank"] is None for q in match_ticks),
                                "rank_one":sum(q["rank"]==1 for q in match_ticks),"selected":len(matched)},
                   holdout_cells=validation_cells(holdout,hold_ticks),
                   common_snapshot=check_same_snapshot(holdout,alternative))
    all_stats=dict(reconstruction=reconstruct,deviations=deviations,decision=primary,distance=secondary,
                   gate_bootstrap=gi,goal_rule=traces["B"]["matched_goal_rule"],
                   mechanism_eligible=sum(g["budget_eligible"] for g in mechanisms),
                   factorial=original["factorial"],examples=original["examples"],
                   same_conditions=summarize_cells(comparison),impact=impact_tables(impacts),**extra)
    (DATA/"r4_results.json").write_text(json.dumps(all_stats,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(f"Verified {len(traces)} complete source/edited replays through step {LOOK} and {len(gate)} gate pairs.")


if __name__=="__main__":
    main()
