# A/B SCOREBOARD
Frozen experiment started 2026-09-20.

Hunt 15 / MASTER Integrator owns this file. Hunters must not score themselves against `BENCHMARK_GOLD.md`.

Scoring dimensions are each 0-5: Target Discovery (TD), Technical Verification (TV), Calibration (CAL), Commercial Reasoning (CR), Evidence Discipline (ED). Pair means use **matched completed tasks only**; raw completion counts include unmatched completed work. A demonstrably superior equivalent can receive full Target Discovery credit.

## Pair summary
| Pair | Tasks | Control completed | Experiment completed | Matched tasks scored | Control matched mean /25 | Experiment matched mean /25 | Control false promotions | Experiment false promotions | Winner so far |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 01-08 | 2 | 0 | 0 | — | — | 0 | 0 | — |
| 2 | 09-15 | 2 | 2 | 2 | 25.0 | 25.0 | 0 | 0 | Tie |
| 3 | 16-22 | 3 | 1 | 1 | 21.0 | 24.0 | 0 | 0 | Experiment |
| 4 | 23-29 | 3 | 3 | 3 | 24.7 | 24.0 | 0 | 0 | Control |
| 5 | 30-36 | 3 | 2 | 2 | 23.5 | 25.0 | 0 | 0 | Experiment |
| 6 | 37-43 | 3 | 3 | 3 | 25.0 | 25.0 | 0 | 0 | Tie |
| 7 | 44-50 | 3 | 2 | 2 | 24.5 | 24.5 | 0 | 0 | Tie |

## Experiment-wide matched metrics
- Matched tasks scored: **13** — 09, 10, 16, 23, 24, 25, 30, 31, 37, 38, 39, 44, 45.
- Control matched mean: **24.31/25**.
- Experiment matched mean: **24.62/25**.
- Mean paired difference (Experiment - Control): **+0.31**.
- Median paired difference: **0.0**.
- Pairwise task win / tie / loss for Experiment: **3 / 7 / 3**.
- False promotions: **0 Control / 0 Experiment** among scored results.
- No-find results: **0 Control / 0 Experiment** among scored results.
- Approximate search effort per validated STRONG result: **Control ~10.2** reported distinct searches+deep inspections; **Experiment ~11.3**. Directional only because result files count discovery modes, triage and deep inspections inconsistently.
- Learning slope: **not yet robustly distinguishable in score**. Among experiment pairs with >=2 matched tasks, Pair 2 is 25→25, Pair 4 is 23→25→24, Pair 5 is 25→25, Pair 6 is 25→25→25, and Pair 7 is 24→25. Median early-to-late within-pair change remains **0**. Qualitative reusable-method transfer is now established on 09→10, 30→31, 37→38→39, and 44→45.

## Scored task details
Scores below preserve all previously scored results and add newly completed unscored results.

