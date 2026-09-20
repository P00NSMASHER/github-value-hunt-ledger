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

## 2026-09-20 — Run 6 evidence-backed update

### H3 refinement — durable uncertainty persistence is a real cross-domain kernel, but reconciliation remains the missing half
STATUS: **SUPPORTED BY A THIRD INDEPENDENT EXECUTION FAMILY; STRONGER DURABILITY EVIDENCE, SAME RECONCILIATION GAP.**

SUPPORTING EVIDENCE:
- `ros-claw/rosclaw@027c66d907a82432be1b0ce7a0e3e8bbd33ff773` persists physical action lifecycle into an append-only SQLite daemon ledger before/around REAL execution, with stable `action_id`, HMAC-chained events, an independently signed head anchor and fail-closed rollback/integrity checks.
- On daemon startup, source reconstructs unfinished durable jobs. A job that was `RUNNING` in `ExecutionMode.REAL` is terminalized with `DAEMON_RESTART_OUTCOME_UNKNOWN`; the daemon requests E-Stop and records a recovery-required gate instead of replaying the command. Regression tests assert the unknown-outcome code and E-Stop latch.
- Runtime status exposes persistent recovery action IDs, and safety/architecture documentation requires operator review before new REAL work after an unclean restart. The control plane therefore preserves **uncertainty itself** across process death rather than forgetting it.
- The LeRobot execution path separately represents command delivery as protocol-acknowledged, delivery-inferred, rejected or uncertain and verifies returned physical feedback before declaring a step complete. Emergency-stop semantics distinguish dispatch/driver acknowledgement from `physical_stop_observed`.
- Commit history shows the durable rosclawd control ledger entered in `0db0d79ca08c2ff382e43e98fd1097880712c39c`; the pinned 1.3.0 Internal Alpha release retains this architecture under an unusually broad daemon/kernel regression matrix.

CONTRARY EVIDENCE:
- ROSClaw does **not** generically prove what the interrupted physical command actually did after restart. Its recovery acknowledgement is an operator gate, not an authoritative device-specific reconciliation of the original effect.
- No inspected universal schema durably binds every abstract `action_id` to a vendor-native command ID that can be re-queried after process loss.
- The strongest physical readback evidence is operation-specific (for example verified feedback during LeRobot steps and observed stop state for E-Stop), not a generic post-crash resolver for arbitrary REAL actions.
- The pinned release is explicitly `1.3.0 Internal Alpha`; source/tests are strong, but field maturity and scientific-lab deployment evidence are limited.

LESSON IMPACT:
- LOCAL-2 now has a **third independent implementation-family success** (Opentrons-Flex, PyLabRobot VSpin/Access2, ROSClaw cross-domain robotics analog). The durable version of the pattern is sharper: persist `SENT/IN_PROGRESS` before external effect, preserve `OUTCOME_UNKNOWN` through restart, block replay, and require a separate reconciliation authority to close the state.
- This does not justify a global `SEARCH_SKILLS.md` promotion from the shadow lane. Keep the lesson STAGED-eligible locally and preserve the distinction between **durable uncertainty** and **resolved physical truth**.

NEXT TEST:
Find a scientific executor whose post-restart recovery path reuses the same durable effect/command identity to query the real instrument/system-of-record and transitions `OUTCOME_UNKNOWN → SUCCEEDED/FAILED_NO_EFFECT` from authoritative readback without issuing a second physical command.

CONFIDENCE: **HIGH that durable unknown-outcome gating is a reusable kernel; MEDIUM that a broadly reusable authoritative reconciliation implementation is public.**

## 2026-09-20 — Run 7 evidence-backed update

### H3 refinement — effect truth needs a temporal durability axis
STATUS: **SUPPORTED; A NEW INTERMEDIATE SAFETY/TRUTH LAYER IS VERIFIED, BUT THE STRONGEST H3 RECONCILIATION TARGET REMAINS UNRESOLVED.**

SUPPORTING EVIDENCE:
- `Abenor-Labs/Open-MHS@92b04b023915ba7cdf2cac55eb58e86a3c94cc0d` independently implements a declarative hardware safety envelope with two pre-transport enforcement points. Dedicated tests assert unsafe writes produce zero transport emissions and no state change, including a deliberately naive driver behind the middleware.
- The same write path does not equate transport success with physical truth: where feedback exists it polls the declared sensor and raises explicit desync when the command landed but the observed state did not follow.
- The RPC/audit boundary distinguishes four materially different classes: policy refusal (`transmitted: null`), concrete transmitted values with verification status, transmitted-but-desynced state, and transport failure where whether the effect occurred is genuinely **unknown**.
- Audit records are hash-chained, flushed/fsynced, and a fresh process resumes sequence/hash state from the prior file. This makes recorded effect truth persistent across ordinary restart.
- The official Model Hardware Standard entered limited research preview on 2026-08-27, while `Abenor-Labs/Open-MHS` and `SCUT-ESA/open-mhs` appeared independently within days. The technical category is therefore beginning to branch before the official public specification exists.

CONTRARY EVIDENCE:
- Open-MHS writes its audit event only **after** the driver write returns or throws. A process/power failure after bytes reached the device but before the audit append can lose the fact that the effect may have happened.
- No inspected durable business-effect/native-command identity is reserved before dispatch; the registry and last-write state are in memory, so restart does not itself block a repeated command because an earlier physical outcome is unresolved.
- No generic post-restart resolver reuses the original native command identity to query the device/system-of-record and close ambiguity without redispatch.
- The project explicitly states real-hardware validation is still roadmap work; serial/manipulation evidence is fake-port/loopback/simulation rather than physical metal.
- The official MHS schema/API is not yet public, so independent “Open-MHS” projects are emergence evidence, not proof of conformance to the eventual official standard.

