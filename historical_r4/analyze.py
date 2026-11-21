"""Deterministic summaries, clustered bootstrap intervals, and figure case selection."""
import csv
from collections import defaultdict
import gzip
import json
from pathlib import Path
import numpy as np

from protocol import BOOTSTRAPS, BOOT_SEED, LOOK, MARGIN, POLICIES, SOURCES, strata

DATA = Path("data")
P = BOOTSTRAPS
ADJ = .05/(len(strata())*2*2)


def read(name):
    path = DATA/name
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(s) for s in f]


def avg(x):
    x = list(x)
    return sum(x)/len(x) if x else None


def quant(x, q):
    z = np.asarray(x, dtype=float)
    return float(np.quantile(z, q)) if z.size and np.isfinite(z).all() else None


def band(x):
    return [quant(x,q) for q in (.025,.975)]


def write_csv(path, rows):
    if rows:
        with (DATA/path).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def key(r):
    return r["layout"],r["n"],r["multiplier"]


def run_key(r):
    return (*key(r),r["source"],r["seed"])


def rank_group(rank):
    return "2-4" if rank <= 4 else "5-8" if rank <= 8 else "9+"


def clipped(t):
    return t if t is not None else LOOK


def first_stats(rows):
    ww = lambda fun: sum(bool(fun(q,q["focus"])) for q in rows)
    gate = [q for q in rows if q["at_risk"][q["focus"]]]
    n = len(rows)
    cc = {name:sum(q[name] for q in rows) for name in (
        "gained","changed","category1","category2","category3","co_burden_gate")}
    focus_val = lambda branch, kind: [q[branch][kind][q["focus"]] for q in rows]
    base_t, new_t = focus_val("baseline","task"), focus_val("treatment","task")
    durations = [q["task_delta"][q["focus"]] for q in rows]
    results = dict(pairs=n, runs=len({run_key(q) for q in rows}), **cc,
                   category2_both_censored=ww(lambda q,i: q["category2"] and
                                               q["baseline"]["task"][i] is None and q["treatment"]["task"][i] is None),
                   focal_earlier=sum(v<0 for v in durations), focal_later=sum(v>0 for v in durations),
                   other_later_pairs=sum(bool(q["others_later"]) for q in rows),
                   other_later_total=sum(len(q["others_later"]) for q in rows),
                   other_earlier_total=sum(len(q["others_earlier"]) for q in rows),
                   focal_task_both_done=sum(x is not None and y is not None for x,y in zip(base_t,new_t)),
                   only_baseline_done=sum(x is not None and y is None for x,y in zip(base_t,new_t)),
                   only_treatment_done=sum(x is None and y is not None for x,y in zip(base_t,new_t)),
                   focal_task_both_censored=sum(x is None and y is None for x,y in zip(base_t,new_t)),
                   baseline_task_done=sum(t is not None for t in base_t),
                   treatment_task_done=sum(t is not None for t in new_t),
                   focus_delta=avg(durations),
                   completed_in_both_delta=avg(y-x for x,y in zip(base_t,new_t) if x is not None and y is not None),
                   other_delta_per_car=avg(v for q in rows for i,v in enumerate(q["task_delta"]) if i != q["focus"]),
                   benchmark_cut=ww(lambda q,i:q["baseline"]["round_budget_cut"]),
                   treatment_cut=ww(lambda q,i:q["treatment"]["round_budget_cut"]),
                   focal_seed_baseline=ww(lambda q,i:q["baseline"]["seed_retained"][i]),
                   focal_seed_treatment=ww(lambda q,i:q["treatment"]["seed_retained"][i]),
                   fallback_baseline=ww(lambda q,i:q["baseline"]["fallback"]),
                   fallback_treatment=ww(lambda q,i:q["treatment"]["fallback"]),
                   gate_pairs=len(gate), gate_earlier=sum(q["gate_delta"][q["focus"]]<0 for q in gate),
                   gate_later=sum(q["gate_delta"][q["focus"]]>0 for q in gate),
                   gate_inside=sum(q["initial_inside"][q["focus"]] for q in gate),
                   gate_delta=avg(q["gate_delta"][q["focus"]] for q in gate))
    for b in ("baseline","treatment"):
        ex = [q[b]["gate"][q["focus"]] for q in gate]
        enter = [q[b]["gate_entry"][q["focus"]] for q in gate]
        duration = [q[b]["zone"][q["focus"]] for q in gate if not q["initial_inside"][q["focus"]]]
        outside_entry = [q[b]["gate_entry"][q["focus"]] for q in gate if not q["initial_inside"][q["focus"]]]
        inside_exit = [q[b]["gate"][q["focus"]] for q in gate if q["initial_inside"][q["focus"]]]
        results.update({b+"_gate_exited":sum(v is not None for v in ex),
                        b+"_gate_no_entry":sum(v is None for v in enter),
                        b+"_gate_enter_no_exit":sum(e is not None and x is None for x,e in zip(ex,enter)),
                        b+"_gate_mean_capped":avg(clipped(v) for v in ex),
                        b+"_gate_zone_n":sum(v is not None for v in duration),
                        b+"_gate_mean_zone":avg(v for v in duration if v is not None),
                        b+"_gate_mean_to_first_entry":avg(clipped(v) for v in outside_entry),
                        b+"_gate_mean_remaining_inside":avg(clipped(v) for v in inside_exit)})
    return results


