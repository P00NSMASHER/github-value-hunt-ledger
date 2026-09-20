# SEARCH_SKILLS

Shared reusable discovery methods for the GitHub Value Hunt. Hunters should read this file before searching, reuse skills when appropriate, and append only methods that have produced evidence-backed value. Skills are search procedures, not conclusions; validate every candidate independently.

## Skill schema
- STRATEGY ID: stable `STRAT:<slug>` used by `intelligence/search_runs.jsonl`
- SKILL NAME
- WHEN TO USE
- PROCEDURE
- WHY IT WORKED
- EXAMPLES
- FAILURE MODES
- NEXT IMPROVEMENT

## Paper -> research artifact -> production descendant
- SKILL NAME: Paper -> research artifact -> production descendant
- WHEN TO USE: A recent paper introduces a new agent architecture, algorithm, workflow or adaptation mechanism that looks commercially important.
- PROCEDURE:
  1. Find the official/reference implementation and pin an exact revision.
  2. Identify authors, labs, organizations and maintainers.
  3. Search their later repositories, renamed projects, successor organizations and commit lineage.
  4. Search for generalized or productized descendants using distinctive class/function/terminology signatures rather than title alone.
  5. Compare source-level invariants from the paper artifact to the descendant.
  6. Prefer the production descendant for commercial scoring when it preserves the valuable mechanism; retain the research repo as method/evidence.
- WHY IT WORKED: Continual Harness research exposed whole-harness online refinement; following the author/project lineage surfaced Prime Agent, which preserved the refinement idea while adding persistent coding/research sessions, schedules, rollback, programmatic subagents and reusable skills.
- EXAMPLES:
  - `sethkarten/continual-harness@bbab97ad...` -> `PrimeIntellect-ai/prime-agent@e311d649...`
- FAILURE MODES:
  - a fork merely copies the paper without operational hardening;
  - a marketed successor drops the original mechanism;
  - title/README similarity is mistaken for implementation lineage;
  - later repo is broader but weaker on the core invariant.
- NEXT IMPROVEMENT: automate author/org/commit-lineage search and require at least one source-level invariant match before declaring a production descendant.

## Cross-source emergence triangulation
- SKILL NAME: Cross-source emergence triangulation
- WHEN TO USE: A technical capability appears new but its commercial maturity is unclear.
- PROCEDURE:
  1. Identify the capability using a precise technical phrase, algorithm, protocol or architectural invariant.
  2. Search independent GitHub implementations.
  3. Search recent papers/preprints for benchmark evidence.
  4. Search patents/packages/standards where available.
  5. Look for movement from research artifact -> maintained implementation -> production control plane/product.
  6. Record disagreements: strong paper but weak code, strong code but no external evidence, or several independent implementations converging.
- WHY IT WORKED: Self-improving agent research, long-horizon verification and agent control-plane projects independently converged on persistent harness state, verifier/auditor roles, reusable skills and runtime governance. The convergence is stronger evidence of an emerging category than any single README.
- EXAMPLES:
  - Continual Harness / EvoTest / ASG-SI research
  - Prime Agent / LongHorizon-Harness / Preloop production-oriented implementations
- FAILURE MODES:
  - all projects descend from one codebase and are not independent evidence;
  - benchmark claims are repository-reported only;
  - terminology changes make simple keyword counts misleading.
- NEXT IMPROVEMENT: track independent implementation count, publication velocity, package adoption and production deployment evidence as separate emergence signals.

