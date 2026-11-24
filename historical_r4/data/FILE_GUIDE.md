# R4 历史数据文件指南 · R4 historical data file guide

配对记录包含原顺序和一次提权两条分支。阅读截尾完工或出区用时时，请同时查阅是否观察到对应事件。[计时定义与核验方法](../R4_METHODS.md)

Paired records contain the original-order and single-promotion branches. Read capped completion and strip-exit times alongside the corresponding event flags. [Clock definitions and audit methods](../R4_METHODS.md)

[返回历史复现文件指南 · Historical replication file guide](../FILE_GUIDE.md)

## 原始记录和局部对照 · Raw records and local controls

| 文件 · File | 中文用途 | English purpose |
| --- | --- | --- |
| [selection.jsonl](selection.jsonl) | 主超龄试验的逐次运行抽样记录，保留候选周期、焦点名次与抽中时刻。 | Per-run selection records for the primary overdue experiment, with eligibility counts, focal ranks, and sampled ticks. |
| [pairs.jsonl.gz](pairs.jsonl.gz) | 主超龄样本的 367 个配对，保存两分支的规划与后续执行结局。 | The 367 primary overdue pairs, with plans and follow-up outcomes for both arms. |
| [gate_selection.jsonl](gate_selection.jsonl) | 瓶颈探索试验逐次运行的候选、筛除和抽样记录。 | Per-run eligibility, exclusions, and sampling for the exploratory bottleneck experiment. |
| [gate_pairs.jsonl.gz](gate_pairs.jsonl.gz) | 瓶颈探索组的 480 个配对，包含焦点与其他车辆的轨迹、出区和完工结局。 | The 480 exploratory bottleneck pairs, with focal and other robots’ trajectories, strip exits, and completion outcomes. |
| [matched_source_runs.jsonl](matched_source_runs.jsonl) | 同条件验证的来源运行元数据及其步数、完成量和吞吐量。 | Source-run metadata, durations, completions, and throughput for the matched validation. |
| [matched_selection.jsonl.gz](matched_selection.jsonl.gz) | 同条件验证的每个预定时刻及其焦点、名次、入选状态和对向标签。 | Scheduled matched-validation ticks with focal robot, rank, selection status, and opposition label. |
| [matched_pairs.jsonl.gz](matched_pairs.jsonl.gz) | 相同焦点筛选条件下入选的 445 个配对，供比较有无对向交通。 | The 445 selected pairs for comparing presence or absence of opposing traffic under the same focal-selection rule. |
| [holdout_source_runs.jsonl](holdout_source_runs.jsonl) | 新布局留出验证的逐次来源运行吞吐量，按种子构造器记录。 | Per-run source throughput for the new-layout holdout, recorded by seed constructor. |
| [holdout_selection.jsonl.gz](holdout_selection.jsonl.gz) | 新布局上两种种子构造的预定时刻、焦点信息和入选判定。 | Scheduled ticks, focal information, and selection decisions for the two seed constructors on the new layouts. |
| [holdout_pairs.jsonl.gz](holdout_pairs.jsonl.gz) | Ladder 和 Offset 布局的 1,252 个留出配对轨迹，涵盖递归和串行种子。 | The 1,252 paired holdout trajectories on Ladder and Offset, covering recursive and serial seed construction. |
| [holdout_alternative_first_round.jsonl.gz](holdout_alternative_first_round.jsonl.gz) | 从递归来源的同一批快照出发，在首轮改用串行种子进行对照的 532 个配对。 | The 532 pairs that use a serial seed in the opening round on the same snapshots from recursive source runs. |
| [mechanism_budget.jsonl](mechanism_budget.jsonl) | 固定查询预留时增加焦点预算的局部再查询记录，含查找结果和原预算。 | Local focal-query reruns with added budget under fixed reservations, with baseline budgets and search outcomes. |
| [mechanism_route.jsonl](mechanism_route.jsonl) | 替换前车等价候选路径后的局部对照记录，保留有无适用替代路径的结果。 | Local controls for replacing a predecessor’s candidate path with an equivalent one, including cases without an eligible alternative. |
| [policies.jsonl.gz](policies.jsonl.gz) | 896 次持续策略运行的原始统计，含吞吐、超龄车辆步和服务尾部指标。 | Raw statistics from 896 continuous-policy runs, including throughput, overdue robot-steps, and service-tail measures. |
| [small_cases.json](small_cases.json) | 小规模固定目标案例 S0 至 S3 的配置、精确参照和窗口规划结果。 | Configurations, exact references, and window-planning records for fixed-goal cases S0 through S3. |
| [r4_case_replays.json](r4_case_replays.json) | 案例 A、B、C 的完整重放，含顺序、种子、查询预留和路径。 | Full replays of Cases A, B, and C, with orderings, seeds, query reservations, and paths. |

## 汇总表与核验结果 · Summary tables and audit results

