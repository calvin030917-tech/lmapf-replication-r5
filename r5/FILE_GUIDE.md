# `r5/` 文件说明 / File guide

[上一级文件索引 / Parent file guide](../FILE_GUIDE.md)

| 文件或目录 / File or folder | 中文说明 | English description |
| --- | --- | --- |
| [`PROTOCOL_R5.md`](PROTOCOL_R5.md) | 定义公开地图上的场景生成、焦点筛选、配对重放、机制和统计口径。 | Defines public-map scenarios, focal selection, paired replays, mechanism probes, and statistical rules. |
| [`protocol_r5.json`](protocol_r5.json) | 机器可读的冻结参数，包括地图摘要、车数、搜索上限、时域和场景种子。 | Machine-readable frozen settings for map digests, fleet sizes, search caps, horizons, and scenario seeds. |
| [`frozen_protocol.sha256`](frozen_protocol.sha256) | 用于逐文件检查实验方案、配置、仿真和原版规划代码的 SHA-256。 | SHA-256 checks for the frozen protocol, configuration, simulator, and original planning code. |
| [`requirements-r5.txt`](requirements-r5.txt) | 固定 R5 分析、绘图和 Word 构建所用的 Python 包版本。 | Pins Python dependencies for R5 analysis, plotting, and Word builds. |
| [`warehouse.py`](warehouse.py) | 读取原始仓储图，生成任务流，定义优先级规则，并执行滚动规划路径。 | Loads warehouse maps, generates tasks, defines priority rules, and executes rolling plans. |
| [`interval_planner.py`](interval_planner.py) | 原版滚动安全区间规划器，生成安全种子路径、维护预留并受预算约束地规划。 | Original rolling safe-interval planner that builds a safe joint seed, maintains reservations, and plans under a search budget. |
| [`reference.py`](reference.py) | 显式枚举时间层，独立检查最早合法到达、受控机制和重放轨迹。 | Explicitly enumerates time layers to verify earliest legal arrivals, controlled mechanisms, and replay traces. |
| [`run_r5.py`](run_r5.py) | 运行公开图诊断与持续策略实验，写出快照、配对轨迹、策略和计时记录。 | Runs public-map diagnostics and continuing-policy experiments and writes snapshots, paired traces, policy results, and timing records. |
| [`analyze_r5.py`](analyze_r5.py) | 读取归档轨迹，复核完成时刻和机制，再计算分层、策略和工作量表。 | Checks archived trajectories, completion times, and mechanisms, then produces stratum, policy, and workload summaries. |
| [`figures_r5.py`](figures_r5.py) | 生成原论文所用的中英文仓储地图示意和诊断结果图。 | Generates the original bilingual public-map and diagnostic figures used by the manuscript. |
| [`interval_planner_fast.py`](interval_planner_fast.py) | 供单独选用的优化规划器，复用固定实验的搜索逻辑并减少重复计算。 | Opt-in optimized planner that reuses the frozen search logic while reducing repeated computation. |
| [`benchmark_planners.py`](benchmark_planners.py) | 在相同场景上比对原版与优化版的路径、计数和规划耗时。 | Compares original and optimized paths, counters, and planning time on the same cases. |
| [`supplemental_figures.py`](supplemental_figures.py) | 从归档数据生成中英文诊断结果、策略对比及工作量图。 | Generates bilingual diagnostic, policy contrast, and workload figures from archived data. |
| [`benchmarks/`](benchmarks/FILE_GUIDE.md) | Moving AI 原版仓储地图。 | Original Moving AI warehouse maps. |
| [`data_r5/`](data_r5/FILE_GUIDE.md) | R5 图表和论文所依据的实验记录与统计结果。 | R5 records and statistics underlying the figures and manuscripts. |
| [`test_analyze_r5.py`](test_analyze_r5.py) | 回归检查重放事件标签、快照抽样和策略及计时实验的覆盖。 | Regression tests for replay event labels, snapshot selection, and policy and timing coverage. |
| [`test_interval_planner.py`](test_interval_planner.py) | 核验安全初始路径的生成与非法路径的拒绝，同时覆盖禁用 Python 断言的模式。 | Tests seed-path construction and unsafe-path rejection, including with Python assertions disabled. |
