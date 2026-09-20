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
