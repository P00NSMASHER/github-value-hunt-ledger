# ALLOCATOR LEARNING REPORT

- Portfolio policy: **PORTFOLIO:92c1307240fd**
- Mode: **learning_bootstrap_second_measurement_slot**
- Attributed assignment runs: **6**
- Attribution-debt runs: **0**
- Roles with sufficient evidence: **0**
- Learning bootstrap active: **true**

V10 changes portfolio capacity only from executed assignment telemetry. Generated plans that were never run receive no learning credit.

## Slot-role evidence

| Role | Runs | Inspected | Retained precision | New-cap run rate | MASTER/run | Experiment-touch rate | Outcome-run rate | Duplicate ratio | Signal | Evidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| adjacency | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| coverage | 1 | 3 | 33.3% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.050 | insufficient |
| experiment | 3 | 8 | 75.0% | 0.0% | 0.0% | 100.0% | 0.0% | 14.3% | 0.248 | insufficient |
| measurement | 0 | 0 | — | — | — | — | — | — | 0.000 | insufficient |
| verification | 1 | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% | 100.0% | 0.150 | insufficient |
| wildcard | 1 | 4 | 50.0% | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 0.225 | insufficient |

## Effective portfolio

| Role | Baseline slots | Effective slots |
|---|---:|---:|
| adjacency | 2 | 1 |
| coverage | 3 | 3 |
| experiment | 6 | 6 |
| measurement | 1 | 2 |
| verification | 1 | 1 |
| wildcard | 1 | 1 |

## Adaptation decision

- Shift: **{"automatic_revert_condition": "first strategy-level prior becomes eligible_for_policy_consideration", "blind_confirmation_operational": true, "confirmed_strategy_priors": 0, "from_role": "adjacency", "measurement_recommendations": 3, "reason": "blind_learning_bootstrap_no_confirmed_strategy_priors", "slot_id": "SLOT-11", "to_role": "measurement"}**
- At most one slot can move per generation.
- Measurement, verification and wildcard remain protected roles during ordinary performance adaptation.
- During blind-learning bootstrap only, one adjacency/coverage/experiment slot above its configured minimum may temporarily become a second measurement slot; this reverts after the first confirmed strategy prior.
- Experiment, coverage and adjacency cannot move outside configured minimum slot bounds.
- Manual overrides are measured separately and never silently treated as generated allocator success.
- Allocation signal is a scheduling heuristic; realized outcomes remain the strongest downstream evidence.
