"""Render bilingual supplementary figures from the archived R5 CSV tables."""

import argparse
from ast import literal_eval
from collections import Counter
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import MaxNLocator


DATA = Path(__file__).resolve().parent / "data_r5"
INK = "#17334A"
MUTED = "#415C70"
GRID = "#DFE8EE"
BLUE = "#08788A"
PALE_BLUE = "#E2F1F2"
ORANGE = "#AA4D21"
PALE_ORANGE = "#F5E8DE"
NEUTRAL = "#EAF0F5"
CJK_FAMILIES = (
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "Source Han Sans SC",
    "PingFang SC",
    "Heiti SC",
    "Microsoft YaHei",
    "SimHei",
    "Songti SC",
    "WenQuanYi Zen Hei",
)


def read_table(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def select_font(language, path):
    if path is not None:
        font_manager.fontManager.addfont(path)
        return font_manager.FontProperties(fname=path).get_name()
    if language == "en":
        return "DejaVu Sans"
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font in CJK_FAMILIES:
        if font in available:
            return font
    raise ValueError("No Simplified Chinese font found. Pass --font /path/to/NotoSansCJKsc-Regular.otf.")


def heading(fig, title, subtitle):
    fig.text(.07, .955, title, color=INK, fontsize=19, fontweight="bold", va="top")
    fig.text(.07, .902, subtitle, color=MUTED, fontsize=10, va="top")


def note(fig, content):
    fig.text(.07, .026, content, color=MUTED, fontsize=9, va="bottom", linespacing=1.5)


def chart_axes(ax, grid_axis):
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_axisbelow(True)
    ax.grid(axis=grid_axis, color=GRID, linewidth=.8)
    ax.tick_params(length=0, labelcolor=INK, pad=6)


def confusion_matrix(ax, rows, proxy, title, tr):
    counts = Counter((int(row["delta"]) < 0, row[proxy] == "True") for row in rows)
    labels = (
        (tr("命中", "Detected"), PALE_BLUE),
        (tr("漏判", "Missed"), PALE_ORANGE),
        (tr("误报", "False alarm"), PALE_ORANGE),
        (tr("正确排除", "Correct negative"), NEUTRAL),
    )
    for index, (label, color) in enumerate(labels):
        observed, predicted = index < 2, index % 2 == 0
        row, col = divmod(index, 2)
        ax.add_patch(Rectangle((col + .025, row + .035), .95, .93, facecolor=color))
        ax.text(col + .5, row + .42, counts[observed, predicted], ha="center", va="center",
                color=INK, fontsize=20, fontweight="bold")
        ax.text(col + .5, row + .73, label, ha="center", va="center", color=MUTED, fontsize=9)
    ax.set(xlim=(0, 2), ylim=(2, 0))
    ax.set_xticks((.5, 1.5), (tr("预测提前", "Predicted gain"), tr("预测未提前", "Predicted no gain")))
    ax.set_yticks((.5, 1.5), (tr("实际提前", "Observed gain"), tr("实际未提前", "No observed gain")))
    ax.tick_params(length=0, labelcolor=INK, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, fontsize=12, loc="left", color=INK, pad=8)


def diagnostic_outcomes(tr):
    rows = read_table("r5_pair_summary.csv")
    gains = sum(int(row["delta"]) < 0 for row in rows)
    fig = plt.figure(figsize=(11.2, 7.25))
    heading(fig, tr("单轮调序的完工结果与判据误差", "Completion outcomes after a one-round promotion"),
            tr(f"{len(rows)} 个快照配对中，{gains} 个焦点任务提前完工。", f"The focal task finished earlier in {gains} of {len(rows)} paired snapshots."))
    grid = fig.add_gridspec(2, 2, left=.19, right=.94, top=.82, bottom=.21, hspace=.68, wspace=.42)
    confusion_matrix(fig.add_subplot(grid[0, 0]), rows, "direction", tr("首步方向判据", "First direction proxy"), tr)
    confusion_matrix(fig.add_subplot(grid[0, 1]), rows, "distance", tr("两步进展判据", "Two-step progress proxy"), tr)
    ax = fig.add_subplot(grid[1, :])
    outcomes = Counter()
    for row in rows:
        delta = int(row["delta"])
        outcome = (delta > 0) - (delta < 0)
        outcomes[outcome, int(row["n_others_later"]) > 0] += 1
    tiers = (
        (-1, tr("提前完工", "Earlier")),
        (0, tr("截尾时间相同", "Same capped time")),
        (1, tr("较晚完工", "Later")),
    )
    row_labels = []
    for index, (outcome, label) in enumerate(tiers):
        delayed, none_delayed = outcomes[outcome, True], outcomes[outcome, False]
        total = delayed + none_delayed
        row_labels.append(f"{label} (n={total})")
        if total == 0:
            continue
        share = 100 * delayed / total
        ax.barh(index, share, color=ORANGE, height=.54)
        ax.barh(index, 100 - share, left=share, color=PALE_BLUE, height=.54)
        if delayed:
            ax.text(share / 2, index, delayed, ha="center", va="center", color="white", fontweight="bold")
        if none_delayed:
            ax.text((share + 100) / 2, index, none_delayed, ha="center", va="center", color=INK, fontweight="bold")
    ax.set_title(tr("按焦点任务结果划分的他车延迟", "Other robots’ delays by focal-task outcome"), loc="left",
                 fontsize=12, color=INK, pad=8)
    ax.set_yticks(range(len(tiers)), row_labels)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    ax.set_xlabel(tr("该组内的配对比例（%）", "Share of pairs within each group (%)"), color=MUTED)
    chart_axes(ax, "x")
    fig.legend(handles=[Patch(facecolor=ORANGE, label=tr("至少一辆他车延迟", "At least one other robot delayed")),
                        Patch(facecolor=PALE_BLUE, label=tr("无他车延迟", "No other robot delayed"))],
               loc="lower left", bbox_to_anchor=(.19, .083), ncol=2, frameon=False, fontsize=9)
    note(fig, tr("完工时间按 32 个时间步截尾。条内数字为配对数量，百分比按行计算。",
                 "Completion times are capped at 32 steps. Segment labels are pair counts and percentages are computed within rows."))
    return fig


def setting_label(row, separator=" · "):
    return separator.join((row["layout"].upper(), row["n"], row["cap"]))


def policy_comparison(tr):
    rows = read_table("r5_policy_comparison.csv")
    metrics = (
        ("rate", tr("吞吐量", "Throughput"), tr("每 100 步的完工任务数差", "Difference in completions per 100 steps")),
        ("overdue_pp", tr("超时占比", "Overdue robot-time"), tr("差值（百分点）", "Difference (percentage points)")),
        ("cohort_by64_pp", tr("截至第 64 步的首个任务完工率", "Initial tasks completed by step 64"),
         tr("完工率差值（百分点）", "Completion-rate difference (percentage points)")),
        ("cohort_capped", tr("首个任务的截尾完工时间", "Capped time for initial tasks"),
         tr("完工时间差值（时间步）", "Completion-time difference (steps)")),
    )
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.55))
    fig.subplots_adjust(left=.2, right=.94, top=.811, bottom=.17, hspace=.49, wspace=.60)
    settings = [setting_label(row) for row in rows]
    headings = tr("地图 · 机器人数量 · 展开上限", "Map · robots · expansion cap")
    heading(fig, tr("两阶段排序与按剩余距离排序的对比", "Two-stage versus remaining-distance ordering"),
            tr("数值为两阶段排序减去剩余距离排序，均按场景配对。每行是一种仿真设置。",
               "Differences are two-stage minus remaining-distance, paired by scenario. Each row is a simulation setting."))
    for ax, (key, title, unit) in zip(axes.flat, metrics):
        for index, row in enumerate(rows):
            point = float(row[key])
            low, high = literal_eval(row[f"{key}_ci"])
            ax.hlines(index, low, high, color=BLUE, linewidth=2, zorder=3)
            ax.plot(point, index, "o", color=BLUE, markersize=5, zorder=4)
        ax.axvline(0, color=MUTED, linewidth=1.1, linestyle="--", zorder=2)
        ax.set_yticks(range(len(rows)), settings)
        ax.set_ylim(len(rows) - .5, -.5)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, min_n_ticks=3))
        ax.set_title(title, fontsize=12, color=INK, loc="left", pad=10)
        ax.set_xlabel(unit, color=MUTED, fontsize=9)
        chart_axes(ax, "x")
    fig.text(.07, .866, headings, fontsize=9, color=MUTED)
    pairs = sorted({int(row["scenarios"]) for row in rows})
    sizes = sorted({int(row["cohort"]) for row in rows})
    pair_text = "/".join(map(str, pairs))
    cohort_range = "–".join(map(str, (sizes[0], sizes[-1])))
    note(fig, tr(f"点为配对差值，线为逐项 95% bootstrap 区间。每种设置有 {pair_text} 对场景。\n"
                 f"每种设置包含 {cohort_range} 个对齐的首个任务，随访到第 64 步。虚线表示差值为零。",
                 f"Dots are paired estimates and lines are pointwise 95% bootstrap intervals. {pair_text} scenario pairs per setting.\n"
                 f"Settings include {cohort_range} matched initial tasks observed to step 64. The dashed line marks zero difference."))
    return fig