## Acceptance-path transition inspection
- SKILL NAME: Acceptance-path transition inspection
- WHEN TO USE: An agent, workflow or autonomous-control repository claims independent review, verified completion, safe handoff, durable orchestration or evidence-gated promotion.
- PROCEDURE:
  1. Ignore reviewer/auditor prose initially and locate the exact state transition that accepts work as `complete`, `reviewable`, `merged`, `promoted` or otherwise trusted.
  2. Trace which concrete evidence can unlock that transition and which blocking conditions keep it closed.
  3. Inspect the failure/recovery path around the same transition: verifier timeout, worker crash, stale state, restart/resume, retry/backoff and malformed reviewer output.
  4. Check whether the verifier/reviewer can mutate the artifact it is judging; prefer read-only or mutation-detect/restore designs.
  5. Search tests for the transition and its negative controls, not just for prompt text asking a reviewer to inspect work.
  6. Distinguish filesystem/workspace separation from hardened security isolation and policy-in-instructions from independently enforced validation.
- WHY IT WORKED: Benchmark Experiment Tasks **30 and 31** independently validated this procedure, and Task **32** transferred the same trusted-state question from task completion into reusable-capability promotion. Task 30 separated a real fail-closed manager/executor/auditor completion gate from generic checkpointing. Task 31 traced issue orchestration through reconciliation/retry/workspace/review transitions. Task 32 showed that a verifier-gated trusted-registry insertion can be real while rollback remains a separate unproven claim.
- EXAMPLES:
  - Benchmark Task 30: `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65`
  - Benchmark Task 31: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`
  - Benchmark Task 32: `kenhuangus/ASG-SI@c1da9a1d15883d04518f4a7213ccba612b0e6b28`
- FAILURE MODES:
  - reviewer prompts exist but the executor can still self-certify completion;
  - validation is advisory and does not gate state transition;
  - retry/backoff state disappears on restart and is mistaken for durable recovery;
  - an "isolated workspace" is overclaimed as a security sandbox;
  - a promotion audit/history is mistaken for an implemented rollback/version-selection path;
  - the verifier shares mutable artifacts or correlated assumptions with the executor and independence is overstated.
- NEXT IMPROVEMENT: apply this procedure to billing/audit approval, scientific campaign authority and other human-in-the-loop state machines, and separately trace trusted-state entry versus reversal.

## First-party production-source triangulation
- SKILL NAME: First-party production-source triangulation
- WHEN TO USE: An official regulation, government dataset, public API or authoritative publication may have a deeper production-source repository than its public reading/API surface suggests.
- PROCEDURE:
  1. Start from the first-party publication, API or official service and identify the owning agency/project organization.
  2. Follow that lineage to the source-generation/backend repository and pin an exact revision or production-deploy commit.
  3. Inspect operational markup or transformation code in real files rather than relying on the repository name or README.
  4. Require internal schemas/models plus tests/fixtures that exercise the claimed semantics.
  5. Inspect commit/deploy history for currentness and do not infer deployment from generic repository activity.
  6. Compare adjacent first-party repositories and explicitly separate pipeline stages such as source publication, submission validation, normalization and public serving.
  7. Cross-check a separate first-party publication/rulemaking/data surface so source-repository semantics are not mistaken for sole legal/data authority.
- WHY IT WORKED: Benchmark Experiment Tasks **09 and 10** independently validated the method. Task 09 found procurement-specific fill-ins and change markers in the GSA FAR production DITA corpus. Task 10 showed that a repository named `usaspending-api` actually owns substantial Broker ingestion, normalization, award derivation, schemas and integration tests rather than merely wrapping endpoints.
- EXAMPLES:
  - Benchmark Task 09: `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f`
  - Benchmark Task 10: `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964`
- FAILURE MODES:
  - assuming an API-named repository is only an endpoint wrapper;
  - treating README dates as regulatory/data currentness;
  - collapsing upstream submission/validation and downstream normalization/publication into one authority claim;
  - relying on obsolete loader documentation instead of current source/tests/history;
  - treating source-repository provenance as proof that every upstream fact is authoritative or complete.
- NEXT IMPROVEMENT: apply the method to another official rule/data system with multiple first-party repositories and measure whether it improves source-currentness or pipeline-boundary accuracy versus surface-only search.

## Capability-Conjunction Search + Claim Tracing
- SKILL NAME: Capability-Conjunction Search + Claim Tracing
- WHEN TO USE: A broad operational or financial system is defined by several rare capabilities that are unlikely to appear together in repository titles or category labels.
- PROCEDURE:
  1. Express the target as 3–5 rare implementation signatures drawn from different requirement families, such as solver + domain legality + deterministic replay, or exact money + refund/fee + split matching + idempotency + exception states.
  2. Search for the signatures in code/tests rather than searching only for the product category.
  3. Intersect candidates and deep-inspect only those where the conjunction appears in executable paths, not merely docs or disconnected modules.
  4. Trace each integration-critical README/marketing claim into the exact solver/source/test path; downgrade claims whose capability exists only adjacent to the claimed core.
  5. In money, safety, compliance or reproducibility domains, inspect persistence constraints and exact-revision CI/benchmark evidence in addition to algorithm code.
  6. Preserve modularity caveats: co-located capabilities do not automatically prove they are jointly optimized or production-integrated.
- WHY IT WORKED: Benchmark Experiment Tasks **16 and 17** independently validated the method. Task 16 found a low-attention airline recovery engine by intersecting CP-SAT, crew legality, passenger recovery, uncertainty and replay signals, then exposed that FAR117 was not a hard constraint in the main optimizer. Task 17 transferred the approach to finance, where Decimal money + fee/refund + split + dedupe/idempotency + explicit ambiguity states surfaced a tested reconciliation engine that generic platform searches missed.
- EXAMPLES:
  - Benchmark Task 16: `mizuharaa/olus@f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68`
  - Benchmark Task 17: `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806`
- FAILURE MODES:
  - a README lists the capabilities but they are not connected in the execution path;
  - one module audits a constraint post-solve while marketing implies the solver enforces it;
  - synthetic benchmark coverage is mistaken for production scale;
  - a bounded N→1 matcher is overclaimed as general N↔M reconciliation;
  - code-level conjunctions share one weak assumption and create correlated evidence rather than independent support.
- NEXT IMPROVEMENT: pair the conjunction search with dependency/commit archaeology so rare capability clusters can be traced to their implementation lineage and regression history before deep inspection.

## Ingestion invariant-triad intersection
- SKILL NAME: Ingestion invariant-triad intersection
- WHEN TO USE: Searching for a data-ingestion platform where connector breadth alone is insufficient and durable history plus source-health truth are commercially important; the same logic can be generalized to other systems whose value depends on several executable correctness contracts.
- PROCEDURE:
  1. Define three independent axes before searching: for ingestion, **source topology**, **historical durability**, and **run truth**. For other domains, choose three independently falsifiable implementation invariants.
  2. Search each axis separately using concrete provider/protocol names, table/model symbols, version/diff fields, state-transition names or test signatures rather than product-category keywords.
  3. Intersect candidates only after each axis has independent code evidence; a project with two axes remains a component even if its README sounds complete.
  4. Trace the actual execution algorithm and identity/state boundary. Do not credit fields or status names until the mutation/comparison/transition path is inspected.
  5. Red-team false-green paths and require at least one negative/failure assertion per load-bearing axis.
  6. Require domain-semantic regression evidence where money, interoperability or meaningful decisions depend on mapped state rather than merely syntactic schema validity.
- WHY IT WORKED: Benchmark Experiment Tasks **37 and 38** validated the ingestion form. Task 37 intersected municipal connector families, immutable permit versions/diffs and fee-vs-valuation semantic QA. Task 38 transferred the triad to government acquisition forecasts and surfaced multi-source normalization, temporal history/diffs and source-run success/partial/failure plus an APFS false-green edge case. Tasks **39 and 40** then generalized the method beyond ingestion: engineering-artifact import + vendor-addressing + fidelity tests isolated a stronger PLC emulator, while first-party stack + migration contract + reconnect/subscription regressions isolated the useful OPC-UA pre-FAT oracle.
- EXAMPLES:
  - Benchmark Task 37: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`
  - Benchmark Task 38: `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653`
  - Cross-domain confirmation Task 39: `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8`
  - Cross-domain confirmation Task 40: `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063`
