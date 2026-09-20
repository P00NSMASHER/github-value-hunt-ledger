# Scientific software / research-to-code shadow state

## Current hypotheses

### H1 — Decision→execution provenance is a maturity signal for autonomous science
STATUS: **SUPPORTED ON ONE SHADOW RUN; not yet generalized.**

SUPPORTING EVIDENCE:
- `NatLabRockies/ALchemist@02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf` implements a thread-safe experiment queue, records model-suggested versus actually executed conditions, stores per-variable deltas, persists provenance through save/load, and regression-tests exclusion of provenance identifiers from model features.
- The same repository tests batch/categorical BoTorch acquisition paths and runs a cross-platform Python CI matrix.
- NIST's separate AFL ecosystem provides independent evidence that active-learning + automated-lab systems have reached physical experimental validation, while ALchemist adds a distinct governance/provenance emphasis.

CONTRARY EVIDENCE:
- BoTorch and Ax already provide strong optimization/experiment abstractions, so acquisition algorithms and generic trial state alone are not rare.
- ALchemist physical instrument execution and crash/restart exactly-once behavior were not established in this run.

NEXT TEST:
Find an independent scientific automation implementation that records proposed versus executed conditions and verify whether that provenance survives hardware retries/process restarts or is used to prevent bad retraining.

CONFIDENCE: **MEDIUM**.

## Validated local lessons

### LOCAL-1 — Search the decision→execution seam, not just the optimizer
WHEN TO USE: autonomous laboratories, self-driving experiments, research orchestration, scientific active learning.

PROCEDURE: combine domain terms with operational invariants such as `actual_inputs`, `suggested`, `provenance`, `queue complete`, `audit`, `failed`, `retrain`, `save/load`, concurrency guards and retry tests. Then inspect the callback that moves a suggestion into the measured dataset and verify persistence/model-feature boundaries.

WHY IT WORKED: broad Bayesian-optimization searches mostly surface algorithm demos. The operational seam exposed ALchemist's low-attention but tested suggestion→actual provenance contract and queue lifecycle.

EXAMPLE: `NatLabRockies/ALchemist@02c7a6e...`.

FAILURE MODES: provenance may be UI/logging only; queue state may not be durable; optimizer can still be commodity; physical hardware integration may be external/unverified.

NEXT IMPROVEMENT: add explicit crash/restart and hardware-retry terms; compare suggested→actual provenance against physical campaign datasets.

Evidence count: **1 successful shadow task**. Keep LOCAL; do not promote globally.

## Failed search patterns
- Broad repository queries centered only on `autonomous experimentation`, `self-driving lab`, or `Bayesian optimization` produced many simulation-first, framework-only or README-heavy candidates. Require an operational invariant (queue/provenance/retry/instrument driver/test) before deep inspection.
- Treat optimization algorithms alone as low-signal unless paired with scientific validation, experiment lifecycle state, instrument integration or durable provenance.

## Candidate skills

### CANDIDATE-SKILL — Suggestion→Execution Provenance Search
Status: **OBSERVED ONCE / LOCAL ONLY**.
Inputs: a scientific automation domain and one or more optimizer/orchestrator ecosystems.
Outputs: candidates where model recommendation, actual execution, result and retraining state are joined by a durable identifier or audit record.
Preconditions: source/test access at an exact revision.
Success criterion: implemented + tested suggested-vs-actual capture with persistence or execution-lifecycle consequences.
Promotion status: ineligible until repeated on a distinct shadow task and then evaluated under the production skill gate.

## Open referrals
- SHADOW-COMMERCIAL referral pending for `NatLabRockies/ALchemist@02c7a6e...`: determine whether a closed-loop experiment governance integration/audit has a budget owner and measurable ROI distinct from generic Bayesian-optimization consulting.
