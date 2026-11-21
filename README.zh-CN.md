# 仓储终身多智能体路径规划 · R5 项目导读

[English](README.md)

## 这个项目研究什么

在终身多智能体路径规划（LMAPF）中，仓储机器人到达当前目标后会立即接收下一个导航目标。如果只在一轮规划中把一辆机器人移到队首，它会更早完成任务吗？其他机器人会因此变慢吗？实验从同一个仓库状态出发，用相同的搜索预算分别按原顺序和移首后的顺序重放，再根据实际执行轨迹比较任务完工时间。

R5 在两张 Moving AI 公开仓储地图上运行了 128 次基准仿真，并比较了 460 个配对快照。其中 39 个配对的焦点机器人更早完工，30 个同时有至少一辆其他机器人变慢。仅看首步计划方向能识别其中 1 次提前完工，看前两步的剩余距离变化能识别 22 次。独立的时间层参照对 920 个焦点查询核验了四项条件，包括搜索预算、他车的时空预留、到达后是否需要留驻目标格，以及规划窗口长度。这些结果对应本研究的仿真场景和快照入选规则。见[结果汇总](data_r5/r5_summary.json)和[实验方案](PROTOCOL_R5.md)。

## 文件分类

| 类别 | 从哪里找 | 包含什么 |
| --- | --- | --- |
| 实验方案与环境 | [实验方案](PROTOCOL_R5.md)、[参数](protocol_r5.json)、[运行环境](ENVIRONMENT.txt)、[Python 依赖](requirements-r5.txt)、[冻结文件校验值](frozen_protocol.sha256) | 预先设定的实验条件、软件版本和完整性校验 |
| 地图与参考来源 | [benchmarks/](benchmarks/)、[来源说明](SOURCES.md) | 两张 Moving AI 仓储地图、资料出处与参考文献 |
| 仿真与规划器 | [warehouse.py](warehouse.py)、[interval_planner.py](interval_planner.py)、[reference.py](reference.py) | 仓储仿真和任务生成、滚动安全区间规划器、独立时间层参照 |
| 运行与分析入口 | [run_r5.py](run_r5.py)、[analyze_r5.py](analyze_r5.py)、[figures_r5.py](figures_r5.py) | 运行实验、核验轨迹和局部查询、生成图表 |
| R5 数据与结果 | [data_r5/](data_r5/)、[结果汇总](data_r5/r5_summary.json)、[查询核验表](data_r5/r5_query_checks.csv)、[策略对比表](data_r5/r5_policy_comparison.csv) | 原始运行和重放日志、逐查询结果、汇总统计、补充策略实验与计时 |
| 已生成图表 | [中文](figures_r5/cn/)、[英文](figures_r5/en/) | 仓储地图示意与诊断结果，提供 PNG、SVG 和 PDF 格式 |
| 中英文论文源文件 | [中文正文](manuscript_cn/paper_cn.txt)、[英文正文](manuscript_en/paper_en.txt)、[中文构建目录](manuscript_cn/)、[英文构建目录](manuscript_en/) | 正文、表格、参考文献和 Word、LaTeX 构建输入。[发布清单](manuscript_release.json)记录产物校验值，[中文审阅回复](REVIEW_RESPONSE_CN.md)记录修订说明。 |
| R4 历史实验 | [historical_r4/](historical_r4/)、[R4 导读](historical_r4/README.md) | 早期合成场景的仿真器、实验日志、结果和图表 |

## 从哪里开始

- **了解研究**。先读[中文正文](manuscript_cn/paper_cn.txt)，再看[诊断结果图](figures_r5/cn/diagnostic_validation.png)和[结果汇总](data_r5/r5_summary.json)。
- **核验已有结果**。使用 Python 3.12，在仓库根目录运行 `python -m pip install -r requirements-r5.txt` 和 `python analyze_r5.py --verify-probes`。分析脚本会校验轨迹和到达时间，并重新生成汇总结果与数值表。
- **重跑实验**。先运行 `python run_r5.py --workers 4`，再运行分析脚本。需要单独运行诊断实验时，可加 `--only diagnostic`。软件版本、R4 核验、绘图和论文构建命令见[复现说明](README.md#reproduction-instructions)。归档提供论文构建源文件，两份 Word 文档和英文投稿 PDF 可从源码生成。
