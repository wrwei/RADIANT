# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.8723 | 0.5781 | 0.5881 | 0.0000 | 0.8767 | 0.8767 | 0.1778 | 0.5542 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 1 | 0.9318 | 0.0000 | 0.9318 | 0.9318 | 0.9318 |
| dedup_vocabulary_recall | 1 | 0.8200 | 0.0000 | 0.8200 | 0.8200 | 0.8200 |
| dedup_vocabulary_f1 | 1 | 0.8723 | 0.0000 | 0.8723 | 0.8723 | 0.8723 |
| requirement_linked_micro_precision | 1 | 0.8222 | 0.0000 | 0.8222 | 0.8222 | 0.8222 |
| requirement_linked_micro_recall | 1 | 0.4458 | 0.0000 | 0.4458 | 0.4458 | 0.4458 |
| requirement_linked_micro_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| requirement_linked_macro_f1 | 1 | 0.5881 | 0.0000 | 0.5881 | 0.5881 | 0.5881 |
| requirement_linked_exact_match_rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| requirement_linked_hallucination_rate | 1 | 0.1778 | 0.0000 | 0.1778 | 0.1778 | 0.1778 |
| requirement_linked_omission_rate | 1 | 0.5542 | 0.0000 | 0.5542 | 0.5542 | 0.5542 |
| concept_precision | 1 | 0.7500 | 0.0000 | 0.7500 | 0.7500 | 0.7500 |
| concept_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 1 | 0.8571 | 0.0000 | 0.8571 | 0.8571 | 0.8571 |
| instance_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 1 | 0.7805 | 0.0000 | 0.7805 | 0.7805 | 0.7805 |
| instance_f1 | 1 | 0.8767 | 0.0000 | 0.8767 | 0.8767 | 0.8767 |
| typed_instance_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 1 | 0.7805 | 0.0000 | 0.7805 | 0.7805 | 0.7805 |
| typed_instance_f1 | 1 | 0.8767 | 0.0000 | 0.8767 | 0.8767 | 0.8767 |
| instance_type_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 1 | 0.7805 | 0.0000 | 0.7805 | 0.7805 | 0.7805 |
| instance_type_f1 | 1 | 0.8767 | 0.0000 | 0.8767 | 0.8767 | 0.8767 |
| term_structural_precision | 1 | 0.8222 | 0.0000 | 0.8222 | 0.8222 | 0.8222 |
| term_structural_recall | 1 | 0.4458 | 0.0000 | 0.4458 | 0.4458 | 0.4458 |
| term_structural_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| field_gid_f1 | 1 | 0.6875 | 0.0000 | 0.6875 | 0.6875 | 0.6875 |
| field_concept_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| field_instance_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| field_instance_of_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| term_field_f1 | 1 | 0.6055 | 0.0000 | 0.6055 | 0.6055 | 0.6055 |
| term_alias_precision | 1 | 0.8222 | 0.0000 | 0.8222 | 0.8222 | 0.8222 |
| term_alias_recall | 1 | 0.4458 | 0.0000 | 0.4458 | 0.4458 | 0.4458 |
| term_alias_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| dedup_term_structural_precision | 1 | 0.8222 | 0.0000 | 0.8222 | 0.8222 | 0.8222 |
| dedup_term_structural_recall | 1 | 0.4458 | 0.0000 | 0.4458 | 0.4458 | 0.4458 |
| dedup_term_structural_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
| dedup_term_field_f1 | 1 | 0.6055 | 0.0000 | 0.6055 | 0.6055 | 0.6055 |
| dedup_term_alias_precision | 1 | 0.8222 | 0.0000 | 0.8222 | 0.8222 | 0.8222 |
| dedup_term_alias_recall | 1 | 0.4458 | 0.0000 | 0.4458 | 0.4458 | 0.4458 |
| dedup_term_alias_f1 | 1 | 0.5781 | 0.0000 | 0.5781 | 0.5781 | 0.5781 |
