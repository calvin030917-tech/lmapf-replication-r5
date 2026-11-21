# LMAPF priority-promotion study — R4 replication

This archive contains the simulator, protocols, raw logs, derived results, and publication figures for the Chinese and English manuscripts. The goal streams, maps, decisions, and synthetic fixed-goal cases are defined in code. No data download, GPU, training, or service credentials are needed.

## Start with the recorded runs

From this directory, with Python 3.10 or newer:

```sh
python -m pip install -r requirements.txt
python analyze.py
python revision_audit.py
python verify.py
python verify_r4.py
```

To regenerate all simulation data:

```sh
python small_cases.py
python run.py --mode all --workers 4
python gate_probe.py --workers 4
python validation.py --workers 4
python analyze.py
python revision_audit.py
python verify.py
python verify_r4.py
```

Run in this directory so scripts can resolve `data/`. The simulators rely on deterministic scenario keys and integer node counts. Wall-clock latency in the historical policy logs is machine-dependent and is outside the main comparison. For figures, run `python figures.py --out figures_en --lang en`. For Chinese, run `python figures.py --out figures --lang cn --font path/to/a/CJK-font.otf` with a font covering Simplified Chinese. Both languages' rendered PNG and path-based SVG figures are included. Coordinates and robot IDs use zero-based indexing.

## Scope and files

- `PROTOCOL.md` and `GATE_PROBE.md` record the original designs and split seeds. `VALIDATION.md` specifies the new scenario protocol written before the first validation run. `R4_METHODS.md` details clock accounting, query semantics, and tables.
- `simulator.py` implements the shared node-limited planner. `validation.py` contains the alternate serial seed and the Ladder and Offset layouts. `diagnose.py` implements the one-round change and continuation.
- `data/pairs.jsonl.gz` and `data/gate_pairs.jsonl.gz` contain 367 overdue and 480 exploratory pairs. `data/{matched,holdout}_selection.jsonl.gz` has every scheduled tick and its eligibility, with replay outcomes in the corresponding `*_pairs.jsonl.gz`. `holdout_alternative_first_round.jsonl.gz` isolates replacement of the initial seed on the 532 recursive-source snapshots.
- `data/r4_case_replays.json` gives complete replays of A, B, and C from Figure 5, with the active tasks, source order, promoted order, joint seed, non-focal reservations by query, remaining budgets, and chosen paths. The original-order branch matches all 32 executed actions of its source run. `data/small_cases.json` is the fixed-goal reference and submission log for Table 3.
- `data/r4_gate_clocks_all.csv` gives raw F, L, E, and retreats for the exploratory focal robots. `r4_gate_reconstruction.csv` gives exact group totals and means for Table 6. `r4_gate_vs_task_deltas.csv` locates the four mismatching exit and completion deltas.
- `data/r4_interference_summary.csv` underlies Table 7. Other `r4_interference_*.csv` files give scenario, snapshot, and robot details. `r4_same_conditions.csv` underlies Table A1. `r4_holdout_cells.csv`, `holdout_source_runs.jsonl`, and `r4_same_snapshot_seed_comparison.csv` underlie Table 8 and the seed comparison in Table A2.
- `data/policies.jsonl.gz` contains 896 policy runs. Each primary stratum has 16 independent paired scenarios. `r4_joint_bounds.csv` supplies all 32 adjusted primary bounds in Table 10 and comparisons at 0%, 5%, and 10% tolerance. `factorial.csv` and `r4_distance_contrasts.csv` support Tables B1 and B2. `policy_summary.csv` contains per-stratum task-length and fleet statistics.
- `literature_evidence.tsv` gives a source pointer and a label for the evidence checked in each row of Table 1. `literature_screening.csv` preserves ranked query hits and screening. No literature PDFs are redistributed here.
- `data/r4_results.json` and `data/results.json` collect the calculations used by the manuscript. `manuscript/` contains the two document sources and assembly scripts for readers wishing to rebuild the Word layout. For that optional step, install `python-docx`, then run `python manuscript/build_r4.py --out manuscript_output`.

Historical, exploratory, matched and new-layout logs are kept separately. Capped time is the recorded event time or 32 if unobserved. For conclusions about completion rates, use the event flag, including completions exactly at 32. Counts over multiple snapshots in a scenario are descriptive and share dependence.
