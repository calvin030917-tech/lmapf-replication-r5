# LMAPF R5 reproducibility archive

[简体中文](README.zh-CN.md) · [Bilingual file index](FILE_GUIDE.md)

## What this project studies

In lifelong multi-agent path finding (LMAPF), each warehouse robot receives a new navigation goal as soon as it reaches the current one. This study asks what happens when one robot moves to the front of the planning order for a single round. It replays the original and promoted orders from the same warehouse state with the same search budget, then checks when the promoted robot finishes and whether other robots take longer.

R5 uses two public Moving AI warehouse maps, 128 source simulations, and 460 paired snapshots. The promoted robot finished earlier in 39 pairs, and at least one other robot took longer in 30 of those pairs. First-step direction identified 1 of the 39 earlier completions, while two-step progress identified 22. Across 920 focal queries, an independent time-layer reference checked the effects of search budget, other robots’ reservations, goal occupancy rules, and the planning horizon. These counts describe the simulated scenarios and the study’s snapshot selection rules. See the [R5 summary](r5/data_r5/r5_summary.json) and [experimental protocol](r5/PROTOCOL_R5.md).

## Repository guide

The [R5 reproduction directory](r5/) contains the experiment code, protocol, benchmark maps, and recorded data. [Supporting documents](docs/) contain the environment notes, sources, and manuscript release records.

Open the [bilingual file index](FILE_GUIDE.md) for the purpose of each file. Each directory links to its own guide.

| Category | Where to look | What it contains |
| --- | --- | --- |
| Experiment design and environment | [Protocol](r5/PROTOCOL_R5.md), [parameters](r5/protocol_r5.json), [environment](docs/ENVIRONMENT.txt), [Python dependencies](r5/requirements-r5.txt), [frozen checksums](r5/frozen_protocol.sha256) | Predefined experiment settings, software versions, and integrity checks for the frozen inputs |
| Maps and references | [benchmarks/](r5/benchmarks/), [source notes](docs/SOURCES.md) | The two Moving AI maps, benchmark provenance, and research references |
| Simulator and planners | [warehouse.py](r5/warehouse.py), [interval_planner.py](r5/interval_planner.py), [reference.py](r5/reference.py) | Warehouse simulation and task generation, rolling safe-interval planning, and an independent time-layer reference |
| Experiment and analysis entry points | [run_r5.py](r5/run_r5.py), [analyze_r5.py](r5/analyze_r5.py), [figures_r5.py](r5/figures_r5.py) | Run simulations, verify recorded trajectories and local queries, and generate figures |
| R5 data and results | [data_r5/](r5/data_r5/), [summary](r5/data_r5/r5_summary.json), [query checks](r5/data_r5/r5_query_checks.csv), [policy comparison](r5/data_r5/r5_policy_comparison.csv) | Raw run and replay logs, query-level checks, aggregate results, and supplementary policy and timing data |
| Rendered figures | [English](figures_r5/en/), [Chinese](figures_r5/cn/) | Warehouse layouts and diagnostic results in PNG, SVG, and PDF |
| Manuscript sources | [Chinese source](manuscript_cn/paper_cn.txt), [English source](manuscript_en/paper_en.txt), [Chinese build files](manuscript_cn/), [English build files](manuscript_en/) | Manuscript text, tables, references, and the Word and LaTeX build inputs. The [release manifest](docs/manuscript_release.json) records artifact checksums and the [review response](docs/REVIEW_RESPONSE_CN.md) tracks revisions. |
| Historical R4 experiments | [historical_r4/](historical_r4/), [R4 guide](historical_r4/README.md) | Earlier synthetic experiments, their simulator, data, and figures |

To read the study, start with the [manuscript](manuscript_en/paper_en.txt) and the [diagnostic figure](figures_r5/en/diagnostic_validation.png). To check the archived results, run the verification commands below from the repository root. To regenerate R5, run the simulation, analysis, and figure steps in that order.

## Planner optimization and supplemental figures

The original planner builds a safe-interval cache for each robot query and sorts reservation times on cache misses. The optimized planner encodes the occupied time steps as bitmasks and reuses the corresponding intervals across robot queries in the same round. It eliminates intervals outside a transition’s feasible time range before checking reverse edges. With `r5/` on the Python import path, use `from interval_planner_fast import plan` to opt in. The frozen experiment runner uses the original planner. [Optimized planner](r5/interval_planner_fast.py)

In 4,608 paired timed rounds across 48 configurations on macOS arm64 with Python 3.14.2, pooled P50 fell from 1.584 to 1.424 ms and P95 from 3.161 to 2.720 ms. Paths, query results, focal controls, and work counters matched across 5,760 rolling rounds, including warm-up. The measured timings are specific to this machine and workload. [Benchmark results](docs/planner_benchmark.json)

The published timing measurements use the archive baseline. A separate parity check with the planner updates in pull request #1 matched 624 rolling rounds, 24 promoted-order rounds, and 35 fixture queries.

The supplemental figures show proxy prediction errors and other-robot delays, paired policy contrasts with pointwise 95% intervals, and archived planning time and work counts. Each plot is available in English and Chinese as PNG, PDF, and SVG. [English figures](figures_r5/en/FILE_GUIDE.md) · [Chinese figures](figures_r5/cn/FILE_GUIDE.md)

Run from the project root after installing the dependencies listed in the reproduction instructions.

