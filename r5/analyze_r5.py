"""Independent checks and scenario-level summaries for the public-layout results."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import itertools
import json
import math
from pathlib import Path
import platform
from random import Random
import sys

import numpy as np

from interval_planner import Query
from reference import caps, inspect_query, replay_events
from run_r5 import direction, keys
from warehouse import CFG, E, H, W, load_map

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data_r5"
FLAGS=("budget","reservation","goal_rule","horizon")
ARMS=("baseline","promoted")
POLICIES = ("dual", "distance")
WORKLOAD_FIELDS = ("seed_tests", "interval_expanded", "edge_tests", "reservation_writes", "wall_ms")


def read(data_dir, name):
    p=data_dir/name
    op=gzip.open if p.suffix==".gz" else open
    with op(p,"rt",encoding="utf-8") as fl:
        return [json.loads(t) for t in fl]


def csvfile(data_dir, name, rows):
    with (data_dir/name).open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cell(q):
    return q["layout"],q["n"],q["multiplier"]


def mean(a):
    return float(np.mean(a))


def ci(a):
    return tuple(map(float,np.quantile(a,[.025,.975])))


def reader_pair(r):
    f=r["focus"]
    b,t=r["baseline"],r["promoted"]
    out=dict(layout=r["layout"],n=r["n"],cap=r["cap"],seed=r["seed"],time=r["time"],focus=f,rank=r["rank"],
             match=r["match"],delta=r["delta"][f],original=b["finish"][f],promoted=t["finish"][f],
             n_others_later=len(r["others_later"]),
             largest_other_delay=max((r["delta"][i] for i in r["others_later"]),default=0),
             direction=r["proposed_direction"],distance=r["proposed_distance"],
             e1=r["event1"],e2=r["event2"],e3=r["event3"])
    for arm in ARMS:
        for k in FLAGS:
            out[f"{arm}_{k}"]=r[arm]["controls"]["reference"][k]
        out[f"{arm}_query_status"]=r[arm]["focal_query"]["state"]
    return out


def arm_records(rows):
    diagnostics=[]
    live=[]
    for r in rows:
        for arm in ARMS:
            a=r[arm]
            q=a["controls"]
            obj={**{k:r[k] for k in ("layout","n","cap","seed","time","rank","focus")},
                "arm":arm,"state":a["focal_query"]["state"],"expansions":a["focal_query"]["expanded"],
                "no_candidate":a["fallback"],"candidate_equal_seed":a["candidate_same_seed"],
                "window_equal_seed":a["committed_same_seed"],"prefix_equal_seed":a["executed_same_seed"]}
            for k in FLAGS:
                obj[f"probe_{k}"]=q["estimate"][k]
                obj[f"ref_{k}"]=q["reference"][k]
            for k,p in q["probes"].items():
                obj[f"probe_{k}_time"]=p["interval_earliest"]
                obj[f"ref_{k}_time"]=p["reference_earliest"]
            diagnostics.append(obj)
            live.append(a)
    return diagnostics,live


def confusion(rows,col):
    c=Counter((bool(q[col]),bool(q["earlier"])) for q in rows)
    return dict(tp=c[True,True],fp=c[True,False],fn=c[False,True],tn=c[False,False],
                early_other_delay=sum(q[col] and q["event3"] for q in rows))


def mean_use(groups, query_recs, data_source):
    cells=[]
    for s,rs in sorted(groups.items()):
        m,n,k=s
        ss=[q for q in data_source if cell(q)==s]
        measures=[q for q in query_recs if (q["layout"],q["n"],q["cap"])==(m,n,n*k)]
        pairs=len(rs)
        ans=dict(layout=m,n=n,multiplier=k,cap=n*k,scenarios=len(ss),
                 min_rate=min(q["rate"] for q in ss),mean_rate=mean([q["rate"] for q in ss]),
                 max_rate=max(q["rate"] for q in ss),
                 pairs=pairs,matched=sum(q["match"] for q in rs),
                 distinct_scenes_with_match=len({q["seed"] for q in rs if q["match"]}),
                 distinct_scenes_without_match=len({q["seed"] for q in rs if not q["match"]}),
                 event1=sum(q["event1"] for q in rs),
                 event2=sum(q["event2"] for q in rs),
                 event3=sum(q["event3"] for q in rs),early=sum(q["earlier"] for q in rs),
                 baseline_done=sum(q["baseline"]["finish"][q["focus"]] is not None for q in rs),
                 promoted_done=sum(q["promoted"]["finish"][q["focus"]] is not None for q in rs),
                 e3_matched=sum(q["match"] and q["event3"] for q in rs),
                 e3_unmatched=sum(not q["match"] and q["event3"] for q in rs),
                 **{k:sum(t[f"ref_{k}"] for t in measures) for k in FLAGS})
        cells.append(ans)
    return cells


def rate_contrast(rows, source):
    rng=np.random.default_rng(CFG["bootstrap_seed"])
    draws=CFG["bootstrap_draws"]
    groups=defaultdict(dict)
    for q in source:
        groups[q["layout"],q["n"]].setdefault(q["seed"],np.zeros((2,2),int))
    for q in rows:
        groups[q["layout"],q["n"]][q["seed"]][int(q["match"])]+=[int(q["event3"]),1]
    estimates=np.zeros((draws,2,2),int)
    found=np.zeros((2,2),int)
    for d in groups.values():
        ty=np.stack(list(d.values()))
        ids=rng.integers(len(ty),size=(draws,len(ty)))
        estimates+=ty[ids].sum(axis=1)
        found+=ty.sum(axis=0)
    key=lambda q:(q["layout"],q["n"],q["seed"])
    ns=[len({key(q) for q in rows if q["match"]==which}) for which in (False,True)]
    observed=[(int(a),int(b)) for a,b in found]
    result=dict(independent_scenarios=ns, tradeoffs_and_pairs=observed, diff=None, interval=None)
    if all(b for a,b in observed):
        rates=found[:,0]/found[:,1]
        result["diff"]=100*float(rates[1]-rates[0])
    if min(ns)>=CFG["contrast_cluster_min_per_label"]:
        good=estimates[(estimates[:,:,1]>0).all(axis=1)]
        rs=good[:,:,0]/good[:,:,1]
        result["interval"]=ci(100*(rs[:,1]-rs[:,0]))
        result["valid_draws"]=len(rs)
    return result


def policies(all_rows):
    expected = set(itertools.product(keys("policy"), POLICIES))
    check_run_coverage(((run_key(row), row["policy"]) for row in all_rows), expected, "policy run")
    edge=CFG["task_cohort_followup"]
    groups=defaultdict(dict)
    for r in all_rows:
        key = run_key(r)
        location = f"Policy run {key} {r['policy']}"
        check_logged_fields(r, location, cap=r["n"] * r["multiplier"])
        for field in ("job0_first", "job0_initial_length"):
            if len(r[field]) != r["n"]:
                raise ValueError(f"{location} {field} expected {r['n']} entries, found {len(r[field])}")
        groups[key][r["policy"]]=r
    split=defaultdict(list)
    for (*s,seed),a in groups.items():
        d,l=a["dual"],a["distance"]
        if d["job0_initial_length"] != l["job0_initial_length"]:
            raise ValueError(f"Policy run {(*s, seed)} initial task lengths differ between policies")
        outcome=np.array([d["rate"]-l["rate"],100*(d["overdue"]-l["overdue"]),
                           100*mean([(x is not None and x<=edge)-(y is not None and y<=edge)
                                     for x,y in zip(d["job0_first"],l["job0_first"])]),
                           mean([caps(x,edge)-caps(y,edge)
                                 if (x is None or x<=edge) and (y is None or y<=edge)
                                 else min(caps(x,edge),edge)-min(caps(y,edge),edge)
                                 for x,y in zip(d["job0_first"],l["job0_first"])])])
        split[tuple(s)].append((seed,outcome,sum(x is not None and x<=edge for x in d["job0_first"]),
                                sum(y is not None and y<=edge for y in l["job0_first"])))
    rng=np.random.default_rng(CFG["bootstrap_seed"]+1)
    summary=[]
    labels=("rate","overdue_pp","cohort_by64_pp","cohort_capped")
    for (m,n,b),rows in sorted(split.items()):
        a=np.stack([r[1] for r in sorted(rows,key=lambda r:r[0])])
        ix=rng.integers(len(a), size=(CFG["bootstrap_draws"],len(a)))
        draws=a[ix].mean(axis=1)
        means=a.mean(axis=0)
        summary.append(dict(layout=m,n=n,multiplier=b,cap=b*n,scenarios=len(a),cohort=n*len(a),
                            dual_finishes=sum(r[2] for r in rows),distance_finishes=sum(r[3] for r in rows),
                            **{k:float(v) for k,v in zip(labels,means)},
                            **{k+"_ci":ci(draws[:,i]) for i,k in enumerate(labels)}))
    return summary


def ambiguous_signatures(rows, match_initial=False):
    groups=defaultdict(list)
    for q in rows:
        a,b=[q[k]["direction"] for k in ARMS]
        signature=(*cell(q),q["rank"], tuple(a["heading"]), tuple(b["heading"]),
                   a["progress_two"], b["progress_two"])
        if match_initial:
            signature+=q["start_remaining"],
        groups[signature].append(q)
    def vector(q):
        return tuple(q[a]["controls"]["reference"][k] for a in ARMS for k in FLAGS)
    groups=[q for q in groups.values() if len(q)>=2]
    mech=[q for q in groups if len({vector(r) for r in q})>1]
    service=[q for q in groups if len({(r["earlier"],r["event3"]) for r in q})>1]
    usable=[r for group in groups for r in group]
    examples=[]
    if mech:
        chosen=max(mech,key=len)
        seen={}
        for q in chosen:
            seen.setdefault(vector(q),q)
        examples=[reader_pair(r) for r in list(seen.values())[:4]]
    return dict(repeated_signatures=len(groups), repeated_pair_count=len(usable),
                different_mechanism_group=len(mech),different_service_group=len(service),
                example_different_mechanism=examples)


def reserved_intent_overlap(rows):
    found={}
    tagged=[q for q in rows if q["match"]]
    for arm in ARMS:
        swap_count=0
        for q in tagged:
            f=q["focus"]
            p=q[arm]["focal"]["reservations"]
            swap_count+=any((p[j-(j>f)][t-1],p[j-(j>f)][t])==(v,u)
                            for j,u,v,t,_ in q["matches"])
        found[arm]=dict(reverse_edge=swap_count,tagged=len(tagged))
    return found


def check_logged_fields(record, location, **expected):
    for field, value in expected.items():
        if record[field] != value:
            raise ValueError(f"{location} {field} expected {value!r}, found {record[field]!r}")


def run_key(record):
    return (*cell(record), record["seed"])


def snapshot_key(record):
    return (*run_key(record), record["time"])


def check_run_coverage(record_keys, expected, kind):
    counts = Counter(record_keys)
    for key, count in counts.items():
        if count > 1:
            raise ValueError(f"Duplicate {kind} {key}")
        if key not in expected:
            raise ValueError(f"Unexpected {kind} {key}")
    missing = expected - counts.keys()
    if missing:
        raise ValueError(f"Missing {kind} {min(missing)} ({len(missing)} missing)")


def check_timing(rows):
    first_seed = CFG["diagnostic_seeds"][0]
    expected = {key for key in keys("diagnostic") if key[-1] == first_seed}
    check_run_coverage(map(run_key, rows), expected, "timing run")
    for row in rows:
        location = f"Timing run {run_key(row)}"
        check_logged_fields(row, location, cap=row["n"] * row["multiplier"], policy="density")
        for field in WORKLOAD_FIELDS:
            values = row["timing"].get(field)
            if (not isinstance(values, list) or len(values) != 2
                    or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values)
                    or not 0 <= values[0] <= values[1]):
                raise ValueError(f"{location} {field} must contain valid P50 and P95 values")


def check_selection(rows, ticks, source):
    runs = {}
    for run in source:
        key = run_key(run)
        if key in runs:
            raise ValueError(f"Duplicate source run {key}")
        runs[key] = run
    expected_runs = set(keys("diagnostic"))
    if runs.keys() != expected_runs:
        raise ValueError(f"Source runs differ from the protocol (missing {sorted(expected_runs - runs.keys())}, "
                         f"unexpected {sorted(runs.keys() - expected_runs)})")

    landmarks = range(CFG["first_landmark"], CFG["last_landmark"]+1, CFG["landmark_stride"])
    expected_ticks = {(*key, time) for key in runs for time in landmarks}
    ticks_by_key = {}
    eligible = defaultdict(list)
    for tick in ticks:
        key = snapshot_key(tick)
        if key in ticks_by_key:
            raise ValueError(f"Duplicate scheduled snapshot {key}")
        if key not in expected_ticks:
            raise ValueError(f"Unexpected scheduled snapshot {key}")
        ticks_by_key[key] = tick
        if tick["focus"] is not None:
            eligible[key[:-1], tick["shared"]].append(tick["time"])
    if missing := expected_ticks - ticks_by_key.keys():
        raise ValueError(f"Missing scheduled snapshot {min(missing)} ({len(missing)} missing)")

    sampled = defaultdict(set)
    seen = set()
    for pair in rows:
        key = snapshot_key(pair)
        if key in seen:
            raise ValueError(f"Duplicate paired snapshot {key}")
        seen.add(key)
        tick = ticks_by_key.get(key)
        if tick is None or tick["focus"] is None:
            raise ValueError(f"Paired snapshot {key} has no eligible scheduled snapshot")
        sampled[key[:-1], tick["shared"]].add(pair["time"])

    limit = CFG["max_pairs_per_scene_and_resource_label"]
    for key, run in runs.items():
        rng = Random(f"sample:{key}")
        for label in (False, True):
            times = sorted(eligible[key, label])
            count = len(times)
            expected = min(count, limit)
            location = f"Source run {key}, shared={label}"
            check_logged_fields(run["selection"][str(label)], location, eligible=count, sampled=expected)
            actual = sampled[key, label]
            if len(actual) != expected:
                raise ValueError(f"{location} expected {expected} paired snapshots, found {len(actual)}")
            # Match the generator's chronological candidates and shared RNG across labels.
            expected_times = set(rng.sample(times, expected))
            if actual != expected_times:
                raise ValueError(f"{location} seeded snapshot times expected {sorted(expected_times)}, "
                                 f"found {sorted(actual)}")


def check_pairs(rows, ticks, recompute):
    allowed = {snapshot_key(tick): tick for tick in ticks}
    for q in rows:
        b=load_map(q["layout"])
        identity = snapshot_key(q)
        source=allowed[identity]
        f=q["focus"]
        check_logged_fields(q, f"Snapshot {identity}", cap=source["cap"],
                            focus=source["focus"], rank=source["rank"],
                            match=source["shared"], matches=source["matches"])
        assert q["rank"]==q["baseline"]["ordered"].index(f)+1
        assert q["promoted"]["ordered"]==[f]+[i for i in q["baseline"]["ordered"] if i!=f]
        prefixes = []
        directions = []
        finishes = []
        comparisons = []
        goal = q["goals"][f]
        for arm in ARMS:
            a=q[arm]
            location = f"Snapshot {identity} {arm}"
            finish = replay_events(b, q["positions"], q["goals"], a["observed"])
            prefix = a["observed"][f][:E+1]
            if a["commit"][f][:E+1] != prefix:
                raise ValueError(f"{location} committed prefix differs from the observed trajectory")

            motion = direction(b, prefix, goal)
            motion["heading"] = list(motion["heading"])
            check_logged_fields(a, location, finish=list(finish), first_focal=prefix)
            check_logged_fields(a["direction"], f"{location} direction", **motion)
            prefixes.append(prefix)
            directions.append(motion)
            finishes.append(finish)
            order = a["ordered"]
            comparisons.append(dict(kind=arm, rank=order.index(f)+1, order=order, **motion))
            if recompute:
                x=a["focal_query"]
                checked=inspect_query(b,q["positions"][f],q["goals"][f],
                                      tuple(tuple(r) for r in a["focal"]["reservations"]),W,Query(**x))
                assert json.loads(json.dumps(checked))==a["controls"]

        location = f"Snapshot {identity}"
        if [o for o in q["order_comparison"] if o["kind"] in ARMS] != comparisons:
            raise ValueError(f"{location} order_comparison differs from the matched replay arms")
        res = [caps(promoted)-caps(baseline) for baseline, promoted in zip(*finishes)]
        early = res[f] < 0
        others = [i for i, delta in enumerate(res) if i != f and delta > 0]
        changed = prefixes[0] != prefixes[1]
        gained = (q["baseline"]["focal_query"]["state"] == "skipped"
                  and q["promoted"]["focal_query"]["state"] != "skipped")
        baseline, promoted = directions
        check_logged_fields(
            q, location, delta=res, earlier=early, others_later=others,
            start_remaining=b.distances(goal)[q["positions"][f]],
            proposed_direction=promoted["relative"] > baseline["relative"],
            proposed_distance=promoted["progress_two"] > baseline["progress_two"],
            event1=gained and not changed, event2=changed and not early,
            event3=early and bool(others),
        )


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify-probes",action="store_true")
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="read R5 run data and write analysis results here (default: r5/data_r5)")
    ap=parser.parse_args()
    data_dir=ap.data_dir.resolve()
    try:
        rows=read(data_dir, "r5_pairs.jsonl.gz")
        source=read(data_dir, "r5_source_runs.jsonl")
        ticks=read(data_dir, "r5_ticks.jsonl.gz")
        policy_runs=read(data_dir, "r5_policy_runs.jsonl.gz")
        serial=read(data_dir, "r5_work_timing.jsonl")
    except FileNotFoundError as error:
        parser.error(f"Missing input file {error.filename}")
    try:
        policy = policies(policy_runs)
        check_timing(serial)
        check_selection(rows, ticks, source)
        check_pairs(rows, ticks, ap.verify_probes)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    diag,live=arm_records(rows)
    csvfile(data_dir, "r5_query_checks.csv", diag)
    csvfile(data_dir, "r5_pair_summary.csv", [reader_pair(r) for r in rows])
    by_arm={}
    for arm in ARMS:
        data=[x for x in diag if x["arm"]==arm]
        by_arm[arm]={k:sum(a[f"ref_{k}"] for a in data) for k in FLAGS}
        by_arm[arm].update({k:sum(a[k] for a in data) for k in (
            "no_candidate","candidate_equal_seed","window_equal_seed","prefix_equal_seed")})
    ver={k:dict(positive=sum(x[f"ref_{k}"] for x in diag),
                fp=sum(x[f"probe_{k}"] and not x[f"ref_{k}"] for x in diag),
                fn=sum(not x[f"probe_{k}"] and x[f"ref_{k}"] for x in diag))
         for k in FLAGS}
    query_agreement=sum(all(r["estimate"][k]==r["reference"][k] for k in FLAGS)
                        for r in [a["controls"] for a in live])
    exact_time_disagree=sum(r["interval_earliest"]!=r["reference_earliest"]
                           for a in live for r in a["controls"]["probes"].values())
    groups={cell(x):[] for x in source}
    for q in rows:
        groups[cell(q)].append(q)
    cells=mean_use(groups,diag,source)
    csvfile(data_dir, "r5_scenario_cells.csv", cells)
    csvfile(data_dir, "r5_policy_comparison.csv", policy)
    proxies={p:confusion(rows,p) for p in ("proposed_direction","proposed_distance")}
    alternate_patterns=[dict(kind=f,**Counter(str(o["relative"]) for q in rows
                                for o in q["order_comparison"] if o["kind"]==f))
                         for f in ("baseline","promoted","random")]
    examples={}
    for name,ok in (
        ("missed_service",lambda r:r["earlier"] and not r["proposed_direction"]),
        ("false_gain",lambda r:r["proposed_direction"] and not r["earlier"]),
        ("cross_robot_cost",lambda r:r["event3"]),
        ("goal_rule",lambda r:any(r[a]["controls"]["reference"]["goal_rule"] for a in ARMS))):
        options=[r for r in rows if ok(r)]
        if options:
            examples[name]=reader_pair(options[0])
    case=ambiguous_signatures(rows)
    n_multi=sum(sum(x[f"ref_{k}"] for k in FLAGS)>1 for x in diag)
    statuses=Counter()
    for q in rows:
        f=q["focus"]
        a,b=q["baseline"]["finish"][f],q["promoted"]["finish"][f]
        statuses[f"{int(a is not None)}{int(b is not None)}"]+=1
        statuses["original_at_32"]+=a==H
        statuses["promoted_at_32"]+=b==H
    other_delay=Counter(len(q["others_later"]) for q in rows)
    workload=[dict(layout=q["layout"],n=q["n"],cap=q["cap"],seed=q["seed"],
                   **{f"{k}_{j}":w for k in WORKLOAD_FIELDS for j,w in zip(("p50","p95"),q["timing"][k])})
              for q in serial]
    csvfile(data_dir, "r5_workload.csv", workload)
    summ=dict(source_n=len(source),landmarks=len(ticks),pairs=len(rows),queries=len(diag),
              focal_capped_change=mean([q["delta"][q["focus"]] for q in rows]),
              e_counts=[sum(r[f"event{i}"] for r in rows) for i in (1,2,3)],
              all_source_active=all(q["completions"]>0 for q in source),
              source_range=[min(q["rate"] for q in source),max(q["rate"] for q in source)],
              focal_finish_pattern=statuses,
              other_delay_count=dict(other_delay),
              probes_verified=ver,by_arm=by_arm,multilabel=n_multi,
              agree=query_agreement,time_checks=len(diag)*4,time_disagree=exact_time_disagree,
              proxies=proxies,selected_examples=examples,repeated=case,
              repeated_with_initial=ambiguous_signatures(rows,match_initial=True),
              reserved_intent_overlap=reserved_intent_overlap(rows),directions=alternate_patterns,
              resource=rate_contrast(rows,source),cells=cells,policy=policy,workload=workload,
              environment=dict(python=platform.python_version(),versions={"numpy":np.__version__},
                               system=platform.platform(),machine=platform.machine()))
    (data_dir/"r5_summary.json").write_text(json.dumps(summ,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in summ.items() if k not in ("cells","policy","by_arm","workload","selected_examples")},
                     indent=2))


if __name__=="__main__":
    main()
