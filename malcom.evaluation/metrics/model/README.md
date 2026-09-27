# Model Creation Metrics

This is the retained EOL/model evaluation workflow.

For each run:
1. convert `result_dsml.emf` to a run-specific `.ecore`;
2. execute `result_model.eol` against that generated metamodel;
3. parse the generated `.model`;
4. compare object, attribute, and link facts with the audited independent expert
   reference at
   `malcom.evaluation/reference_models/auv_independent_expert_20260612/result_AUV.model`.

Primary metric:
- `end_to_end_micro_f1`: micro-F1 across all model facts; failed execution is 0.

Diagnostics:
- Ecore conversion and EOL execution success
- object F1
- attribute F1
- link F1
- end-to-end macro F1

Files:
- `emfatic_to_ecore.py`: generated Emfatic to Ecore conversion
- `metrics.py`: XML/XMI fact extraction and F1 algorithms
- `compute.py`: MALCOMj execution, aggregation, and reports
- `aliases_auv.json`: class, feature, and value aliases

Run:

```powershell
python .\compute.py --pattern "web_*"
```

Reports and run-specific generated models are written to
`../results/model_creation/` by default.