```sh
python r5/benchmark_planners.py --seeds 6101 6102 --policies density distance dual
python r5/supplemental_figures.py --language en --out figures_r5/en
python r5/supplemental_figures.py --language cn --out figures_r5/cn --font /path/to/NotoSansCJKsc-Regular.otf
```

The benchmark accepts `--json` for machine-readable output. The Chinese plot command can also use a supported system CJK font when `--font` is omitted.

## Reproduction instructions

This release contains the independent public-map validation, the original synthetic suite, raw action-level traces, diagnostic witnesses and both manuscript build sources. Data are generated by deterministic simulation. No model fitting, credentials, or extra data download is required.

### Verify the release

Use Python 3.12 and the versions in `r5/requirements-r5.txt`. Run these commands from the repository root.

```sh
(cd r5 && shasum -a 256 -c frozen_protocol.sha256)
python -m pip install -r r5/requirements-r5.txt
python r5/analyze_r5.py --verify-probes
cd historical_r4
python verify.py
python verify_r4.py
python check_r5_legacy.py --out ../r5/data_r5
cd ..
```

The analysis reads both observed trajectories and the issued goals to check each first arrival. The separate time-layer enumerator is run again for every recorded focal query and all four settings. The historical check regenerates the full original 32-action paths for 367 overdue and 480 exploratory pairs, replays both terminal rules in case B, and obtains actual rolling-planner outputs for fixed reference examples. R4 matched-condition and holdout traces were verified with complete source-action checks when generated. The first-round seed substitution on 532 snapshots is an alternate intervention with a changed initial seed, so its original-order arm is not intended to reproduce the untouched source.

### Rerun

- `python r5/run_r5.py --workers 4` reruns controlled fixtures, 128 public-layout source runs, their paired diagnostics, 256 continuing-policy runs, and the final serial timing measures. The diagnostic block can be run independently with `--only diagnostic`. The frozen files and their checksums are in [the R5 checksum manifest](r5/frozen_protocol.sha256). Timing is host-dependent.
- `python r5/analyze_r5.py --verify-probes` then rebuilds the summaries, validates legality and arrival from the raw paths, repeats the fixed-reservation reference checks, and regenerates the numerical tables. All primary runs use separate scene seeds from the supplemental policy comparison.
- `python r5/figures_r5.py --language en --out figures_r5/en` regenerates English figures. The Chinese equivalent uses `--language cn --out figures_r5/cn --font path/to/NotoSansCJKsc-Regular.otf`.
- `python manuscript_cn/build_cn.py --out manuscript_output` builds the Chinese Word manuscript. `python manuscript_en/build_aligned_word.py --out manuscript_output` builds its complete English counterpart. The Word manuscripts follow the same section and display order.
- In `manuscript_en/`, run `python build_aligned_tex.py` to generate the submission layout from the English manuscript source, then run `pdflatex lmapf_r5.tex`, `bibtex lmapf_r5`, and `pdflatex lmapf_r5.tex` twice. The compiler uses standard TeX Live and the included ICML style. The full text of Sections 4.1, 4.2, 5.2, and 5.4 and some large displays appear in Appendix D of the PDF.
- Historical experiment entry points are in `historical_r4/README.md`. They are separate from the public-map engine and use different search expansion units.

### Main data

| Dataset | Contents |
| --- | --- |
| `r5/data_r5/r5_ticks.jsonl.gz` | 2,432 scheduled ticks, eligible focal and exact shared-edge intent matches |
| `r5/data_r5/r5_pairs.jsonl.gz` | 460 snapshots, two complete 32-step replays, original/promotion/six random orders, search statuses, immutable query reservations, independent witnesses |
| `r5/data_r5/r5_query_checks.csv` | 920 focal queries, four reference labels and earliest arrivals |
| `r5/data_r5/r5_scenario_cells.csv` | Eight validation strata, service rates, denominators, mechanism counts and per-label scene support |
| `r5/data_r5/r5_policy_runs.jsonl.gz` | 256 new policy runs, task-index-zero arrival times and aggregate service |
| `r5/data_r5/r5_policy_comparison.csv` | Eight paired policy contrasts and pointwise intervals |
| `r5/data_r5/r5_workload.csv` | Serial end-to-end planning timing P50/P95 and distinct operation counts |
| `r5/data_r5/r5_historical_checks.json` | Algorithm 1 versus fixed-goal reference outputs, controlled case B, all-source-action audit summaries and actual seed/candidate distinctions |
| `r5/data_r5/r5_fixtures.json` | Seven manually specified examples, expected flags, fixed reservations and legal witnesses |
| `r5/data_r5/r5_summary.json` | All aggregate R5 results, including repeated signatures with and without static-distance matching, and overlap with recorded reverse reservations |
| `historical_r4/data/` | Original 367- and 480-pair data, R4 synthetic validations, legacy policy data and historical statistic outputs |

The full public maps are unmodified files from Moving AI. Their URLs and checksums are given in [the source notes](docs/SOURCES.md), and their freely routable areas follow the supplied bitmap. Per-robot goals are generated and are intentionally distinct from the original one-shot benchmark scenarios. The shared-edge label is given by opposing intentions on the same physical edge, and the supplementary readout checks whether it is actually reserved in that direction at the focal intended time. Completion status and capped elapsed time remain separate.

The three manuscript builds share the same archived inputs and results. The two Word outputs and the compiled submission PDF are listed in [the release manifest](docs/manuscript_release.json). This archive includes their build sources and an author-facing Chinese revision crosswalk.
