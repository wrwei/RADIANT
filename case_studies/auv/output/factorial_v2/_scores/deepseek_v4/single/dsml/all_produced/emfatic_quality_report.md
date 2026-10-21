# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_001 | 0 | 1 | 0 | 1 | 0.8889 | 0.8889 | 0.7143 | 0.8175 | 0.0000 | 14/13 | 14/13 | 24/18 | AUV;ReturnValue | Component |
| run_002 | 0 | 1 | 0 | 1 | 0.8519 | 0.8889 | 0.7838 | 0.8349 | 0.0000 | 14/13 | 14/13 | 19/18 | ReturnValue;TypedElement | RoboticPlatform |
| run_003 | 0 | 1 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.0000 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_004 | 0 | 1 | 0 | 1 | 0.9231 | 0.9231 | 0.7429 | 0.8494 | 0.0000 | 13/13 | 13/13 | 17/18 | ReturnValue | Component |
| run_005 | 0 | 1 | 0 | 1 | 0.8800 | 0.8800 | 0.7778 | 0.8382 | 0.0000 | 12/13 | 12/13 | 18/18 | Callable | Component;Parameter |
| run_006 | 0 | 1 | 0 | 1 | 0.8889 | 0.8889 | 0.8108 | 0.8569 | 0.0000 | 14/13 | 14/13 | 19/18 | AUV;ReturnValue | Component |
| run_007 | 0 | 1 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.0000 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_008 | 0 | 1 | 0 | 1 | 0.8889 | 0.8889 | 0.7895 | 0.8482 | 0.0000 | 14/13 | 14/13 | 20/18 | BehavioralFeature;ReturnValue | Component |
| run_009 | 0 | 1 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.0000 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_010 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| syntax_ok | 10 | 0.1000 | 0.3000 | 0.0000 | 0.0000 | 1.0000 |
| syntax_error_count | 10 | 0.9000 | 0.3000 | 1.0000 | 0.0000 | 1.0000 |
| syntax_warning_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 10 | 0.8925 | 0.0375 | 0.9199 | 0.8214 | 0.9231 |
| class_recall | 10 | 0.9115 | 0.0246 | 0.9231 | 0.8462 | 0.9231 |
| class_f1 | 10 | 0.9014 | 0.0239 | 0.9060 | 0.8519 | 0.9231 |
| attr_precision | 10 | 0.8961 | 0.0318 | 0.9199 | 0.8571 | 0.9231 |
| attr_recall | 10 | 0.9154 | 0.0231 | 0.9231 | 0.8462 | 0.9231 |
| attr_f1 | 10 | 0.9051 | 0.0182 | 0.9060 | 0.8800 | 0.9231 |
| ref_precision | 10 | 0.7803 | 0.0608 | 0.7836 | 0.6250 | 0.8333 |
| ref_recall | 10 | 0.8139 | 0.0352 | 0.8333 | 0.7222 | 0.8333 |
| ref_f1 | 10 | 0.7952 | 0.0398 | 0.8001 | 0.7143 | 0.8333 |
| macro_f1 | 10 | 0.8672 | 0.0230 | 0.8629 | 0.8307 | 0.8932 |
| weighted_f1 | 10 | 0.8591 | 0.0244 | 0.8531 | 0.8175 | 0.8864 |
| conditional_weighted_f1 | 1 | 0.8864 | 0.0000 | 0.8864 | 0.8864 | 0.8864 |
| end_to_end_weighted_f1 | 10 | 0.0886 | 0.2659 | 0.0000 | 0.0000 | 0.8864 |
