# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.8824 | 0.8000 | 0.7764 | 0.3000 | 1.0000 | 0.9351 | 0.2184 | 0.1807 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 1 | 0.8654 | 0.0000 | 0.8654 | 0.8654 | 0.8654 |
| dedup_vocabulary_recall | 1 | 0.9000 | 0.0000 | 0.9000 | 0.9000 | 0.9000 |
| dedup_vocabulary_f1 | 1 | 0.8824 | 0.0000 | 0.8824 | 0.8824 | 0.8824 |
| requirement_linked_micro_precision | 1 | 0.7816 | 0.0000 | 0.7816 | 0.7816 | 0.7816 |
| requirement_linked_micro_recall | 1 | 0.8193 | 0.0000 | 0.8193 | 0.8193 | 0.8193 |
| requirement_linked_micro_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| requirement_linked_macro_f1 | 1 | 0.7764 | 0.0000 | 0.7764 | 0.7764 | 0.7764 |
| requirement_linked_exact_match_rate | 1 | 0.3000 | 0.0000 | 0.3000 | 0.3000 | 0.3000 |
| requirement_linked_hallucination_rate | 1 | 0.2184 | 0.0000 | 0.2184 | 0.2184 | 0.2184 |
| requirement_linked_omission_rate | 1 | 0.1807 | 0.0000 | 0.1807 | 0.1807 | 0.1807 |
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
| instance_type_recall | 1 | 0.8780 | 0.0000 | 0.8780 | 0.8780 | 0.8780 |
| instance_type_f1 | 1 | 0.9351 | 0.0000 | 0.9351 | 0.9351 | 0.9351 |
| term_structural_precision | 1 | 0.7816 | 0.0000 | 0.7816 | 0.7816 | 0.7816 |
| term_structural_recall | 1 | 0.8193 | 0.0000 | 0.8193 | 0.8193 | 0.8193 |
| term_structural_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| field_gid_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_concept_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_instance_f1 | 1 | 0.9765 | 0.0000 | 0.9765 | 0.9765 | 0.9765 |
| field_instance_of_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| term_field_f1 | 1 | 0.9324 | 0.0000 | 0.9324 | 0.9324 | 0.9324 |
| term_alias_precision | 1 | 0.7816 | 0.0000 | 0.7816 | 0.7816 | 0.7816 |
| term_alias_recall | 1 | 0.8193 | 0.0000 | 0.8193 | 0.8193 | 0.8193 |
| term_alias_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| dedup_term_structural_precision | 1 | 0.7816 | 0.0000 | 0.7816 | 0.7816 | 0.7816 |
| dedup_term_structural_recall | 1 | 0.8193 | 0.0000 | 0.8193 | 0.8193 | 0.8193 |
| dedup_term_structural_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
| dedup_term_field_f1 | 1 | 0.9324 | 0.0000 | 0.9324 | 0.9324 | 0.9324 |
| dedup_term_alias_precision | 1 | 0.7816 | 0.0000 | 0.7816 | 0.7816 | 0.7816 |
| dedup_term_alias_recall | 1 | 0.8193 | 0.0000 | 0.8193 | 0.8193 | 0.8193 |
| dedup_term_alias_f1 | 1 | 0.8000 | 0.0000 | 0.8000 | 0.8000 | 0.8000 |
