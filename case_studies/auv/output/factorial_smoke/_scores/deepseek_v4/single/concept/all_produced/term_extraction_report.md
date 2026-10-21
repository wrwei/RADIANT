# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 1 | 0.9615 | 0.0000 | 0.9615 | 0.9615 | 0.9615 |
| dedup_vocabulary_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| dedup_vocabulary_f1 | 1 | 0.9804 | 0.0000 | 0.9804 | 0.9804 | 0.9804 |
| requirement_linked_micro_precision | 1 | 0.9540 | 0.0000 | 0.9540 | 0.9540 | 0.9540 |
| requirement_linked_micro_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| requirement_linked_micro_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| requirement_linked_macro_f1 | 1 | 0.9867 | 0.0000 | 0.9867 | 0.9867 | 0.9867 |
| requirement_linked_exact_match_rate | 1 | 0.9000 | 0.0000 | 0.9000 | 0.9000 | 0.9000 |
| requirement_linked_hallucination_rate | 1 | 0.0460 | 0.0000 | 0.0460 | 0.0460 | 0.0460 |
| requirement_linked_omission_rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| concept_precision | 1 | 0.8182 | 0.0000 | 0.8182 | 0.8182 | 0.8182 |
| concept_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 1 | 0.9000 | 0.0000 | 0.9000 | 0.9000 | 0.9000 |
| instance_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_f1 | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_f1 | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_precision | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_f1 | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| term_structural_precision | 1 | 0.9540 | 0.0000 | 0.9540 | 0.9540 | 0.9540 |
| term_structural_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| term_structural_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_gid_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_concept_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_instance_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_instance_of_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| term_field_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| term_alias_precision | 1 | 0.9540 | 0.0000 | 0.9540 | 0.9540 | 0.9540 |
| term_alias_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| term_alias_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| dedup_term_structural_precision | 1 | 0.9540 | 0.0000 | 0.9540 | 0.9540 | 0.9540 |
| dedup_term_structural_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| dedup_term_structural_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| dedup_term_field_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| dedup_term_alias_precision | 1 | 0.9540 | 0.0000 | 0.9540 | 0.9540 | 0.9540 |
| dedup_term_alias_recall | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| dedup_term_alias_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
