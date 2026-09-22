# NEGATIVE TRAINING / CANDIDATE LEARNING REPORT

Candidate dispositions are normalized into controlled reason categories while the original evidence-bearing reason text remains preserved in the source run.

- Structured candidate dispositions: **47**
- Direct controlled reasons: **30**
- Legacy reasons normalized through reviewed aliases: **17**
- Unmapped custom reasons: **0**
- Unique unmapped custom reason strings: **0**

## Disposition mix

| Status | Count |
|---|---:|
| rejected_or_negative | 16 |
| strong | 13 |
| watch | 11 |
| other | 7 |

## Controlled reason distribution

| Reason | Count | Alias-normalized |
|---|---:|---:|
| interesting_but_not_load_bearing | 10 | 2 |
| state_transition_verified | 9 | 4 |
| independent_negative_control | 5 | 1 |
| authority_location_bypass | 3 | 3 |
| needs_runtime_validation | 3 | 0 |
| strengthens_active_experiment | 3 | 0 |
| unsafe_retry_or_idempotency | 2 | 2 |
| no_semantic_tests | 2 | 2 |
| duplicate_or_dominated | 2 | 0 |
| authority_lineage_verified | 1 | 1 |
| fail_open_boundary | 1 | 1 |
| circular_evaluation | 1 | 1 |
| needs_exactly_once_reconciliation | 1 | 0 |
| independent_falsifier | 1 | 0 |
| needs_current_authority | 1 | 0 |
| thin_implementation | 1 | 0 |
| external_wrapper_only | 1 | 0 |

## Remaining unmapped legacy reasons

| Reason | Count |
|---|---:|
| — | 0 |

## Learning policy

- V4 runs use `reason_code_standard` for aggregation and `reason_detail` for precise technical evidence.
- Reviewed aliases normalize old runs without rewriting their source history.
- A frequent rejection reason becomes a cheap prefilter only after false-negative audits show it does not suppress unusual high-value discoveries.
- Record false-negative rescues explicitly when a previously rejected/dominated candidate later becomes strong or MASTER.
