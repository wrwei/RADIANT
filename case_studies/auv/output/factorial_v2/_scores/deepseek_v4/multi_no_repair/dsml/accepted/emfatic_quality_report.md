# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_002 | 1 | 0 | 0 | 1 | 0.7931 | 0.8276 | 0.7368 | 0.7803 | 0.7803 | 16/13 | 16/13 | 20/18 | DataType;ParameterizedElement;ReturnValue;TypedElement | Type |
| run_003 | 1 | 0 | 0 | 1 | 0.8621 | 0.8966 | 0.8205 | 0.8553 | 0.8553 | 16/13 | 16/13 | 21/18 | Operation;ReturnValue;TypedElement | - |
| run_004 | 1 | 0 | 0 | 1 | 0.9200 | 0.9600 | 0.7647 | 0.8683 | 0.8683 | 12/13 | 12/13 | 16/18 | - | Parameter |
| run_005 | 1 | 0 | 0 | 1 | 0.8276 | 0.8276 | 0.7500 | 0.7958 | 0.7958 | 16/13 | 16/13 | 22/18 | AUV;Callable;ReturnValue;TypedElement | Component |
| run_006 | 1 | 0 | 0 | 1 | 0.7931 | 0.8276 | 0.8000 | 0.8061 | 0.8061 | 16/13 | 16/13 | 22/18 | DataType;Operation;ReturnValue;TypedElement | Type |
| run_007 | 1 | 0 | 0 | 1 | 0.9286 | 0.9286 | 0.7368 | 0.8501 | 0.8501 | 15/13 | 15/13 | 20/18 | Callable;ReturnValue | - |
| run_008 | 1 | 0 | 0 | 1 | 0.8276 | 0.8276 | 0.6667 | 0.7618 | 0.7618 | 16/13 | 16/13 | 21/18 | BehavioralFeature;InterfaceUser;ReturnValue;TypedElement | Component |
| run_009 | 1 | 0 | 0 | 1 | 0.9600 | 0.9600 | 0.8857 | 0.9296 | 0.9296 | 12/13 | 12/13 | 17/18 | - | Parameter |
| run_010 | 1 | 0 | 0 | 1 | 0.8889 | 0.8889 | 0.8108 | 0.8569 | 0.8569 | 14/13 | 14/13 | 19/18 | ReturnValue;TypedElement | Component |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| syntax_ok | 9 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| syntax_error_count | 9 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| syntax_warning_count | 9 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 9 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 9 | 0.8223 | 0.0982 | 0.7812 | 0.7188 | 1.0000 |
| class_recall | 9 | 0.9231 | 0.0363 | 0.9231 | 0.8846 | 1.0000 |
| class_f1 | 9 | 0.8668 | 0.0575 | 0.8621 | 0.7931 | 0.9600 |
| attr_precision | 9 | 0.8374 | 0.0974 | 0.8125 | 0.7500 | 1.0000 |
| attr_recall | 9 | 0.9402 | 0.0320 | 0.9231 | 0.9231 | 1.0000 |
| attr_f1 | 9 | 0.8827 | 0.0542 | 0.8889 | 0.8276 | 0.9600 |
| ref_precision | 9 | 0.7449 | 0.0809 | 0.7273 | 0.6190 | 0.9118 |
| ref_recall | 9 | 0.8117 | 0.0611 | 0.8333 | 0.7222 | 0.8889 |
| ref_f1 | 9 | 0.7747 | 0.0593 | 0.7647 | 0.6667 | 0.8857 |
| macro_f1 | 9 | 0.8414 | 0.0496 | 0.8597 | 0.7739 | 0.9352 |
| weighted_f1 | 9 | 0.8338 | 0.0493 | 0.8501 | 0.7618 | 0.9296 |
| conditional_weighted_f1 | 9 | 0.8338 | 0.0493 | 0.8501 | 0.7618 | 0.9296 |
| end_to_end_weighted_f1 | 9 | 0.8338 | 0.0493 | 0.8501 | 0.7618 | 0.9296 |
