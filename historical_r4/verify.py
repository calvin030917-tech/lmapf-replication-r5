"""Check replay validity, search budgets, and the reported outcome distinctions."""
import gzip
import json
from pathlib import Path

from protocol import LOOK, EXEC, W
from simulator import layout, paths_valid


def load_rows(path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(s) for s in f]


def censored_time(t):
    return LOOK if t is None else t


def check_pair(q, grid=None):
    grid = layout(q["layout"]) if grid is None else grid
    f = q["focus"]
    a,b = q["baseline"],q["treatment"]
    assert [f]+[i for i in q["order"] if i!=f] == q["promoted"]
    assert q["order"][q["rank"]-1] == f and q["rank"]>1
    assert all(x[0]==y[0] for x,y in zip(a["path"],b["path"]))
    for out in (a,b):
        assert paths_valid(grid, out["window"])
        assert paths_valid(grid, out["path"])
        assert all(p[:EXEC+1] == f for p,f in zip(out["path"],out["first"]))
        assert all(p[:EXEC+1] == f for p,f in zip(out["window"],out["first"]))
        assert all(len(w)==W+1 for w in out["window"])
        assert sum(r["expanded"] for r in out["solver"]) <= q["budget"]
        assert not out["published"] == out["fallback"]
        for i,r in enumerate(out["solver"]):
            assert out["window"][i] == (r["path"] or q["seed_paths"][i])
            reached = next((t for t,p in enumerate(out["path"][i]) if p==q["goals"][i]),None)
            assert reached == out["task"][i]
    task = [censored_time(y)-censored_time(x) for x,y in zip(a["task"],b["task"])]
    assert q["task_delta"] == task
    gained = (a["solver"][f]["status"]=="not_started" and b["solver"][f]["status"]!="not_started")
    changed = a["first"][f]!=b["first"][f]
    assert q["category1"] == (gained and not changed)
    assert q["category2"] == (changed and task[f]>=0)
    assert q["category3"] == (task[f]<0 and any(i!=f and v>0 for i,v in enumerate(task)))


def main():
    p = Path("data")
    for file,n,counts in (("pairs",367,[26,12,0]),("gate_pairs",480,[43,10,16])):
        rows = load_rows(p/(file+".jsonl.gz"))
        assert len(rows)==n
        for q in rows:
            check_pair(q)
        assert [sum(q[f"category{i}"] for q in rows) for i in (1,2,3)] == counts
        print(f"{file}: {n} verified pairs, event counts {counts}")
    s = json.loads((p/"small_cases.json").read_text())
    assert s["S0"]["exact"]["expansions"] == 10
    assert [x["expansions"] for x in s["S1"]["by_window"]] == [20,29]
    assert s["S1"]["online"][0]["planner_submitted"] and not s["S1"]["online"][0]["fallback"]
    assert len(s["S2"]["exact"]["path"]) == 4 and s["S2"]["equal_path"]["low_expanded"] == 1
    assert s["S3"]["stay"]["status"] == "exhausted" and len(s["S3"]["release"]["path_with_arrival_flags"]) == 4
    rows = load_rows(p/"policies.jsonl.gz")
    assert len(rows)==len({(r["layout"],r["n"],r["multiplier"],r["seed"],r["policy"]) for r in rows})==896
    assert all(sum(group[0] for group in r["by_length"])==144*r["n"] for r in rows)
    outputs = json.loads((p/"results.json").read_text())
    assert len(outputs["contrasts"]) == 16 and not any(r["joint"] for r in outputs["contrasts"])
    print("Small cases and 896 distinct policy runs verified.")


if __name__ == "__main__":
    main()