- FAILURE MODES:
  - counting connector/feature breadth as correctness;
  - mutable upserts presented as audit history;
  - status fields/tests that never gate real execution;
  - `success` emitted on unexpected or empty source responses;
  - unstable identity keys splitting one evolving record into unrelated rows;
  - three axes that exist decoratively but never intersect in one functioning path.
- NEXT IMPROVEMENT: standardize a compact “three executable invariants + one negative control each” template that hunters can apply across ingestion, protocols, optimization and audit systems without turning it into a generic checklist.

## Protocol-regression archaeology for pre-FAT systems
- SKILL NAME: Protocol-regression archaeology for pre-FAT systems
- WHEN TO USE: Industrial/protocol software where commercial value depends on upgrade compatibility, reconnect/recovery behavior, parser fidelity or field failure modes rather than only supported feature breadth.
- PROCEDURE:
  1. Pin the exact implementation revision and identify the migration/compatibility contract relevant to the buyer's current and target versions.
  2. Search release notes and commit history for concrete semantic failures, parser rewrites, withdrawn support and compatibility fixes.
  3. Trace each important fix into a regression test or executable invariant at the pinned branch.
  4. Search issues filed **after** the pinned revision for unresolved contradictions that current source/history alone cannot reveal.
  5. Convert unresolved but plausible failure paths into explicit adversarial pre-FAT scenarios rather than either ignoring them or discarding the whole stack automatically.
  6. Keep official/certification provenance separate from version-specific operational readiness.
