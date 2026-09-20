# A/B SCOREBOARD
Frozen experiment started 2026-09-20.

Hunt 15 / MASTER Integrator owns this file. Hunters must not score themselves against `BENCHMARK_GOLD.md`.

Scoring dimensions are each 0-5: Target Discovery (TD), Technical Verification (TV), Calibration (CAL), Commercial Reasoning (CR), Evidence Discipline (ED). Pair means use **matched completed tasks only**; raw completion counts include unmatched completed work. A demonstrably superior equivalent can receive full Target Discovery credit.

## Pair summary
| Pair | Tasks | Control completed | Experiment completed | Matched tasks scored | Control matched mean /25 | Experiment matched mean /25 | Control false promotions | Experiment false promotions | Winner so far |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 01-08 | 5 | 0 | 0 | — | — | 0 | 0 | — |
| 2 | 09-15 | 6 | 6 | 6 | 24.67 | 25.00 | 0 | 0 | Experiment |
| 3 | 16-22 | 7 | 5 | 5 | 23.20 | 24.60 | 0 | 0 | Experiment |
| 4 | 23-29 | 7 | 7 | 7 | 24.86 | 24.57 | 0 | 0 | Control |
| 5 | 30-36 | 7 | 6 | 6 | 24.50 | 24.83 | 0 | 0 | Experiment |
| 6 | 37-43 | 5 | 6 | 5 | 25.00 | 25.00 | 0 | 0 | Tie |
| 7 | 44-50 | 7 | 5 | 5 | 24.60 | 24.80 | 0 | 0 | Experiment |

## Experiment-wide matched metrics
- Matched tasks scored: **34** — 09, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 44, 45, 46, 47, 48.
- Control matched mean: **24.50/25**.
- Experiment matched mean: **24.79/25**.
- Mean paired difference (Experiment - Control): **+0.29**.
- Median paired difference: **0.0**.
- Pairwise task win / tie / loss for Experiment: **7 / 23 / 4**.
- False promotions: **0 Control / 0 Experiment** among scored results.
- No-find results: **0 Control / 0 Experiment** among scored results.
- Approximate search effort per validated STRONG result remains **Control ~10-11 reported search/deep-inspection units; Experiment ~11-12**. This is directional because result files mix query counts, candidate triage counts, specialist passes and deep inspections.
- Learning slope remains **mildly positive but score-ceiling limited**. Pair 2 is 25→25→25→25→25→25; Pair 3 24→25→25→25→24; Pair 4 23→25→24→25→25→25→25; Pair 5 25→25→24→25→25→25; Pair 6 25→25→25→25→25 with unmatched Task 42 also scoring 25; Pair 7 24→25→25→25→25. Median early-to-late within-pair change remains about **+0.5**, while most recent tasks often tie at the ceiling. Qualitative learning remains stronger than the score slope.

## Scored task details
Scores preserve prior scored results and add newly completed unscored results observed in this integration run.

