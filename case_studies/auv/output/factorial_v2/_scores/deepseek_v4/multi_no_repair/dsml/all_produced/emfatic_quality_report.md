# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_001 | 0 | 1 | 0 | 1 | 0.4063 | 0.3256 | 0.3889 | 0.3753 | 0.0000 | 19/13 | 30/13 | 18/18 | AUV_Autopilot;AUV_Module;AUV_Operator;AUV_Platform;Actuators;Close;Inputs;LRE_Ctrl;Obstacle;Outputs;SVec;Sensors | Event;Function;Parameter;PrimitiveType;Type;Value |
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
| syntax_ok | 10 | 0.9000 | 0.3000 | 1.0000 | 0.0000 | 1.0000 |
| syntax_error_count | 10 | 0.1000 | 0.3000 | 0.0000 | 0.0000 | 1.0000 |
| syntax_warning_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 10 | 0.7743 | 0.1716 | 0.7656 | 0.3421 | 1.0000 |
| class_recall | 10 | 0.8808 | 0.1315 | 0.9231 | 0.5000 | 1.0000 |
| class_f1 | 10 | 0.8207 | 0.1485 | 0.8448 | 0.4063 | 0.9600 |
| attr_precision | 10 | 0.7770 | 0.2034 | 0.7812 | 0.2333 | 1.0000 |
| attr_recall | 10 | 0.9000 | 0.1243 | 0.9231 | 0.5385 | 1.0000 |
| attr_f1 | 10 | 0.8270 | 0.1749 | 0.8582 | 0.3256 | 0.9600 |
| ref_precision | 10 | 0.7093 | 0.1315 | 0.7136 | 0.3889 | 0.9118 |
| ref_recall | 10 | 0.7694 | 0.1395 | 0.8056 | 0.3889 | 0.8889 |
| ref_f1 | 10 | 0.7361 | 0.1287 | 0.7574 | 0.3889 | 0.8857 |
| macro_f1 | 10 | 0.7946 | 0.1480 | 0.8333 | 0.3736 | 0.9352 |
| weighted_f1 | 10 | 0.7880 | 0.1453 | 0.8281 | 0.3753 | 0.9296 |
| conditional_weighted_f1 | 9 | 0.8338 | 0.0493 | 0.8501 | 0.7618 | 0.9296 |
| end_to_end_weighted_f1 | 10 | 0.7504 | 0.2545 | 0.8281 | 0.0000 | 0.9296 |
