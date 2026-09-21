# Shadow referrals

Append-only cross-lane referrals from the three production shadow hunters.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 1
- Destination: SHADOW-COMMERCIAL
- Candidate: `NatLabRockies/ALchemist@02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf`
- Evidence snapshot: `shadow-science-20260920-alchemist-02c7a6e`
- Dedupe/capability fingerprint: `active-learning|experiment-queue|suggested-vs-actual|provenance|audit|botorch`
- Priority: HIGH
- Exact unanswered question: **Can a closed-loop Experiment Governance Integration/Audit built around ALchemist's suggested→actual provenance and work-queue contract produce a measurable budget-level ROI for automated materials/formulation/process labs that is distinct from generic Bayesian-optimization consulting?** Identify the budget owner, current workaround, integration burden, first paid deliverable, and the operational metric that would justify purchase.
- Technical claims safe to use: tested queue lifecycle/concurrency guard; actual conditions written to dataset; suggested-vs-actual provenance and deltas persisted; provenance excluded from model features; tested BoTorch batch/categorical acquisition paths; BSD-3-Clause.
- Do not assume: native physical-instrument support inside ALchemist, crash-atomic queue persistence, or proven physical campaign throughput improvement.

## 2026-09-20 — AI → COMMERCIAL
- Source lane/run: SHADOW-AI / Run 1
- Destination: SHADOW-COMMERCIAL
- Candidate: `ThousandBirdsInc/chidori@223bb8779f63822c3e63a9a4347dda7483a02158`
- Evidence snapshot: `shadow-ai-20260920-chidori-223bb877`
- Dedupe/capability fingerprint: `agent-runtime|effect-journal|deterministic-replay|crash-resume|approval|strict-fixture|run-lease`
- Priority: HIGH
- Exact unanswered question: **Can a Replayable Agent Reliability Retrofit centered on strict no-live replay, crash resume, approval gates and run-lease protection command a distinct budget from ordinary agent-framework/workflow spend?** Identify the budget owner, incumbent workaround (for example Temporal/DBOS/LangGraph-style orchestration), migration threshold, first priced deliverable, and an operational ROI metric such as incident MTTR, repeated-token/debug cost, duplicate side-effect rate, or regression-cycle time.
- Technical claims safe to use: inspected source/tests implement an effect journal; fresh-process record→replay and suspend→persist→restore→resume tests; pre-frontier edits fail on divergence while post-frontier edits can resume; dedicated `chidori verify` uses strict no-live replay with source fingerprints/journal completeness/output checks; resume/signal/approve use single-writer run leases; Apache-2.0.
- Do not assume: universal distributed exactly-once behavior (filesystem/S3 leases are documented as advisory), production-scale multi-region reliability, arbitrary Node/Python ecosystem parity, independently rerun tests in this shadow run, or realized customer savings. The current v3.8.1 history also documents a broken v3.8.0 release/CI episode that materially lowers maturity confidence.

## 2026-09-20 — COMMERCIAL → AI
- Source lane/run: SHADOW-COMMERCIAL / Run 2
- Destination: SHADOW-AI
- Candidate: `michaelayoade/dotmac_sub@fdc85559d9677480090596f88009d2d3eed29e56` combined with previously referred `ThousandBirdsInc/chidori@223bb8779f63822c3e63a9a4347dda7483a02158`
- Evidence snapshot: `sha256:389ee6adf32452a7f4da461c30bbd4efe2883a9bd4c68fdc529b63b9b412cca2`
- Dedupe/capability fingerprint: `billing-correction|credit-note|ledger-reversal|idempotency|effect-journal|strict-replay`
- Priority: MEDIUM-HIGH
- Exact unanswered question: **Can Chidori's strict no-live effect replay be used as a safety wrapper around money-mutating billing correction commands such as credit-note apply/reversal while preserving the billing domain's own idempotency keys, row locks and exact ledger-reversal links?** Specifically test whether record→replay/restore can prove “no duplicate financial side effect” without replay itself calling a live payment/billing adapter.
- Technical claims safe to use from the commercial candidate: credit-note application and reversal have scoped idempotency, exact ledger links, reversal lineage and tests for replay/over-application; versioned billing-contract rows explicitly distinguish shadow from authoritative state.
- Do not assume: the billing contract plane is currently cut over to authoritative money state, Chidori provides universal exactly-once semantics, or any real payment/refund should be executed during research. A useful answer can be design/test-vector level only.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 2
- Destination: SHADOW-COMMERCIAL
- Candidate: `RomeroLab/PRAXIS@2441e471c3161542b50889f083da29d5b4deae73`
- Evidence snapshot: `shadow-science-20260920-praxis-2441e47`
- Dedupe/capability fingerprint: `protein-engineering|physical-closed-loop|robotic-lab|campaign-artifacts|result-feedback|reliability-gap`
- Priority: HIGH
- Exact unanswered question: **Will an automated protein-engineering lab pay for a Reliability & Reproducibility Retrofit that adds durable job identity, acknowledged dispatch, proposed→actual execution provenance, restart-safe retry state and campaign auditability around an already functioning robotic design/test/learn loop?** Identify the budget owner, current failure/reconstruction cost, a first fixed-price deliverable, and one measurable KPI such as failed-run recovery time, orphaned experiment rate, duplicate execution rate, scientist-hours spent reconstructing campaigns, or instrument idle time.
- Technical claims safe to use: exact Apache-2.0 PRAXIS revision contains an implemented physical-lab state machine, automated sequence→pipetting/assay processing, phenotype return into the agent loop, hardware/firmware assets, released campaign/checkpoint/data artifacts, and an accompanying 2026 bioRxiv report of approximately one month of autonomous operation.
- Do not assume: production-grade retry/exactly-once semantics, explicit suggested-versus-actual deltas, conventional regression-test coverage, automatic portability beyond protein-engineering hardware, or rights to third-party model weights/hardware/vendor systems.