def select_summary(selection):
    common = ("periods","already_first","eligible","picked")
    key_observed = "overdue" if selection and "overdue" in selection[0] else "gate_conflict_cycles"
    return dict(**{k:sum(v[k] for v in selection) for k in (*common,key_observed)},
                source_runs=len(selection), contributing_runs=sum(v["picked"]>0 for v in selection))


def pair_ci(selection, pairs, rng):
    values = defaultdict(list)
    for q in pairs:
        f = q["focus"]
        values[run_key(q)].append((q["task_delta"][f],q["gate_delta"][f]))
    group = defaultdict(lambda:defaultdict(lambda:np.zeros(4)))
    for s in selection:
        v = values[run_key(s)]
        gg = [g for t,g in v if g is not None]
        group[(s["layout"],s["n"])][s["seed"]] += [sum(x for x,g in v),len(v),sum(gg),len(gg)]
    z = np.zeros((P,4))
    for seq in group.values():
        a = np.stack(list(seq.values()))
        ids = rng.integers(len(seq),size=(P,len(seq)))
        z += a[ids].sum(axis=1)
    def ci(k):
        valid = z[:,k+1]>0
        if not valid.any():
            return [None,None]
        return band(z[valid,k]/z[valid,k+1])
    return dict(focus_task_ci=ci(0), focal_gate_ci=ci(2))


def summarize_pairs(selection,pairs,rng,gate=False):
    sources = ("congestion",) if gate else SOURCES
    all_summary = dict(**select_summary(selection),**first_stats(pairs),**pair_ci(selection,pairs,rng))
    per_source, cells, by_rank = [],[],[]
    for scr in sources:
        s = [a for a in selection if a["source"]==scr]
        q = [a for a in pairs if a["source"]==scr]
        per_source.append(dict(source=scr,**select_summary(s),**first_stats(q),**pair_ci(s,q,rng)))
        for m,n,b in strata():
            g = [a for a in s if key(a)==(m,n,b)]
            if not g:
                continue
            u = [a for a in q if key(a)==(m,n,b)]
            cells.append(dict(source=scr, layout=m,n=n,multiplier=b,
                              **select_summary(g),**first_stats(u)))
            for i,rr in enumerate(("2-4","5-8","9+")):
                l,h = ((1,4),(4,8),(8,n))[i]
                by_rank.append(dict(source=scr,layout=m,n=n,multiplier=b,rank=rr,
                                    eligible=sum(sum(v["eligible_ranks"][l:h]) for v in g),
                                    **first_stats([x for x in u if rank_group(x["rank"])==rr])))
    return dict(total=all_summary,sources=per_source,cells=cells,rank=by_rank)