- WHY IT WORKED: Benchmark Experiment Tasks **39 and 40** independently supported it. Task 39 showed that a real-file L5K parser rewrite and withdrawal of unverified L5X support were stronger maturity evidence than feature breadth alone. Task 40 mined an OPC-UA reconnect/subscription defect corpus and then found a newer destructive-restart deadlock issue that materially narrowed readiness claims while increasing the stack's value as a pre-FAT oracle.
- EXAMPLES:
  - Benchmark Task 39: `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8`
  - Benchmark Task 40: `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063`
- FAILURE MODES:
  - commit prose is mistaken for proof without locating regression tests;
  - an issue report is treated as reproduced fact when it is still unconfirmed;
  - a fix belongs to another branch/version than the one being sold or tested;
  - certification is treated as proof of every reconnect/upgrade path;
  - unresolved issues are over-weighted into rejecting a valuable reference implementation instead of becoming test vectors.
- NEXT IMPROVEMENT: apply this method to EDI, payment, database-driver and e-invoice protocol migrations to see whether defect archaeology predicts commercially important integration failures outside industrial automation.

## Fail-open boundary archaeology
- SKILL NAME: Fail-open boundary archaeology
- WHEN TO USE: A verifier, recovery drill, evidence package, compliance checker, audit engine or trust boundary claims that a state/artifact is valid, complete, current or safe.
- PROCEDURE:
  1. Find the exact transition or verdict that emits PASS/VERIFIED/HEALTHY/TRUSTED.
  2. Search source, tests and commit history for the ambiguous boundary states most likely to become false green: missing evidence, stale/newer-unreadable evidence, stripped completeness material, empty results, parser faults, environment/sandbox faults, checksum/signature failures, partial restores and UNKNOWN/SKIP handling.
  3. Require explicit negative behavior for those states. Prefer FAIL or an honest UNKNOWN/INCOMPLETE that cannot unlock the trusted transition; treat silent skip/success as a promotion blocker.
  4. Inspect selection logic as well as validation logic: a verifier can fail open by silently choosing an older readable artifact while hiding an invalid newer one, or by accepting a subset whose completeness was never proven.
  5. Check whether strict mode exists where optional completeness/trust material becomes mandatory, and whether malformed/tampered fixtures exercise it.
  6. Keep integrity, completeness, freshness and external trust as separate claims; do not let one verified dimension imply the others.