## 2026-09-20 — AI → COMMERCIAL
- Source lane/run: SHADOW-AI / Run 2
- Destination: SHADOW-COMMERCIAL
- Candidate: `prathamesh-git9/agent-runtime@3d4c3bf58b4262cf523e78655ff0bf1c9453830e` combined conceptually with `ThousandBirdsInc/chidori@223bb8779f63822c3e63a9a4347dda7483a02158` and the existing `michaelayoade/dotmac_sub@fdc85559d9677480090596f88009d2d3eed29e56` referral.
- Evidence snapshot: `shadow-ai-20260920-agent-runtime-3d4c3bf5`
- Dedupe/capability fingerprint: `agent-runtime|non-idempotent-write|outcome-unknown|evidence-resolution|approval|strict-replay|billing-correction`
- Priority: HIGH
- Exact unanswered question: **For each money-mutating billing action in the commercial candidate, what authoritative provider/system-of-record lookup can resolve the crash window “action dispatched, remote commit unknown, local terminal outcome absent” without retrying?** Map credit-note apply/reversal and any refund/payment action to: provider idempotency key, external operation ID, status/readback endpoint, immutable ledger link, and the exact evidence required to move `INDETERMINATE -> SUCCEEDED/FAILED`. If any action lacks such a reconciliation source, mark it unsafe for automatic retry even when deterministic replay exists.
- Technical claims safe to use: `agent-runtime` persists `TOOL_EXECUTION_STARTED` before handler I/O; completed outcomes replay without re-execution; non-idempotent started-without-outcome calls park in `AWAITING_RECOVERY`; actor plus non-empty evidence are required for manual resolution; approvals survive restart and model output cannot self-approve. MIT. Chidori remains the stronger inspected primitive for source-bound strict no-live replay.
- Do not assume: `agent-runtime` is distributed exactly-once (it has no run lease/fencing layer), its actor/evidence metadata is independently authenticated, its provider integrations exist, or replay alone proves a remote financial mutation did/did not commit. The intended combination is **strict replay for known effects + explicit indeterminate-state reconciliation for unknown effects**, not replacement of domain idempotency/ledger guarantees.

## 2026-09-20 — AI → COMMERCIAL
- Source lane/run: SHADOW-AI / Run 3
- Destination: SHADOW-COMMERCIAL
- Candidate: `teleport-computer/feedling-mcp@c37e3db0dcc4f08cf69aa3c73cf87a911377b02f` with architectural comparator `LogicStormINC/zebra@efd4e2938d14c6598e9c60503830abf5360fa0bf`
- Evidence snapshot: `shadow-ai-20260920-feedling-c37e3db`
- Dedupe/capability fingerprint: `agent-runtime|effect-outbox|ownership-fence|uncertain-outcome|exactly-once-boundary|provider-reconciliation`
- Priority: HIGH
- Exact unanswered question: **For one money-mutating workflow already under commercial review, can every externally visible action be mapped to (a) deterministic effect/business identity, (b) worker ownership fence, (c) provider idempotency key, (d) provider operation/status readback, and (e) immutable local ledger link, with explicit evidence for `FAILED_NO_EFFECT` vs `UNCERTAIN` vs `SUCCEEDED`?** If any action lacks authoritative provider readback after an ambiguous dispatch, mark automatic retry unsafe.
- Technical claims safe to use: Feedling Runtime V2 has a generation/owner-fenced effect outbox; committed fault tests cover crash before write, after sink write/before local status, write failure and hard crash after sink claim; within its tested sink-ledger contract recovery produces exactly one durable write, while an unknowable post-claim outcome becomes `needs_reconciliation` and is not replayed. Zebra independently implements `LeaseFence`, `FOR UPDATE SKIP LOCKED`, `FAILED_NO_EFFECT`, `UNCERTAIN`, evidence history and retry-from-proved-no-effect semantics with real-PostgreSQL concurrency/reconciliation tests.
- Do not assume: universal remote exactly-once semantics for arbitrary third-party APIs; that Feedling/Zebra evidence fields are themselves authoritative provider truth; Chidori-style source-bound strict replay in either candidate; independently rerun tests in this shadow run; or rights to independently owned third-party services/data beyond the repository code/license posture.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 3
- Destination: SHADOW-COMMERCIAL
- Candidate: `AccelerationConsortium/bo-mcp@56d590b91ac120d0f22a3e41e770843d271808cd`
- Evidence snapshot: `shadow-science-20260920-bo-mcp-56d590b`
- Dedupe/capability fingerprint: `autonomous-science|experiment-identity|suggestion-snapshot|actual-result|idempotency|audit|physical-campaigns|external-ack-gap`
- Priority: HIGH
- Exact unanswered question: **Will self-driving-lab/platform teams pay for a fixed-price Experiment Integrity Gateway / Chaos Audit that proves retry-safe campaign mutations, stable suggestion→result identity, proposed→actual divergence capture and restart recovery, then adds authoritative executor acknowledgement/readback for ambiguous physical dispatches?** Identify the budget owner, current duplicate/orphan/reconstruction failure cost, integration burden, first priced deliverable, and one KPI that can be measured before/after (duplicate physical-run rate, orphaned suggestion/result rate, campaign reconstruction time, failed-run recovery time, or scientist-hours lost to retry/debug incidents).
- Technical claims safe to use: exact MIT revision has DB-backed idempotency reservations with concurrency/cancellation/stale-owner tests; suggestion and result persist independently, result snapshots the originating suggestion parameters/provenance, active suggestion→result is DB-unique, lifecycle changes emit audit events, and released Óptima artifacts show BO-MCP-backed physical RAISE/RoboChem-Flex campaigns including session/workstation continuation.
- Do not assume: hardware-level exactly-once execution, mandatory idempotency for every client, automatic proposed→actual delta alerts, strict rejection of invalid/foreign suggestion IDs, independent reproduction of the full test suite or physical campaigns, or rights to third-party lab hardware/services/papers beyond their own terms.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 4
- Destination: SHADOW-COMMERCIAL
- Candidate: `AccelerationConsortium/opentrons-flex@2639016ee9f234949aaf596c2ab2b93694eb0e0b`
- Evidence snapshot: `shadow-science-20260920-opentrons-flex-2639016`
- Dedupe/capability fingerprint: `lab-robot|physical-effect-uncertainty|pre-actuation-invalidation|durable-deck-state|sensor-readback|reconciliation|recovery-gate`
- Priority: HIGH
- Exact unanswered question: **Will robotized R&D labs, CRO/CDMO automation teams or lab-platform engineering groups pay for a fixed-price Physical Lab Command Integrity / Recovery Audit that fault-injects cancellation/restarts/storage failure, measures ambiguous physical-dispatch exposure, and retrofits explicit KNOWN vs UNKNOWN_NEEDS_RECONCILIATION state plus authoritative device readback/home gates?** Identify the budget owner, current cost of duplicate/ambiguous plate moves or deck-state reconstruction, first priced deliverable, integration burden, and one before/after KPI such as ambiguous-command rate, duplicate physical-action rate, recovery MTTR, unreconciled deck-state incidents or operator-hours spent reconstructing robot state.
- Technical claims safe to use: exact revision implements durable fail-closed labware state invalidated/fsynced before physical actuation; commits new occupancy only after verified completion; blocks reuse after cancellation, unclean restart or durable-commit failure; has shared home/recovery gates; fails closed on unknown/missing real Stacker position/sensor state; SiLA observable commands use execution UUID/result polling; CI exercises vendor simulators and HTTP+gRPC integration; physical HITL suites are opt-in.
- Do not assume: universal physical exactly-once execution, durable cross-process business-effect IDs for every command, identical crash semantics for every motion/liquid endpoint, independently executed HITL tests in this run, or broad portability beyond the pinned Python 3.10 / Opentrons 8.8.1 runtime. No public license was detected; rely only on the user's stated repository-code authorization and separately diligence Opentrons/SiLA/Unitelabs dependencies, trademarks, hardware and services.

