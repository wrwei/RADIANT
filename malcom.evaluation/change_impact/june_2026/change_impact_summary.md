# Change-impact correctness

Runs: `case_studies/auv/experiment` (June 2026 sweep; per-run data in the public data package). Micro P/R/F1 of the computed impact set against the expert reference over 18 injected behaviour-requirement changes per run; runs whose behaviour phase was rejected are not scored (runs_scored). Arch phase spread = mean number of phases reached when the root requirement SD1 changes.

| Model | Cfg | Runs (scored) | Changes | P | R | F1 | Arch phase spread |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4 | single | 10 (10) | 180 | 0.000 | 0.000 | 0.000 | 1.00 |
| DeepSeek-V4 | multi | 10 (10) | 180 | 1.000 | 1.000 | 1.000 | 3.00 |
| QWEN3-max | single | 10 (10) | 180 | 0.000 | 0.000 | 0.000 | 1.00 |
| QWEN3-max | multi | 10 (10) | 180 | 1.000 | 1.000 | 1.000 | 3.00 |
| Claude Sonnet 4.6 | single | 10 (10) | 180 | 0.000 | 0.000 | 0.000 | 1.00 |
| Claude Sonnet 4.6 | multi | 10 (10) | 180 | 1.000 | 1.000 | 1.000 | 3.00 |
