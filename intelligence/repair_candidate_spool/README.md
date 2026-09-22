# Repair candidate spool

Immutable submissions for **candidate fixes** to an existing `READY_FOR_REPAIR` task.

A repair candidate is not a live edit. It is a bounded proposed variant that must be bound to the exact current repair-task hash and must carry reproducible regression-test evidence.

## Contract

1. Start from `../REPAIR_CANDIDATE_TEMPLATE.json`.
2. Copy the exact `repair_task_id` and `repair_task_sha256` from the generated repair workbench.
3. The task must currently be `READY_FOR_REPAIR`; `NEEDS_REPRODUCTION` cannot accept a candidate fix.
4. `target_type`, `target_id`, and `changed_logical_targets` must match the repair task exactly.
5. Freeze baseline and candidate artifact references plus the complete diff SHA-256.
6. Copy the repair task's exact regression-test requirement into the candidate packet; every stated test must pass and have durable evidence.
7. Do not include sensitive/confidential payloads or benchmark-contaminated evidence.
8. Spool files are immutable. Correct a bad packet with a new candidate ID rather than rewriting history.

The intake can emit only `READY_FOR_SKILL_EVAL` or reject/block the submission. It cannot write the live skill, promote globally, modify the verifier/evaluator/controller, or bypass the independent held-out/canary gates.