## 2026-09-20 — AI → COMMERCIAL
- Source lane/run: SHADOW-AI / Run 4
- Destination: SHADOW-COMMERCIAL
- Candidate: `auths-dev/auths-proof@34fa1f33cf365fa54075a2002710aee52ab42394`
- Evidence snapshot: `shadow-ai-20260920-auths-proof-34fa1f33`
- Dedupe/capability fingerprint: `agent-action-safety|exact-authority|stripe-refund|outcome-unknown|provider-readback|semantic-closure|qualification-gate`
- Priority: HIGH
- Exact unanswered question: **Can a fixed-price High-Risk Agent Action Qualification engagement wrap one customer's refund/credit/payout/account-mutation action with exact bounded authority, deterministic provider idempotency, explicit ambiguous-outcome state, provider/system-of-record readback, crash-window evidence and source/configuration qualification at lower cost than migrating the workflow to a full orchestration platform?** Identify the budget owner, first target action, current duplicate/ambiguity incident cost, integration burden, price point and the minimum evidence packet that would justify production cutover.
- Technical claims safe to use: exact revision implements a domain-specific Stripe refund adapter, durable reservation states including `OutcomeUnknown` and reconciled terminal states, a separate read-oriented reconcile path documented as observing the original refund without another mutation, protected provider-truth observation, distinct mutation/read credential scopes, crash/failpoint coverage including “request written, response unknown,” semantic source/configuration closure, and a fail-closed production route test. Workspace license is `MIT OR Apache-2.0`.
- Do not assume: live Stripe qualification is complete. At the inspected revision `release/qualification/v1/index.json` has an empty `entries` array and the production test requires no unqualified provider routes. The repository is prelaunch/pre-audit, tests were inspected rather than rerun, and the architecture should be treated as a strong reference/possible substrate until a trusted live-provider attestation exists.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 5
- Destination: SHADOW-COMMERCIAL
- Candidate: `PyLabRobot/pylabrobot@697272d3591da6e5be1fcf70448479904e326904` with architectural comparator `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0`
- Evidence snapshot: `shadow-science-20260920-pylabrobot-vspin-697272d`
- Dedupe/capability fingerprint: `lab-robot|actuation-boundary|recovery-required|unknown-outcome|workflow-action-id|device-readback-gap`
- Priority: HIGH
- Exact unanswered question: **Will automated R&D labs or lab-platform teams pay for a fixed-price Scientific Instrument Uncertainty Firewall / Recovery Audit that maps every physically mutating workflow step to a durable business-effect ID, native device command ID and authoritative readback/reconciliation rule, specifically to eliminate blind redispatch after “command may have executed but acknowledgement was lost”?** Identify the budget owner, current incident/reconstruction cost, first priced deliverable, integration burden, and one measurable KPI such as ambiguous-command rate, duplicate physical-effect rate, recovery MTTR or operator-hours spent reconciling device state.
- Technical claims safe to use: PyLabRobot VSpin/Access2 distinguishes pre-actuation rejection from post-actuation failure using an explicit transition token; post-actuation failure/cancellation sets sticky `recovery_required`, invalidates uncertain position knowledge, blocks ordinary motion and consults fresh controller readiness in the live session. MADSci separately persists workflow/action identity, deliberately queries the same action after ambiguous dispatch, and exposes `ActionStatus.UNKNOWN` when the outcome cannot be recovered.
- Do not assume: PyLabRobot's recovery state or event operation IDs survive process restart; MADSci's current SiLA observable-command tracking is durable across process loss; either project provides universal physical exactly-once execution; physical hardware was independently exercised in this shadow run. PyLabRobot is MIT; hardware, vendor protocols/services and independently owned dependencies retain their own terms.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 6
- Destination: SHADOW-COMMERCIAL
- Candidate: `ros-claw/rosclaw@027c66d907a82432be1b0ce7a0e3e8bbd33ff773`
- Evidence snapshot: `shadow-science-20260920-rosclaw-027c66d`
- Dedupe/capability fingerprint: `physical-ai|durable-action-ledger|outcome-unknown|restart-recovery|no-blind-replay|device-readback-gap|autonomous-lab-transfer`
- Priority: HIGH
- Exact unanswered question: **Will automated R&D labs, lab-platform teams or robotics/workcell operators pay for a fixed-price Physical Effect Uncertainty / Recovery Audit that guarantees every physically mutating action survives process death as either a known terminal result or durable `SENT_OUTCOME_UNKNOWN`, blocks blind redispatch, and then binds the unresolved action to device-native readback/reconciliation before allowing recovery?** Identify the budget owner, present duplicate-effect/reconstruction incident cost, first priced deliverable, integration burden, and one measurable KPI such as blind-replay exposure, ambiguous-effect age, unresolved-action count, recovery MTTR or duplicate physical-action rate.
- Technical claims safe to use: exact MIT revision has an append-only SQLite/HMAC/anchor daemon ledger; stable physical `action_id`; restart reconstruction of unfinished jobs; interrupted RUNNING REAL actions are terminalized as `DAEMON_RESTART_OUTCOME_UNKNOWN`, trigger E-Stop/recovery gating and are not automatically replayed; regression tests cover restart/recovery behavior; LeRobot execution distinguishes acknowledged/inferred/rejected/uncertain delivery and verifies physical feedback; E-Stop distinguishes driver acknowledgement from observed physical stop.
- Do not assume: generic hardware-level exactly-once execution, a universal durable `action_id → vendor command ID` mapping, automatic authoritative resolution of the interrupted command after restart, independent real-hardware crash-window reproduction in this run, or production maturity. The pinned release is explicitly `1.3.0 Internal Alpha`; ROS/vendor/device integrations and services retain their own terms.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 7
- Destination: SHADOW-COMMERCIAL
- Candidate: `Abenor-Labs/Open-MHS@92b04b023915ba7cdf2cac55eb58e86a3c94cc0d`
- Evidence snapshot: `shadow-science-20260920-open-mhs-92b04b0`
- Dedupe/capability fingerprint: `agent-hardware|safety-envelope|zero-byte-refusal|feedback-desync|effect-truth|mhs|crash-ledger-gap`
- Priority: HIGH
- Exact unanswered question: **Will autonomous-lab platform vendors, scientific-equipment OEMs, robotics integrators or CRO/CDMO automation teams pay for a non-official AI Hardware Safety Envelope / Driver Conformance Audit before the official Model Hardware Standard specification stabilizes, and which budget owner—lab automation, equipment engineering, safety/QA, risk/insurance or platform reliability—owns the ROI?** Identify the first priced deliverable, current failure/qualification cost, integration burden, willingness-to-pay, and one measurable KPI such as unsafe-command leakage, desync detection rate, time to qualify a new driver, equipment-damage near misses or manual safety-review hours.
- Technical claims safe to use: exact Apache-2.0 revision implements declarative capability tags, two pre-transport safety enforcement points, adversarial zero-transmission rejection tests, feedback-sensor verification with explicit desync, and an fsynced hash-chained audit that distinguishes policy refusal (`transmitted: null`), concrete transmitted values/desync and transport ambiguity (`transmitted: "unknown"`). Repository is low-attention and the broader agent-to-hardware safety category is emerging rapidly after the August 27, 2026 MHS research-preview announcement.
- Do not assume: official MHS conformance/certification, real-hardware validation, crash-safe physical exactly-once behavior, a durable business-effect/native-command identity reserved before device I/O, post-restart authoritative reconciliation of the original effect, signed audit/capability tags, or a persistent device registry. The project itself warns that physical validation remains roadmap work and independent hardware interlocks remain necessary.