def mean_line(rows):
    res = {name:avg(r[name] for r in rows) for name in
           ("throughput","f2","f3","f4","vehicle_median","vehicle_q25","vehicle_q75","vehicle_max",
            "longest","plan_p95_ms","seed_tries_mean","budget_rounds","empty_plan_rounds")}
    res["throughput_sd"] = float(np.std([r["throughput"] for r in rows],ddof=1))
    res["f3_sd"] = float(np.std([r["f3"] for r in rows],ddof=1))
    res["n_seeds"] = len(rows)
    for j in range(3):
        den, over, exc = map(sum,zip(*(r["by_length"][j] for r in rows)))
        v = [x for r in rows for b,x,c in r["tasks_capped"] if b==j]
        done = [c for r in rows for b,x,c in r["tasks_capped"] if b==j]
        res.update({f"d{j}_exposure":den, f"d{j}_f3":over/den if den else None,
                    f"d{j}_mean_excess":exc/den if den else None,
                    f"d{j}_task_n":len(v), f"d{j}_done":avg(done), f"d{j}_task_p90":quant(v,.9),
                    f"d{j}_task_mean_capped":avg(v)})
    return res


def summarize_policies(rows,rng):
    by_cell = defaultdict(lambda:defaultdict(list))
    for r in rows:
        by_cell[key(r)][r["policy"]].append(r)
    summaries, contrasts, factorial = [],[],[]
    for cell in strata():
        m,n,b = cell
        g = by_cell[cell]
        g = {p:sorted(g[p],key=lambda r:r["seed"]) for p in POLICIES}
        assert all([r["seed"] for r in g[p]] == [r["seed"] for r in g["dual"]] for p in POLICIES)
        e = len(g["dual"])
        ids = rng.integers(e,size=(P,e))
        for pol in POLICIES:
            summaries.append(dict(layout=m,n=n,multiplier=b,policy=pol,**mean_line(g[pol])))
        effects_verdict = []
        for control in ("congestion","relative"):
            a_rate = np.asarray([r["throughput"] for r in g["dual"]])
            b_rate = np.asarray([r["throughput"] for r in g[control]])
            abs_rate = a_rate-b_rate
            mean_comparison = a_rate[ids].mean(axis=1)
            base = b_rate[ids].mean(axis=1)
            ratio = (mean_comparison/base) if (base > 0).all() else []
            tau = {}
            for j in (2,3,4):
                v = np.asarray([x[f"f{j}"]-y[f"f{j}"] for x,y in zip(g["dual"],g[control])])*100
                tau[j]=(v.mean().item(), band(v[ids].mean(axis=1)),quant(v[ids].mean(axis=1),1-ADJ))
            rlo = quant(ratio, ADJ)
            sat = tau[3][2] < 0 and rlo is not None and rlo > 1-MARGIN
            effects_verdict.append(sat)
            contrasts.append(dict(layout=m,n=n,multiplier=b,n_seeds=e,control=control,
                                  f2_pp=tau[2][0], f2_ci=tau[2][1], f3_pp=tau[3][0],
                                  f3_ci=tau[3][1], f3_upper=tau[3][2],
                                  f4_pp=tau[4][0], f4_ci=tau[4][1],
                                  rate_diff=abs_rate.mean().item(), rate_diff_ci=band(abs_rate[ids].mean(axis=1)),
                                  rate_ratio=(a_rate.mean()/b_rate.mean()).item() if b_rate.mean()>0 else None,
                                  ratio_ci=band(ratio), rate_ratio_lower=rlo,
                                  this_control=sat, joint=False))
        if all(effects_verdict):
            contrasts[-1]["joint"]=contrasts[-2]["joint"]=True
        vals = {}
        for stat,factor in (("f3",100),("throughput",1)):
            a,c,p,f = (np.asarray([r[stat] for r in g[method]]) for method in
                       ("dual","congestion","protect_fixed","fixed"))
            d = (a-c-p+f)*factor
            vals.update({f"{stat}_protected_congestion":avg((a-c)*factor),
                         f"{stat}_protected_fixed":avg((p-f)*factor),
                         f"{stat}_interaction":avg(d),f"{stat}_ci":band(d[ids].mean(axis=1))})
        factorial.append(dict(layout=m,n=n,multiplier=b,n_seeds=e,**vals))
    return summaries,contrasts,factorial


