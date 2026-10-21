# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_002 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_003 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_004 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_005 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_006 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_007 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_008 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_009 | 0.8817 | 0.6615 | 0.6833 | 0.0500 | 0.8767 | 0.8767 | 0.0851 | 0.4819 |
| run_010 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 10 | 0.9607 | 0.0024 | 0.9615 | 0.9535 | 0.9615 |
| dedup_vocabulary_recall | 10 | 0.9820 | 0.0540 | 1.0000 | 0.8200 | 1.0000 |
| dedup_vocabulary_f1 | 10 | 0.9705 | 0.0296 | 0.9804 | 0.8817 | 0.9804 |
| requirement_linked_micro_precision | 10 | 0.9501 | 0.0117 | 0.9540 | 0.9149 | 0.9540 |
| requirement_linked_micro_recall | 10 | 0.9518 | 0.1446 | 1.0000 | 0.5181 | 1.0000 |
| requirement_linked_micro_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| requirement_linked_macro_f1 | 10 | 0.9563 | 0.0910 | 0.9867 | 0.6833 | 0.9867 |
| requirement_linked_exact_match_rate | 10 | 0.8150 | 0.2550 | 0.9000 | 0.0500 | 0.9000 |
| requirement_linked_hallucination_rate | 10 | 0.0499 | 0.0117 | 0.0460 | 0.0460 | 0.0851 |
| requirement_linked_omission_rate | 10 | 0.0482 | 0.1446 | 0.0000 | 0.0000 | 0.4819 |
| concept_precision | 10 | 0.8182 | 0.0000 | 0.8182 | 0.8182 | 0.8182 |
| concept_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 10 | 0.9000 | 0.0000 | 0.9000 | 0.9000 | 0.9000 |
| instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 10 | 0.9780 | 0.0659 | 1.0000 | 0.7805 | 1.0000 |
| instance_f1 | 10 | 0.9877 | 0.0370 | 1.0000 | 0.8767 | 1.0000 |
| typed_instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 10 | 0.9780 | 0.0659 | 1.0000 | 0.7805 | 1.0000 |
| typed_instance_f1 | 10 | 0.9877 | 0.0370 | 1.0000 | 0.8767 | 1.0000 |
| instance_type_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 10 | 0.9780 | 0.0659 | 1.0000 | 0.7805 | 1.0000 |
| instance_type_f1 | 10 | 0.9877 | 0.0370 | 1.0000 | 0.8767 | 1.0000 |
| term_structural_precision | 10 | 0.9501 | 0.0117 | 0.9540 | 0.9149 | 0.9540 |
| term_structural_recall | 10 | 0.9518 | 0.1446 | 1.0000 | 0.5181 | 1.0000 |
| term_structural_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| field_gid_f1 | 10 | 0.9511 | 0.0760 | 0.9765 | 0.7231 | 0.9765 |
| field_concept_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| field_instance_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| field_instance_of_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| term_field_f1 | 10 | 0.9465 | 0.0899 | 0.9765 | 0.6769 | 0.9765 |
| term_alias_precision | 10 | 0.9501 | 0.0117 | 0.9540 | 0.9149 | 0.9540 |
| term_alias_recall | 10 | 0.9518 | 0.1446 | 1.0000 | 0.5181 | 1.0000 |
| term_alias_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| dedup_term_structural_precision | 10 | 0.9501 | 0.0117 | 0.9540 | 0.9149 | 0.9540 |
| dedup_term_structural_recall | 10 | 0.9518 | 0.1446 | 1.0000 | 0.5181 | 1.0000 |
| dedup_term_structural_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
| dedup_term_field_f1 | 10 | 0.9465 | 0.0899 | 0.9765 | 0.6769 | 0.9765 |
| dedup_term_alias_precision | 10 | 0.9501 | 0.0117 | 0.9540 | 0.9149 | 0.9540 |
| dedup_term_alias_recall | 10 | 0.9518 | 0.1446 | 1.0000 | 0.5181 | 1.0000 |
| dedup_term_alias_f1 | 10 | 0.9450 | 0.0945 | 0.9765 | 0.6615 | 0.9765 |