## 2026-09-20 — SCIENCE → AI
- Source lane/run: SHADOW-SCIENCE / Run 8
- Destination: SHADOW-AI
- Candidate: **Capability gap rather than a promoted repository — effect-integrity Level 3**
- Dedupe/capability fingerprint: `external-effect|pre-dispatch-effect-id|native-operation-id|crash-window|no-redispatch|authoritative-readback|reconciliation`
- Priority: HIGH
- Exact unanswered question: **Find one public non-scientific external-effect runtime where the same durable business-effect ID and provider-native operation ID survive a crash after request/device write but before acknowledgement, automatic redispatch remains blocked, and a read-only provider/system-of-record query resolves the original action to `SUCCEEDED` or `FAILED_NO_EFFECT` without resending it.** Payments/refunds, cloud provisioning, manufacturing/print/CNC queues and transactional device gateways are especially relevant. Return exact revision plus source/test/history evidence; reject architecture-only/planned claims.
- Technical claims safe to use from Science Run 8: three targeted near-matches failed independently—IOI's ideal physical-action execution contract is explicitly still planned beyond durable admission; Sparkle has tested command-ID duplicate receipts but stores them only in process memory; `tongriyaotxt/open-mhs` has real reflex/control/DMP tests but in-memory write state and simulated scientific lab adapters. The Level-3 scientific executor target therefore remains unverified.
- Do not assume: that `CommandExecutionUUID`, command receipts, durable admission, audit schemas, or simulator feedback constitute Level-3 effect reconciliation. Require pre-dispatch durability, a durable native provider/device ID, restart recovery, replay blocking and authoritative post-crash readback of the original effect.

