# NEGATIVE TRAINING / CANDIDATE LEARNING REPORT

Candidate-level dispositions are the bridge between broad discovery and cheap triage. This report measures what the system is rejecting, retaining and still failing to encode consistently.

- Structured candidate dispositions: **17**
- Candidate records using controlled reason codes: **0**
- Candidate records using free-form/custom reason codes: **17**
- Unique custom reason strings: **17**

## Disposition mix

| Status | Count |
|---|---:|
| strong | 6 |
| watch | 6 |
| rejected_or_negative | 5 |

## Controlled reasons observed

| Reason | Count |
|---|---:|
| — | 0 |

## Free-form reasons that should eventually map to controlled reasons

| Reason | Count |
|---|---:|
| exact-line-allocation-graph-capacity-conservation-reload-revalidation | 1 |
| service-and-blanket-semantics-but-product-level-lineage-collapse | 1 |
| low-attention-HES-to-invoice-lineage-seller-side-narrow-tests | 1 |
| provider-inquiry-unknown-state-one-shot-refund-signed-delta-compensating-ledger | 1 |
| refund-confirmation-reversal-entry-settlement-dedup | 1 |
| independent-bank-transaction-reconciliation-plane | 1 |
| multi-engine-semantic-restore-signed-evidence-explicit-subject-completeness-gate | 1 |
| postgres-rabbitmq-dual-plane-semantic-recovery-tamper-chain-fail-closed-cleanup | 1 |
| validation-query-exit-zero-false-green-and-cleanup-error-swallowed | 1 |
| same-action-readback-on-lost-response-unknown-fail-closed-but-retry-loophole | 1 |
| real-vendor-run-id-but-weak-ambiguous-post-handling-no-behavior-tests | 1 |
| madsci-shaped-physics-sim-harness-no-ambiguity-regression-found | 1 |
| postcondition-self-validates-command-mutated-local-state | 1 |
| tested-progress-to-claim-bridge-but-no-independent-measurement-approval-and-alternate-line-mutation-bypasses | 1 |
| approved-unbilled-selector-exists-but-current-bill-path-creates-and-later-approves-its-own-measurement-book | 1 |
| caller-authored-bill-economics-free-text-measurement-reference-and-unguarded-lifecycle-transitions | 1 |
| startup-cancels-active-workflow-with-fresh-result-id-before-physical-reconciliation-then-retry-can-create-fresh-action-id | 1 |

## Learning policy

- V3 search runs should use `reason_code_standard` for machine learning and `reason_detail` for the precise technical explanation.
- Never discard the detailed reason text: standardized categories are for aggregation, not a substitute for evidence.
- A frequently observed rejection reason can become a cheap prefilter only after confirming that it does not suppress rare high-value discoveries.
- Track false negatives explicitly whenever a candidate initially filtered out is later promoted.
