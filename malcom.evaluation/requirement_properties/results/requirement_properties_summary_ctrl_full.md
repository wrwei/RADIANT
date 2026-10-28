# Requirement-level FDR properties

Cells: models passing / models checked. Clean models should pass every column;
each mutant should fail at least one of its target properties.

| Block | Model | Arm / mutant | R1 | R2 | R3 | R4 | S1 | S2 | S3 | V1 | V2 | V3 | M1 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| factorial_v2 | deepseek_v4 | multi | 0/9 | 0/9 | 9/9 | 9/9 | 0/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 |
| factorial_v2 | deepseek_v4 | multi_no_repair | 0/8 | 0/8 | 8/8 | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| factorial_v2 | deepseek_v4 | single | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| factorial_v2 | deepseek_v4 | single_repair | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| june_2026 | claude_sonnet_46 | multi | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| june_2026 | deepseek_v4 | multi | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| june_2026 | qwen3_max | multi | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| mutant | deepseek_v4 | M1_hazard_gate_drops_inOPEZ | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| mutant | deepseek_v4 | M2_HCM_entry_advice_missing | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| mutant | deepseek_v4 | M3_CAM_released_on_risk | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| mutant | deepseek_v4 | M4_CAM_override_removed | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| mutant | deepseek_v4 | M5_spurious_heading_advice | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| table1_v2 | deepseek_v4 | multi | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |

Mutant detection:

- M1_hazard_gate_drops_inOPEZ: targets R1, S1; failed R1, S1
- M2_HCM_entry_advice_missing: targets R1, R3; failed R1, R3
- M3_CAM_released_on_risk: targets R1; failed R1
- M4_CAM_override_removed: targets R2, R3, S3; failed R2
- M5_spurious_heading_advice: targets R1; failed R1