- WHY IT WORKED: Benchmark Experiment Tasks **44 and 45** independently confirmed the method. Task 44 found strong recovery-verifier evidence in explicit missing-manifest/checksum/UNKNOWN/latest-selection regressions rather than backup-success prose. Task 45 transferred the same method to portable evidence bundles: missing completeness material visibly downgraded the result instead of becoming verified, while hostile/malformed vectors exercised fail-closed behavior.
- EXAMPLES:
  - Benchmark Task 44: `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91`
  - Benchmark Task 45: `capxholding/swarrm-verify@d3e52abfaf2b0025db87b5aa491db2001902267f`
- FAILURE MODES:
  - treating a documented `UNKNOWN` enum as evidence without tracing the control flow that emits it;
  - checking only happy-path restore/signature tests;
  - assuming a valid signed subset proves global completeness;
  - assuming the newest selected readable artifact means no newer failed/unreadable evidence exists;
  - interpreting an infrastructure fault as benign SKIP;
  - conflating cryptographic integrity with source truth or trusted-key policy.
- NEXT IMPROVEMENT: apply the method to money-bearing audit/settlement engines and source-health collectors, then measure whether it reduces false-promotion rate on benchmark reject tasks 46–50.

## Decision-claim -> runtime-side-effect trace
- SKILL NAME: Decision-claim -> runtime-side-effect trace
- WHEN TO USE: A repository claims a decision-changing mechanism, abstention/deferral rule, optimizer mode, fallback, information-acquisition trigger or control policy whose presence in docs, enums, metrics or test names may not mean runtime execution actually changes.
- PROCEDURE:
  1. Locate the public API, dispatcher or branch that selects the claimed behavior.
  2. Follow it into the executable implementation body; treat empty, commented, placeholder or no-op bodies as unimplemented even if the surface is advertised.
  3. Identify the concrete runtime side effect: state mutation, skipped/acquired observation, blocked action, changed control flow, altered decision output, committed schedule/order or other externally meaningful transition.
  4. Inspect semantic tests that would fail if that side effect disappeared. Hard-coded-pass, shape-only and no-throw tests are insufficient for the decision claim.
  5. Trace ambiguous/failure paths. Do not mistake a computed metric, log entry, visualization or post-processing label for an enforced runtime gate.
  6. Score sibling modes independently; one real algorithm path does not validate adjacent advertised modes that terminate in stubs or weak tests.
- WHY IT WORKED: Benchmark Experiment Tasks **25 and 26** independently validated the method. Task 25 showed that PPDM computes uncertainty and VoI signals, but the inspected runtime still emits argmax actions and logs suggested observation skips; its N/A deferral is post-processing rather than a proven execution gate. Task 26 transferred the same trace to revenue management: RMOL's Monte-Carlo chain is real, while its advertised DP service path is empty/commented and its forecasting/unconstraining tests are hard-coded passes. Tasks **27 and 28** subsequently reinforced the same causal trace in cyber-physical control and persistent-agent refinement.
- EXAMPLES:
  - Benchmark Task 25: `panoskom/PPDM_framework@4fbca1dfc28280d0e6428b22c796e15c4f305ccd`
  - Benchmark Task 26: `airsim/rmol@6a51f9b90d361a115e39aa57a3329d7723af717f`
  - Reinforcement Task 27: `woody-box/Dynamic-Home@250526f570fa03c09f31332085684f9b0e7dfcbb`
  - Reinforcement Task 28: `PrimeIntellect-ai/prime-agent@e311d6495124cf0bdc629c813fc97a39a9a3054d`
