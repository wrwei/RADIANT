# Emfatic Metrics

Input: `result_dsml.emf`.

Default reference: `reference_models/auv_independent_expert_20260612/result_dsml.emf`.

Metrics:
- Eclipse Emfatic parser syntax pass rate, error count, and warning count
- class precision, recall, and F1
- attribute precision, recall, and F1
- reference precision, recall, and F1
- macro F1 and fact-count-weighted F1
- conditional weighted F1 over syntax-valid outputs
- end-to-end weighted F1, with syntax-invalid outputs assigned zero

Syntax is checked with the official Eclipse Emfatic parser through MALCOMj's
`EmfaticHelper`. Structural matching uses canonical equality, an auditable
alias table, and conservative fuzzy matching. The match log records why each
pair was accepted.

Files:
- `metrics.py`: Emfatic parsing, inherited-feature expansion, and matching
- `compute.py`: batch aggregation and report generation
- `aliases_auv.json`: AUV class, feature, and type aliases

Run:

```powershell
python .\compute.py
```

Reports are written to `../results/emfatic/` by default.