def plot_percentiles(ax, rows, key, title, unit):
    medians = [float(row[f"{key}_p50"]) for row in rows]
    tails = [float(row[f"{key}_p95"]) for row in rows]
    x = list(range(len(rows)))
    ax.vlines(x, medians, tails, color=BLUE, linewidth=1.4)
    ax.scatter(x, tails, marker="D", s=45, facecolor="white", edgecolor=BLUE, linewidth=1.3, zorder=4)
    ax.scatter(x, medians, marker="o", s=16, color=BLUE, zorder=5)
    ax.set_xticks(x, [setting_label(row, "\n") for row in rows])
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title(title, fontsize=12, color=INK, pad=8, loc="left")
    ax.set_ylabel(unit, color=MUTED, fontsize=9)
    ax.set_ylim(0, max(tails) * 1.12 if max(tails) else 1)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    chart_axes(ax, "y")


def planning_workload(tr):
    rows = read_table("r5_workload.csv")
    fig = plt.figure(figsize=(11.2, 10.15))
    heading(fig, tr("每轮规划的耗时与操作量", "Planning time and work per round"),
            tr("各组依次标示地图、机器人数量及展开上限。每个坐标图使用独立的纵轴。",
               "Each setting lists the map, robot count, and search expansion cap. Vertical scales are independent."))
    grid = fig.add_gridspec(3, 2, left=.15, right=.94, top=.825, bottom=.15, hspace=.68, wspace=.37)
    plot_percentiles(fig.add_subplot(grid[0, :]), rows, "wall_ms", tr("单轮总耗时", "End-to-end round time"),
                     tr("毫秒", "Milliseconds"))
    metrics = (
        ("seed_tests", tr("初始路径候选动作检查", "Seed move tests")),
        ("interval_expanded", tr("安全区间状态展开", "Safe-interval state expansions")),
        ("edge_tests", tr("转移与边时约束检查", "Transition and edge-time checks")),
        ("reservation_writes", tr("预留表更新", "Reservation writes")),
    )
    for index, (key, title) in enumerate(metrics):
        plot_percentiles(fig.add_subplot(grid[index // 2 + 1, index % 2]), rows, key, title,
                         tr("每轮次数", "Count per round"))
    fig.legend(handles=[Line2D([], [], color=BLUE, marker="o", markersize=4, linestyle="none", label=tr("中位数（P50）", "Median (P50)")),
                        Line2D([], [], color=BLUE, marker="D", markerfacecolor="white", markersize=6,
                               linestyle="none", label=tr("第 95 百分位数（P95）", "95th percentile (P95)"))],
               loc="upper right", bbox_to_anchor=(.945, .876), ncol=2, frameon=False, fontsize=9)
    note(fig, tr("原始实验采用 Xeon/Linux 单进程。每种设置用种子 6101，预热后测量 96 轮。\n"
                 "总耗时包括优先顺序、初始路径生成、区间搜索、预留更新和合法性检查，随硬件与环境而变。",
                 "Archived Xeon/Linux timings use one process, seed 6101 and 96 post-warm-up rounds per setting.\n"
                 "Round time includes ordering, seed generation, search, reservations and validation. Timings depend on the system."))
    return fig


def draw(language, folder, font=None):
    def tr(chinese, english):
        return chinese if language == "cn" else english

    family = select_font(language, font)
    folder.mkdir(parents=True, exist_ok=True)
    plots = (
        ("diagnostic_outcomes", diagnostic_outcomes),
        ("policy_comparison", policy_comparison),
        ("planning_workload", planning_workload),
    )
    style = {"font.family": family, "font.size": 10, "axes.unicode_minus": False,
             "svg.fonttype": "path", "pdf.fonttype": 42}
    with plt.rc_context(style):
        for name, chart in plots:
            figure = chart(tr)
            for extension in ("png", "pdf", "svg"):
                figure.savefig(folder / f"{name}.{extension}", dpi=300, facecolor="white")
            plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("cn", "en"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font", type=Path, help="Optional font file. Use a Simplified Chinese font for cn.")
    args = parser.parse_args()
    try:
        draw(args.language, args.out, args.font)
    except (ValueError, OSError) as error:
        parser.error(str(error))
