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
