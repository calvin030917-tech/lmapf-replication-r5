# `r5/data_r5/` 文件说明 / File guide

[上一级文件索引 / Parent file guide](../FILE_GUIDE.md)

| 文件或目录 / File or folder | 中文说明 | English description |
| --- | --- | --- |
| [`analysis_log.txt`](analysis_log.txt) | 原版 R5 分析运行日志，保留脚本输出的汇总，便于查验。 | Archived output of the original R5 analysis run for inspection. |
| [`r5_fixtures.json`](r5_fixtures.json) | 七个受控小例，记录输入、期望机制、查询结果和独立路径见证。 | Seven controlled fixtures with inputs, expected mechanisms, query results, and independent path witnesses. |
| [`r5_historical_checks.json`](r5_historical_checks.json) | R4 补核结果，涵盖原序完整重放、案例 B 和小规模参考案例。 | R4 follow-up checks covering complete original-order replays, case B, and small reference cases. |
| [`r5_pair_summary.csv`](r5_pair_summary.csv) | 每行一个配对快照，列出焦点完工差、其他车辆延误、代理判断和机制标签。 | One row per paired snapshot with focal completion change, other delays, proxy predictions, and probe labels. |
| [`r5_pairs.jsonl.gz`](r5_pairs.jsonl.gz) | 460 个配对快照的压缩原始记录，含两臂轨迹、规划比较、焦点查询和时空预留。 | Compressed raw records of 460 paired snapshots with both trajectories, plan comparisons, focal queries, and reservations. |
| [`r5_policy_comparison.csv`](r5_policy_comparison.csv) | 八个地图、车队和预算组合的双阶段与剩余距离策略配对差值及区间。 | Dual-stage versus remaining-distance contrasts and intervals for eight map, fleet, and budget settings. |
| [`r5_policy_runs.jsonl.gz`](r5_policy_runs.jsonl.gz) | 256 次补充策略运行，记录吞吐、超龄暴露和第零批任务的首次到达。 | 256 supplementary policy runs with throughput, overdue exposure, and first arrivals for the initial task cohort. |
| [`r5_query_checks.csv`](r5_query_checks.csv) | 920 次焦点查询的逐行核验，含规划状态、扩展次数、局部机制标签和独立到达时间。 | 920 per-query checks with planning status, expansion counts, local mechanism labels, and independent arrival times. |
| [`r5_scenario_cells.csv`](r5_scenario_cells.csv) | 按地图、车数和预算分层，记录来源运行吞吐、配对数、两分支完成数、事件数与共享边支持度。 | Strata by map, fleet, and budget with source throughput, pair counts, completion counts by arm, events, and shared-edge support. |
| [`r5_source_runs.jsonl`](r5_source_runs.jsonl) | 128 次原优先级仿真的运行统计和诊断快照抽样信息。 | Run statistics and snapshot selection for 128 baseline-priority simulations. |
| [`r5_summary.json`](r5_summary.json) | 统一的 R5 汇总，含代理表现、机制标签、共享边结果、策略、工作量和环境。 | Combined R5 summary covering proxies, mechanisms, shared edges, policy contrasts, workload, and environment. |
| [`r5_ticks.jsonl.gz`](r5_ticks.jsonl.gz) | 2,432 个预定观测时刻，记录焦点资格和对向共享边意图。 | 2,432 scheduled observations with focal eligibility and opposing shared-edge intentions. |
| [`r5_work_timing.jsonl`](r5_work_timing.jsonl) | 按计时场景保存原 R5 串行规划耗时与操作计数的中位数和 P95。 | Per-scenario medians and P95 values for original serial planning time and operation counts. |
| [`r5_workload.csv`](r5_workload.csv) | 八个实验设置下整轮毫秒数及各类操作计数的 P50/P95 汇总。 | P50/P95 summaries of round time in milliseconds and operation counts for eight experiment settings. |
