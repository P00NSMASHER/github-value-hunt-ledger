# A/B SCOREBOARD
Frozen experiment started 2026-09-20.

Hunt 15 / MASTER Integrator owns this file. Hunters must not score themselves against BENCHMARK_GOLD.md.

Scoring dimensions are each 0-5: Target Discovery (TD), Technical Verification (TV), Calibration (CAL), Commercial Reasoning (CR), Evidence Discipline (ED). Pair means below use **matched completed tasks only**; raw completion counts include unmatched completed work.

## Pair summary
| Pair | Tasks | Control completed | Experiment completed | Matched tasks scored | Control matched mean /25 | Experiment matched mean /25 | Control false promotions | Experiment false promotions | Winner so far |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 01-08 | 1 | 0 | 0 | — | — | 0 | 0 | — |
| 2 | 09-15 | 1 | 1 | 1 | 25.0 | 25.0 | 0 | 0 | Tie |
| 3 | 16-22 | 1 | 1 | 1 | 21.0 | 24.0 | 0 | 0 | Experiment |
| 4 | 23-29 | 1 | 1 | 1 | 24.0 | 23.0 | 0 | 0 | Control |
| 5 | 30-36 | 2 | 2 | 2 | 23.5 | 25.0 | 0 | 0 | Experiment |
| 6 | 37-43 | 1 | 1 | 1 | 25.0 | 25.0 | 0 | 0 | Tie |
| 7 | 44-50 | 2 | 0 | 0 | — | — | 0 | 0 | — |

## Experiment-wide matched metrics
- Matched tasks scored: **6** (09, 16, 23, 30, 31, 37).
- Control matched mean: **23.67/25**.
- Experiment matched mean: **24.50/25**.
- Mean paired difference (Experiment - Control): **+0.83**.
- Median paired difference: **0.0**.
- Pairwise task win / tie / loss for Experiment: **2 / 3 / 1**.
- False promotions: **0 Control / 0 Experiment** among scored results.
- No-find results: **0 Control / 0 Experiment** among scored results.
- Approximate search effort per validated STRONG find: **Control ~9.5** distinct searches+deep inspections; **Experiment ~9.4**. This is approximate because result files do not yet report effort with perfectly uniform counting conventions.
- Learning slope: **not yet robustly estimable**. Only Pair 5 has two matched Experiment tasks; its scored trajectory is flat at 25 -> 25, while qualitative lesson reuse is visible from Task 30 into Task 31. Other experiment pairs have one completed task each.

## Scored task details

### Task 01 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected capability; source-level geofence/dwell, fail-closed pricing, evidence freezing, approval-to-charge and failure semantics were verified with explicit caveats around unexecuted E2E deployment/tests.

### Task 09 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- False promotion: **No**. No-find: **No**.
- Justification: exact first-party target; real DITA source, fill-in semantics and FAC/change provenance were inspected directly and bounded carefully.

### Task 09 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus stronger triangulation across source markup, exact history and independent first-party publication/rulemaking surfaces; unsupported XSD/currentness claims were explicitly withheld.

### Task 16 — CONTROL — 21/25
- TD 2 / TV 5 / CAL 5 / CR 4 / ED 5.
- Candidate: `broad-well/recovair-abm@7b3379cb431591c148a26993097a08487ae6886b`.
- False promotion: **No**. No-find: **No**.
- Justification: technically deep and well verified, but only a partial match to the requested integrated recovery target; the WATCH verdict correctly recognized simplified crew legality, non-joint passenger recovery and missing explicit replay/uncertainty depth.

