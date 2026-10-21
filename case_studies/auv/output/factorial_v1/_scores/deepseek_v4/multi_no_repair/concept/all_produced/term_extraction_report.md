# Term Extraction Evaluation

Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.

## Per-run Results

| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run_001 | 0.9709 | 0.9708 | 0.9700 | 0.8500 | 1.0000 | 1.0000 | 0.0568 | 0.0000 |
| run_002 | 0.8824 | 0.8000 | 0.7764 | 0.3000 | 1.0000 | 0.9351 | 0.2184 | 0.1807 |
| run_003 | 0.8824 | 0.8000 | 0.7764 | 0.3000 | 1.0000 | 0.9351 | 0.2184 | 0.1807 |
| run_004 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| run_005 | 0.9709 | 0.9540 | 0.9533 | 0.7000 | 1.0000 | 1.0000 | 0.0879 | 0.0000 |
| run_006 | 0.9804 | 0.8477 | 0.8081 | 0.0500 | 1.0000 | 1.0000 | 0.0588 | 0.2289 |
| run_007 | 0.9709 | 0.9708 | 0.9700 | 0.8500 | 1.0000 | 1.0000 | 0.0568 | 0.0000 |
| run_008 | 0.9804 | 0.9765 | 0.9867 | 0.9000 | 1.0000 | 1.0000 | 0.0460 | 0.0000 |
| run_009 | 1.0000 | 0.6613 | 0.6335 | 0.0500 | 1.0000 | 1.0000 | 0.0000 | 0.5060 |
| run_010 | 0.9709 | 0.9708 | 0.9700 | 0.8500 | 1.0000 | 1.0000 | 0.0568 | 0.0000 |

## Summary

| Metric | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| valid_json | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_valid | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_entry_ratio | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| duplicate_rate | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| dedup_vocabulary_precision | 10 | 0.9427 | 0.0439 | 0.9434 | 0.8654 | 1.0000 |
| dedup_vocabulary_recall | 10 | 0.9800 | 0.0400 | 1.0000 | 0.9000 | 1.0000 |
| dedup_vocabulary_f1 | 10 | 0.9609 | 0.0407 | 0.9709 | 0.8824 | 1.0000 |
| requirement_linked_micro_precision | 10 | 0.9200 | 0.0737 | 0.9432 | 0.7816 | 1.0000 |
| requirement_linked_micro_recall | 10 | 0.8904 | 0.1592 | 1.0000 | 0.4940 | 1.0000 |
| requirement_linked_micro_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
| requirement_linked_macro_f1 | 10 | 0.8844 | 0.1194 | 0.9617 | 0.6335 | 1.0000 |
| requirement_linked_exact_match_rate | 10 | 0.5850 | 0.3507 | 0.7750 | 0.0500 | 1.0000 |
| requirement_linked_hallucination_rate | 10 | 0.0800 | 0.0737 | 0.0568 | 0.0000 | 0.2184 |
| requirement_linked_omission_rate | 10 | 0.1096 | 0.1592 | 0.0000 | 0.0000 | 0.5060 |
| concept_precision | 10 | 0.8273 | 0.0916 | 0.8182 | 0.7500 | 1.0000 |
| concept_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| concept_f1 | 10 | 0.9029 | 0.0522 | 0.9000 | 0.8571 | 1.0000 |
| instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_f1 | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_recall | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| typed_instance_f1 | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_precision | 10 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| instance_type_recall | 10 | 0.9756 | 0.0488 | 1.0000 | 0.8780 | 1.0000 |
| instance_type_f1 | 10 | 0.9870 | 0.0260 | 1.0000 | 0.9351 | 1.0000 |
| term_structural_precision | 10 | 0.9200 | 0.0737 | 0.9432 | 0.7816 | 1.0000 |
| term_structural_recall | 10 | 0.8904 | 0.1592 | 1.0000 | 0.4940 | 1.0000 |
| term_structural_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
| field_gid_f1 | 10 | 0.9331 | 0.0960 | 0.9708 | 0.6613 | 1.0000 |
| field_concept_f1 | 10 | 0.9305 | 0.0979 | 0.9708 | 0.6613 | 1.0000 |
| field_instance_f1 | 10 | 0.9305 | 0.0979 | 0.9708 | 0.6613 | 1.0000 |
| field_instance_of_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
| term_field_f1 | 10 | 0.9223 | 0.0949 | 0.9624 | 0.6613 | 1.0000 |
| term_alias_precision | 10 | 0.9200 | 0.0737 | 0.9432 | 0.7816 | 1.0000 |
| term_alias_recall | 10 | 0.8904 | 0.1592 | 1.0000 | 0.4940 | 1.0000 |
| term_alias_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
| dedup_term_structural_precision | 10 | 0.9200 | 0.0737 | 0.9432 | 0.7816 | 1.0000 |
| dedup_term_structural_recall | 10 | 0.8904 | 0.1592 | 1.0000 | 0.4940 | 1.0000 |
| dedup_term_structural_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
| dedup_term_field_f1 | 10 | 0.9223 | 0.0949 | 0.9624 | 0.6613 | 1.0000 |
| dedup_term_alias_precision | 10 | 0.9200 | 0.0737 | 0.9432 | 0.7816 | 1.0000 |
| dedup_term_alias_recall | 10 | 0.8904 | 0.1592 | 1.0000 | 0.4940 | 1.0000 |
| dedup_term_alias_f1 | 10 | 0.8952 | 0.1064 | 0.9624 | 0.6613 | 1.0000 |