| Task | Condition | Score | TD/TV/CAL/CR/ED | Candidate | False promotion | No-find | Concise justification |
|---:|---|---:|---|---|---|---|---|
| 01 | CONTROL | 25 | 5/5/5/5/5 | `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045` | No | No | Exact target; physical-event truth, fail-closed pricing, evidence freeze, approval-to-charge and failure semantics verified with deployment/test limits preserved. |
| 02 | CONTROL | 25 | 5/5/5/5/5 | `emoss08/Trenova@3bbd4801978ec069d5a1059dfdf466764a03934f` | No | No | Exact target; dispatch/rates/detention/invoice variance/settlement transitions verified; pre-release and broken-head limits preserved. |
| 09 | CONTROL | 25 | 5/5/5/5/5 | `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f` | No | No | Exact first-party target; real DITA source, fill-ins and FAC/change provenance inspected directly. |
| 09 | EXPERIMENT | 25 | 5/5/5/5/5 | `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f` | No | No | Exact target plus source/history/official-publication triangulation; unsupported schema/currentness claims withheld. |
| 10 | CONTROL | 25 | 5/5/5/5/5 | `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` | No | No | Exact first-party backend/ETL target; Broker loading, normalized models, transforms and tests inspected. |
| 10 | EXPERIMENT | 25 | 5/5/5/5/5 | `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` | No | No | Exact target with especially strong pipeline-boundary discipline and deploy/history triangulation. |
| 16 | CONTROL | 21 | 2/5/5/4/5 | `broad-well/recovair-abm@7b3379cb431591c148a26993097a08487ae6886b` | No | No | Deep partial match correctly kept WATCH because joint optimization, legality, uncertainty and explicit replay were incomplete. |
| 16 | EXPERIMENT | 24 | 5/5/5/4/5 | `mizuharaa/olus@f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68` | No | No | Exact target with solver, legality, uncertainty, simulation and replay; source tracing correctly bounded the FAR117 integration claim. |
| 17 | CONTROL | 25 | 5/5/5/5/5 | `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806` | No | No | Demonstrably equivalent target with exact/net/fee/refund/split/dedupe/ambiguity semantics and direct tests/CI. |
| 18 | CONTROL | 25 | 5/5/5/5/5 | `Vzlentin/calibre@264b6fc27fd4293660983c2adf9f86cfa1b4d733` | No | No | Exact target; temporal admissibility, immutable issued decisions, late-resolution/calibration correctness, inventory settlement and order-up-to pipeline semantics are implemented and directly tested. Production-adapter limits were preserved. |
| 23 | CONTROL | 24 | 5/5/4/5/5 | `Dynamical-Systems-Research/dynamical-cli@b4823fb4e4babd942e3beafcad8042ea0684f1c0` | No | No | Strong equivalent campaign-governance substrate with replay/branching/authority evidence; one calibration point withheld because requested action classes are semantic rather than closed runtime states. |
| 23 | EXPERIMENT | 23 | 3/5/5/5/5 | `fl-sean03/OpenSDL@43f49889c87e78cffb383f8683766453e4daaff1` | No | No | Excellent runtime verification and correctly calibrated WATCH; first-class acquire-context and richer campaign-level recovery/escalation transitions are missing. |
| 24 | CONTROL | 25 | 5/5/5/5/5 | `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a` | No | No | Exact target; CP-SAT feasibility, literal locked-work equalities, adversarial lock tests and robustness/Plan-B machinery verified with prototype caveats intact. |
| 24 | EXPERIMENT | 25 | 5/5/5/5/5 | `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a` | No | No | Exact target plus explicit hard-lock-vs-warm-start falsification; resource/production limits preserved. |
| 25 | CONTROL | 25 | 5/5/5/5/5 | `panoskom/PPDM_framework@4fbca1dfc28280d0e6428b22c796e15c4f305ccd` | No | No | Exact target; scarce slots, hold/imperfect-repair/replace actions, uncertainty/deferral and VoI surfaces were traced into source and paper evidence, while runtime-enforcement/data-artifact limitations were explicitly disclosed. |
| 25 | EXPERIMENT | 24 | 5/5/4/5/5 | `panoskom/PPDM_framework@4fbca1dfc28280d0e6428b22c796e15c4f305ccd` | No | No | Exact target and superior runtime-side-effect tracing, but WATCH is slightly over-conservative relative to the benchmark capability: the repository does implement the requested mechanism family even though deferral/observation-skipping are weaker than the paper wording. |
| 30 | CONTROL | 22 | 4/4/4/5/5 | `levi-qiao/longgraph-skill@b27376fd44f30505cbc52c2520c42e725b028ea1` | No | No | Strong conceptual match, but primarily a Markdown/file control plane rather than an executable orchestration runtime. |
| 30 | EXPERIMENT | 25 | 5/5/5/5/5 | `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65` | No | No | Exact target; fail-closed completion guards, auditor mutation handling, original-contract checks, durable resume and hardening tests verified. |
| 31 | CONTROL | 25 | 5/5/5/5/5 | `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e` | No | No | Exact target; issue-state reconciliation, retry/backoff, per-issue workspaces, proof surfaces and broad tests verified with trusted-environment limits preserved. |
| 31 | EXPERIMENT | 25 | 5/5/5/5/5 | `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e` | No | No | Exact target plus useful descendant-cluster→canonical-spec pivot and red-team separation of workspace isolation, retry durability and independent-verifier claims. |
| 32 | CONTROL | 25 | 5/5/5/5/5 | `SlanchaAI/ingot@9a91b98bece00f74bea67c20a8316c55c93c379d` | No | No | Demonstrably superior equivalent: held-out/leakage gates, full-agent replay, executable checks, exact-revision promotion, rollback/snapshots and audit events are source/test backed; bypass and audit-durability caveats are preserved. |
| 37 | CONTROL | 25 | 5/5/5/5/5 | `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d` | No | No | Exact target; heterogeneous connectors, append-style version history/diffs, version-race tests and semantic fee-vs-valuation QA verified. |
| 37 | EXPERIMENT | 25 | 5/5/5/5/5 | `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d` | No | No | Exact target plus explicit invariant-triad search and comparison showing connector breadth cannot substitute for version/diff semantics and semantic QA. |
| 38 | CONTROL | 25 | 5/5/5/5/5 | `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653` | No | No | Exact target; multiple government forecast connectors, first/last seen, history/diffs and success/partial/failure semantics verified. |
| 38 | EXPERIMENT | 25 | 5/5/5/5/5 | `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653` | No | No | Exact target plus successful invariant-triad transfer; verifier also found the APFS unexpected-shape→empty-result false-green risk. |
| 39 | CONTROL | 25 | 5/5/5/5/5 | `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8` | No | No | Exact target; L5K import, canonical Rockwell namespace, UDT/AOI/array/BOOL semantics, typed OPC-UA nodes and fidelity tests were inspected with live-hardware/opt-in-test limits preserved. |
| 39 | EXPERIMENT | 25 | 5/5/5/5/5 | `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8` | No | No | Exact target with stronger three-invariant intersection and history archaeology; negative NodeId assertions and explicit withdrawal of unverified L5X support improved calibration. |
| 44 | CONTROL | 25 | 5/5/5/5/5 | `vncwr/backwyn@57f4b8afc3d9ce14f2a35febc802536cfa816839` | No | No | Exact target; scratch restore, corruption/staleness/unverified-state negatives and successful exact-revision CI checked. |
| 44 | EXPERIMENT | 24 | 4/5/5/5/5 | `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91` | No | No | Strong equivalent with scratch restore, corruption/fail-open controls and truthful unknown/latest semantics; one discovery point withheld because it stops short of booted-DB/application invariants and explicit age-based stale-proof semantics. |
| 45 | CONTROL | 24 | 5/5/4/5/5 | `DNYoussef/guardspine-spec@4b21006daa82af52647c5b6e4288d995ccbaf401` + companion verifier | No | No | Exact evidence-interoperability component with strong malformed/tamper/signature checks; one calibration point withheld because trusted-key policy/external adoption remain separate. |
| 45 | EXPERIMENT | 25 | 5/5/5/5/5 | `capxholding/swarrm-verify@d3e52abfaf2b0025db87b5aa491db2001902267f` | No | No | Demonstrably superior equivalent: normative portable contract, offline verifier, hostile/golden/fuzz vectors, explicit completeness UNKNOWN/strict mode, and a genuinely separate implementation whose differential testing caught a real spec/crypto bug. External trust/global completeness limits are sharply bounded. |
| 46 | CONTROL | 24 | 5/5/5/4/5 | `Kjudeh/railway-postgres-backups@1949082f892f62fe47764f490683795d85a6dedd` | No | No | Demonstrably equivalent negative-control result: fail-open SQL restore behavior, zero-table default acceptance, non-blocking row-count failure and placeholder verification SQL justified REJECT despite polished claims. |

