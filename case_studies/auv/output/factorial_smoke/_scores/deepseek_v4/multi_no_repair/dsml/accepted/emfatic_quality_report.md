# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_001 | 1 | 0 | 0 | 1 | 0.8571 | 0.8571 | 0.6842 | 0.7864 | 0.7864 | 15/13 | 15/13 | 20/18 | CallableFeature;ReturnValue;TypedElement | Component |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| syntax_ok | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| syntax_error_count | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| syntax_warning_count | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| class_recall | 1 | 0.9231 | 0.0000 | 0.9231 | 0.9231 | 0.9231 |
| class_f1 | 1 | 0.8571 | 0.0000 | 0.8571 | 0.8571 | 0.8571 |
| attr_precision | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| attr_recall | 1 | 0.9231 | 0.0000 | 0.9231 | 0.9231 | 0.9231 |
| attr_f1 | 1 | 0.8571 | 0.0000 | 0.8571 | 0.8571 | 0.8571 |
| ref_precision | 1 | 0.6500 | 0.0000 | 0.6500 | 0.6500 | 0.6500 |
| ref_recall | 1 | 0.7222 | 0.0000 | 0.7222 | 0.7222 | 0.7222 |
| ref_f1 | 1 | 0.6842 | 0.0000 | 0.6842 | 0.6842 | 0.6842 |
| macro_f1 | 1 | 0.7995 | 0.0000 | 0.7995 | 0.7995 | 0.7995 |
| weighted_f1 | 1 | 0.7864 | 0.0000 | 0.7864 | 0.7864 | 0.7864 |
| conditional_weighted_f1 | 1 | 0.7864 | 0.0000 | 0.7864 | 0.7864 | 0.7864 |
| end_to_end_weighted_f1 | 1 | 0.7864 | 0.0000 | 0.7864 | 0.7864 | 0.7864 |
