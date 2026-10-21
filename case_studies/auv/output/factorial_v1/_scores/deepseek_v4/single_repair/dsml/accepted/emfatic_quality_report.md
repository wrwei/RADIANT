# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_001 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_002 | 1 | 0 | 0 | 1 | 0.8571 | 0.8571 | 0.7692 | 0.8212 | 0.8212 | 15/13 | 15/13 | 21/18 | Callable;ReturnValue;TypedElement | Component |
| run_003 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_004 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_005 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_006 | 1 | 0 | 0 | 1 | 0.8889 | 0.8889 | 0.8108 | 0.8569 | 0.8569 | 14/13 | 14/13 | 19/18 | ReturnValue;TypedElement | Component |
| run_007 | 1 | 0 | 0 | 1 | 0.8889 | 0.8889 | 0.7895 | 0.8482 | 0.8482 | 14/13 | 14/13 | 20/18 | BehavioralFeature;ReturnValue | Component |
| run_008 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_009 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_010 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| syntax_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| syntax_error_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| syntax_warning_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 10 | 0.8976 | 0.0416 | 0.9231 | 0.8000 | 0.9231 |
| class_recall | 10 | 0.9231 | 0.0000 | 0.9231 | 0.9231 | 0.9231 |
| class_f1 | 10 | 0.9096 | 0.0221 | 0.9231 | 0.8571 | 0.9231 |
| attr_precision | 10 | 0.8976 | 0.0416 | 0.9231 | 0.8000 | 0.9231 |
| attr_recall | 10 | 0.9231 | 0.0000 | 0.9231 | 0.9231 | 0.9231 |
| attr_f1 | 10 | 0.9096 | 0.0221 | 0.9231 | 0.8571 | 0.9231 |
| ref_precision | 10 | 0.8087 | 0.0412 | 0.8333 | 0.7143 | 0.8333 |
| ref_recall | 10 | 0.8333 | 0.0000 | 0.8333 | 0.8333 | 0.8333 |
| ref_f1 | 10 | 0.8203 | 0.0220 | 0.8333 | 0.7692 | 0.8333 |
| macro_f1 | 10 | 0.8799 | 0.0219 | 0.8932 | 0.8278 | 0.8932 |
| weighted_f1 | 10 | 0.8731 | 0.0219 | 0.8864 | 0.8212 | 0.8864 |
| conditional_weighted_f1 | 10 | 0.8731 | 0.0219 | 0.8864 | 0.8212 | 0.8864 |
| end_to_end_weighted_f1 | 10 | 0.8731 | 0.0219 | 0.8864 | 0.8212 | 0.8864 |
