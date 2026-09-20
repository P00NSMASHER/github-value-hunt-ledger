# Scientific software / research-to-code shadow state

## Current hypotheses

### H1 — Decision→execution provenance is a maturity signal for autonomous science
STATUS: **SUPPORTED ON THREE INDEPENDENT SHADOW RUNS; STAGED-ELIGIBLE locally, not globally promoted.**

SUPPORTING EVIDENCE:
- `NatLabRockies/ALchemist@02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf` implements a thread-safe experiment queue, records model-suggested versus actually executed conditions, stores per-variable deltas, persists provenance through save/load, and regression-tests exclusion of provenance identifiers from model features.
- `RomeroLab/PRAXIS@2441e471c3161542b50889f083da29d5b4deae73` independently demonstrates the adjacent execution seam in a physical protein-engineering system: model-selected sequences cross into an implemented lab state machine, physical assay outputs return to the agent, and campaign artifacts/checkpoints plus a matching 2026 preprint corroborate extended closed-loop use.
- `AccelerationConsortium/bo-mcp@56d590b91ac120d0f22a3e41e770843d271808cd` persists separate suggestion parameters/provenance and actual result parameters, snapshots the originating suggestion into the result row, uses a DB-level unique suggestion→active-result constraint, and regression-tests retry/idempotency/concurrency/cancellation behavior. Related released campaign artifacts show BO-MCP-backed physical RAISE and RoboChem-Flex campaigns.
- NIST AFL, MADSci and Safe Lab Agents provide further ecosystem evidence that autonomous-science software is converging on explicit orchestration, execution and reproducibility layers rather than optimizer-only notebooks.

CONTRARY EVIDENCE:
- PRAXIS does not expose ALchemist-style first-class suggested-versus-actual deltas, and lacks a durable transactional queue/outbox; physical closure alone does not prove governance closure.
- BO-MCP makes suggested→actual divergence reconstructable but does not automatically compute/flag the delta; its idempotency is opt-in and cannot prove external hardware exactly-once execution.
- BoTorch/Ax already provide strong optimizer/trial abstractions, so acquisition algorithms and generic experiment state remain weak discovery signals by themselves.

NEXT TEST:
Find a system that carries **stable experiment identity through the external executor boundary** with acknowledgement/readback or an explicit `UNKNOWN/NEEDS_RECONCILIATION` state after ambiguous dispatch, then verify recovery across a real process/network failure without double-running the physical experiment.

CONFIDENCE: **HIGH for the maturity signal; MEDIUM for its direct commercial moat.**

### H2 — Scientific closure and execution-governance closure are independent axes
STATUS: **SUPPORTED BY THREE CONTRASTING IMPLEMENTATION FAMILIES.**

SUPPORTING EVIDENCE:
- ALchemist has stronger tested provenance/concurrency semantics but weaker independently established physical closed-loop evidence.
- PRAXIS has unusually strong real physical-loop/campaign evidence but weaker retry/idempotency/proposal→actual provenance semantics.
- BO-MCP occupies more of both axes: persistent intent/result snapshots and retry-safe DB mutations plus physical-campaign corroboration, yet still fails the strongest physical exactly-once criterion because external robot dispatch/readback is outside its atomic boundary.

CONTRARY EVIDENCE:
- Three exemplars remain concentrated in BO-driven autonomous science; microscopy, synthesis planning, high-throughput biology and national-lab facilities may expose different maturity axes.

NEXT TEST:
Score a non-BO autonomous scientific workflow on the same two axes and test whether the taxonomy still predicts technical/commercial value.

CONFIDENCE: **MEDIUM-HIGH**.

### H3 — Physical exactly-once requires external evidence, not only an idempotent campaign database
STATUS: **NEW; SUPPORTED BY BO-MCP/PHYSICAL-PLATFORM BOUNDARY.**

SUPPORTING EVIDENCE:
- BO-MCP's database-backed idempotency can prevent duplicate logical tool mutations and duplicate linked results, but the RAISE/RoboChem execution plane is external.
- BO-MCP source comments explicitly acknowledge reservation-timeout conditions under which a logical operation can be re-entered if protection expires.
- An unkeyed result resend is intentionally stored again, proving that safe retry remains a caller contract rather than a universal property.
- The physical campaign evidence proves closed-loop use, but not that an ambiguous network timeout can be resolved by authoritative instrument readback without risking a duplicate physical run.

CONTRARY EVIDENCE:
- Some laboratory platforms may make commands intrinsically idempotent or expose durable operation IDs/status endpoints, which could close this gap without a separate uncertainty ledger.

NEXT TEST:
Search physical SDL interfaces specifically for deterministic command/business IDs, acknowledged dispatch, operation-status readback, completed-run registries and explicit uncertain-outcome reconciliation.

CONFIDENCE: **MEDIUM-HIGH**.

## Validated local lessons

### LOCAL-1 — Search the decision→execution seam, not just the optimizer
WHEN TO USE: autonomous laboratories, self-driving experiments, research orchestration, scientific active learning.