LESSON IMPACT:
- Refine LOCAL-2 with an **effect-integrity ladder** instead of a binary “safe/unsafe” label:
  0. no explicit external-effect truth distinction;
  1. runtime truth classification (`NOT_SENT / SENT_VERIFIED / SENT_DESYNC / SEND_OUTCOME_UNKNOWN`);
  2. uncertainty/effect identity is durably persisted **before** external actuation and restart blocks blind replay;
  3. the same durable native/effect identity supports authoritative post-crash reconciliation to `SUCCEEDED` or `FAILED_NO_EFFECT` without issuing a second physical command.
- Run 7 verifies a strong Level-1 component. ROSClaw/Opentrons-style patterns cover much of Level 2. Level 3 remains the high-value missing kernel.
- New LOCAL-3 candidate lesson: **inspect the effect truth table and the timing of persistence relative to actuation**. One successful task only; keep it LOCAL and do not stage/promote globally yet.

NEXT TEST:
Find a scientific executor that reaches **Level 3**: crash after device write but before acknowledgement, restart with the same durable business-effect/native-command identity, query authoritative device/system-of-record state, and resolve the original action without redispatch.

CONFIDENCE: **HIGH that the ladder correctly separates auditability from crash-safe effect integrity; MEDIUM that a public Level-3 implementation exists.**

## 2026-09-20 — Run 8 evidence-backed update

### H3 refinement — Level 3 remains unverified after three targeted near-matches
STATUS: **NO_FIND FOR LEVEL 3; CONFIDENCE IN THE GAP INCREASED.**

SUPPORTING / NEGATIVE EVIDENCE:
- `ioi-foundation/ioi@93f34155295b3c6122d7eb000cbe0333cc5a4f0b` is an especially instructive near-match: its canonical physical-action architecture names controller idempotency, execution receipts and ambiguous-effect reconciliation, but the same canonical file marks the implementation as only a **partial admission precursor** and says the execution core, controller-side idempotency and durable execution receipts remain planned. Commit history confirms the implemented path is durable admission, not physical execution.
- `MacKenzieLuong/sparkle@a9b4e38bfbfb0926723460c63cc4355b1bfabfc0` tests command-ID duplicate detection and receipt lookup, but the receipt store is process-local memory. Same-process idempotency therefore must not be mistaken for restart-safe effect identity.
- `tongriyaotxt/open-mhs@61ced4d976dd192623cfc715139a061783972cae` provides meaningful local-control evidence—tick-priority reflexes, forward-model correction, DMP learning/generalization, habit/reflex hierarchy and Microduck deadman/safety tests—but its device write history is in memory and scientific lab adapters are explicitly simulated. It is a WATCH-level control kernel, not a Level-3 physical-effect executor.
- SiLA-style command-execution UUIDs remain useful correlation primitives, but this run found no qualifying public implementation that proves the full durable join through process loss and authoritative no-resend reconciliation.

CONTRARY EVIDENCE:
- The search did not exhaust every proprietary/vendor instrument API; a Level-3 implementation may exist in closed or domain-specific software.
- IOI's architecture shows that the desired contract is understood and being designed, so the gap may close rapidly.

NEXT TEST:
Keep the Level-3 proof obligation unchanged and broaden to **non-scientific external-effect systems with authoritative provider status APIs**—payments, cloud provisioning, manufacturing jobs, print/CNC queues, or transactional device gateways—then transfer only implementations that prove: pre-dispatch durable effect reservation, durable provider/native operation ID, crash-after-write recovery, replay block, and read-only status reconciliation of the original action.

CONFIDENCE: **HIGH that public scientific executors rarely close Level 3 end-to-end; MEDIUM-HIGH that a transferable implementation may first appear in an adjacent external-effect domain.**

### LOCAL-3 refinement — effect truth table + persistence timing
Evidence count: **2 useful tasks (Run 7 direct success; Run 8 falsification use).** Run 8 showed the method also prevents false positives: an architecture can describe perfect effect semantics while explicitly marking them planned, and a command receipt can look idempotent while living only in memory. Keep LOCAL/STAGED-ELIGIBLE only inside shadow; do not edit global `SEARCH_SKILLS.md`.

### New LOCAL candidate — Planned-vs-implemented collapse check
WHEN TO USE: architecture-heavy, standards-driven, safety-critical, autonomous-science and agent-to-hardware repositories whose documentation appears to exactly match the target capability.

PROCEDURE: before scoring, locate the repository's own implementation-status declaration, owning source path, persistence boundary, executable tests and feature-introducing history. If the document says `planned`, `partial`, `precursor`, or names future execution components, downgrade those objects to design evidence unless source/tests independently prove otherwise.

WHY IT WORKED: Run 8's strongest apparent Level-3 hit, IOI, was rejected by its own canonical implementation-status text and admission-history commits.

FAILURE MODES: implementation-status docs may lag code, so a `planned` label should trigger source/history verification rather than automatic rejection; generated schemas alone do not prove runtime ownership.

NEXT IMPROVEMENT: apply this check to one more independent architecture-heavy candidate before considering it staged.

Evidence count: **1 task**. Keep LOCAL only.

### Failed-search memory added
- Do not promote a repository because its architecture schema contains the exact ideal fields; require runtime ownership and tests for the external-effect path.
- Same-process command dedupe/receipt lookup is not durable idempotency unless the receipt/effect identity survives restart in a real backing store and restart tests exercise it.
- Simulation-rich local control can still be commercially useful, but it is not evidence for physical effect reconciliation; score the local-control kernel separately from physical execution integrity.
