"""Manuscript tables generated from the reported data and bibliographic locators."""

from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
REPRO = ROOT.parent/"historical_r4"
DATA = REPRO/"data"
R = json.loads((DATA/"r4_results.json").read_text(encoding="utf-8"))
ORIGINAL = json.loads((DATA/"results.json").read_text(encoding="utf-8"))


def build_tables(lang):
    cn = lang == "cn"
    def lang_text(a,b):
        return a if cn else b
    L = lang_text
    def enc(x):
        return "—" if x is None else f"{x:,.0f}"
    def signed(v, n=3):
        if abs(v)<.5*10**(-n):
            return f"{0:.{n}f}"
        return f"{v:+.{n}f}".replace("-", "−")
    def interval(values, n=3):
        return "["+", ".join(signed(v,n) for v in values)+"]"
    def yn(value):
        return L("是","Yes") if value else L("否","No")
    layouts = {"single":L("单中央","Single"),"bypass":L("旁路","Bypass"),
               "ladder":L("平行","Ladder"),"offset":L("错位","Offset")}
    names = {
        "age":L("原始任务年龄","Raw age"),"fixed":L("固定顺序","Fixed"),
        "relative":L("相对年龄","Relative age"),"congestion":L("局部拥堵","Congestion"),
        "distance":L("剩余距离","Remaining distance"),"dual":L("双阶段","Two-stage"),
        "protect_fixed":L("保护＋固定","Protection + fixed")}
    sample_names = {
        "R3_overdue":L("超龄主样本","Overdue"),
        "R3_gate":L("瓶颈探索","Exploratory"),
        "R4_matched":L("同条件验证","Matched conditions"),
        "R4_holdout":L("新地图","New layouts")
    }
    def cell(s):
        return f"{layouts[s['layout']]} · {s['n']} · {s['n']*s['multiplier']}"
    tables={}
    def add(key,no,caption,headers,rows,widths,note="",size=None):
        title=(f"表{no}　" if cn else f"Table {no}. ")+caption
        tables[key]=(title,headers,rows,widths,note,size)

    with (REPRO/"literature_evidence.tsv").open(encoding="utf-8",newline="") as f:
        lit=list(csv.DictReader(f,delimiter="\t"))
    add("literature",1,L("相关研究的决策、证据范围与原文定位","Related decisions, evidence, and source locations"),
        L(["文献","调整或考察的决策","原文支持的判断","定位及核对范围"],
          ["Study","Decision examined","Result or scope","Location checked"]),
        [[f"[{r['ref']}] {r['authors']}",r[f"mechanism_{lang}"],r[f"evidence_{lang}"],r[f"locator_{lang}"]] for r in lit],
        [1.02,1.40,2.49,1.79],
        L("可直接检索的正文或摘要链接见 literature_evidence.tsv。查询与去重日志见 literature_screening.csv。",
          "Direct text and abstract links are in literature_evidence.tsv. The query and screening log is literature_screening.csv."))

    policy_lines=[
        ("fixed","车辆编号升序","ID, ascending","关／固定","Off / fixed"),
        ("age","任务已耗步数降序","Time since goal issuance, descending","原始时长基线","Raw-age baseline"),
        ("relative","任务年龄除以初始最短路，降序","Task age divided by initial shortest distance, descending","主比较基线","Primary comparator"),
        ("congestion","曼哈顿距离2格内的他车数，降序","Other robots within Manhattan distance two, descending","关／拥堵，主基线","Off / congestion, primary comparator"),
        ("distance","静态剩余距离降序","Static remaining distance, descending","附加配对比较","Secondary comparator"),
        ("dual","相对年龄 >2.5 的车先按相对年龄排，其余按拥堵","Relative age >2.5 first, ordered by relative age, then congestion","开／拥堵","On / congestion"),
        ("protect_fixed","相对年龄 >2.5 的车先按相对年龄排，其余按车号","Relative age >2.5 first, ordered by relative age, then ID","开／固定","On / fixed")
    ]
    add("policies",2,L("排序规则及消融条件","Priority policies and factorial conditions"),
        L(["策略","排序","用途"],["Policy","Order","Role"]),
        [[names[p],L(a,b),L(c,d)] for p,a,b,c,d in policy_lines],[1.32,3.53,1.85],
        L("全部平局按车号。2.5为保护开关阈值，3为主要评价阈值。",
          "Robot ID breaks all ties. The protection cutoff is 2.5, and the primary evaluation cutoff is 3."))

    toy_cn=[
        ["S0 直线","留驻；10次展开后穷尽","无完成轨迹","完整计划未提交","全队等待"],
        ["S1 退避 W=4","深度内无全体完工；展开20","5步解的前4步","提交安全候选，窗内未完工","无"],
        ["S1 退避 W=5","找到解；展开29","最短5步","提交安全候选，窗内未完工","无"],
        ["S2 A 先","联合最短3步；展开15","3步联合见证","贪心路径使 B 无路","全队等待"],
        ["S2 同序换路","A先，替代等长候选","同序可行","A 第3步、B 第1步到达","无"],
        ["S2 B 先","联合可行","3步同序计划","3节点截断，20节点提交","3节点时等待"],
        ["S3 四格 T 形","留驻穷尽5，释放有解","释放时3步","未运行在线求解器","不适用"]
    ]
    toy_en=[
        ["S0 Line","Hold: exhausted after 10 expansions","No complete plan","No complete plan submitted","All wait"],
        ["S1 Refuge, W=4","No 4-step finish, 20 expansions","4-step prefix of 5-step plan","Safe window, no finish","None"],
        ["S1 Refuge, W=5","Solution, 29 expansions","Shortest: five steps","Safe window, no finish","None"],
        ["S2 A first","Joint optimum 3, 15 expansions","Joint 3-step witness","Greedy route blocks B","All wait"],
        ["S2 Same order","A first, equal route length","Feasible at same order","A arrives at 3, B at 1","None"],
        ["S2 B first","Jointly feasible","3-step ordered plan","Cap 3 cuts, cap 20 submits","All wait at cap 3"],
        ["S3 T graph","Hold exhausts 5, release feasible","Release: 3 steps","Online solver not run","N/A"]
    ]
    add("toy",3,L("固定目标的参考见证、在线提交与回退","Fixed-goal references, submitted plans, and fallbacks"),
        L(["算例","参考搜索","可行见证","实际提交","回退"],["Case","Reference search","Witness","Actual submission","Fallback"]),
        L(toy_cn,toy_en),[1.09,1.58,1.28,1.72,1.03],
        L("数据文件 small_cases.json 含坐标、展开和执行轨迹。","Coordinates, expansions, and paths are in small_cases.json."))

    r_sources=ORIGINAL["primary"]["sources"]+ORIGINAL["probe"]["sources"]
    add("samples",4,L("原始样本的快照筛选与配对数","Snapshot selection in the original cohorts"),
        L(["样本","轨迹数（贡献）","查阅周期","触发","已排首","可提权","抽取配对"],
          ["Cohort","Runs (contributing)","Ticks","Trigger","Already first","Eligible","Sampled"]),
        [[lab,f"{a['source_runs']} ({a['contributing_runs']})",
          *[enc(a[k]) for k in ("periods",tr,"already_first","eligible","picked")]]
         for lab,a,tr in zip([L("超龄·原始年龄","Overdue / raw age"),L("超龄·拥堵","Overdue / congestion"),L("瓶颈探索","Exploratory")],
                            r_sources,("overdue","overdue","gate_conflict_cycles"))],
        [1.52,1.22,.82,.62,.75,.74,1.03])
    ev=[]
    for i,a in enumerate(r_sources):
        cis=R["gate_bootstrap"] if i==2 else a
        ev.append([
            L(["超龄·原始年龄","超龄·拥堵","瓶颈探索"][i],["Overdue / raw age","Overdue / congestion","Exploratory"][i]),
            a["pairs"],a["category1"],a["category2"],a["category3"],a["gate_pairs"],
            f"{signed(a['focus_delta'])}\n{interval(cis['focus_task_ci'])}",
            f"{signed(a['gate_delta'])}\n{interval(cis['focal_gate_ci'])}"
        ])
    add("events",5,L("首轮事件与截断时间差","First-round events and capped time differences"),
        L(["样本","配对","①","②","③","出区分母","完工差（步）","出区差（步）"],
          ["Cohort","Pairs","E1","E2","E3","Exit n","Completion Δ (steps)","Exit Δ (steps)"]),
        ev,[1.18,.50,.35,.35,.35,.72,1.62,1.63],
        L("时间差为提权减原序，括号为场景重采样双侧95%区间。事件口径见§3.2。",
          "Differences are promoted minus original. Brackets are two-sided 95% scenario-bootstrap intervals. See §3.2 for events."))

    clocks=[]
    for a in R["reconstruction"]:
        arm=L("原序","Original") if a["arm"]=="baseline" else L("提权","Promoted")
        area={"outside":L("区外","Outside"),"inside":L("区内","Inside"),"total":L("全部","All")}[a["location"]]
        clocks.append([arm,area,a["n"],*[f"{a[k+'_mean']:.4f}" for k in (
            "before_first","entry_to_entry","final_segment","exit")],enc(a["exit_sum"])])
    add("clocks",6,L("探索样本从快照至出区的分组还原","Reconstruction of exploratory exit times"),
        L(["分支","初始位置","分母","F","L−F","E−L","E 均值","E 步数总和"],
          ["Arm","Start","n","F","L − F","E − L","Mean E","Total E steps"]),
        clocks,[.87,.93,.60,.75,.85,.85,.89,.96],
        L("时间均以步计。区外者有26次、区内者有84次在各分支中至少一次退回起始侧。",
          "Units are steps. In each arm, 26 outside starts and 84 inside starts retreat to the origin bank at least once."))

    filtered={a["sample"]:a for a in R["impact"] if a["layout"]=="all"}
    panels=[
        (L("快照配对数","Snapshot pairs"),lambda a:enc(a["pairs"])),
        (L("至少一辆他车变慢","Pairs with any delay elsewhere"),lambda a:enc(a["any_later"])),
        (L("至少两辆他车变慢","Pairs with ≥2 delayed robots"),lambda a:enc(a["pairs_two_or_more"])),
        (L("焦点未提前且他车变慢","Other delay without focal gain"),lambda a:enc(a["focus_not_earlier_others_later"])),
        (L("单配对最多变慢车辆数","Max. delayed robots in one pair"),lambda a:enc(a["slow_n_max"])),
        (L("逐车时间差：提前／相同／变慢","Robot-pair Δ: earlier / tied / later"),lambda a:" / ".join(enc(a[k]) for k in ("negative_n","zero_n","positive_n"))),
        (L("正差 P50／P90／最大（步）","Positive Δ: P50 / P90 / max (steps)"),
         lambda a:" / ".join(f"{a[k]:g}" for k in ("slow_time_p50","slow_time_p90","slow_time_max"))),
        (L("两边完成","Done in both arms"),lambda a:enc(a["both_done"])),
        (L("仅原序完成／仅提权完成","Done original only / promoted only"),lambda a:f"{enc(a['baseline_only'])} / {enc(a['promotion_only'])}"),
        (L("两边未完成","Unfinished in both arms"),lambda a:enc(a["both_open"])),
        (L("第32步完成：原序／提权","Finishes at 32: original / promoted"),lambda a:f"{enc(a['baseline_exact32'])} / {enc(a['promotion_exact32'])}")
    ]
    add("others",7,L("他车完工用时差及32步完成状态","Other robots' completion-time changes and status by step 32"),
        [L("指标","Measure")]+list(sample_names.values()),
        [[m]+[fun(filtered[s]) for s in sample_names] for m,fun in panels],
        [2.16,1.09,1.12,1.17,1.16],
        L("分布以逐车配对或快照配对统计。场景和逐车交叉项见 r4_interference_*.csv。",
          "Rows use either robot-level pairs or snapshot pairs as indicated. Scenario and robot records are in r4_interference_*.csv."))

    rates=defaultdict(list)
    for ln in (DATA/"holdout_source_runs.jsonl").read_text().splitlines():
        z=json.loads(ln)
        rates[z["layout"],z["multiplier"],z["constructor"]].append(z["throughput"])
    hold=[]
    for a in R["holdout_cells"]:
        m,b,c=a["layout"],a["multiplier"],a["constructor"]
        if m=="all":
            continue
        typ=L("递归","Recursive") if c=="recursive" else L("串行","Serial")
        hold.append([layouts[m],b*24,typ,a["n_scenarios"],a["pairs"],
                     f"{a['e1']} / {a['e2']} / {a['e3']}",f"{mean(rates[m,b,c]):.2f}"])
    add("holdout",8,L("新布局和任务流的计划执行结果","Replication on new layouts and goal streams"),
        L(["布局","节点","种子构造","场景","配对","①／②／③","来源吞吐"],
          ["Layout","Node cap","Constructor","Scenarios","Pairs","E1 / E2 / E3","Source rate"]),
        hold,[.91,.75,1.16,.83,.70,1.15,1.20],
        L("来源吞吐为第64步后至320步每100步的完工数。每图的两预算、两构造共享场景种子。",
          "Source rate is the number of completions per 100 steps from step 65 through 320. Seeds are shared across budgets and constructors on each map."))

    summary=[]
    for p in names:
        group=[a for a in ORIGINAL["summaries"] if a["policy"]==p]
        def num(k,multiplier=1):
            return f"{mean(r[k] for r in group)*multiplier:.2f}"
        summary.append([names[p],num("throughput")," / ".join(num(f"f{tau}",100) for tau in (2,3,4)),
                        f"{num('vehicle_median',100)} [{num('vehicle_q25',100)}, {num('vehicle_q75',100)}]",
                        num("vehicle_max",100),num("longest")])
    add("descriptive",9,L("七种排序的描述结果，八层等权","Descriptive policy outcomes, with eight equally weighted strata"),
        L(["排序","吞吐","超龄% τ=2／3／4","逐车中位数 [Q1, Q3] %","逐车最大 %","最长连续步"],
          ["Policy","Rate","Overdue % τ=2/3/4","Robot median [Q1, Q3] %","Robot max %","Max. spell"]),
        summary,[1.48,.66,1.22,1.65,.87,.82],
        L("吞吐单位为项／100步。每层16场景，分位数及最长段均先在单次运行内计算。",
          "Rate is completions per 100 steps. Each stratum has 16 scenarios. Within-run statistics are aggregated across scenarios."))

    bounds=[]
    for a in R["decision"]:
        bounds.append([cell(a),names[a["control"]],signed(a["f3_pp"]),signed(a["f3_upper"]),
                       signed(a["rate_diff"],2),f"{100*a['rate_ratio_lower']:.2f}%",
                       yn(a["overdue_pass"])+"/"+yn(a["rate_pass_5"]),yn(a["joint"])])
    add("bounds",10,L("长期策略的主要比较与 Bonferroni 校正界","Primary policy comparisons and adjusted bounds"),
        L(["布局·车·节点","基线","超龄差","上界 U","吞吐差","比值下界 L","分项 U/L","层联合"],
          ["Layout · N · B","Baseline","Overdue Δ","Upper U","Rate Δ","Ratio lower L","U/L pass","Joint"]),
        bounds,[1.28,1.12,.70,.70,.73,.78,.70,.69],
        L("超龄差及 U 为百分点，吞吐差为项／100步。每层16个配对场景，50,000次重采样。单界名义置信度99.84375%。U<0且L>95%为该基线通过。",
          "Overdue Δ and U are in pp. Rate Δ is per 100 steps. Each stratum has 16 paired scenarios and 50,000 replicates. Nominal confidence per bound is 99.84375%. U<0 and L>95% are required."))

    index={(r["sample"],r["layout"],r["multiplier"],r["rank"],r["opposed"]):r for r in R["same_conditions"]}
    strat=[]
    for g in ("single","bypass"):
        for b in (5,14):
            for k in ("2-4","5-8","9+"):
                row=[layouts[g],b*24,k.replace("-","–")]
                for sample,flag in (("R3_overdue_same_fleet","all"),("R3_gate","all"),("R4_matched",True),("R4_matched",False)):
                    a=index.get((sample,g,b,k,flag))
                    row.append(f"{a['e3']}/{a['pairs']}" if a else "0/0")
                strat.append(row)
    add("stratified","A1",L("固定24车与拥堵来源的事件③分层数","Stratified E3 counts at 24 robots and congestion ordering"),
        L(["布局","节点","原名次","超龄组","探索组","新验证·对向","新验证·无对向"],
          ["Layout","Cap","Rank","Overdue","Exploratory","New / Opposed","New / Unopposed"]),
        strat,[.86,.65,.77,.92,.95,1.24,1.31],
        L("0/0表示该比较格没有配对。","0/0 indicates an empty comparison cell."))

    common=R["common_snapshot"]
    same=[]
    for i in range(1,4):
        counts=common[f"e{i}"]
        same.append([L(f"事件{('①','②','③')[i-1]}",f"E{i}"),
                     *[counts[k] for k in ("both","recursive_only","serial_only","neither")]])
    add("same_seed","A2",L("同一批532个快照更换首轮公共种子的事件一致性",
                           "Event agreement on 532 identical snapshots under both initial seeds"),
        L(["事件","两种均有","仅递归","仅串行","两种均无"],
          ["Event","Both","Recursive only","Serial only","Neither"]),
        same,[1.15,1.17,1.50,1.50,1.38],
        L("首轮结束后两分支均恢复递归构造。","Both arms resume recursive construction after the intervention round."))

    inter=[]
    for s in R["factorial"]:
        inter.append([cell(s),s["n_seeds"],signed(s["f3_interaction"]),interval(s["f3_ci"]),
                      signed(s["throughput_interaction"]),interval(s["throughput_ci"])])
    add("factorial","B1",L("保护开关与背景排序的交互","Interaction of protection and background order"),
        L(["布局·车·节点","种子","超龄差中差","95%区间","吞吐差中差","95%区间"],
          ["Layout · N · B","Seeds","Overdue interaction","95% interval","Rate interaction","95% interval"]),
        inter,[1.30,.60,1.06,1.32,1.07,1.35],
        L("超龄单位为百分点。吞吐为项／100步。括号为点位双侧区间。",
          "Overdue units are pp, and throughput uses completions per 100 steps. Intervals are pointwise and two-sided."))

    distance=[]
    for a in R["distance"]:
        distance.append([cell(a),signed(a["overdue_pp"]),signed(a["overdue_upper"]),
                         signed(a["absolute_rate_diff"]),f"{100*a['rate_ratio']:.2f}%",
                         f"{100*a['rate_lower']:.2f}%",yn(a["this_control"])])
    add("distance","B2",L("双阶段相对剩余距离的配对比较","Two-stage ordering versus remaining-distance ordering"),
        L(["布局·车·节点","超龄差","上界 U","吞吐差","比值","下界 L","通过"],
          ["Layout · N · B","Overdue Δ","Upper U","Rate Δ","Ratio","Lower L","Pass"]),
        distance,[1.37,.88,.85,.90,.93,.93,.84],
        L("16个单侧界构成单独比较族，置信度99.6875%。每层16个配对场景。",
          "The 16 one-sided bounds form a separate family, with nominal 99.6875% confidence per bound. Each stratum has 16 paired scenarios."))
    return tables
