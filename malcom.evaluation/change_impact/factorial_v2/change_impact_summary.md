# Change-impact correctness

Runs: `case_studies/auv/output/factorial_v2`. Micro P/R/F1 of the computed impact set against the expert reference over 18 injected behaviour-requirement changes per run; runs whose behaviour phase was rejected are not scored (runs_scored). Arch phase spread = mean number of phases reached when the root requirement SD1 changes.

| Model | Cfg | Runs (scored) | Changes | P | R | F1 | Arch phase spread |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4 | single | 10 (1) | 18 | 0.000 | 0.000 | 0.000 | 1.00 |
| DeepSeek-V4 | single_repair | 10 (10) | 180 | 0.000 | 0.000 | 0.000 | 1.00 |
| DeepSeek-V4 | multi_no_repair | 10 (9) | 162 | 1.000 | 0.988 | 0.994 | 3.00 |
| DeepSeek-V4 | multi | 10 (9) | 162 | 1.000 | 0.876 | 0.934 | 2.78 |