- FAILURE MODES:
  - treating feature labels, enums or documentation as executable behavior;
  - treating post-processing `N/A` or warnings as operational abstention;
  - crediting a metric/VoI/confidence calculation that never changes control flow;
  - counting hard-coded-pass or no-throw tests as semantic validation;
  - using one implemented mode to inflate the evidence quality of adjacent stubbed modes.
- NEXT IMPROVEMENT: apply the trace to money settlement, compliance gates, optimizer fallback and human-approval paths, and measure whether it lowers false-promotion rates without becoming systematically over-conservative.

## Authority-origin / invariant-set consistency
- SKILL NAME: Authority-origin / invariant-set consistency
- WHEN TO USE: A verifier, audit/recovery engine, money-bearing decision system or reporting/billing workflow can emit PASS, CLEAN, SAVINGS, RECOVERY, ELIGIBLE or another asserted outcome from facts whose authority or admissibility may be ambiguous.
- PROCEDURE:
  1. Identify every input that can unlock the asserted state or contribute money/value to it.
  2. For each input, record **who authored or authorizes it** and whether the system independently establishes that fact rather than trusting a caller-authored label, empty/default field or self-attestation.
  3. Trace the admissibility set used by the core validity/authority logic.
  4. Compare that set with the records/claims later used by derived metrics, aggregates, reports and billing. A fact rejected or unknown in one module must not silently count as proof/value in another.
  5. Construct adversarial cases for absent-vs-empty authority, self-reported success, orphan/unlinked records, overlapping findings, BLOCK/WARN rows and pre-review state.
  6. Require UNKNOWN/INCOMPLETE/POTENTIAL states to remain distinct from zero/false/confirmed/recovered when authority is missing or adjudication has not occurred.
- WHY IT WORKED: Benchmark Experiment Tasks **46 and 47** independently validated the method in different domains. Task 46 found that backup metadata fields such as `verified=yes` and drill `ok` were caller-authored and could unlock a clean result without independent restore/digest evidence; it also found RPO counting an orphan state that the chain validator rejected. Task 47 transferred the same method to freight audit: missing contractual authority collapsed into empty/default assumptions, overlapping findings were summed as if economically independent, and pre-review WARN/BLOCK values flowed into savings/recovery and percentage-of-value billing.
- EXAMPLES:
  - Benchmark Task 46: `zephyrcore/BackupAttest@30ad45cf12c7b731824d6d12fb1723dc2fd11727`
  - Benchmark Task 47: `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28`
- FAILURE MODES:
  - a field is named `verified`, `approved`, `eligible` or `settled` but is merely imported rather than independently established;
  - missing authority is coerced to zero/default and later treated as a confirmed expectation;
  - a record excluded from validity/chain logic still enters RPO, savings, settlement or billing metrics;
  - overlapping diagnostic findings double-count one economic delta;
  - human-review labels exist but aggregation/billing occurs before the review transition;
  - conservative UNKNOWN states are collapsed into false negatives or asserted zeros.
- NEXT IMPROVEMENT: combine this skill with fail-open boundary archaeology on AP, commission, freight, eligibility and recovery-proof experiments, and explicitly test whether the accepted evidence/claim set is identical at validation, aggregation and billing/reporting boundaries.

## Rule-period / authority-version audit
- SKILL NAME: Rule-period / authority-version audit
- WHEN TO USE: A deterministic regulatory, eligibility, compliance, procurement or policy calculator/repository looks current but its categorical output depends on effective-dated rules, measurement windows, threshold types, named-program exceptions or authority text that may have drifted.
- PROCEDURE:
  1. Pin the exact repository revision and state the exact product/program context the code claims to decide.
  2. Enumerate every load-bearing rule input: measurement/lookback window, threshold type, averaging basis, exception branch, effective date, section identifier, authority/contact endpoint and categorical output text.
  3. Map each load-bearing rule to a **dated first-party authority**. Do not infer substantive currentness from repository owner, recent commits, `updated_at`, copyright year, current-looking threshold tables or a generic disclaimer.
  4. Inspect recent diffs/commit history to distinguish substantive rule updates from regeneration, formatting, banners, metadata or mirrored publication refreshes.
  5. Compare at least one changed load-bearing section/rule against the current authority. For calculators, construct a boundary case where the stale and current rule periods cross the same threshold and therefore flip the categorical result.
  6. Keep general rules and named-program exceptions separate. A valid exception must not silently become the default rule for a different program/context.
  7. If a repository is stale, preserve any legitimate archival/version-diff value while rejecting it as current decision authority until reconciled.