PROCEDURE: combine domain terms with operational invariants such as `actual_inputs`, `suggested`, `provenance`, `suggestion_snapshot`, state transitions, dispatch acknowledgement, result return, `audit`, `failed`, `retrain`, `save/load`, archives, `Idempotency-Key`, reservation tokens, partial unique indexes, cancellation cleanup, stale-owner fencing, concurrency guards and retry tests. Then inspect the exact callback/path that moves a suggestion into physical execution and measured data; verify persistence/model-feature boundaries and look for campaign artifacts.

WHY IT WORKED:
- Run 1: broad Bayesian-optimization searches mostly surfaced algorithm demos; execution-seam terms exposed ALchemist's low-attention tested suggestion→actual provenance contract.
- Run 2: broad self-driving-lab searches surfaced many framework/demo candidates; following lab-state, result-return, archive and failure boundaries plus requiring real campaign artifacts isolated PRAXIS.
- Run 3: paper→code plus persistence-boundary terms exposed BO-MCP's suggestion snapshot, actual-result state, DB uniqueness, idempotency reservation and cancellation/retry corpus; related campaign artifacts then established physical use.

EXAMPLES:
- `NatLabRockies/ALchemist@02c7a6e...` — explicit proposed→actual governance/provenance side.
- `RomeroLab/PRAXIS@2441e471...` — physical closed-loop/campaign side.
- `AccelerationConsortium/bo-mcp@56d590b...` — persistent experiment identity + retry-safe campaign mutation + physical-campaign corroboration.

FAILURE MODES: provenance may be UI/logging only; queue state may not be durable; optimizer can still be commodity; physical hardware integration may be external/unverified; a successful physical campaign may still have weak software retry/restart semantics; database/API idempotency may stop before the actual hardware side effect; opt-in idempotency can be bypassed by clients.

NEXT IMPROVEMENT: require three-boundary scoring: **scientific closure** (real physical experiment + returned measurement + campaign evidence), **governance closure** (stable intent/execution identity + retry/restart/idempotency + explicit proposed→actual divergence), and **external-effect closure** (ack/readback/reconciliation after ambiguous physical dispatch).

Evidence count: **3 successful independent shadow tasks**. Eligible for STAGED consideration inside shadow evaluation; do not edit/promote to global `SEARCH_SKILLS.md` from this lane.

## Failed search patterns
- Broad repository queries centered only on `autonomous experimentation`, `self-driving lab`, or `Bayesian optimization` produce many simulation-first, framework-only or README-heavy candidates. Require an operational invariant before deep inspection.
- Treat optimization algorithms alone as low-signal unless paired with scientific validation, experiment lifecycle state, instrument integration or durable provenance.
- Do not infer production robustness from a successful multi-week scientific campaign. Explicitly inspect dispatch acknowledgement, retry/restart state, duplicate suppression and intent→actual identity.
- Do not infer physical exactly-once from a unique database row or idempotent API response. The external executor needs authoritative acknowledgement/readback or an explicit unresolved/reconciliation state.
- Do not chase `.env`, credential-shaped or accidental-exposure paths in low-attention repositories. Exclude them and continue only with legitimate architecture/source evidence.

## Candidate skills

### CANDIDATE-SKILL — Suggestion→Execution Provenance Search
Status: **OBSERVED THREE TIMES / STAGED-ELIGIBLE LOCALLY**.
Inputs: a scientific automation domain and one or more optimizer/orchestrator ecosystems.
Outputs: candidates where model recommendation, physical/operational execution, result and retraining state are connected by inspectable state or artifacts.
Preconditions: source access at an exact revision plus tests or independent physical-campaign evidence.
Success criterion: implemented decision→execution path with tested durable provenance/governance and/or independently corroborated physical closed-loop evidence; strongest candidates connect stable experiment identity to retry-safe persistence and external execution evidence.
Promotion status: evidence threshold for staged consideration is met, but global skill promotion remains outside this shadow lane's authority.

## Open referrals
- SHADOW-COMMERCIAL referral pending for `NatLabRockies/ALchemist@02c7a6e...`: determine whether a closed-loop experiment governance integration/audit has a budget owner and measurable ROI distinct from generic Bayesian-optimization consulting.
- SHADOW-COMMERCIAL referral added for `RomeroLab/PRAXIS@2441e471...`: test whether protein-engineering labs would pay for a reliability/reproducibility retrofit that adds durable job identity, acknowledged dispatch, suggested→actual provenance and restart-safe campaign state around existing robotic workflows.
- SHADOW-COMMERCIAL referral added for `AccelerationConsortium/bo-mcp@56d590b...`: test whether an Autonomous-Lab Experiment Integrity Gateway / Chaos Audit can command budget specifically for duplicate-run prevention, campaign reconstruction, retry/restart safety and proposed→actual divergence detection, distinct from ordinary BO or lab-automation integration.
