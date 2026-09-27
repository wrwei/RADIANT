# Term Extraction Metrics

Input: `result_concept_trace.json`.

Default reference: `reference_models/auv_independent_expert_20260612/result_concept_extraction.json`.

Primary metric:
- `dedup_vocabulary_f1`: micro F1 over unique concept facts and
  `(Instance, Instance_of)` facts, excluding requirement identifiers.
- `requirement_linked_micro_f1`: global set-level F1 over unique
  `(GID, Concept, Instance, Instance_of)` tuples.
- `requirement_linked_macro_f1`: the mean of set-level F1 calculated
  independently for every GID in the prediction/reference union.
- `requirement_linked_exact_match_rate`: fraction of GIDs whose complete
  deduplicated `(GID, Concept, Instance, Instance_of)` set exactly matches the
  reference.
- `typed_instance_f1`: set-level F1 over nonblank `(Concept, Instance)` facts.
- `instance_type_f1`: set-level F1 over nonblank
  `(Instance, Instance_of)` facts.

Diagnostics:
- JSON and schema validity
- deduplicated vocabulary precision and recall
- concept and instance set-level precision, recall, and F1
- typed-instance and instance-type precision, recall, and F1
- requirement-linked hallucination rate (`FP / (TP + FP)`)
- requirement-linked omission rate (`FN / (TP + FN)`)
- GID-linked structural F1 over `(GID, Concept, Instance, Instance_of)`
- `term_field_f1`: field-level macro F1
- `term_alias_f1`: alias-aware structural F1
- set/deduplicated F1
- duplicate rate

Files:
- `metrics.py`: parsing, normalization, matching, and metric algorithms
- `compute.py`: run discovery, aggregation, CSV, and Markdown reports
- `aliases_auv.json`: auditable AUV semantic aliases

Run:

```powershell
python .\compute.py
```

Reports are written to `../results/term_extraction/` by default.
