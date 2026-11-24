# R4 历史复现文件指南 · R4 historical replication file guide

这里保留 R4 仿真设计、运行与核验脚本、原始日志、汇总表和双语论文插图。复现命令见 [README.md](README.md)。

This archive holds the R4 simulation design, execution and verification scripts, raw logs, summary tables, and bilingual paper figures. See [README.md](README.md) for reproduction commands.

本项目中的论文源文件位于 [manuscript_cn/](../manuscript_cn/) 和 [manuscript_en/](../manuscript_en/)。历史 README 中的论文构建示例采用 R4 归档时的目录结构。

The current project stores its manuscript sources in [manuscript_cn/](../manuscript_cn/) and [manuscript_en/](../manuscript_en/). The manuscript build example in the historical README follows the original R4 archive layout.

[返回项目文件指南 · Project file guide](../FILE_GUIDE.md)

## 子目录 · Subdirectories

| 子目录 · Directory | 中文用途 | English purpose |
| --- | --- | --- |
| [data/](data/FILE_GUIDE.md) | 原始运行、快照选择记录、成对轨迹、局部对照和结果汇总。 | Raw runs, snapshot selection records, paired trajectories, local controls, and summary results. |
| [figures/](figures/FILE_GUIDE.md) | 中文历史论文插图，每张提供 PNG 和 SVG。 | Chinese historical paper figures, each available in PNG and SVG. |
| [figures_en/](figures_en/FILE_GUIDE.md) | 英文历史论文插图，每张提供 PNG 和 SVG。 | English historical paper figures, each available in PNG and SVG. |

## 设计、文献和运行环境 · Design, literature, and environment

| 文件 · File | 中文用途 | English purpose |
| --- | --- | --- |
| [README.md](README.md) | 历史复现的入口，给出环境、运行顺序、输出范围和截尾时间的读法。 | Entry point for historical reproduction, with environment, run order, output scope, and guidance on capped times. |
| [PROTOCOL.md](PROTOCOL.md) | 主分析的试验设计，定义地图、共享搜索预算、一次提权事件、配对抽样和策略比较。 | Main experimental design defining maps, shared search budget, single-promotion events, paired sampling, and policy comparisons. |
| [GATE_PROBE.md](GATE_PROBE.md) | 瓶颈探索样本的独立种子、受阻候选条件、抽样规则及估计范围。 | Independent seeds, blocking criteria, sampling rules, and scope for the exploratory bottleneck sample. |
| [VALIDATION.md](VALIDATION.md) | 预先规定同条件对向比较、新布局留出验证及同快照种子构造对照。 | Prespecifies matched opposition comparisons, holdout layouts, and same-snapshot controls for seed construction. |
| [R4_METHODS.md](R4_METHODS.md) | 说明瓶颈分段计时、规划器规则、匹配与统计推断方法，以及复核入口。 | Defines bottleneck split clocks, planner rules, matching and inference methods, and audit entry points. |
| [REVISION_NOTES.md](REVISION_NOTES.md) | 将本轮修订与审稿意见对应，定位更新过的分析和证据。 | Maps the revision to reviewer comments and identifies updated analyses and supporting evidence. |
| [LITERATURE.md](LITERATURE.md) | 记录检索问题、筛选过程与文献证据的纳入范围。 | Records literature queries, screening, and which evidence is in scope. |
| [literature_evidence.tsv](literature_evidence.tsv) | 按参考文献列出中英文机制、证据描述、原文位置和核验链接。 | Tab-separated bilingual mechanism, evidence, source locator, and verification URL for each reference. |
| [literature_screening.csv](literature_screening.csv) | 保存检索命中的次序、标题和纳入或排除理由。 | Preserves ranked search hits, titles, and reasons for inclusion or exclusion. |
| [requirements.txt](requirements.txt) | 指定运行历史统计和绘图所需的 NumPy、Matplotlib 最低版本。 | Specifies minimum NumPy and Matplotlib versions for historical analysis and plotting. |

## 仿真、分析和绘图 · Simulation, analysis, and plotting

| 文件 · File | 中文用途 | English purpose |
| --- | --- | --- |
| [protocol.py](protocol.py) | 定义地图、车辆数、预算层、试验种子和采样参数供各脚本使用。 | Defines experiment strata, seed splits, and sampling parameters shared by the scripts. |
| [simulator.py](simulator.py) | 实现历史网格地图、任务流、安全种子、预留表、限额搜索和滚动执行。 | Implements historical grid maps, task streams, safe seed paths, reservations, budgeted search, and rolling execution. |
| [diagnose.py](diagnose.py) | 比较焦点车辆提权前后轨迹，并实现固定预留加预算和替换前车候选路径的局部对照。 | Compares baseline and one-time promotion trajectories and implements local controls for added budget and alternate predecessor paths. |
| [run.py](run.py) | 批量生成主诊断、持续策略测试及局部机制运行的数据。 | Batch-runs the primary diagnostics, continuous-policy comparisons, and local mechanism experiments. |
| [gate_probe.py](gate_probe.py) | 执行独立的瓶颈受阻探索试验并写出其抽样记录和配对。 | Runs the independent bottleneck-blocking probe and writes its selection records and pairs. |
| [small_cases.py](small_cases.py) | 构造固定目标的小例子，计算精确参照并记录短窗口执行，用于检查规则语义。 | Builds small fixed-goal cases, computes exact references, and records short-window executions to examine rule semantics. |
| [validation.py](validation.py) | 定义 Ladder 和 Offset 留出布局及串行安全种子，生成同条件与留出验证数据。 | Defines the Ladder and Offset holdout layouts and serial safe seeds, then generates matched and holdout validation data. |
| [analyze.py](analyze.py) | 从日志生成诊断、策略和机制统计，计算按场景重采样的区间，并选取绘图案例。 | Produces diagnostic, policy, and mechanism summaries, computes scenario bootstrap intervals, and selects examples for figures. |
| [revision_audit.py](revision_audit.py) | 从原始轨迹重建 R4 表、复核案例时序与跨机器人影响，并比较同快照种子。 | Reconstructs R4 tables from trajectories, audits case clocks and impacts on other robots, and compares seeds on identical snapshots. |
| [verify.py](verify.py) | 检查早期配对轨迹的合法性、搜索预算和结局分类。 | Checks legality, search budgets, and outcome distinctions for the earlier paired trajectories. |
| [verify_r4.py](verify_r4.py) | 核验验证样本的入选、配对、事件标签、时钟恒等式及主策略判据。 | Verifies validation eligibility, pairing, event labels, clock identities, and primary policy criteria. |
| [check_r5_legacy.py](check_r5_legacy.py) | 用原求解器核验历史原序分支，复算案例 B 的终点规则对照并导出 R5 历史检查结果。 | Audits historical original-order replays with the original solver, reruns the Case B goal-rule control, and exports the R5 historical checks. |
| [figures.py](figures.py) | 由场景、轨迹和汇总数据生成带中文或英文标签的历史论文插图。 | Regenerates historical paper figures with Chinese or English labels from scenarios, replays, and summaries. |
| [corridor_figure.py](corridor_figure.py) | 绘制固定起终点的退避格示意和六步合法轨迹示例。 | Draws the retreat-cell example and its legal six-step trajectory with fixed starts and goals. |
| [figure_labels.py](figure_labels.py) | 提供历史论文插图所用的中文标签与英文译文。 | Provides the Chinese plot labels and their English translations. |
