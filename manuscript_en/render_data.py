"""Write LaTeX results directly from the R5 data."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
results=json.loads((ROOT.parent/"data_r5/r5_summary.json").read_text())
queries=results["queries"]
px=results["proxies"]
pr=results["probes_verified"]

values={"BenchRuns":results["source_n"],"BenchPairs":results["pairs"],
        "BenchQueries":queries,"RefChecks":f"{results['time_checks']:,}",
        "Earlier":px["proposed_direction"]["tp"]+px["proposed_direction"]["fn"],
        "Tradeoffs":results["e_counts"][2],"DirectionHits":px["proposed_direction"]["tp"],
        "ProgressHits":px["proposed_distance"]["tp"],
        "RateLow":f"{results['source_range'][0]:.2f}","RateHigh":f"{results['source_range'][1]:.2f}"}
def rows(seq):
    return "\n".join(" & ".join(map(str,line))+" \\\\" for line in seq)

def write(name,body):
    (ROOT/name).write_text(body+"\n")

write("generated_values.tex","\n".join(r"\newcommand{"+f"\\{k}"+"}{"+f"{val}"+"}" for k,val in values.items()))
write("generated_proxy.tex",rows([(name,*[px[k][x] for x in ("tp","fp","fn","tn")])
                                 for name,k in (("First direction","proposed_direction"),
                                                ("Two-step progress","proposed_distance"))]))
write("generated_mechanisms.tex",rows([(label,pr[name]["positive"],pr[name]["fp"],pr[name]["fn"])
                                      for name,label in zip(pr,("Budget","Reservations","Goal rule","Window"))]))
f=lambda r:f"{r['layout'].upper()} / {r['n']} / {r['cap']}"
write("generated_cells.tex",rows([
    (f(r),f"{r['mean_rate']:.2f}",r["pairs"],f"{r['event1']}/{r['event2']}/{r['event3']}",
     f"{r['baseline_done']}/{r['promoted_done']}",f"{r['e3_matched']}/{r['matched']}",
     f"{r['e3_unmatched']}/{r['pairs']-r['matched']}")
    for r in results["cells"]]))
def signed(v):
    return f"{v:+.2f}" if abs(v)>=.005 else "0.00"
def est(r,k):
    return f"{signed(r[k])} [{', '.join(signed(x) for x in r[k+'_ci'])}]"
write("generated_policy.tex",rows([
    (f(r),est(r,"rate"),est(r,"overdue_pp"),est(r,"cohort_by64_pp"),est(r,"cohort_capped"))
    for r in results["policy"]]))
write("generated_workload.tex",rows([
    (f(r),f"{r['wall_ms_p50']:.2f}/{r['wall_ms_p95']:.2f}",f"{r['seed_tests_p50']:g}",
     f"{r['interval_expanded_p50']:g}",f"{r['edge_tests_p50']:g}",f"{r['reservation_writes_p50']:g}")
    for r in results["workload"]]))
