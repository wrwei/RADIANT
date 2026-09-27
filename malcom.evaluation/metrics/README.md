# MALCOM Evaluation Metrics

This directory contains the current evaluation framework. Each pipeline stage
has one self-contained folder with its metric algorithms, batch driver,
auditable aliases where needed, and documentation.

```
metrics/
  concept/
  dsml/
  model/
  behaviour/
  results/              # generated CSV and Markdown reports
```

| Stage | Primary metric | Evaluation unit |
|---|---|---|
| Term extraction | `dedup_vocabulary_f1` | unique `(Concept, Instance, Instance_of)` tuples |
| Emfatic generation | `syntax_ok`, `end_to_end_weighted_f1` | official Emfatic syntax validity plus reference-based classes, attributes, and references |
| Model creation | `end_to_end_micro_f1` | executed EMF object, attribute, and link facts |
| State machine | `behavior_micro_f1` | initial nodes, states, and transition edges |

All primary scores are deterministic precision/recall/F1 measures. Alias tables
are explicit JSON files and are applied only to normalize reviewer-auditable
semantic equivalents. No learned embedding score contributes to the primary
accuracy values.

Run a stage from its directory:

```powershell
cd .\malcom.evaluation\metrics\term_extraction
python .\compute.py
```

The default inputs are the AUV runs under
`case_studies/auv/output/runs`. Term extraction, Emfatic, and model
creation use the audited independent expert reference under
`malcom.evaluation/reference_models/auv_independent_expert_20260612`.
The current state-machine driver uses the MALCOMj AUV `result_behaviour_model.rct` reference, as
documented by its `compute.py` defaults.

Each driver writes CSV and Markdown reports under `metrics/results/<stage>/`.
Use `python .\compute.py --help` inside a stage directory to override the run
root, reference, run pattern, aliases, or output directory where supported.
