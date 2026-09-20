# NEGATIVE TRAINING / CANDIDATE LEARNING REPORT

Candidate dispositions are normalized into controlled reason categories while the original evidence-bearing reason text remains preserved in the source run.

- Structured candidate dispositions: **19**
- Direct controlled reasons: **2**
- Legacy reasons normalized through reviewed aliases: **17**
- Unmapped custom reasons: **0**
- Unique unmapped custom reason strings: **0**

## Disposition mix

| Status | Count |
|---|---:|
| strong | 7 |
| watch | 7 |
| rejected_or_negative | 5 |

## Controlled reason distribution

| Reason | Count | Alias-normalized |
|---|---:|---:|
| state_transition_verified | 5 | 4 |
| authority_location_bypass | 3 | 3 |
| interesting_but_not_load_bearing | 2 | 2 |
| unsafe_retry_or_idempotency | 2 | 2 |
| no_semantic_tests | 2 | 2 |
| authority_lineage_verified | 1 | 1 |
| independent_negative_control | 1 | 1 |
| fail_open_boundary | 1 | 1 |
| circular_evaluation | 1 | 1 |
| needs_exactly_once_reconciliation | 1 | 0 |

## Remaining unmapped legacy reasons

| Reason | Count |
|---|---:|
| — | 0 |

## Learning policy

- V4 runs use `reason_code_standard` for aggregation and `reason_detail` for precise technical evidence.
- Reviewed aliases normalize old runs without rewriting their source history.
- A frequent rejection reason becomes a cheap prefilter only after false-negative audits show it does not suppress unusual high-value discoveries.
- Record false-negative rescues explicitly when a previously rejected/dominated candidate later becomes strong or MASTER.
