# Pair 4 — EXPERIMENT persistent state

## Validated reusable lessons
None yet.

## Failed search patterns
- Task 23: Broad queries built only from "self-driving lab", "optimizer", "campaign" and "autonomous laboratory" mostly surfaced orchestration/optimization frameworks without evidence that the campaign authority distinguishes scientific confirmation, recovery, context acquisition, escalation and stopping. Do not treat generic closed-loop execution as a governance-state match without source-level transition evidence.

## Useful terminology / signatures
- Task 23: High-signal implementation signatures were `DecisionRecorded`, `campaign_id` + monotonic iteration identity, `evidence_run_ids`, explicit `stop_reason`, `intervention_required`, resume/replay from append-only events, optimizer-state restoration, and refusal to continue across an unknown physical outcome.
- Task 23: High-signal scientific-governance vocabulary was exploration/confirmation/replication/failure-recovery/human-escalation/stopping plus transition guards. Searching this vocabulary separately from optimizer terms exposed the difference between scientific authority and execution recovery.
- Task 23: A missing first-class `acquire_context`/context-acquisition transition is meaningful negative evidence when the benchmark asks for a campaign authority that can deliberately seek more context rather than merely retry or stop.

## Candidate search skills awaiting second-task confirmation
- STATE-MACHINE + AUDIT-LOG CONJUNCTION: When a task asks for governed autonomous decisions, search for explicit domain-state/transition vocabulary and durable decision/event persistence as a conjunction. Then red-team each requested action independently; do not infer scientific recovery/escalation/context acquisition from generic retries, resume or human-intervention plumbing. Task 23 used this procedure to identify OpenSDL's strong replay/governance substrate while correctly withholding STRONG because the full requested action repertoire was not implemented.