| Task | Condition | Score | TD/TV/CAL/CR/ED | Candidate | False promotion | No-find | Concise justification |
|---:|---|---:|---|---|---|---|---|
| 01 | CONTROL | 25 | 5/5/5/5/5 | `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045` | No | No | Exact target; physical-event truth, fail-closed pricing, evidence freeze, approval-to-charge and failure semantics verified. |
| 02 | CONTROL | 25 | 5/5/5/5/5 | `emoss08/Trenova@3bbd4801978ec069d5a1059dfdf466764a03934f` | No | No | Exact target; dispatch/rates/detention/invoice variance/settlement transitions verified with release limits preserved. |
| 03 | CONTROL | 25 | 5/5/5/5/5 | `nace-martin/Project-RateEngine@dddd2c2df3d35e857e627e9132fe879821fdd538` | No | No | Demonstrably equivalent rerating target with effective dating, ambiguity rejection, overlap prevention and multiple charge bases. |
| 04 | CONTROL | 25 | 5/5/5/5/5 | `Shreyas2409/freight-intake@49ee48e383aea202cc5ddf15c500a5b39092d8b7` | No | No | Superior/equivalent extraction target with page-grounded facts, deterministic money arithmetic, review gates and adversarial fixtures; production extraction accuracy bounded. |
| 05 | CONTROL | 25 | 5/5/5/5/5 | `srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac` | No | No | Exact target; deterministic proof obligations, blocker explanations, same-adjudicator counterfactual next-evidence ranking, negative tests and calibration caveat all correctly verified. |
| 09 | CONTROL | 25 | 5/5/5/5/5 | `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f` | No | No | Exact first-party target; DITA source, fill-ins and change provenance inspected. |
| 09 | EXPERIMENT | 25 | 5/5/5/5/5 | `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f` | No | No | Exact target plus source/history/publication triangulation; unsupported currentness/schema claims withheld. |
| 10 | CONTROL | 25 | 5/5/5/5/5 | `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` | No | No | Exact first-party backend/ETL target with loaders, models, transforms and tests. |
| 10 | EXPERIMENT | 25 | 5/5/5/5/5 | `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` | No | No | Exact target with stronger pipeline-boundary and deployment/history discipline. |
| 11 | CONTROL | 25 | 5/5/5/5/5 | `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` | No | No | Strong equivalent identity/award-lineage target with ambiguity-safe joins and tested parent/reference semantics. |
| 11 | EXPERIMENT | 25 | 5/5/5/5/5 | `fedspendingtransparency/data-act-broker-backend@76dcae4ccbf6951223608bc1d8fd0c5b03da5d68` | No | No | Exact target with SAM identity/hierarchy ingestion, deterministic award keys and negative cross-file tests. |
| 12 | CONTROL | 23 | 5/5/4/5/4 | `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` | No | No | Strong equivalent, but missed a zero-check path that can make validation pass without a semantic assertion. |
| 12 | EXPERIMENT | 25 | 5/5/5/5/5 | `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` | No | No | Same target plus exact PASS-boundary red-team; zero-check false green and current CI/security caveats found and bounded. |
| 13 | CONTROL | 25 | 5/5/5/5/5 | `joschiservice/RosterSpec@f7e701c694bf1facdc4999e1681a3aa11493614d` | No | No | Exact target; hard locks, coverage/stability objective, replay and adverse repair tests verified. |
| 13 | EXPERIMENT | 25 | 5/5/5/5/5 | `joschiservice/RosterSpec@f7e701c694bf1facdc4999e1681a3aa11493614d` | No | No | Exact target with deeper published-plan transition tracing, optimality flags and comparator/current-CI caveats. |
| 14 | CONTROL | 25 | 5/5/5/5/5 | `novonordisk-research/OptiHPLCHandler@96399dcddc1457a5b942f61585b9e8fcf78b9a72` | No | No | Exact vendor-specific CDS integration; installed-Empower mutation/acquisition paths, original/non-overwrite semantics, tests and vendor audit boundary verified with validation/entitlement caveats. |
| 14 | EXPERIMENT | 25 | 5/5/5/5/5 | `novonordisk-research/OptiHPLCHandler@96399dcddc1457a5b942f61585b9e8fcf78b9a72` | No | No | Same exact target with deeper API/version/commit archaeology; TLS, optional audit comments, mocked-test and system-suitability caveats correctly bounded without overrejecting the integration. |
| 16 | CONTROL | 21 | 2/5/5/4/5 | `broad-well/recovair-abm@7b3379cb431591c148a26993097a08487ae6886b` | No | No | Deep partial correctly kept WATCH; joint optimization, legality, uncertainty and replay incomplete. |
| 16 | EXPERIMENT | 24 | 5/5/5/4/5 | `mizuharaa/olus@f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68` | No | No | Exact target with solver, legality, uncertainty, simulation and replay; FAR117 integration overclaim bounded. |
| 17 | CONTROL | 25 | 5/5/5/5/5 | `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806` | No | No | Strong equivalent with exact/net/fee/refund/split/dedupe/ambiguity semantics and tests. |
| 17 | EXPERIMENT | 25 | 5/5/5/5/5 | `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806` | No | No | Same equivalent with deeper conjunction search and algorithm/database/CI verification. |
| 18 | CONTROL | 25 | 5/5/5/5/5 | `Vzlentin/calibre@264b6fc27fd4293660983c2adf9f86cfa1b4d733` | No | No | Exact target; temporal admissibility, immutable issued decisions, calibration, settlement and ordering semantics tested. |
| 18 | EXPERIMENT | 25 | 5/5/5/5/5 | `Vzlentin/calibre@264b6fc27fd4293660983c2adf9f86cfa1b4d733` | No | No | Exact target plus transition-order and exact-revision archaeology that rejected stale pre-reset architecture claims. |
| 19 | CONTROL | 24 | 5/5/4/5/5 | `MudharsonPrabhu/FairRelay@19b9614616780c3eaeba7894ba85ee619edb7114` | No | No | Strong equivalent; one point withheld because override fairness snapshots can be misleading. |
| 19 | EXPERIMENT | 25 | 5/5/5/5/5 | `KesavamurthyT/Fair-Dispatch-Transparent-Fair-Route-Allocation@90f8768abe3b49e7bd577cd666096a93ff2da3cd` | No | No | Exact target; route/fairness loop, explanations, appeals/overrides and logs real; CI/governance seams bounded. |
| 20 | CONTROL | 21 | 2/5/5/4/5 | `sachinpatel-or/Production-Scheduling-and-Optimization-System@3b545e7ea5ca2f5efd1c5f4b283bd7b52de17bbe` | No | No | Deep partial kept WATCH; no immutable baseline, non-regression gate, safe-plan fallback or durable repair lineage. |
| 20 | EXPERIMENT | 24 | 5/4/5/5/5 | `cls1277/RACE-Sched@e44c3aa92f29d93208c3942d6d704216c1d06e62` | No | No | Strong equivalent promotion transaction; baseline/candidate gate, matched evaluation, commit-or-retain and lineage evidence are real, but no local tests and only partial whole-plan validation/repair ancestry cap verification. |
| 21 | CONTROL | 24 | 5/4/5/5/5 | `Himanshu-Laddhad/Nudge-Causal-Promotion-Intelligence-System@21783bf341d25c82fcff208735041637b2ceba10` | No | No | Strong causal-promotion equivalent; one verification point withheld because outputs were model-based and not independently rerun/test-backed. |
| 22 | CONTROL | 25 | 5/5/5/5/5 | `josephazar/FreshRetailnet-50k-Analysis@fd17142943f61452381841cbe67f67ded5fd3a52` | No | No | Demonstrably strong equivalent; censored-demand reconstruction, leakage-free calibration, validation-only policy selection, inventory economics, negative tests and proxy-economics limits all verified. |
| 23 | CONTROL | 24 | 5/5/4/5/5 | `Dynamical-Systems-Research/dynamical-cli@b4823fb4e4babd942e3beafcad8042ea0684f1c0` | No | No | Strong campaign-governance substrate; requested action classes are semantic rather than one closed runtime state machine. |
| 23 | EXPERIMENT | 23 | 3/5/5/5/5 | `fl-sean03/OpenSDL@43f49889c87e78cffb383f8683766453e4daaff1` | No | No | Correct WATCH; first-class acquire-context and richer campaign-level recovery/escalation transitions missing. |
| 24 | CONTROL | 25 | 5/5/5/5/5 | `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a` | No | No | Exact target; hard locks, feasibility, adversarial lock tests and robustness/Plan-B machinery verified. |
| 24 | EXPERIMENT | 25 | 5/5/5/5/5 | `Arpita2919/RailSync@f82d600f62fc355fd755ca3e6d457c384a300c4a` | No | No | Exact target plus explicit hard-lock-vs-warm-start falsification. |
| 25 | CONTROL | 25 | 5/5/5/5/5 | `panoskom/PPDM_framework@4fbca1dfc28280d0e6428b22c796e15c4f305ccd` | No | No | Exact target; scarce slots, repair/replace, uncertainty/deferral and VoI surfaces verified with execution limits disclosed. |
| 25 | EXPERIMENT | 24 | 5/5/4/5/5 | `panoskom/PPDM_framework@4fbca1dfc28280d0e6428b22c796e15c4f305ccd` | No | No | Exact target with stronger runtime-side-effect tracing but slightly over-conservative calibration. |
| 26 | CONTROL | 25 | 5/5/5/5/5 | `airsim/rmol@6a51f9b90d361a115e39aa57a3329d7723af717f` | No | No | Exact target; censoring, unconstraining, forecasting and stochastic protection/booking control verified; DP path bounded. |
| 26 | EXPERIMENT | 25 | 5/5/5/5/5 | `airsim/rmol@6a51f9b90d361a115e39aa57a3329d7723af717f` | No | No | Exact target; dispatch-to-body trace found empty/commented DP and hard-coded-pass tests without overrejecting real Monte-Carlo chain. |
| 27 | CONTROL | 25 | 5/5/5/5/5 | `woody-box/Dynamic-Home@250526f570fa03c09f31332085684f9b0e7dfcbb` | No | No | Exact target; integrated control context, tariff/headroom/occupancy/solar effects, reason-coded intent and CI verified. |
| 27 | EXPERIMENT | 25 | 5/5/5/5/5 | `woody-box/Dynamic-Home@250526f570fa03c09f31332085684f9b0e7dfcbb` | No | No | Exact target with context→decision→actuator→reason side-effect tracing and conflict tests. |
| 28 | CONTROL | 25 | 5/5/5/5/5 | `PrimeIntellect-ai/prime-agent@e311d6495124cf0bdc629c813fc97a39a9a3054d` | No | No | Exact target; prompt/memory/skill/subagent refinement, persistence/versioning, rollback and failure/reload tests verified. |
| 28 | EXPERIMENT | 25 | 5/5/5/5/5 | `PrimeIntellect-ai/prime-agent@e311d6495124cf0bdc629c813fc97a39a9a3054d` | No | No | Exact target with trajectory→typed artifact→versioned persistence→later use/rollback tracing; executable-skill packaging separated. |
| 29 | CONTROL | 25 | 5/5/5/5/5 | `ryanwi/agent-control-plane@99da3934faa2aa7be09df72134cc5e8023e8704f` | No | No | Demonstrably strong equivalent; fail-closed tool governance, durable approvals/budgets/audit/revocation/kill semantics and exact-head CI verified while host-integration/global-halt limits are preserved. |
| 29 | EXPERIMENT | 25 | 5/5/5/5/5 | `ryanwi/agent-control-plane@99da3934faa2aa7be09df72134cc5e8023e8704f` | No | No | Same strong equivalent with execution-chokepoint/bypass archaeology; integrated tool governance and persisted stop semantics verified while host-wired model governance, budget-facade and alpha-maturity caveats are explicitly bounded. |
| 30 | CONTROL | 22 | 4/4/4/5/5 | `levi-qiao/longgraph-skill@b27376fd44f30505cbc52c2520c42e725b028ea1` | No | No | Strong conceptual match but primarily a Markdown/file control plane rather than executable orchestration runtime. |
| 30 | EXPERIMENT | 25 | 5/5/5/5/5 | `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65` | No | No | Exact target; fail-closed completion, auditor mutation handling, contracts, durable resume and hardening tests verified. |
| 31 | CONTROL | 25 | 5/5/5/5/5 | `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e` | No | No | Exact target; issue reconciliation, retry/backoff, per-issue workspaces and proof/review surfaces verified. |
| 31 | EXPERIMENT | 25 | 5/5/5/5/5 | `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e` | No | No | Exact target plus descendant→canonical pivot and separation of workspace/retry/verifier claims. |
| 32 | CONTROL | 25 | 5/5/5/5/5 | `SlanchaAI/ingot@9a91b98bece00f74bea67c20a8316c55c93c379d` | No | No | Superior equivalent with held-out gates, full-agent replay, exact-revision promotion, rollback/snapshots and audit events. |
| 32 | EXPERIMENT | 24 | 5/5/4/5/5 | `kenhuangus/ASG-SI@c1da9a1d15883d04518f4a7213ccba612b0e6b28` | No | No | Exact capability with verified-skill gate/audit; rollback/version selection not implemented despite stronger framing. |
| 33 | CONTROL | 25 | 5/5/5/5/5 | `MSLNZ/GTC@1c165fce9bbfd7f75f00e43157dbe5773cc94332` | No | No | Strong NMI equivalent preserving correlated uncertainty/dependency state through calculations and archive round trips. |
| 33 | EXPERIMENT | 25 | 5/5/5/5/5 | `usnistgov/rmellipse@79daadef817c892e0366cd748279665c6f1f8dd3` | No | No | Strong NIST equivalent with shared uncertainty mechanisms, arbitrary-function propagation and tested HDF5/object round trips. |
| 34 | CONTROL | 25 | 5/5/5/5/5 | `ORNL/flowcept@c000b10ea49659af6c5821b61918f3893bd46a92` | No | No | Strong first-party ORNL runtime-provenance component; provenance not overstated as tamper-evident proof. |
| 34 | EXPERIMENT | 25 | 5/5/5/5/5 | `ORNL/flowcept@c000b10ea49659af6c5821b61918f3893bd46a92` | No | No | Exact target with cross-framework lineage verification and explicit immutability/replay limits. |
| 35 | CONTROL | 25 | 5/5/5/5/5 | `hdkim99/OperandoMerge@06d2ca8e9b0dfc2683c8ca77b19a1ab6f1623b92` | No | No | Exact target; type-aware time-fusion semantics, no extrapolation/event interpolation, row provenance and public-data validation verified. |
| 35 | EXPERIMENT | 25 | 5/5/5/5/5 | `hdkim99/OperandoMerge@06d2ca8e9b0dfc2683c8ca77b19a1ab6f1623b92` | No | No | Exact target; measurement-semantic typing, negative interpolation/extrapolation tests and per-output raw-row provenance verified; maturity/alignment assumptions bounded. |
| 36 | CONTROL | 25 | 5/5/5/5/5 | `thermofisherlsms/meth-modifications@b30bbe120268344c7b6f75e33944d8b30baed0ea` | No | No | Exact official vendor component; versioned method schemas plus validate/export/create/modify surfaces and first-party release-history corroboration verified, with runtime/round-trip limits preserved. |
| 37 | CONTROL | 25 | 5/5/5/5/5 | `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d` | No | No | Exact target; heterogeneous connectors, append-style versions/diffs, race tests and fee-vs-valuation QA verified. |
| 37 | EXPERIMENT | 25 | 5/5/5/5/5 | `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d` | No | No | Exact target plus invariant-triad search and breadth-vs-history red-team. |
| 38 | CONTROL | 25 | 5/5/5/5/5 | `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653` | No | No | Exact target; forecast connectors, first/last seen, history/diffs and run-state semantics verified. |
| 38 | EXPERIMENT | 25 | 5/5/5/5/5 | `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653` | No | No | Exact target plus invariant-triad transfer and an unexpected-shape→empty false-green risk. |
| 39 | CONTROL | 25 | 5/5/5/5/5 | `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8` | No | No | Exact target; L5K import, Rockwell namespace, UDT/AOI/array semantics, typed OPC-UA nodes and fidelity tests verified. |
| 39 | EXPERIMENT | 25 | 5/5/5/5/5 | `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8` | No | No | Exact target with invariant/history archaeology and withdrawal of unverified L5X support. |
| 40 | CONTROL | 25 | 5/5/5/5/5 | `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063` | No | No | Exact official target; reconnect/subscription recovery, chaos tests and migration tooling verified. |
| 40 | EXPERIMENT | 25 | 5/5/5/5/5 | `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063` | No | No | Exact target plus defect archaeology and newer destructive-restart deadlock evidence used to narrow readiness claims. |
| 41 | CONTROL | 25 | 5/5/5/5/5 | `geminimir/meterguard@9147d6fdf9fd8ee8761d732e956fc0a8c86989bd` | No | No | Exact target; local/provider parity, drift, corrections and stale demo/test caveats verified and bounded. |
| 41 | EXPERIMENT | 25 | 5/5/5/5/5 | `geminimir/meterguard@9147d6fdf9fd8ee8761d732e956fc0a8c86989bd` | No | No | Exact target; symmetry/executability red-team found stale workflow, unused period semantics and legacy provider lifecycle. |
| 42 | EXPERIMENT | 25 | 5/5/5/5/5 | `cboxdk/laravel-billing@ac3305f2a857baf5208a1170387f7771dba40ca7` | No | No | Superior/equivalent billing-journal target with balanced posting, derived balances, unique-key dedupe, retries and append-only hardening; raw-SQL/portability limits bounded. |
| 44 | CONTROL | 25 | 5/5/5/5/5 | `vncwr/backwyn@57f4b8afc3d9ce14f2a35febc802536cfa816839` | No | No | Exact target; scratch restore, corruption/staleness/unverified negatives and exact-revision CI checked. |
| 44 | EXPERIMENT | 24 | 4/5/5/5/5 | `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91` | No | No | Strong equivalent with scratch restore/fail-open controls; one discovery point withheld because it stops before application invariants. |
| 45 | CONTROL | 24 | 5/5/4/5/5 | `DNYoussef/guardspine-spec@4b21006daa82af52647c5b6e4288d995ccbaf401 + companion verifier` | No | No | Exact evidence-interoperability component; malformed/tamper/signature checks strong, external trust/adoption separate. |
| 45 | EXPERIMENT | 25 | 5/5/5/5/5 | `capxholding/swarrm-verify@d3e52abfaf2b0025db87b5aa491db2001902267f` | No | No | Superior equivalent with normative contract, offline verifier, hostile/fuzz vectors and differential implementation; trust/completeness separated. |
| 46 | CONTROL | 24 | 5/5/5/4/5 | `Kjudeh/railway-postgres-backups@1949082f892f62fe47764f490683795d85a6dedd` | No | No | Superior/equivalent negative control: fail-open SQL restore, zero-table acceptance and placeholder verification justify REJECT. |
| 46 | EXPERIMENT | 25 | 5/5/5/5/5 | `zephyrcore/BackupAttest@30ad45cf12c7b731824d6d12fb1723dc2fd11727` | No | No | Superior negative control: self-reported verification can unlock green state and RPO counts a chain-invalid state; correct REJECT. |
| 47 | CONTROL | 25 | 5/5/5/5/5 | `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28` | No | No | Superior/equivalent negative control: missing authority becomes default/zero, provisional findings feed value, and overlapping findings double-count dollars; REJECT justified. |
| 47 | EXPERIMENT | 25 | 5/5/5/5/5 | `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28` | No | No | Same negative control with deeper authority→finding→aggregate→review→billing trace; missing authority and pre-review/double-counted value contamination verified. |
| 48 | CONTROL | 25 | 5/5/5/5/5 | `mycomind4-arch/permitsignal@4a734615a8e388a98e085026a877b3bdfc1ac8b1` | No | No | Superior/equivalent negative control: unreachable authoritative systems plus missing completeness/freshness/PARTIAL semantics justify rejection for production lead intelligence. |
| 48 | EXPERIMENT | 25 | 5/5/5/5/5 | `stojanpetkovic/sawfleet@02c1c52847e3e3f83ae7dc7dcf72ae5f6bb29fbb` | No | No | Superior/equivalent negative control: real UI over opaque source plane; health lacks freshness/completeness/degraded contracts and placeholder contact contamination is handled; correct REJECT. |
| 49 | CONTROL | 25 | 5/5/5/5/5 | `rc2consulting/rc2consulting.github.io@05c644c9fe7b27db941e26f926461a3b44768138` | No | No | Superior/equivalent stale-authority trap: current thresholds do not rescue obsolete measurement-window logic; reject for current eligibility use. |
| 50 | CONTROL | 25 | 5/5/5/5/5 | `GSA/GSA-Acquisition-NMCARS@09d5b2d...` | No | No | Accepted negative-control result: recent repository activity but source-level comparison showed substantive staleness; recent Git history is not current authority. |