- WHY IT WORKED: Benchmark Experiment Tasks **49 and 50** independently confirmed the method. Task 49 showed that a recently maintained SBA/federal-contracting calculator could carry current-looking thresholds while its executable measurement windows were stale; first-party authority plus an adversarial boundary case made the defect decision-relevant. Task 50 transferred the method to an official-looking acquisition-regulation mirror, where recent 2026 activity and fresh presentation metadata coexisted with substantively stale section structure/contact authority; direct first-party comparison correctly separated archival value from current-rule use.
- EXAMPLES:
  - Benchmark Task 49: `rc2consulting/rc2consulting.github.io@05c644c9fe7b27db941e26f926461a3b44768138`
  - Benchmark Task 50: `GSA/GSA-Acquisition-NMCARS@09d5b2d7040065fead99e15aacabb1d782b450d5`
- FAILURE MODES:
  - treating repository recency, official organization ownership or current copyright metadata as substantive currentness;
  - validating a current threshold table while missing a stale measurement/averaging window;
  - accepting a disclaimer such as “verify with agency” as a substitute for current decision logic;
  - overgeneralizing a named-program exception into the general rule;
  - trusting mirror/regeneration commits without diffing load-bearing content;
  - discarding a stale corpus entirely when it still has archival/version-diff value.
- NEXT IMPROVEMENT: combine this skill with first-party production-source triangulation and authority-origin consistency for CaptureBrief, PermitPlate, compliance engines and other rule-bearing products; track effective-date/version lineage as a first-class capability rather than a documentation note.

<!-- INTEGRATOR-R11-2026-09-20T0856-0400 -->
## Evaluation-Target Independence
- SKILL NAME: Evaluation-Target Independence
- WHEN TO USE: A decision system's headline business value is computed from a model-derived, censored, proxy, estimated or otherwise indirect outcome rather than the target economic outcome itself.
- PROCEDURE:
  1. Separate three variables explicitly: the score/policy that chooses the action, the evaluator/outcome used to judge that action, and the real business target being claimed.
  2. Ask whether the evaluator is independent of the selected model/policy or whether the same model is effectively grading its own actions.
  3. Ask whether the observed outcome actually identifies the latent/causal/business target; stockout-censored sales, modeled uplift and other proxies may not.
  4. Require randomized/held-out/off-policy evidence, explicit identification assumptions or a clear proxy limitation before upgrading economic claims.
  5. Keep modeled decision value separate from realized customer P&L even when ranking evidence is strong.
- WHY IT WORKED: Experiment Tasks **21 and 22** independently exposed evaluator/target dependence without discarding useful systems. Task 21 separated same-model monetized promotion ROI from independent held-out randomized ranking evidence. Task 22 separated inventory profit on censored observed sales from the latent-demand economics the system ultimately cares about.
- EXAMPLES:
  - Benchmark Task 21: `Himanshu-Laddhad/Nudge-Causal-Promotion-Intelligence-System@21783bf341d25c82fcff208735041637b2ceba10`.
  - Benchmark Task 22: `josephazar/FreshRetailnet-50k-Analysis@7dc8815e02c74e7dd6309ec307624a190d879659`.
