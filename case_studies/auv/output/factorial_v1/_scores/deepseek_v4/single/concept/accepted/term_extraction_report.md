# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.9709 | 0.9708 | 0.9700 | 0.8500 | 1.0000 | 1.0000 | 0.0568 | 0.0000 |
| run_002 | 0.8817 | 0.5968 | 0.6147 | 0.0500 | 0.8767 | 0.8767 | 0.0976 | 0.5542 |
| run_003 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_004 | 0.9804 | 0.8477 | 0.8081 | 0.0500 | 1.0000 | 1.0000 | 0.0588 | 0.2289 |
| run_005 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| run_006 | 0.9615 | 0.9379 | 0.9400 | 0.7000 | 1.0000 | 1.0000 | 0.1170 | 0.0000 |
| run_007 | 0.8817 | 0.7832 | 0.8323 | 0.5500 | 0.8767 | 0.8767 | 0.0667 | 0.3253 |
| run_008 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_009 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_010 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 10 | 0.0093 | 0.0280 | 0.0000 | 0.0000 | 0.0933 |
| dedup_vocabulary_precision | 10 | 0.9584 | 0.0176 | 0.9615 | 0.9259 | 1.0000 |
| dedup_vocabulary_recall | 10 | 0.9640 | 0.0720 | 1.0000 | 0.8200 | 1.0000 |
| dedup_vocabulary_f1 | 10 | 0.9598 | 0.0401 | 0.9804 | 0.8817 | 1.0000 |
| requirement_linked_micro_precision | 10 | 0.9419 | 0.0301 | 0.9486 | 0.8830 | 1.0000 |
| requirement_linked_micro_recall | 10 | 0.8892 | 0.1851 | 1.0000 | 0.4458 | 1.0000 |
| requirement_linked_micro_f1 | 10 | 0.9042 | 0.1216 | 0.9736 | 0.5968 | 1.0000 |
| requirement_linked_macro_f1 | 10 | 0.9112 | 0.1182 | 0.9783 | 0.6147 | 1.0000 |
| requirement_linked_exact_match_rate | 10 | 0.6800 | 0.3370 | 0.8750 | 0.0500 | 1.0000 |
| requirement_linked_hallucination_rate | 10 | 0.0581 | 0.0301 | 0.0514 | 0.0000 | 0.1170 |
| requirement_linked_omission_rate | 10 | 0.1108 | 0.1851 | 0.0000 | 0.0000 | 0.5542 |
| concept_precision | 10 | 0.8170 | 0.0732 | 0.8182 | 0.6923 | 1.0000 |
| concept_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 10 | 0.8975 | 0.0430 | 0.9000 | 0.8182 | 1.0000 |
| instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 10 | 0.9561 | 0.0878 | 1.0000 | 0.7805 | 1.0000 |
| instance_f1 | 10 | 0.9753 | 0.0493 | 1.0000 | 0.8767 | 1.0000 |
| typed_instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 10 | 0.9561 | 0.0878 | 1.0000 | 0.7805 | 1.0000 |
| typed_instance_f1 | 10 | 0.9753 | 0.0493 | 1.0000 | 0.8767 | 1.0000 |
| instance_type_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 10 | 0.9561 | 0.0878 | 1.0000 | 0.7805 | 1.0000 |
| instance_type_f1 | 10 | 0.9753 | 0.0493 | 1.0000 | 0.8767 | 1.0000 |
| term_structural_precision | 10 | 0.9331 | 0.0402 | 0.9486 | 0.8533 | 1.0000 |
| term_structural_recall | 10 | 0.8892 | 0.1851 | 1.0000 | 0.4458 | 1.0000 |
| term_structural_f1 | 10 | 0.9005 | 0.1239 | 0.9736 | 0.5968 | 1.0000 |
| field_gid_f1 | 10 | 0.9160 | 0.1014 | 0.9736 | 0.6613 | 1.0000 |
| field_concept_f1 | 10 | 0.9005 | 0.1239 | 0.9736 | 0.5968 | 1.0000 |
| field_instance_f1 | 10 | 0.9005 | 0.1239 | 0.9736 | 0.5968 | 1.0000 |
| field_instance_of_f1 | 10 | 0.9005 | 0.1239 | 0.9736 | 0.5968 | 1.0000 |
| term_field_f1 | 10 | 0.9044 | 0.1182 | 0.9736 | 0.6129 | 1.0000 |
| term_alias_precision | 10 | 0.9331 | 0.0402 | 0.9486 | 0.8533 | 1.0000 |
| term_alias_recall | 10 | 0.8892 | 0.1851 | 1.0000 | 0.4458 | 1.0000 |
| term_alias_f1 | 10 | 0.9005 | 0.1239 | 0.9736 | 0.5968 | 1.0000 |
| dedup_term_structural_precision | 10 | 0.9419 | 0.0301 | 0.9486 | 0.8830 | 1.0000 |
| dedup_term_structural_recall | 10 | 0.8892 | 0.1851 | 1.0000 | 0.4458 | 1.0000 |
| dedup_term_structural_f1 | 10 | 0.9042 | 0.1216 | 0.9736 | 0.5968 | 1.0000 |
| dedup_term_field_f1 | 10 | 0.9072 | 0.1166 | 0.9736 | 0.6129 | 1.0000 |
| dedup_term_alias_precision | 10 | 0.9419 | 0.0301 | 0.9486 | 0.8830 | 1.0000 |
| dedup_term_alias_recall | 10 | 0.8892 | 0.1851 | 1.0000 | 0.4458 | 1.0000 |
| dedup_term_alias_f1 | 10 | 0.9042 | 0.1216 | 0.9736 | 0.5968 | 1.0000 |
