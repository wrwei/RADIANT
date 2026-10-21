# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.8824 | 0.8000 | 0.7764 | 0.3000 | 1.0000 | 0.9351 | 0.2184 | 0.1807 |
| run_002 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_003 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_004 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_005 | 0.9615 | 0.9379 | 0.9400 | 0.7000 | 1.0000 | 1.0000 | 0.1170 | 0.0000 |
| run_006 | 0.9709 | 0.9540 | 0.9533 | 0.7000 | 1.0000 | 1.0000 | 0.0879 | 0.0000 |
| run_007 | 1.0000 | 0.7328 | 0.7067 | 0.0500 | 1.0000 | 1.0000 | 0.0000 | 0.4217 |
| run_008 | 0.9899 | 0.6720 | 0.6309 | 0.0500 | 0.9877 | 0.9877 | 0.0000 | 0.4940 |
| run_009 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_010 | 0.9709 | 0.9540 | 0.9533 | 0.7000 | 1.0000 | 1.0000 | 0.0879 | 0.0000 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 10 | 0.9524 | 0.0365 | 0.9615 | 0.8654 | 1.0000 |
| dedup_vocabulary_recall | 10 | 0.9880 | 0.0299 | 1.0000 | 0.9000 | 1.0000 |
| dedup_vocabulary_f1 | 10 | 0.9697 | 0.0308 | 0.9804 | 0.8824 | 1.0000 |
| requirement_linked_micro_precision | 10 | 0.9305 | 0.0608 | 0.9540 | 0.7816 | 1.0000 |
| requirement_linked_micro_recall | 10 | 0.8904 | 0.1828 | 1.0000 | 0.5060 | 1.0000 |
| requirement_linked_micro_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
| requirement_linked_macro_f1 | 10 | 0.8907 | 0.1271 | 0.9533 | 0.6309 | 0.9867 |
| requirement_linked_exact_match_rate | 10 | 0.6100 | 0.3292 | 0.7000 | 0.0500 | 0.9000 |
| requirement_linked_hallucination_rate | 10 | 0.0695 | 0.0608 | 0.0460 | 0.0000 | 0.2184 |
| requirement_linked_omission_rate | 10 | 0.1096 | 0.1828 | 0.0000 | 0.0000 | 0.4940 |
| concept_precision | 10 | 0.8283 | 0.0950 | 0.8182 | 0.6923 | 1.0000 |
| concept_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 10 | 0.9032 | 0.0550 | 0.9000 | 0.8182 | 1.0000 |
| instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 10 | 0.9976 | 0.0073 | 1.0000 | 0.9756 | 1.0000 |
| instance_f1 | 10 | 0.9988 | 0.0037 | 1.0000 | 0.9877 | 1.0000 |
| typed_instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 10 | 0.9976 | 0.0073 | 1.0000 | 0.9756 | 1.0000 |
| typed_instance_f1 | 10 | 0.9988 | 0.0037 | 1.0000 | 0.9877 | 1.0000 |
| instance_type_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 10 | 0.9854 | 0.0365 | 1.0000 | 0.8780 | 1.0000 |
| instance_type_f1 | 10 | 0.9923 | 0.0194 | 1.0000 | 0.9351 | 1.0000 |
| term_structural_precision | 10 | 0.9305 | 0.0608 | 0.9540 | 0.7816 | 1.0000 |
| term_structural_recall | 10 | 0.8904 | 0.1828 | 1.0000 | 0.5060 | 1.0000 |
| term_structural_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
| field_gid_f1 | 10 | 0.9133 | 0.1071 | 0.9652 | 0.6720 | 0.9765 |
| field_concept_f1 | 10 | 0.9133 | 0.1071 | 0.9652 | 0.6720 | 0.9765 |
| field_instance_f1 | 10 | 0.9133 | 0.1071 | 0.9652 | 0.6720 | 0.9765 |
| field_instance_of_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
| term_field_f1 | 10 | 0.9089 | 0.1053 | 0.9540 | 0.6720 | 0.9765 |
| term_alias_precision | 10 | 0.9305 | 0.0608 | 0.9540 | 0.7816 | 1.0000 |
| term_alias_recall | 10 | 0.8904 | 0.1828 | 1.0000 | 0.5060 | 1.0000 |
| term_alias_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
| dedup_term_structural_precision | 10 | 0.9305 | 0.0608 | 0.9540 | 0.7816 | 1.0000 |
| dedup_term_structural_recall | 10 | 0.8904 | 0.1828 | 1.0000 | 0.5060 | 1.0000 |
| dedup_term_structural_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
| dedup_term_field_f1 | 10 | 0.9089 | 0.1053 | 0.9540 | 0.6720 | 0.9765 |
| dedup_term_alias_precision | 10 | 0.9305 | 0.0608 | 0.9540 | 0.7816 | 1.0000 |
| dedup_term_alias_recall | 10 | 0.8904 | 0.1828 | 1.0000 | 0.5060 | 1.0000 |
| dedup_term_alias_f1 | 10 | 0.8957 | 0.1097 | 0.9540 | 0.6720 | 0.9765 |