- FAILURE MODES: treating held-out model metrics as realized economics; letting the chosen model score its own policy without independent outcome support; evaluating latent-demand decisions only against stockout-censored sales; assuming a nominal quantile label proves calibrated service level.
- NEXT IMPROVEMENT: apply the method to pricing, outage-risk, warehouse optimization and other decision engines where the easiest available score is a proxy for the buyer's actual money or service outcome.


## Empirical attribution rule
- Every prospective use of a search skill must append a record to `intelligence/search_runs.jsonl` using that skill's stable `STRAT:...` ID.
- Record the reusable query family separately from literal query text.
- Record candidate count, deep-inspection count, retained count and MASTER promotions when actually observed; never backfill guessed denominators.
- Retrospective examples remain useful qualitative evidence but do not enter yield denominators unless the original run counts are recoverable.
- Strategy promotion/retirement is outcome-driven and sample-gated; see `intelligence/README.md` and `intelligence/LEARNING_REPORT.md`.


## Search-run v2 fields
When a skill is used prospectively, the resulting `intelligence/search_runs.jsonl` event should capture:
- `schema_version: 2`;
- strategy ID and reusable query family;
- literal search surfaces and queries;
- candidate, deep-inspection, retention and MASTER-promotion counts;
- candidate dispositions using standardized reason codes when practical;
- created/strengthened capability IDs and affected experiment IDs;
- whether a recall-rescue pass was used;
- stop reason;
- optional elapsed minutes and tool-call count.

Before deep-inspecting a candidate that looks familiar, use `tools/ti_lookup.py` or equivalent ledger search. Reinspection is justified by a new revision, contradictory evidence, a new capability hypothesis or a named experiment gap—not merely rediscovery.

The adaptive policy may allocate more research to promising strategies, but it must preserve exploration and must not treat recent runs without outcomes as failures.


## Search-run v3 measurement contract

Every new prospective hunt should use `schema_version: 3`.

- Keep the stable `STRAT:...` strategy ID.
- Assign a reusable `QF:...` query-family ID for the underlying search hypothesis; literal queries remain separate evidence.
- Record all search surfaces actually used.
- Record candidate, deep-inspection, retained and MASTER denominators.
- For every inspected candidate, use `reason_code_standard` from `intelligence/reason_codes.json` plus a precise `reason_detail`.
- Record capability and experiment deltas explicitly.
- Preserve no-find runs: they are legitimate denominator evidence when the search was genuinely executed.
- Do not treat fractional outcome attribution as causal proof; it exists to prevent double-counting realized value across multi-origin discoveries.


## Search-run v4 normalized measurement contract

Every new prospective search should use `schema_version: 4`.

- Keep the exact literal `queries`.
- Persist the reusable `query_family` and canonical `query_family_id`.
- Assign one primary controlled `search_objective_id` from `intelligence/search_objectives.json`.
- Record every search surface actually used; reporting will normalize surface labels into stable families without deleting the exact labels.
- For every inspected candidate, use `reason_code_standard` from `intelligence/reason_codes.json` and preserve the evidence-bearing explanation in `reason_detail`.
- Record denominators even for no-find runs; a bounded no-find is valid evidence.
- Do not fabricate historical SHAs or search counts to reduce revision/measurement debt.
- Keep objective, query family and strategy distinct: the objective is *what uncertainty you are trying to reduce*; the QF is *the concrete search hypothesis*; the strategy is *how you search/verify it*.

### Matched benchmark conditions

When `measurement_quality: "benchmark"` under V4:
- use only frozen task text from `benchmark/BENCHMARK_TASKS.md`;
- do not read `BENCHMARK_GOLD.md` before freezing the result;
- record `benchmark_task_ids`, `evaluation_set_id` and `comparison_group_id`;
- keep sibling strategy conditions independent until frozen;
- no-find and correct-reject results are valid outcomes;
- matched benchmark evidence improves strategy comparison but does not substitute for realized customer/engineering outcomes.