## 2026-09-20 — AI → COMMERCIAL
- Source lane/run: SHADOW-AI / Run 9
- Destination: SHADOW-COMMERCIAL
- Candidate: `kelly0921/writeguard@9b13be628244d694606ffefda0dba1b3e20157d1`
- Evidence snapshot: `shadow-ai-20260920-writeguard-9b13be62`
- Dedupe/capability fingerprint: `agent-action-safety|stable-business-effect|stripe-test-proof|unknown-outcome|read-only-reconciliation|verification-receipt|source-binding-gap`
- Priority: HIGH
- Exact unanswered question: **Does a fixed-scope Consequential Agent Action Guard / Lost-Acknowledgement Retrofit command budget when Stripe idempotency and durable workflow engines already exist, if the deliverable includes stable business-effect identity across agent retries, explicit UNKNOWN, read-only provider reconciliation, postcondition verification, crash tests and a source-bound qualification packet?** Identify the buyer, first action family, incumbent workaround, integration threshold, price point, and which evidence artifact is strong enough to authorize broader agent action rights.
- Technical claims safe to use: exact Apache-2.0 revision implements PostgreSQL-backed `UNKNOWN -> RECONCILING`, stable business identity separate from framework call IDs, a Stripe adapter that uses one operation ID for idempotency plus metadata, read-only refund discovery by PaymentIntent + exact operation marker, explicit zero/multiple/unavailable handling, verification of provider fields, and committed crash/concurrency tests. A retained 2026-07-15 Stripe test-mode report records provider acceptance, deliberately lost local confirmation, second-worker/different-call-ID readback, one guarded refund and a confirmed receipt.
- Do not assume: production certification, independent third-party/provider attestation, exact-current-head qualification, automatic invalidation of the July provider proof after behavior-bearing source/configuration drift, production-funds evidence, or full coverage of rate limits/delayed consistency/pagination/webhooks. The commercial hypothesis should price the **join between provider proof and source/config qualification**, not oversell the founder-run test-mode drill as production qualification.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 9
- Destination: SHADOW-COMMERCIAL
- Candidate: **Autonomous-Lab External Effect Reconciliation Gateway**, transfer kernel from `auths-dev/auths-proof@34fa1f33cf365fa54075a2002710aee52ab42394`
- Evidence snapshot: `shadow-science-20260920-auths-refund-level3-34fa1f33`
- Dedupe/capability fingerprint: `autonomous-lab|external-effect|durable-reservation|outcome-unknown|stable-business-reference|authoritative-readback|reconciliation-gateway`
- Priority: HIGH
- Exact unanswered question: **Will autonomous-lab platform teams, CRO/CDMO automation groups or scientific-equipment integrators pay for an External Effect Reconciliation Gateway/Audit that reserves every physical business effect before dispatch, embeds a stable job/reference ID into the instrument/LIMS/robot queue, forbids resend after lost acknowledgement, and reconciles the original effect by read-only job/history lookup after restart?** Identify the budget owner, first instrument/workflow family whose API exposes client-set metadata plus history lookup, integration burden, fixed-price first deliverable, and one KPI such as duplicate-command rate, ambiguous-effect age, reconciliation success rate, manual recovery hours or lost-sample cost.
- Technical claims safe to use: the inspected adjacent-domain kernel durably reserves refund intent before provider mutation, uses deterministic idempotency plus stable externally queryable workflow metadata, represents ambiguous provider outcomes explicitly, survives restart in a persistent reservation store, and reconciles through a read-only provider query while tests keep the mutation call count at one. The scientific value is the lifecycle pattern, not Stripe itself.
- Do not assume: that any current lab instrument already exposes equivalent provider-queryable metadata/history, that the payment implementation proves physical hardware exactly-once, that one combined process-kill-after-provider-acceptance test was independently run in Science Run 9, or that provider/service/device rights transfer with the repository code. Workspace code is `MIT OR Apache-2.0`; external APIs/services remain separately governed.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 10
- Destination: SHADOW-COMMERCIAL
- Candidate: `MolBioFreak/BioModStack@9b36a0b106cd538d772de39092c1d532ad361083` — **Physical Effect Reconciliation Retrofit**
- Evidence snapshot: `shadow-science-20260920-biomodstack-bioxp-9b36a0b`
- Dedupe/capability fingerprint: `autonomous-lab|bioxp|idempotency-key|request-by-key|command-receipt|no-blind-retry|durable-outbox-gap`
- Priority: HIGH
- Exact unanswered question: **Will automated biotech/synthetic-biology labs pay specifically for a Physical Effect Reconciliation Retrofit that durably reserves every dangerous BioXP-style physical command before dispatch, preserves the stable external idempotency key through process restart, and resolves ambiguous acceptance by passive key→command→receipt lookup rather than resubmitting?** Identify the buyer/budget owner, current ambiguous-command/duplicate-action recovery cost, first fixed-price deliverable, integration burden, and one measurable KPI such as duplicate physical-action rate, unresolved-effect age, recovery MTTR, operator-hours or lost-sample/reagent cost.
- Technical claims safe to use: the exact MIT revision accepts caller-stable idempotency keys on BioXP operator actions; the physical deck path disables automatic mutation retry; ambiguous submissions use GET-only request lookup; BMS passively resolves the original key to canonical robot `command_id` and current receipt; tests fence identity/generation mismatches and missing identity without POST; direct-liquid lost-response tests issue exactly one POST. The same repository separately implements a durable experiment dispatch outbox/materializer with preallocated scheduler job IDs and replay/reopen/concurrent-claim protections.
- Do not assume: current physical BioXP request custody survives browser/process reload (source says it does not), underlying robot-side receipt/idempotency state is proven crash-persistent, a real BioXP crash-after-acceptance/no-second-POST test has been executed, or BioXP hardware/runtime/API rights transfer with the MIT repository code. The opportunity is the missing durable wiring between two implemented halves, not a claim of completed physical exactly-once.

## 2026-09-20 — SCIENCE → AI
- Source lane/run: SHADOW-SCIENCE / Run 11
- Destination: SHADOW-AI
- Candidate: `SUSTechWLA/tangying-robot-agent-os@774bd2a2f4035dbe48f9016a88af1cb6fb4096ae` combined conceptually with `MolBioFreak/BioModStack@9b36a0b106cd538d772de39092c1d532ad361083`
- Evidence snapshot: `shadow-science-20260920-tangying-unknown-tombstone-774bd2a`
- Dedupe/capability fingerprint: `physical-effect|durable-idempotency|outcome-unknown|restart|tombstone|provider-readback`
- Priority: HIGH
- Exact unanswered question: **Can an agent/runtime effect gateway bind Tangying-style durable pre-dispatch command tombstones to a provider-queryable external job/receipt identity so that attended recovery can restore liveness without ever making the old effect replayable, and then automatically resolve that tombstone from authoritative readback?** Build or identify the smallest safe state machine and crash test that proves this join.
- Technical claims safe to use: Tangying's exact MIT revision durably reserves command/idempotency identity before backend side effects; a regression simulates process loss after backend execution begins and proves restart/resubmission executes the backend zero times and returns `EXECUTION_OUTCOME_UNKNOWN`; a separate physical-adapter regression models lost response after sending motion, persists the safety latch through restart, rejects a fresh command/key and keeps movement count at one; known no-effect failure remains retryable; attended local recovery preserves an fsynced audit copy and non-replayable old uncertainty.
- Do not assume: authoritative device/system-of-record resolution of the original Tangying effect, a durable command→vendor-native operation join, hardware-in-loop acceptance, universal physical exactly-once behavior or production maturity. The repository itself states there is no completed physical acceptance result. BioModStack's provider-queryable receipt path is a conceptual complement, not an already integrated proof.

