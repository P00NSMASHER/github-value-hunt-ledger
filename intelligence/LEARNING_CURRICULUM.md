# HUNTER LEARNING CURRICULUM

Evidence-collection plan for the adaptive hunter layer. This is **measurement-only**: learned Q-values, reward means and current policy allocations do not select strategies, and this file does not change live policy.

## Blind confirmation readiness

- Operational: **no**
- Key commitment active: **false**
- Split secret available to CI: **false**
- Pending trusted generated claims: **2**
- Confirmation blocker: **split_key_commitment_inactive**

## Guardrails

- Measurement work must use the normal generated assignment/claim path.
- Never calculate, expose, choose, release, or retry work based on train/confirm membership.
- Manual, legacy, or unallocated work cannot manufacture confirmation evidence.
- Suppressed overfit/regression strategies go to repair or falsification, not additional exploitation.
- Two slots target the closest evidence gates and one slot preserves zero-run exploration.

## Recommended measurements

| Rank | Strategy | Phase | Train evidence | Confirm evidence | Reason |
|---:|---|---|---|---|---|
| 1 | STRAT:acceptance-path-transition-inspection | train_measurement | 4 runs / 10 deep (need 1 / 10) | 0 runs / 0 deep (need 2 / 6) | reduce_train_evidence_deficit |
| 2 | STRAT:evaluation-target-independence | train_measurement | 4 runs / 6 deep (need 1 / 14) | 0 runs / 0 deep (need 2 / 6) | reduce_train_evidence_deficit |
| 3 | STRAT:bidirectional-money-evidence-invariant-tracing | train_measurement | 0 runs / 0 deep (need 5 / 20) | 0 runs / 0 deep (need 2 / 6) | reduce_train_evidence_deficit |

## All active strategies

| Strategy | Phase | Train runs/deep | Confirm runs/deep | Priority |
|---|---|---:|---:|---:|
| STRAT:acceptance-path-transition-inspection | train_measurement | 4/10 | 0/0 | 79.5 |
| STRAT:evaluation-target-independence | train_measurement | 4/6 | 0/0 | 76.5 |
| STRAT:capability-conjunction-search-claim-tracing | train_measurement | 3/9 | 0/0 | 75.8 |
| STRAT:rule-period-authority-version-audit | train_measurement | 2/2 | 0/0 | 67.5 |
| STRAT:fail-open-boundary-archaeology | train_measurement | 1/4 | 0/0 | 66.0 |
| STRAT:protocol-regression-archaeology-for-pre-fat-systems | train_measurement | 1/3 | 0/0 | 65.2 |
| STRAT:authority-origin-invariant-set-consistency | train_measurement | 1/1 | 0/0 | 63.8 |
| STRAT:bidirectional-money-evidence-invariant-tracing | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:cross-source-emergence-triangulation | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:decision-claim-runtime-side-effect-trace | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:first-party-production-source-triangulation | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:ingestion-invariant-triad-intersection | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:nested-authority-and-post-review-invariant-audit | train_measurement | 0/0 | 0/0 | 60.0 |
| STRAT:paper-research-artifact-production-descendant | train_measurement | 0/0 | 0/0 | 60.0 |