### Task 16 — EXPERIMENT — 24/25
- TD 5 / TV 5 / CAL 5 / CR 4 / ED 5.
- Candidate: `mizuharaa/olus@f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected target with strong solver, legality, uncertainty, simulation and deterministic replay evidence. Red-team source tracing correctly downgraded README overstatement about FAR117 being a hard constraint in the main aircraft solver.

### Task 23 — CONTROL — 24/25
- TD 5 / TV 5 / CAL 4 / CR 5 / ED 5.
- Candidate: `Dynamical-Systems-Research/dynamical-cli@b4823fb4e4babd942e3beafcad8042ea0684f1c0`.
- False promotion: **No**. No-find: **No**.
- Justification: demonstrably strong equivalent campaign-governance substrate with replay/branching/authority evidence and external scientific-study support. Calibration loses one point because the six requested action classes are semantic rather than first-class closed runtime states.

### Task 23 — EXPERIMENT — 23/25
- TD 3 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `fl-sean03/OpenSDL@43f49889c87e78cffb383f8683766453e4daaff1`.
- False promotion: **No**. No-find: **No**.
- Justification: excellent runtime verification and correctly calibrated WATCH, but it misses first-class acquire-context and richer campaign-level recovery/escalation transitions, so target discovery is partial rather than equivalent.

### Task 30 — CONTROL — 22/25
- TD 4 / TV 4 / CAL 4 / CR 5 / ED 5.
- Candidate: `levi-qiao/longgraph-skill@b27376fd44f30505cbc52c2520c42e725b028ea1`.
- False promotion: **No**. No-find: **No**.
- Justification: strong conceptual match with independent supervisor and durable ledger, but the core is a Markdown/file control plane rather than an executable long-horizon orchestration runtime; real-run evidence is mostly project-maintained/redacted.

### Task 30 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected target; fail-closed completion guards, auditor mutation handling, original-contract back-checks, durable resume and hardening tests were all verified and caveated appropriately.

### Task 31 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected target; issue-state reconciliation, retry/backoff, per-issue workspaces, validation/review proof surfaces and broad tests were verified with clear limits around trusted-environment isolation and repository-specific quality policy.

### Task 31 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected target with equivalent core verification plus a useful descendant-cluster -> canonical-spec pivot and explicit red-team separation of workspace isolation, durable retry state and independent-verifier claims.

### Task 37 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected target; heterogeneous connectors, append-style PermitVersion history/diffs, version-race tests and semantic fee-vs-valuation mapping QA were directly verified.

### Task 37 — EXPERIMENT — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`.
- False promotion: **No**. No-find: **No**.
- Justification: exact target plus explicit invariant-triad search and a useful comparison showing that broader connector count cannot substitute for immutable version/diff semantics and semantic regression QA.

### Task 44 — CONTROL — 25/25
- TD 5 / TV 5 / CAL 5 / CR 5 / ED 5.
- Candidate: `vncwr/backwyn@57f4b8afc3d9ce14f2a35febc802536cfa816839`.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected recovery-proof component; scratch restore, corruption/staleness/unverified-state negative controls and successful exact-revision CI were all checked.

### Task 45 — CONTROL — 24/25
- TD 5 / TV 5 / CAL 4 / CR 5 / ED 5.
- Candidate: `DNYoussef/guardspine-spec@4b21006daa82af52647c5b6e4288d995ccbaf401` plus companion verifier.
- False promotion: **No**. No-find: **No**.
- Justification: exact expected evidence-interoperability component with strong malformed/tamper/signature checks. Calibration loses one point because the result labels it generically STRONG while portfolio use should remain STRONG COMPONENT/WATCH unless trusted-key policy and external adoption are established.

## Retained-lesson / learning status
- No benchmark-derived lesson is promoted merely because it appeared once.
- **Eligible for SEARCH_SKILLS promotion now:** the narrower acceptance-path inspection lesson is supported by distinct Experiment Tasks **30 and 31**. Both benefited from locating the actual state transition that accepts work as complete/reviewable and then inspecting fail-closed evidence/recovery semantics rather than reviewer prose alone.
- Not yet eligible: Pair 2 production-source triangulation (Task 09 only); Pair 3 capability-conjunction + claim tracing (Task 16 only); Pair 4 state-machine + audit-log conjunction (Task 23 only); Pair 6 ingestion invariant triad (Task 37 only); Pair 5 descendant-cluster -> canonical-spec pivot (Task 31 only).

## Experiment-wide conclusion
Too early for a winner claim. Across six matched tasks the Experiment condition has a higher mean score (24.50 vs 23.67), but the **median paired difference is 0**, with only **2 wins, 3 ties and 1 loss** and no false promotions in either condition. Current evidence supports continuing the benchmark rather than claiming the experimental architecture wins.
