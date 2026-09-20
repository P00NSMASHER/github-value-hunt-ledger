# Scientific software / research-to-code shadow state

## Current hypotheses

### H1 — Decision→execution provenance is a maturity signal for autonomous science
STATUS: **SUPPORTED ON TWO INDEPENDENT SHADOW RUNS; STAGED-ELIGIBLE locally, not globally promoted.**

SUPPORTING EVIDENCE:
- `NatLabRockies/ALchemist@02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf` implements a thread-safe experiment queue, records model-suggested versus actually executed conditions, stores per-variable deltas, persists provenance through save/load, and regression-tests exclusion of provenance identifiers from model features.
- `RomeroLab/PRAXIS@2441e471c3161542b50889f083da29d5b4deae73` independently demonstrates the adjacent execution seam in a physical protein-engineering system: model-selected sequences cross into an implemented lab state machine, physical assay outputs return to the agent, and campaign artifacts/checkpoints plus a matching 2026 preprint corroborate extended closed-loop use.
- NIST AFL, MADSci and Safe Lab Agents provide further ecosystem evidence that autonomous-science software is converging on explicit orchestration, execution and reproducibility layers rather than optimizer-only notebooks.

CONTRARY EVIDENCE:
- PRAXIS does not expose ALchemist-style first-class suggested-versus-actual deltas, and lacks a durable transactional queue/outbox; physical closure alone does not prove governance closure.
- BoTorch/Ax already provide strong optimizer/trial abstractions, so acquisition algorithms and generic experiment state remain weak discovery signals by themselves.

NEXT TEST:
Find a third system where **physical execution plus explicit durable proposed→actual identity** survives retries/restarts, and verify whether the identity is used to prevent duplicate execution, bad retraining or irreproducible campaign state.

CONFIDENCE: **MEDIUM-HIGH**.

### H2 — Scientific closure and execution-governance closure are independent axes
STATUS: **NEW; supported by contrast between Run 1 and Run 2.**

SUPPORTING EVIDENCE:
- ALchemist has stronger tested provenance/concurrency semantics but weaker independently established physical closed-loop evidence.
- PRAXIS has unusually strong real physical-loop/campaign evidence but weaker retry/idempotency/proposal→actual provenance semantics.

CONTRARY EVIDENCE:
- Two exemplars are insufficient to establish a general taxonomy across chemistry, materials, microscopy and biology.

NEXT TEST:
Score future autonomous-science candidates separately on (1) physical/scientific closure and (2) execution-governance closure; test whether high-value systems occupy both quadrants rather than only one.

CONFIDENCE: **MEDIUM**.

## Validated local lessons

### LOCAL-1 — Search the decision→execution seam, not just the optimizer
WHEN TO USE: autonomous laboratories, self-driving experiments, research orchestration, scientific active learning.

PROCEDURE: combine domain terms with operational invariants such as `actual_inputs`, `suggested`, `provenance`, state transitions, dispatch acknowledgement, result return, `audit`, `failed`, `retrain`, `save/load`, archives, concurrency guards and retry tests. Then inspect the exact callback/path that moves a suggestion into physical execution and measured data; verify persistence/model-feature boundaries and look for campaign artifacts.

WHY IT WORKED:
- Run 1: broad Bayesian-optimization searches mostly surfaced algorithm demos; execution-seam terms exposed ALchemist's low-attention tested suggestion→actual provenance contract.
- Run 2: broad self-driving-lab searches surfaced many framework/demo candidates; following lab-state, result-return, archive and failure boundaries plus requiring real campaign artifacts isolated PRAXIS.

EXAMPLES:
- `NatLabRockies/ALchemist@02c7a6e...` — governance/provenance side.
- `RomeroLab/PRAXIS@2441e471...` — physical closed-loop/campaign side.

FAILURE MODES: provenance may be UI/logging only; queue state may not be durable; optimizer can still be commodity; physical hardware integration may be external/unverified; a successful physical campaign may still have weak software retry/restart semantics.

NEXT IMPROVEMENT: require two-axis scoring: **scientific closure** (real physical experiment + returned measurement + campaign evidence) and **governance closure** (stable intent/execution identity + acknowledgement + retry/restart/idempotency + explicit proposed→actual divergence).

Evidence count: **2 successful independent shadow tasks**. Eligible for STAGED consideration inside shadow evaluation; do not edit/promote to global `SEARCH_SKILLS.md` from this lane.

## Failed search patterns
- Broad repository queries centered only on `autonomous experimentation`, `self-driving lab`, or `Bayesian optimization` produce many simulation-first, framework-only or README-heavy candidates. Require an operational invariant before deep inspection.
- Treat optimization algorithms alone as low-signal unless paired with scientific validation, experiment lifecycle state, instrument integration or durable provenance.
- Do not infer production robustness from a successful multi-week scientific campaign. Explicitly inspect dispatch acknowledgement, retry/restart state, duplicate suppression and intent→actual identity.

## Candidate skills

### CANDIDATE-SKILL — Suggestion→Execution Provenance Search
Status: **OBSERVED TWICE / STAGED-ELIGIBLE LOCALLY**.
Inputs: a scientific automation domain and one or more optimizer/orchestrator ecosystems.
Outputs: candidates where model recommendation, physical/operational execution, result and retraining state are connected by inspectable state or artifacts.
Preconditions: source access at an exact revision plus tests or independent physical-campaign evidence.
Success criterion: implemented decision→execution path with either tested durable provenance/governance or independently corroborated physical closed-loop campaign evidence; strongest candidates should have both.
Promotion status: evidence threshold for staged consideration is met, but global skill promotion remains outside this shadow lane's authority.

## Open referrals
- SHADOW-COMMERCIAL referral pending for `NatLabRockies/ALchemist@02c7a6e...`: determine whether a closed-loop experiment governance integration/audit has a budget owner and measurable ROI distinct from generic Bayesian-optimization consulting.
- SHADOW-COMMERCIAL referral added for `RomeroLab/PRAXIS@2441e471...`: test whether protein-engineering labs would pay for a reliability/reproducibility retrofit that adds durable job identity, acknowledged dispatch, suggested→actual provenance and restart-safe campaign state around existing robotic workflows.
