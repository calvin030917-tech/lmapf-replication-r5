"""R5 manuscript tables, rebuilt from the validation summaries and archived outputs."""
from collections import Counter
import gzip
import json
from pathlib import Path

from tables_r4 import build_tables as old

ROOT=Path(__file__).resolve().parent.parent
R5_DATA=ROOT/"r5/data_r5"
data=json.loads((R5_DATA/"r5_summary.json").read_text())
old_checks=json.loads((R5_DATA/"r5_historical_checks.json").read_text())


def build_tables(lang):
    assert lang=="cn"
    ts=old(lang)

    def add(k,title,headers,rows,widths,note="",size=None):
        assert all(len(row)==len(headers)==len(widths) for row in rows)
        assert abs(sum(widths)-6.7)<.011
        ts[k]=(title,headers,rows,widths,note,size)

    add("toy","表3A　固定目标的联合参照与旧式顺序例程",
        ["算例","输出来源","限定条件","结论或见证"],
        [
            ["S0","联合 BFS","五格直线，首次到达后留驻","穷尽10个配置，无固定目标联合解。"],
            ["S0","旧式顺序完整计划","A先，预算20","找不到完整联合计划，回退为全队等待。"],
            ["S1","联合 BFS","添退避格，深度4／5","深度4不可能全部完成，展开20；深度5得最短解，展开29。"],
            ["S2","联合 BFS","二维六格，首次到达后留驻","3步可完成，展开15。"],
            ["S2","旧式顺序完整计划","A先，预算20","第一条 A 最短路阻断 B，回退全队等待。换同长路径有解。"],
            ["S2","旧式顺序完整计划","B先，预算3／20","预算3截断并全队等待，预算20提交3步计划。"],
            ["S3","联合 BFS","四格T形，留驻／释放","留驻穷尽5次。允许到达后离开，有3步完成见证。"],
        ],[.68,1.46,1.85,2.71],
        "旧式例程在完整计划失败时让全队等待。联合参照只回答冻结目标和所列终点语义下的可行性。")
    status={"window":"窗末","budget":"截断","not_started":"未启动","exhausted":"穷尽","goal":"到达"}

    def hits(v):
        return "／".join("—" if x is None else str(x) for x in v)
    toy_live=[]
    for label,a in old_checks["small"].items():
        for q in a["algorithm1"]:
            order="A→B" if q["order"]==[0,1] else "B→A"
            toy_live.append([label,q["window"],q["budget"],order,
                            "／".join(status[t["status"]] for t in q["trace"]),
                            q["fallback_count"],hits(q["hits_in_committed_window"]),
                            hits(q["hits_in_executed_prefix"])])
    add("toy_actual","表3B　算法1首轮的提交与实际执行",
        ["算例","窗长W","上限","顺序","A／B 查询","回退车辆","承诺窗口达标步","实执行两步达标"],
        toy_live,[.61,.70,.62,.71,1.11,.73,1.15,1.07],
        "未返回候选的车辆个别沿用安全种子。达标步列按 A／B 排列。空项表示在该列观察范围内未达标。")
    def rename(k,src,dest):
        t=ts[k]
        ts[k]=(t[0].replace(src,dest),*t[1:])
    rename("events","首轮事件与截断时间差","首轮动作和32步服务事件")
    rename("descriptive","表9","表12")
    rename("bounds","表10","表13")
    oldb=ts["bounds"]
    ts["bounds"]=(oldb[0],["表13\n"+oldb[1][0],*oldb[1][1:]],*oldb[2:])
    hist=ROOT/"historical_r4/data"
    with gzip.open(hist/"holdout_pairs.jsonl.gz","rt") as f:
        groups={k:[] for k in ("recursive","serial")}
        for line in f:
            q=json.loads(line)
            groups[q["constructor"]].append(q)
    panels=[]
    for vs in groups.values():
        tags=Counter()
        for q in vs:
            for i,ab in enumerate(zip(q["baseline"]["task"],q["treatment"]["task"])):
                if i==q["focus"]:
                    continue
                a,b=ab
                tags[(a is not None,b is not None)]+=1
                tags["a32"]+=a==32
                tags["b32"]+=b==32
        panels.append([len(vs),tags[True,True],f"{tags[True,False]:,}／{tags[False,True]:,}",
                       tags[False,False],f"{tags['a32']:,}／{tags['b32']:,}"])
    add("constructors","表A3　R4新合成布局中的他车完工状态，按种子构造分列",
        ["构造","快照配对","两边完工","仅原序／仅提权","两边未完工","第32步完工 原／提"],
        [[k,*[f"{x:,}" if isinstance(x,int) else x for x in group]]
         for k,group in zip(("递归","串行"),panels)],[.83,.93,1.05,1.48,1.10,1.31],
        "逐车配对排除焦点。焦点在递归组两臂分别完工530／532和529／532，在串行组均为0／720。")
    rename("others","完工用时差","完工截断用时差")
    raw=ts["others"]
    changed=[[str(r[0]).replace("逐车时间差","逐车截断差"),*r[1:]] for r in raw[2]]
    ts["others"]=(raw[0],raw[1],changed,*raw[3:])
    px=data["proxies"]
    add("proxy","表9　同一批460个快照上，规划观测对实际提前完工的识别",
        ["规划观测","命中","误报","漏报","正确未报","命中中他车也延误"],
        [(name,*[px[k][col] for col in ("tp","fp","fn","tn","early_other_delay")])
         for name,k in (("首步方向改善","proposed_direction"),("两步剩余距离改善","proposed_distance"))],
        [1.68,.78,.78,.78,1.02,1.66],
        "39个配对的焦点32步截断用时确实缩短，其中30个至少有一辆他车截断用时增加。")
    pr=data["probes_verified"]
    ab=data["by_arm"]
    add("mechanisms","表10　逐查询归因的独立固定预留参照",
        ["标签","原序阳性","提权阳性","合计","假阳性","假阴性"],
        [[label,ab["baseline"][k],ab["promoted"][k],pr[k]["positive"],pr[k]["fp"],pr[k]["fn"]]
         for k,label in (("budget","B 预算"),("reservation","R 预留"),("goal_rule","G 终点规则"),("horizon","W 窗长"))],
        [1.61,1.12,1.12,.86,.99,1.0],
        "920条查询，每个配对两条。标签可并存，31条查询具备多标签，四项最早到达时钟共核验3,680次。")
    formatcell=lambda r:f"{r['layout'].upper()} · {r['n']} · {r['cap']}"
    add("public_cells","表11　公开布局按场景的服务及提权结果",
        ["图·车·上限","平均吞吐","配对","事件①／②／③","原／提完工","同边事件③","无同边事件③"],
        [[formatcell(r),f"{r['mean_rate']:.2f}",r["pairs"],
          f"{r['event1']}／{r['event2']}／{r['event3']}",f"{r['baseline_done']}／{r['promoted_done']}",
          f"{r['e3_matched']}/{r['matched']}", f"{r['e3_unmatched']}/{r['pairs']-r['matched']}"]
         for r in data["cells"]],
        [1.06,.85,.56,1.16,1.05,1.00,1.02],
        "每格16个场景。吞吐单位为项／100步。第32步恰好完成计入完工。两列同边状态以该组配对为分母。")
    fmt=lambda a:f"{a:+.2f}".replace("-","−") if abs(a)>=.005 else "0.00"
    def est(r,k):
        return f"{fmt(r[k])}\n[{', '.join(fmt(x) for x in r[k+'_ci'])}]"
    add("more_policies","表B3　公开布局的新种子策略配对与对齐任务",
        ["图·车·上限","吞吐差","超龄差百分点","首任务完工差百分点","首任务截断差（步）"],
        [[formatcell(r),est(r,"rate"),est(r,"overdue_pp"),est(r,"cohort_by64_pp"),est(r,"cohort_capped")]
         for r in data["policy"]],[1.04,1.21,1.22,1.55,1.68],
        "双阶段减剩余距离。每层16对新场景，括号内为双侧点位95%区间。首任务两边同在第0步发出，随访64步。")
    add("workload","表C1　SIPP 规划每轮整段耗时与工作量",
        ["图·车·上限","耗时P50／P95 ms","种子测试 P50","安全区间展开 P50","邻格区间测试 P50","预留写删 P50"],
        [[formatcell(r),f"{r['wall_ms_p50']:.2f}／{r['wall_ms_p95']:.2f}",f"{r['seed_tests_p50']:g}",
          f"{r['interval_expanded_p50']:g}",f"{r['edge_tests_p50']:g}",f"{r['reservation_writes_p50']:g}"]
         for r in data["workload"]],
        [1.11,1.23,.92,1.16,1.17,1.11],
        "同一主机串行运行。每层取种子6101，预热后96轮。计时含排序、种子、搜索、预留与合法性检查。")
    return ts