## 2026-09-20 — SCIENCE → AI / SYSTEMS
- Source lane/run: SHADOW-SCIENCE / Run 12
- Destination: SHADOW-AI / systems-reliability follow-up
- Candidate: `trieu04/lab-in-the-loop@80eb9524a4a36178b35810a7999cd95e8394d4fc` combined conceptually with `MolBioFreak/BioModStack@9b36a0b106cd538d772de39092c1d532ad361083`
- Evidence snapshot: `shadow-science-20260920-lab-in-loop-80eb952`
- Dedupe/capability fingerprint: `scientific-execution|durable-intent|ambiguous|find-by-idempotency|reconcile-before-resubmit|dry-run-provider-gap`
- Priority: HIGH
- Exact unanswered question: **Can BioModStack's BioXP stable request key → native command → canonical receipt API be wrapped behind lab-in-the-loop's `LabExecutionAdapter.find_by_idempotency_key()` contract so that a durable caller intent is created before physical dispatch, a crash after provider acceptance resumes in reconciliation rather than replay, and GET-only provider evidence resolves the original command with provider mutation count exactly one?** Build or identify the smallest safe adapter/crash test that proves the join.
- Technical claims safe to use: `lab-in-the-loop` durably prepares execution run + submit intent before submit; explicit `AMBIGUOUS/RECONCILING/BLOCKED` states exist; `reconcile_execution()` calls `find_by_idempotency_key()` before any possible resubmit; concurrent reconciliation tests assert only one submit. Its concrete lab provider is nevertheless memory-only dry-run; real mode is explicitly uninstalled and runtime-rejected. BioModStack separately supplies a scientific provider-queryable stable key→command→receipt path but lacks crash-persistent custody on that physical path.
- Do not assume: `lab-in-the-loop` has a real lab adapter, that BioXP provider receipt persistence survives robot restart, that the two repositories are already compatible, that a one-shot crash-after-acceptance/no-second-mutation test exists, or that no-license `lab-in-the-loop` code has public redistribution rights beyond the user's stated separate repository authorization. The referral is for a narrowly scoped integration proof, not a claim of completed Level 3.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 13
- Destination: SHADOW-COMMERCIAL
- Candidate: `lab-emi/OpenDPD@aba888b87199d7ae7802ce931987e3aa3c951410`
- Evidence snapshot: `shadow-science-20260920-opendpd-runtime-aba888b`
- Dedupe/capability fingerprint: `rf-rnd|experiment-runtime|idempotent-run|crash-recovery|retry-lineage|measurement-provenance|capture-hashes`
- Priority: HIGH
- Exact unanswered question: **Will RF power-amplifier/DPD R&D teams or telecom hardware labs pay for a fixed-scope Experiment Reproducibility & Campaign Reliability Retrofit that adds stable run identity, crash/restart qualification, retry ancestry, capture/config hashes and declared measurement conditions around existing measured-hardware sweeps, distinctly enough from MLflow/Prefect/ClearML-style tooling to justify budget?** Identify buyer/budget owner, annual cost of reruns/reconstruction from failed overnight sweeps/config drift/capture provenance gaps, first priced deliverable, integration burden, and one before/after KPI.
- Technical claims safe to use: exact Apache-2.0 revision has SQLite-backed unique run idempotency, append-only sequenced events, immutable terminal-state transitions, real subprocess worker supervision, SIGKILL/restart/orphan recovery tests, explicit retry parent lineage, config hashes, and measured-RF evidence schema binding played/capture SHA-256 plus PA/capture-chain/sample-rate/drive/calibration/time conditions. Visible pinned commit checks include successful Python 3.10 tests and build/publish jobs.
- Do not assume: physical instrument exactly-once, authoritative device readback, distributed transaction semantics, `synchronous=FULL` (it is `NORMAL`), automatic measurement acquisition by OpenDPD (source explicitly says measurement is user-provided and not independently verified), or field maturity of the new September 2026 runtime layer equal to the older research core.

## 2026-09-20 — SCIENCE → COMMERCIAL
- Source lane/run: SHADOW-SCIENCE / Run 14
- Destination: SHADOW-COMMERCIAL
- Candidate: `openmm/openmm@5a7a268616b55d6a85e1c804f1c38681a2756cde` — **Molecular Simulation Campaign Durability / Restart Audit**
- Evidence snapshot: `shadow-science-20260920-openmm-restart-5a7a268`
- Dedupe/capability fingerprint: `molecular-simulation|safe-checkpoint|replica-exchange|expanded-ensemble|resume|generation-skew|campaign-integrity`
- Priority: MEDIUM-HIGH
- Exact unanswered question: **Do computational-chemistry, FEP and enhanced-sampling teams lose enough GPU/HPC time or scientist reconstruction time to checkpoint corruption or cross-file generation skew that a fixed-price Campaign Durability / Restart Audit has measurable budget beyond generic scheduler/workflow tooling?** Identify the buyer, annual recompute/reconstruction loss, first priced deliverable, integration threshold and one before/after KPI such as wasted GPU-hours, failed-resume rate, checkpoint-generation mismatches or scientist-hours spent reconstructing interrupted campaigns.
- Technical claims safe to use: at the pinned revision OpenMM has filename-based safe-save helpers for checkpoint/state replacement, a resumable ReplicaExchangeReporter that reloads replica checkpoints plus the last log assignment, a resumable ExpandedEnsembleSampler checkpoint containing algorithm state plus the full OpenMM State, and regression tests that destroy/recreate simulation objects and verify resumed scientific state. History shows safe-overwrite hardening merged in July 2025, while high-level expanded-ensemble and replica-exchange resume machinery arrived in 2026, long after the core OpenMM 7 publication.
- Do not assume: transactional atomicity across an entire multi-replica checkpoint generation, power-loss durability (`fsync`/directory `fsync` was not established), an executed failpoint test between log and all checkpoint writes, physical-instrument effect semantics, or that checkpointing itself is new to OpenMM. Source ordering allows a log/new-checkpoint subset to exist alongside older replica checkpoints after an interruption, so position this as a durability audit/retrofit opportunity rather than already complete crash-consistent campaign storage.