def summarize_mechanisms(budget, route):
    altered = [r["result"] for r in route if r["result"] is not None]
    return dict(budget_tried=len(budget),
                budget_rescued=sum(not r["first"]["path"] and bool(r["higher"]["path"]) for r in budget),
                route_tried=len(route), route_swap=len(altered),
                route_local_changes=sum(r["old_local"]["path"]!=r["alt_local"]["path"] for r in altered),
                route_local_success_changes=sum(bool(r["old_local"]["path"])!=bool(r["alt_local"]["path"]) for r in altered),
                route_execution_changes=sum(r["old_exec"]!=r["alt_exec"] for r in altered))


def choose_examples(pairs,gate_pairs):
    def all_first(q):
        i=q["focus"]; first=q["baseline"]["first"][i]
        return q["category1"] and len(set(first))==1 and q["at_risk"][i]
    a = next((q for q in [*pairs,*gate_pairs] if all_first(q)),None)
    if a is None:
        a=next(q for q in pairs if q["category1"])
    def both_done(q,j):
        return all(q[b]["task"][j] is not None for b in ("baseline","treatment"))
    b = next(q for q in pairs if q["category2"] and both_done(q,q["focus"]))
    c = next((q for q in gate_pairs if q["co_burden_gate"] and both_done(q,q["focus"])
              and any(both_done(q,j) for j in q["others_later"])),None)
    if c is None:
        c = next((q for q in gate_pairs if q["category3"]),None)
    a["sample_type"] = "main" if a in pairs else "gate"
    b["sample_type"] = "main"
    if c is not None:
        c["sample_type"] = "gate"
    return dict(A=a,B=b,C=c)


def main():
    rng = np.random.default_rng(BOOT_SEED)
    selection = read("selection.jsonl")
    pairs = read("pairs.jsonl.gz")
    gate_sel = read("gate_selection.jsonl")
    gate = read("gate_pairs.jsonl.gz")
    summaries,contrasts,factorial = summarize_policies(read("policies.jsonl.gz"),rng)
    primary = summarize_pairs(selection,pairs,rng)
    probe = summarize_pairs(gate_sel,gate,rng,True)
    res = dict(primary=primary,probe=probe,
               summaries=summaries,contrasts=contrasts,factorial=factorial,
               mechanisms=summarize_mechanisms(read("mechanism_budget.jsonl"),read("mechanism_route.jsonl")),
               examples=choose_examples(pairs,gate),critical_tail=ADJ)
    (DATA/"results.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for prefix, d in (("overdue",primary),("gate",probe)):
        for keyname in ("cells","rank","sources"):
            write_csv(prefix+"_"+keyname+".csv",d[keyname])
    for name,data in (("policy_summary",summaries),("policy_effects",contrasts),("factorial",factorial)):
        write_csv(name+".csv",data)
    print("Primary",primary["total"])
    print("Bottleneck probe",probe["total"])
    print("Mechanisms",res["mechanisms"])
    print("Strata passing the primary criterion:",
          [(r["layout"],r["n"],r["multiplier"]) for r in contrasts if r["joint"] and r["control"]=="congestion"])


if __name__ == "__main__":
    main()