## Retained-lesson / learning status
- No benchmark lesson is promoted from a single task.
- **Promoted to SEARCH_SKILLS:** `First-party production-source triangulation`, supported by Experiment Tasks **09 and 10**; Task 11 reinforces it.
- **Promoted to SEARCH_SKILLS:** `Capability-Conjunction Search + Claim Tracing`, supported by Experiment Tasks **16 and 17**; Task 19 reinforces it.
- **Promoted to SEARCH_SKILLS:** `Acceptance-path transition inspection`, supported by Experiment Tasks **30 and 31**; Task 32 reinforces it.
- **Promoted to SEARCH_SKILLS:** `Ingestion invariant-triad intersection`, supported by Experiment Tasks **37 and 38**; Tasks 39-42 broaden executable-invariant transfer.
- **Promoted to SEARCH_SKILLS:** `Protocol-regression archaeology for pre-FAT systems`, supported by Experiment Tasks **39 and 40**.
- **Promoted to SEARCH_SKILLS:** `Fail-open boundary archaeology`, supported by Experiment Tasks **44 and 45** and reinforced by Task 46.
- **Promoted to SEARCH_SKILLS:** `Decision-claim → runtime-side-effect trace`, supported by Experiment Tasks **25 and 26**, reinforced by Tasks 27 and 28.
- **Promoted to SEARCH_SKILLS:** `Authority-origin / invariant-set consistency`, supported independently by Experiment Tasks **46 and 47**.
- Not yet separately promoted: Transition-Order + Temporal-Invariant Verification (Task 18 only); Governance-Loop Boundary Verification (Task 19 only); Promotion-Transaction Boundary Verification (Task 20 only); Enforcement-Chokepoint + Persisted-Stop Verification (Task 29 only); published-plan replanning invariant quartet (Task 13 only); harness-artifact closed loop (Task 28 only); provenance-adapter intersection (Task 34 only); measurement-semantics fusion intersection (Task 35 only); regulated-vendor installed-system boundary triad (Task 14 only); contract→negative-vector→differential-implementation triangulation (Task 45 only); Value-State Aggregation Audit (Task 47 only); database-boundary bypass check (Task 42 only); opaque-upstream health-contract audit (Task 48 only).

## Experiment-wide conclusion
Too early for a winner claim. Across **34 matched tasks**, Experiment has a small mean advantage (**24.79 vs 24.50**), but the **median paired difference is 0** and task outcomes are **7 wins, 23 ties, 4 losses** for Experiment. Neither condition has produced a scored false promotion or no-find result. The experimental architecture is generating transferable verification/search methods and has improved calibration on several adversarial tasks, but score separation remains modest and the experimental path still appears somewhat more expensive. The evidence does **not** justify declaring the Experiment architecture the winner; continue until materially more matched tasks or all 50 tasks complete.