## 2026-09-20 — SCIENCE → AI / SYSTEMS
- Source lane/run: SHADOW-SCIENCE / Run 15
- Destination: SHADOW-AI / systems-reliability integration proof
- Candidate: NoKV-Lab/NoKV@590d3a4bdca9df604e1dfa5e881a869c8a3bfcdf combined with openmm/openmm@5a7a268616b55d6a85e1c804f1c38681a2756cde or lab-emi/OpenDPD@aba888b87199d7ae7802ce931987e3aa3c951410
- Evidence snapshot: shadow-science-20260920-nokv-manifest-590d3a4
- Dedupe/capability fingerprint: scientific-checkpoint|immutable-shards|manifest-visibility|generation-fence|response-loss-replay|closure-gap
- Priority: HIGH
- Exact unanswered question: **Can a real OpenMM or OpenDPD campaign be wrapped with NoKV so that every checkpoint member is immutable or generation-CASed at manifest commit, workspace incarnation is fenced, process death is injected before and after every shard/manifest boundary, restart uses the application's native resume path, and readers observe complete generation N or N+1 only while a lost response causes zero duplicate publication?**
- Required proof: installed Python wheel against a real NoKV metadata owner and S3-compatible provider; adversarial concurrent replacement before manifest commit; exact process-kill/restart matrix; orphan/corrupt-highest handling; resumed-versus-uninterrupted scientific equivalence; latency/storage overhead and avoided-rerun economics.
- Technical claims safe to use: the exact Apache-2.0 revision implements manifest-last checkpoint discovery, per-shard generation/size/SHA-256 verification, deterministic operation/revision identities, and a deeper durable publication substrate with response-loss replay and path-movement rejection. Exact-SHA Python SDK and Rust CI runs passed.
- Do not assume: atomic closure over current shard generations at manifest commit, helper-level workspace-incarnation fencing, real-provider checkpoint qualification, OpenMM/OpenDPD/atomate2 integration, cross-host fencing, metadata HA, physical power-cycle durability or STRONG scientific-product status. The independent verifier returned INCOMPLETE and the scientific candidate is 23/30 WATCH.

## 2026-09-21 — AI → Commercial: attestation-to-executor binding retrofit

- **Trigger:** Shadow AI Run 17 inspected `agenttrust-labs/agenttrust@21a3b111b7677d0b06ab1b063d647e4f52ea3b17`.
- **Evidence-backed capability:** AgentTrust can atomically fail closed before a payment transfer and retains historical devnet evidence of validation-required → attested → allowed behavior.
- **Load-bearing gap:** the payment policy consumes subject, capability label, attestor, expiry and revocation, but not the stored claim payload/URI hashes and not a runtime-derived executor identity. A valid capability credential can therefore remain admissible when the evidence payload or acting executor has changed.
- **Currentness limit:** historical May 2026 devnet evidence is not current exact-head qualification; September 2026 scheduled devnet smoke remained red.
- **Commercial primitive:** **Attestation-to-Executor Binding Retrofit** for an existing agent payment/action gate—derive identity from the executor/config actually acting, map it to a narrow reviewed behavior closure, bind current provider/action proof, and make the consequence gate consume that exact identity without widening to whole-release churn.
- **Safe claim:** “We can test whether the evidence your agent presents is the evidence your payment gate actually uses.”
- **Unsafe claims:** do not claim AgentTrust is currently live-provider qualified; do not call a capability label a reviewed source closure; do not call a subject asset a runtime measurement; do not combine AgentTrust, Signet and TEE comparators into one public end-to-end implementation.
- **Buyer-validation question:** Will an agent-payment, x402 or automated treasury operator provide one non-production route and pay for a fixed-scope audit/retrofit that plants (a) claim-payload drift, (b) executor-binary/config drift and (c) unrelated documentation drift, requiring the first two to withdraw authority and the third to preserve it?
- **Evidence needed before any outcome claim:** explicit buyer authorization, frozen route/population, before/after gate behavior, exact behavior/executor/provider-proof identities, independently observed zero-effect on planted denials, and an attributable commercial credit/refund/remittance or paid engagement.

## 2026-09-21 — SCIENCE → COMMERCIAL / SYSTEMS
- Source lane/run: SHADOW-SCIENCE / Run 16
- Destination: SHADOW-COMMERCIAL / systems-reliability integration proof
- Candidate: `google/tensorstore@ed9abe0a89ac6631272f4458a90a4f32e6a381f2` OCDBT combined with `openmm/openmm@5a7a268616b55d6a85e1c804f1c38681a2756cde` or `lab-emi/OpenDPD@aba888b87199d7ae7802ce931987e3aa3c951410`, benchmarked against `earth-mover/icechunk@f58fd5b94176e36ff5b6170cc33b1b248f623582`
- Evidence snapshot: `shadow-science-20260921-tensorstore-ocdbt-ed9abe0`
- Dedupe/capability fingerprint: `scientific-checkpoint|one-db-atomic-transaction|immutable-objects|manifest-cas|version-pinned-restore|provider-qualification`
- Priority: MEDIUM-HIGH
- Exact unanswered question: **Can every artifact and metadata record from one real OpenMM or OpenDPD checkpoint be placed under one non-coordinator OCDBT database and atomic transaction, killed at every object/manifest/finalization boundary, reopened by the exact committed generation, and shown scientifically equivalent to an uninterrupted run—and does that deliver better migration cost, throughput or operability than Icechunk for the same workload?**
- Required proof: two concrete adapters (OCDBT and Icechunk); old-or-complete-new process-kill/provider-fault matrix; concurrent-writer CAS conflict; lost-acknowledgement behavior; exact provider/manifest-kind qualification; generation/snapshot-pinned restore; artifact reachability/hash validation; resumed-versus-uninterrupted scientific equivalence; orphan/retention overhead and avoided-rerun economics.
- Technical claims safe to use: the exact Apache-2.0 TensorStore revision has a real same-database atomic publication path that flushes immutable data/tree objects before one conditional manifest update; monotonic versions and version-pinned opens exist; Orbax uses `ts.Transaction(atomic=True)` to merge per-process OCDBT checkpoint state. In this run, 16 real subprocess-kill/reopen trials against the default durable file backend produced all-old state before the manifest change and all-new state after it, never a mixed key set. The independent verifier returned PASS_WITH_LIMITS / WATCH.
- Do not assume: cross-database atomicity, coordinator-mode multi-key atomicity, general snapshot reads without pinning, durable/resumable client transaction identity, acknowledgement-loss exactly-once semantics, provider-neutral safety, an upstream kill/power-cycle matrix, or current OpenMM/OpenDPD integration. The schema says unsafe provider selection should error, but current source falls back to a single manifest even when safety capabilities are unknown. Icechunk and Orbax materially commoditize the generic backend proposition.
- Commercial question: **Will computational-science teams pay for a fixed-price Campaign Crash/Consistency Audit and adapter retrofit that chooses and qualifies OCDBT versus Icechunk, when the KPI is avoided GPU/HPC reruns, failed-resume incidence, scientist recovery hours or corrupted campaign generations?** Identify the buyer, present annual loss, first priced deliverable and maximum acceptable adapter/throughput overhead.

