# Emfatic DSML Quality Evaluation

Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.
Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.

## Per-run Results

| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| run_001 | 1 | 0 | 0 | 1 | 0.8621 | 0.8966 | 0.8000 | 0.8469 | 0.8469 | 16/13 | 16/13 | 22/18 | Callable;ReturnValue;TypedElement | - |
| run_002 | 1 | 0 | 0 | 1 | 0.4231 | 0.3529 | 0.4444 | 0.4111 | 0.4111 | 13/13 | 21/13 | 9/18 | Actuators;Close;Inputs;Obstacle;Outputs;SVec;Sensors | CompositeType;Event;Function;Parameter;PrimitiveType;Type;Value |
| run_003 | 1 | 0 | 0 | 1 | 0.8621 | 0.8966 | 0.7500 | 0.8264 | 0.8264 | 16/13 | 16/13 | 22/18 | Callable;ReturnValue;TypedElement | - |
| run_004 | 1 | 0 | 0 | 1 | 0.9231 | 0.9231 | 0.8333 | 0.8864 | 0.8864 | 13/13 | 13/13 | 18/18 | ReturnValue | Component |
| run_005 | 1 | 0 | 0 | 1 | 0.7586 | 0.7586 | 0.5128 | 0.6581 | 0.6581 | 16/13 | 16/13 | 21/18 | AUV;BehavioralFeature;InterfaceUser;ReturnValue;TypedElement | Component;Interface |
| run_006 | 1 | 0 | 0 | 1 | 0.8333 | 0.8667 | 0.7805 | 0.8216 | 0.8216 | 17/13 | 17/13 | 23/18 | AUV;Callable;ReturnValue;TypedElement | - |
| run_007 | 1 | 0 | 0 | 1 | 0.8148 | 0.8462 | 0.7222 | 0.7862 | 0.7862 | 14/13 | 13/13 | 18/18 | Callable;InterfaceUser;ValueContainer | Component;Parameter |
| run_008 | 1 | 0 | 0 | 1 | 0.8571 | 0.8571 | 0.8718 | 0.8631 | 0.8631 | 15/13 | 15/13 | 21/18 | InterfaceUser;Operation;TypedElement | Component |
| run_009 | 1 | 0 | 0 | 1 | 0.8621 | 0.8966 | 0.8205 | 0.8553 | 0.8553 | 16/13 | 16/13 | 21/18 | ParameterizedElement;ReturnValue;TypedElement | - |
| run_010 | 1 | 0 | 0 | 1 | 0.8387 | 0.8387 | 0.7619 | 0.8073 | 0.8073 | 18/13 | 18/13 | 24/18 | AUV;Operation;ReturnValue;TypedElement;ValueContainer | - |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| syntax_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| syntax_error_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| syntax_warning_count | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| parse_ok | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| class_precision | 10 | 0.7421 | 0.1216 | 0.7812 | 0.4231 | 0.9231 |
| class_recall | 10 | 0.8808 | 0.1599 | 0.9423 | 0.4231 | 1.0000 |
| class_f1 | 10 | 0.8035 | 0.1328 | 0.8479 | 0.4231 | 0.9231 |
| attr_precision | 10 | 0.7467 | 0.1655 | 0.8063 | 0.2857 | 0.9231 |
| attr_recall | 10 | 0.9000 | 0.1578 | 0.9615 | 0.4615 | 1.0000 |
| attr_f1 | 10 | 0.8133 | 0.1595 | 0.8619 | 0.3529 | 0.9231 |
| ref_precision | 10 | 0.7041 | 0.0935 | 0.7089 | 0.4762 | 0.8333 |
| ref_recall | 10 | 0.7778 | 0.1826 | 0.8611 | 0.3333 | 0.9444 |
| ref_f1 | 10 | 0.7298 | 0.1329 | 0.7712 | 0.4444 | 0.8718 |
| macro_f1 | 10 | 0.7822 | 0.1370 | 0.8315 | 0.4068 | 0.8932 |
| weighted_f1 | 10 | 0.7762 | 0.1356 | 0.8240 | 0.4111 | 0.8864 |
| conditional_weighted_f1 | 10 | 0.7762 | 0.1356 | 0.8240 | 0.4111 | 0.8864 |
| end_to_end_weighted_f1 | 10 | 0.7762 | 0.1356 | 0.8240 | 0.4111 | 0.8864 |