| 文件 · File | 中文用途 | English purpose |
| --- | --- | --- |
| [overdue_cells.csv](overdue_cells.csv) | 按来源规则、地图、车数和预算层汇总主超龄样本的纳入流程和结局。 | Summarizes inclusion and outcomes for the primary overdue sample by source policy, map, fleet size, and budget. |
| [overdue_rank.csv](overdue_rank.csv) | 按焦点原顺序名次分组汇总主超龄样本的入选和事件数。 | Summarizes primary overdue eligibility and outcomes by baseline focal rank group. |
| [overdue_sources.csv](overdue_sources.csv) | 主超龄样本按状态来源规则汇总的运行数、取样和诊断结局。 | Run counts, selection, and diagnostic outcomes for the primary overdue sample by source policy. |
| [gate_cells.csv](gate_cells.csv) | 按场景层汇总瓶颈探索的候选周期、抽样和成对事件。 | Candidate cycles, sampling, and paired events for the exploratory bottleneck sample by scenario stratum. |
| [gate_rank.csv](gate_rank.csv) | 瓶颈探索组按原顺序名次细分的候选数、配对数和结局。 | Candidate counts, pair counts, and outcomes for the bottleneck sample by baseline focal rank. |
| [gate_sources.csv](gate_sources.csv) | 瓶颈探索组按状态来源规则汇总的纳入流程和配对结局。 | Inclusion flow and paired outcomes for the exploratory bottleneck sample by source policy. |
| [policy_summary.csv](policy_summary.csv) | 各场景层与策略的吞吐、超龄和逐车服务分布统计。 | Throughput, overdue measures, and per-robot statistics by scenario stratum and policy. |
| [policy_effects.csv](policy_effects.csv) | 双阶段策略相对主比较基线的成对差异、区间和判据。 | Paired effects, intervals, and decision criteria for the two-stage policy versus the primary comparators. |
| [factorial.csv](factorial.csv) | 提取超龄保护与背景排序的 2×2 因子对照差值和交互效应。 | Contrasts and interaction effects from the 2×2 factorial comparison of overdue protection and background ordering. |
| [results.json](results.json) | 基础分析的机器可读汇总，包括主样本、瓶颈试验、机制、策略和绘图案例。 | Machine-readable base analysis of primary and bottleneck samples, mechanisms, policies, and figure examples. |
| [r4_distance_contrasts.csv](r4_distance_contrasts.csv) | 双阶段策略相对剩余距离排序的超龄率和吞吐量补充对比。 | Supplementary overdue-rate and throughput contrasts for the two-stage policy versus remaining-distance ordering. |
| [r4_gate_clocks_all.csv](r4_gate_clocks_all.csv) | 瓶颈探索每个焦点的首次入区、最后入区、出区与退回记录。 | First entry, last entry, strip exit, and retreats for each focal robot in the bottleneck sample. |
| [r4_gate_reconstruction.csv](r4_gate_reconstruction.csv) | 按分支和快照所在位置重建瓶颈分段时钟的总和与均值。 | Reconstructs segment clock sums and means by arm and snapshot location. |
| [r4_gate_vs_task_deltas.csv](r4_gate_vs_task_deltas.csv) | 列出出区用时差与任务完工用时差不一致的四个配对。 | Lists the four pairs where exit-time and task-completion deltas differ. |
| [r4_holdout_cells.csv](r4_holdout_cells.csv) | 汇总新布局留出试验的纳入情况、事件和效应，按布局、预算与种子构造器分组。 | Holdout inclusion, events, and effects grouped by layout, budget, and seed constructor. |
| [r4_interference_by_pair.csv](r4_interference_by_pair.csv) | 快照配对级记录，给出提权后其他车辆的延迟以及焦点是否提前。 | Pair-level records of other robots’ delays and whether the focal robot finished earlier after promotion. |
| [r4_interference_by_scenario.csv](r4_interference_by_scenario.csv) | 场景级汇总其他车辆变慢的配对和延迟分布。 | Scenario-level counts and delay distributions for cases with slower nonfocal robots. |
| [r4_interference_by_vehicle.csv](r4_interference_by_vehicle.csv) | 逐车记录两分支的完工状态、截尾用时和差值。 | Per-robot completion flags, capped times, and differences between the two arms. |
| [r4_interference_summary.csv](r4_interference_summary.csv) | 按样本及场景层汇总其他车辆变慢次数和延迟幅度。 | Summarizes frequencies and magnitudes of delays to other robots by sample and scenario stratum. |
| [r4_joint_bounds.csv](r4_joint_bounds.csv) | 策略主比较的多重校正界限与 0%、5%、10% 吞吐容差判定。 | Adjusted bounds and decisions at 0%, 5%, and 10% throughput tolerances for the primary policy comparisons. |
| [r4_mechanism_selection.csv](r4_mechanism_selection.csv) | 按场景层汇总局部预算与换轨对照的合格、测试和替代路径计数。 | Eligibility, tests, and alternate-path counts by stratum for the local budget and route controls. |
| [r4_results.json](r4_results.json) | 集中保存修订后的核验结果、主策略判定、留出证据与交叉对照统计。 | Consolidates revised audits, primary policy decisions, holdout results, and comparison statistics. |
| [r4_same_conditions.csv](r4_same_conditions.csv) | 在可比较设定下按布局、预算、原始名次和对向标签展示诊断事件。 | Reports diagnostic events by layout, budget, baseline rank, and opposition label in comparable settings. |
| [r4_same_snapshot_seed_comparison.csv](r4_same_snapshot_seed_comparison.csv) | 逐个递归来源快照比较两种首轮种子的路径和三个诊断事件是否一致。 | Compares first-round seed paths and agreement on three diagnostic events for each recursive-source snapshot. |