## 2026-09-21 — SCIENCE → COMMERCIAL / SYSTEMS
- Source lane/run: SHADOW-SCIENCE / Run 17
- Destination: SHADOW-COMMERCIAL / systems-reliability integration proof
- Candidate: earth-mover/icechunk@f58fd5b94176e36ff5b6170cc33b1b248f623582 combined with openmm/openmm@5a7a268616b55d6a85e1c804f1c38681a2756cde or lab-emi/OpenDPD@aba888b87199d7ae7802ce931987e3aa3c951410
- Evidence snapshot: shadow-science-20260921-icechunk-v2-f58fd5b
- Dedupe/capability fingerprint: scientific-checkpoint|zarr-hierarchy|repo-root-cas|write-id-readback|post-cas-process-death|campaign-uuid
- Priority: MEDIUM-HIGH
- Exact unanswered question: **Will computational-science or RF/molecular-simulation teams pay for a Scientific Campaign Crash/Consistency Audit plus native checkpoint adapter that places analytical arrays, opaque framework restart state and provenance under one Icechunk generation, persists a campaign transaction UUID before commit, and proves process-death/lost-acknowledgement recovery without a duplicate logical checkpoint—and does that outperform an OCDBT or incumbent native-checkpoint retrofit on their workload?**
- Required proof: exact-head Icechunk adapter; real S3-compatible provider with conditional writes and metadata enabled; Toxiproxy lost-response plus SIGKILL matrix at every object/root boundary; post-root/pre-ack death; competing writer; UUID-based fresh-process reconciliation; metadata/conditional negative controls; hash/reachability and GC checks; native OpenMM or OpenDPD resumed-versus-uninterrupted equivalence; matched p50/p95 checkpoint/restore latency, object calls, bytes retained, GC cost and avoided rerun economics versus OCDBT/native framework storage.
- Technical claims safe to use: V2 writes manifests, snapshot and transaction log before one conditional repo-root publication; snapshot-pinned reads cover a whole multi-array Zarr hierarchy; matching icechunkwriteid metadata can recover a live client's landed conditional PUT after acknowledgement loss; exact-head readback unit tests passed 9/9 locally; a separate v2.2.2 two-array process-kill probe reopened all-old in 10 pre-root trials and all-new in 10 post-root trials with no mixed state.
- Do not assume: exactly-once application checkpoints, fresh-process recovery of a lost final-CAS acknowledgement, concurrent local-filesystem safety, fsync/power-loss durability, cross-repository atomicity, native OpenMM restart capture, superior speed/cost versus OCDBT/Orbax, fully green exact-head CI, production checkpoint adoption or paid demand. Earthmover already sells generic managed Icechunk through Arraylake, so differentiation must come from domain adapters, adversarial qualification and quantified recovery economics.



## 2026-09-21 — AI → COMMERCIAL / INTEGRATOR: ATTESTED CONSEQUENCE GATE RETROFIT

- Source run: Shadow AI Run 18.
- Candidate/reference: [worldcoin/world-chain@69c7ac9683898d972882ca8959c4579616096816](https://github.com/worldcoin/world-chain/tree/69c7ac9683898d972882ca8959c4579616096816).
- Verdict: **PASS_WITH_LIMITS, proposed 26/30; no STRONG full-target finding.**
- Fingerprint: game-derived exact action payload; immutable verifier/image identity; AWS Nitro attestation-derived signer registration; signature verification over exact transition values; image-scoped signer revocation; proof threshold and finality delay before ERC-20 bond settlement; narrow measured enclave workspace distinct from whole-release provenance; deterministic two-build signed release path.
- Commercial primitive: **Attested Consequence Gate Retrofit** for one refund, payout, treasury transfer or account mutation. The gate reconstructs the business effect from trusted state, derives or verifies the acting executor's narrow behavior identity, requires the credential to sign the exact effect, and retains provider readback/reconciliation evidence.
- Safe claim: World Chain is a strong adjacent implementation showing that an attestation-derived workload identity and exact signed payload can be consumed at a real value-bearing boundary.
- Unsafe claims: do not claim exact-current live qualification, mainnet production acceptance, continuous enclave liveness, agent-provider qualification or a completed neutral-drift test. The strongest signed proof release located is historical prerelease evidence, the deployment evidence is alphanet-shaped, and signer registration is fresh only at registration time.
- Required product controls beyond the reference: bounded attestation/key lease or per-action continuity proof; exact-current live-provider qualification; behavior-measurement-to-reviewed-source receipt; provider postcondition readback; durable ambiguous-outcome reconciliation; covered-change withdrawal test; irrelevant-file preservation test.
- Exact unanswered question: can one pilot action prove that the current executor identity is derived at or near the action boundary, that the gate consumes the exact business-effect payload, that a behavior-bearing change withdraws authority, that unrelated release churn preserves it, and that a lost provider acknowledgement reconciles without a duplicate effect?
- Suggested paid wedge: fixed-scope retrofit and adversarial acceptance pack for one consequential agent tool, delivered with source/measurement closure, action receipt schema, stale-key drill, lost-acknowledgement drill, selective-drift tests and a qualification-currentness dashboard.
