# Pair 4 — EXPERIMENT persistent state

## Validated reusable lessons
None yet.

## Failed search patterns
- Task 23: Broad queries built only from "self-driving lab", "optimizer", "campaign" and "autonomous laboratory" mostly surfaced orchestration/optimization frameworks without evidence that the campaign authority distinguishes scientific confirmation, recovery, context acquisition, escalation and stopping. Do not treat generic closed-loop execution as a governance-state match without source-level transition evidence.
- Task 24: Railway scheduling searches centered on "optimization", "robustness" or "re-planning" alone surfaced many projects that recompute a schedule but do not preserve accepted/underway work. A previous solution supplied as an OR-Tools `AddHint`/warm start is not evidence of a lock: it can be displaced whenever the new objective prefers something else.
- Task 24: README claims of "robustness" are weak evidence. Require executable perturbation or stochastic evaluation and inspect the pass/fail semantics; a robustness percentage can hide tolerated failures, as RailSync explicitly counts a scenario feasible when at most one non-critical unplanned failure remains.

## Useful terminology / signatures
- Task 23: High-signal implementation signatures were `DecisionRecorded`, `campaign_id` + monotonic iteration identity, `evidence_run_ids`, explicit `stop_reason`, `intervention_required`, resume/replay from append-only events, optimizer-state restoration, and refusal to continue across an unknown physical outcome.
- Task 23: High-signal scientific-governance vocabulary was exploration/confirmation/replication/failure-recovery/human-escalation/stopping plus transition guards. Searching this vocabulary separately from optimizer terms exposed the difference between scientific authority and execution recovery.
- Task 23: A missing first-class `acquire_context`/context-acquisition transition is meaningful negative evidence when the benchmark asks for a campaign authority that can deliberately seek more context rather than merely retry or stop.
- Task 24: High-signal lock-preserving scheduling signatures were `locked_assignments`, a scenario model carrying task→block pins, propagation of those pins into the re-solve, and a hard equality such as `model.Add(x[(task_id, locked_block_id)] == 1)`.
- Task 24: High-signal robustness signatures were `ScenarioRobustnessEngine`, deterministic seeded Monte Carlo over failure-time/survival curves, explicit per-scenario failure accounting, `PlanBContingency`, disruption-diff outputs, and an adversarial test where a higher-priority emergency cannot displace locked baseline work.

## Candidate search skills awaiting second-task confirmation
- STATE-MACHINE + AUDIT-LOG CONJUNCTION: When a task asks for governed autonomous decisions, search for explicit domain-state/transition vocabulary and durable decision/event persistence as a conjunction. Then red-team each requested action independently; do not infer scientific recovery/escalation/context acquisition from generic retries, resume or human-intervention plumbing. Task 23 used this procedure to identify OpenSDL's strong replay/governance substrate while correctly withholding STRONG because the full requested action repertoire was not implemented.
- PERTURBATION + INVARIANT TEST: When a scheduling/repair/re-planning task requires preserving an accepted baseline, search for an explicit disruptive scenario and then inspect whether the invariant is encoded as a hard constraint and tested under pressure from a better-scoring/higher-priority alternative. Reject warm starts, hints and objective penalties as substitutes for locks. Separately inspect robustness success semantics so tolerated failures are not mistaken for proof. Task 24 used this procedure to distinguish RailSync's tested hard lock from a comparator whose prior plan is only an `AddHint` warm start.
