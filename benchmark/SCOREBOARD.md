# A/B SCOREBOARD
Frozen experiment started 2026-09-20.

Hunt 15 / MASTER Integrator owns this file. Hunters must not score themselves against BENCHMARK_GOLD.md.

Scoring dimensions are each 0-5: Target Discovery (TD), Technical Verification (TV), Calibration (CAL), Commercial Reasoning (CR), Evidence Discipline (ED). Pair means below use **matched completed tasks only**; raw completion counts include unmatched completed work.

## Pair summary
| Pair | Tasks | Control completed | Experiment completed | Matched tasks scored | Control matched mean /25 | Experiment matched mean /25 | Control false promotions | Experiment false promotions | Winner so far |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 01-08 | 2 | 0 | 0 | — | — | 0 | 0 | — |
| 2 | 09-15 | 2 | 2 | 2 | 25.0 | 25.0 | 0 | 0 | Tie |
| 3 | 16-22 | 2 | 1 | 1 | 21.0 | 24.0 | 0 | 0 | Experiment |
| 4 | 23-29 | 2 | 2 | 2 | 24.5 | 24.0 | 0 | 0 | Control |
| 5 | 30-36 | 2 | 2 | 2 | 23.5 | 25.0 | 0 | 0 | Experiment |
| 6 | 37-43 | 2 | 1 | 1 | 25.0 | 25.0 | 0 | 0 | Tie |
| 7 | 44-50 | 3 | 1 | 1 | 25.0 | 24.0 | 0 | 0 | Control |

## Experiment-wide matched metrics
- Matched tasks scored: **9** (09, 10, 16, 23, 24, 30, 31, 37, 44).
- Control matched mean: **24.11/25**.
- Experiment matched mean: **24.56/25**.
- Mean paired difference (Experiment - Control): **+0.44**.
- Median paired difference: **0.0**.
- Pairwise task win / tie / loss for Experiment: **2 / 5 / 2**.
- False promotions: **0 Control / 0 Experiment** among scored results.
- No-find results: **0 Control / 0 Experiment** among scored results.
- Approximate search effort per validated STRONG find: **Control ~10.0** reported distinct searches+deep inspections; **Experiment ~11.5**. This is directional only because result files count discovery modes, searches, triage and deep inspections inconsistently.
- Learning slope: **no robust score slope yet**. Among experiment pairs with two matched tasks, Pair 2 is flat at 25 -> 25, Pair 4 improves 23 -> 25, and Pair 5 is flat at 25 -> 25. Median within-pair change is 0. Qualitative lesson reuse is nevertheless visible from Task 09 -> 10 and Task 30 -> 31.

## Scored task details

### Task 01 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; source-level physical-event, fail-closed pricing, evidence-freeze, approval-to-charge and failure semantics were verified with deployment/test limits preserved.

### Task 02 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `emoss08/Trenova@3bbd4801978ec069d5a1059dfdf466764a03934f`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target repository and unusually complete freight money/workflow plane; dispatch, carrier rates, detention collectability, invoice-match variance and settlement state transitions were verified directly. Current-head pre-release/typecheck caveats were not hidden.

### Task 09 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- False promotion: **No**. No-find: **No**.
- Justification: exact first-party target; real DITA source, fill-ins and FAC/change provenance inspected directly.

### Task 09 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus source/history/official-publication triangulation; unsupported schema/currentness claims were explicitly withheld.

### Task 10 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964`.
- False promotion: **No**. No-find: **No**.
- Justification: exact first-party backend/ETL target; Broker loading, normalized award/transaction models, Delta transforms and tests were inspected rather than inferring from the public API.

### Task 10 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target with particularly strong pipeline-boundary discipline: official publication -> source repo -> operational transforms/schema/tests -> production-deploy history -> upstream Broker comparison.

### Task 16 — CONTROL — 21/25
- TD 2 / TV 5 / CAL 5 / CR 4 / ED 5.
- Candidate: `broad-well/recovair-abm@7b3379cb431591c148a26993097a08487ae6886b`.
- False promotion: **No**. No-find: **No**.
- Justification: technically deep partial match; correctly held at WATCH because full constrained optimization, legality, joint passenger recovery, uncertainty and explicit replay were not all present.

### Task 16 — EXPERIMENT — 24/25
- TD 5 / TV 5 / CAL 5 / CR 4 / ED 5.
- Candidate: `mizuharaa/olus@f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target with strong solver, legality, uncertainty, simulation and replay evidence; source tracing correctly exposed that FAR117 is not a hard constraint in the main aircraft solver despite broader wording.

### Task 17 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806`.
- False promotion: **No**. No-find: **No**.
- Justification: demonstrably equivalent target: Decimal-safe exact/net/fee/refund/split/dedupe/ambiguity semantics plus substantial direct tests and CI. Bounded split size and synthetic-data limits were preserved.