## Retained-lesson / learning status
- No benchmark lesson is promoted from a single task.
- **Promoted to SEARCH_SKILLS:** `Acceptance-path transition inspection`, supported by Experiment Tasks **30 and 31**.
- **Promoted to SEARCH_SKILLS:** `First-party production-source triangulation`, supported by Experiment Tasks **09 and 10**.
- **Promoted to SEARCH_SKILLS:** `Ingestion invariant-triad intersection`, supported by Experiment Tasks **37 and 38**; Task **39** is a cross-domain confirmation of the broader executable-invariant idea.
- **Now eligible and promoted this scoring cycle:** `Fail-open boundary archaeology`, independently supported by Experiment Tasks **44 and 45**. The safe transferable lesson is to inspect missing/ambiguous/stale evidence and infrastructure-fault paths and require explicit FAIL/UNKNOWN behavior rather than silent green success.
- Not yet separately promoted: Pair 3 capability-conjunction + claim tracing (Task 16 only); Pair 4 state-machine + audit-log conjunction (Task 23 only); Pair 4 perturbation+hard-invariant scheduling (Task 24 only); Pair 4 decision-claim→runtime-side-effect trace (Task 25 only); Pair 5 descendant-cluster→canonical-spec pivot (Task 31 only); Pair 7 contract→negative-vector→differential-implementation triangulation (Task 45 only).
- The broader `Executable-invariant intersection` generalization has evidence across Tasks **37, 38 and 39**, but is not added as a second overlapping central skill yet; the narrower ingestion skill already captures the core method, and duplicate skill names would reduce clarity.

## Experiment-wide conclusion
Too early for a winner claim. Across **13 matched tasks**, Experiment has a slightly higher mean (**24.62 vs 24.31**), but the **median paired difference is 0**, with **3 wins, 7 ties and 3 losses** and no false promotions in either condition. The experimental architecture is producing reusable search methods and stronger red-team boundaries on several tasks, but it is also using somewhat more reported search effort per validated strong result. Continue the benchmark; do not claim an architecture winner yet.
