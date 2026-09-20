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
STATUS: **SUPPORTED; FAIL-CLOSED PHYSICAL-RECOVERY SIGNAL NOW FOUND IN TWO INDEPENDENT EXECUTOR FAMILIES, BUT DURABLE CROSS-PROCESS EFFECT ID REMAINS UNRESOLVED.**

SUPPORTING EVIDENCE:
- BO-MCP's database-backed idempotency can prevent duplicate logical tool mutations and duplicate linked results, but the RAISE/RoboChem execution plane is external.
- BO-MCP source comments explicitly acknowledge reservation-timeout conditions under which a logical operation can be re-entered if protection expires.
- An unkeyed result resend is intentionally stored again, proving that safe retry remains a caller contract rather than a universal property.
- `AccelerationConsortium/opentrons-flex@2639016ee9f234949aaf596c2ab2b93694eb0e0b` supplies the strongest executor-side evidence pattern so far: durable labware state is invalidated and fsynced before physical movement, only committed after verified completion, and remains invalid after cancellation, unclean restart or commit failure.
- The same connector combines software recovery gates with authoritative device readback: unknown/missing Flex Stacker sensor/platform state fails closed, and future actuation is blocked until recovery/reconciliation instead of blindly replaying an ambiguous physical action.
- Its SiLA observable path correlates command initiation and result polling with a `CommandExecutionUUID`, demonstrating protocol-level operation identity while also showing why that UUID alone is not a durable business-effect identity across process loss.
- `PyLabRobot/pylabrobot@697272d3591da6e5be1fcf70448479904e326904` independently implements the same **pre-actuation vs post-actuation** distinction for Agilent VSpin/Access2. A `TransitionToken` records whether hardware may have moved; post-actuation failure/cancellation sets sticky `recovery_required`, clears uncertain bucket/teachpoint knowledge, and ordinary motion is refused until recovery/readiness evidence is re-established. Dedicated tests exercise these paths.
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` exposes the complementary orchestration-side primitive: persisted workflow/action identity and explicit `ActionStatus.UNKNOWN` after ambiguous dispatch/result retrieval, including logic that queries the same `action_id` when dispatch may have succeeded but its response was lost.

CONTRARY EVIDENCE:
- `opentrons-flex` does not prove universal physical exactly-once; after a crash it may intentionally know only that the physical world is uncertain and require operator/local reconciliation.
- Its strongest durable uncertainty semantics are concentrated in labware movement, stacker recovery and controlled run mutation rather than every possible liquid/motion command.
- PyLabRobot's VSpin/Access2 recovery state and event operation IDs are session-local/in-process; a new process does not inherit the sticky recovery flag or a durable business-effect record.
- MADSci's workcell/action identity is durable, but the inspected SiLA client tracks running observable commands in an in-memory map. `UNKNOWN` ultimately fails the workflow rather than itself proving the device effect, so a later resubmission still depends on an external system-of-record to avoid blind physical redispatch.
- Physical/HITL behavior for the newest executor semantics was not independently reproduced in these shadow runs.

NEXT TEST:
Find or construct a scientific execution stack that durably binds **workflow step ID → business-effect ID → native device/protocol command ID → authoritative readback/reconciliation evidence**. Crash after the device write but before acknowledgement, restart the process, and verify that the same durable effect record blocks redispatch until readback resolves the original physical outcome.

CONFIDENCE: **HIGH that campaign idempotency alone is insufficient; HIGH that fail-closed post-actuation uncertainty is a reusable primitive; MEDIUM that a broadly reusable cross-process physical-effect ledger already exists publicly.**

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

### LOCAL-2 — Search physical-effect closure, not just retryable orchestration
WHEN TO USE: laboratory robots, instrument servers, plate handlers, autosamplers, synthesis platforms and any scientific workflow where retrying a side effect can physically duplicate or corrupt work.

PROCEDURE: search for invalidation before actuation, explicit `mark_actuated`/post-actuation markers, `recovery_required`, `clean_shutdown`, `reconcile physical`, `unknown`/`missing` device state, generation fencing, `require_home`, atomic/fsync state commits, command-execution UUIDs plus result polling, and tests that cancel/crash after physical work begins. Inspect whether future actuation is denied until authoritative readback or reconciliation restores certainty, then separately verify whether the unresolved state and command identity survive process loss.

WHY IT WORKED:
- Run 4: these invariants isolated `AccelerationConsortium/opentrons-flex`, whose durable deck ledger is deliberately invalid before movement and remains fail-closed after cancellation, unclean restart or post-move commit failure, with additional device-sensor recovery checks.
- Run 5: `recovery_required`, `position_uncertain` and actuation-boundary terms isolated PyLabRobot's independent VSpin/Access2 semantic state machine. Source/tests distinguish pre-actuation rejection from post-actuation failure, retain recovery state in the live session, invalidate uncertain position knowledge and require fresh controller readiness before ordinary motion. The same pass exposed MADSci's complementary durable action-ID/UNKNOWN semantics and, crucially, the unsafe split between persistent orchestration and in-memory device-command tracking.

FAILURE MODES: a command UUID may die with the process; locks serialize but do not prove execution outcome; simulator success does not prove physical recovery; manual reconciliation may still be required; deep guarantees may cover only selected operations; an in-memory recovery flag can disappear on restart; a durable workflow ID is not sufficient if the native device command/outcome cannot be re-associated after restart.

NEXT IMPROVEMENT: require a **cross-layer durable join** rather than another isolated recovery flag: workflow step ID + business-effect ID + native device command ID + authoritative device/system-of-record readback. Test the crash window after physical dispatch but before acknowledgement and prove retry remains blocked after process restart until reconciliation resolves the original effect.

Evidence count: **2 successful independent executor-family shadow tasks**. Eligible for STAGED consideration inside shadow evaluation; do not promote to global `SEARCH_SKILLS.md` from this lane. The staged lesson must retain the explicit durability caveat above.

## Failed search patterns
- Broad repository queries centered only on `autonomous experimentation`, `self-driving lab`, or `Bayesian optimization` produce many simulation-first, framework-only or README-heavy candidates. Require an operational invariant before deep inspection.
- Treat optimization algorithms alone as low-signal unless paired with scientific validation, experiment lifecycle state, instrument integration or durable provenance.
- Do not infer production robustness from a successful multi-week scientific campaign. Explicitly inspect dispatch acknowledgement, retry/restart state, duplicate suppression and intent→actual identity.
- Do not infer physical exactly-once from a unique database row or idempotent API response. The external executor needs authoritative acknowledgement/readback or an explicit unresolved/reconciliation state.
- Do not infer physical certainty from command IDs, locks or “success” responses alone; inspect when world state becomes non-authoritative and what evidence is required to restore it.
- Durable orchestration state and strong executor recovery often live in different layers. Verify persistence and native command correlation at the handoff rather than scoring either layer alone: a durable workflow ID with an in-memory device-command map is unsafe after process loss, while an executor-local recovery flag without persistent effect identity loses uncertainty on restart.
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
- SHADOW-COMMERCIAL referral added for `AccelerationConsortium/opentrons-flex@2639016...`: test whether robotized labs/CROs will pay for a Physical Lab Command Integrity / Recovery Audit that measures ambiguous-dispatch risk, duplicate physical-action exposure and recovery MTTR, distinct from ordinary instrument integration.
- SHADOW-COMMERCIAL referral to add for `PyLabRobot/pylabrobot@697272d...` + `AD-SDL/MADSci@6b1ab6...`: test whether labs will buy a cross-layer Scientific Instrument Uncertainty Firewall / Recovery Audit focused specifically on blind redispatch risk after “physical command may have executed but acknowledgement was lost.”