### Task 23 — CONTROL — 24/25
- TD 5 / TV 5 / CAL 4 / CR 5 / ED 5.
- Candidate: `Dynamical-Systems-Research/dynamical-cli@b4823fb4e4babd942e3beafcad8042ea0684f1c0`.
- False promotion: **No**. No-find: **No**.
- Justification: strong equivalent campaign-governance substrate with replay/branching/authority evidence; one calibration point withheld because requested action classes are semantic rather than first-class closed runtime states.

### Task 23 — EXPERIMENT — 23/25
- TD 3 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `fl-sean03/OpenSDL@43f49889c87e78cffb383f8683766453e4daaff1`.
- False promotion: **No**. No-find: **No**.
- Justification: excellent runtime verification and correctly calibrated WATCH, but first-class acquire-context and richer campaign-level recovery/escalation transitions are missing.

### Task 24 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; CP-SAT hard feasibility, literal locked-work equalities, adversarial lock-preservation tests and robustness/Plan-B machinery were verified with synthetic/prototype caveats intact.

### Task 24 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus a useful hard-lock-vs-warm-start falsification pass; production and resource-model limits were explicitly preserved.

### Task 30 — CONTROL — 22/25
- TD 4 / TV 4 / CAL 4 / CR 5 / ED 5.
- Candidate: `levi-qiao/longgraph-skill@b27376fd44f30505cbc52c2520c42e725b028ea1`.
- False promotion: **No**. No-find: **No**.
- Justification: strong conceptual match, but primarily a Markdown/file control plane rather than an executable orchestration runtime and with limited independently reproducible production evidence.

### Task 30 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; fail-closed completion guards, auditor mutation handling, original-contract back-checks, durable resume and hardening tests verified.

### Task 31 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; issue-state reconciliation, retry/backoff, per-issue workspaces, proof surfaces and broad tests verified with trusted-environment/policy limits preserved.

### Task 31 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus useful descendant-cluster -> canonical-spec pivot and red-team separation of workspace isolation, retry durability and independent-verifier claims.

### Task 37 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; heterogeneous connectors, append-style PermitVersion history/diffs, version-race tests and semantic fee-vs-valuation QA verified.

### Task 37 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus explicit invariant-triad search and comparison showing connector breadth cannot substitute for immutable version/diff semantics and semantic QA.

### Task 38 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; multiple government forecast connectors, first-seen/last-updated/change-hash, version history/diffs and success/partial/failure run semantics were verified in source.

### Task 44 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `vncwr/backwyn@57f4b8afc3d9ce14f2a35febc802536cfa816839`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target; scratch restore, corruption/staleness/unverified-state negatives and successful exact-revision CI were checked.

### Task 44 — EXPERIMENT — 24/25
- TD 4 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91`.
- False promotion: **No**. No-find: **No**.
- Justification: demonstrably strong equivalent recovery-verification component with real scratch restore, corruption/fail-open regression controls and truthful unknown/latest semantics. One discovery point withheld because it stops short of booted-Postgres/application invariants and does not independently establish age-based stale-proof SLA semantics.

### Task 45 — CONTROL — 24/25
- TD 5 / TV 5 / CAL 4 / CR 5 / ED 5.
- Candidate: `DNYoussef/guardspine-spec@4b21006daa82af52647c5b6e4288d995ccbaf401` plus companion verifier.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected evidence-interoperability component with strong malformed/tamper/signature checks. Calibration loses one point because customer-facing trust still requires explicit trusted-key policy and external adoption evidence.

### Task 46 — CONTROL — 24/25
- TD 5 / TV 5 / CAL 5 / CR 4 / ED 5.
- Candidate: `Kjudeh/railway-postgres-backups@1949082f892f62fe47764f490683795d85a6dedd`.
- False promotion: **No**. No-find: **No**.
- Justification: demonstrably superior-equivalent negative-control result: source inspection proved fail-open SQL restore behavior, zero-table default acceptance, non-blocking row-count failure and placeholder verification SQL. Correctly rejected despite polished recovery-verification claims.

## Retained-lesson / learning status
- No benchmark lesson is promoted from a single task.
- **Promoted to SEARCH_SKILLS:** `Acceptance-path transition inspection`, supported by distinct Experiment Tasks **30 and 31**.
- **Promoted to SEARCH_SKILLS:** `First-party production-source triangulation`, supported by distinct Experiment Tasks **09 and 10**.
- Not yet eligible: Pair 3 capability-conjunction + claim tracing (Task 16 only); Pair 4 state-machine + audit-log conjunction (Task 23 only); Pair 4 perturbation+hard-invariant scheduling test (Task 24 only); Pair 6 ingestion invariant triad (Task 37 only); Pair 5 descendant-cluster -> canonical-spec pivot (Task 31 only); Pair 7 fail-open boundary archaeology (Task 44 only).

## Experiment-wide conclusion
Too early for a winner claim. Across **9 matched tasks**, Experiment has a slightly higher mean (**24.56 vs 24.11**), but the **median paired difference is 0**, with **2 wins, 5 ties and 2 losses** and no false promotions in either condition. The experimental architecture has produced two independently reusable search skills, but it is also using somewhat more search effort per validated strong result in the current sample. Continue the benchmark; do not claim an architecture winner yet.
