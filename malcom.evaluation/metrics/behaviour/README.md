# State Machine Metrics

Input: `result_behaviour_model.rct`.

Primary metric:
- `behavior_micro_f1`: micro-F1 over initial nodes, states, and transition
  edges `(source, target)`.

Diagnostics:
- structural parse validity
- transition identifier F1
- variables, constants, and functions F1
- triggers, conditions, and actions F1
- detail and full micro-F1

The parser supports multiline and compact RoboChart-like transition blocks.
This is structural parse validity, not full FDR4 formal verification.

Files:
- `metrics.py`: parser, fact extraction, and F1 algorithms
- `compute.py`: batch aggregation and report generation

Run:

```powershell
python .\compute.py --pattern "web_*"
```

Reports are written to `../results/state_machine/` by default.
