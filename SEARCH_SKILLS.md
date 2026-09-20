# SEARCH_SKILLS

Shared reusable discovery methods for the GitHub Value Hunt. Hunters should read this file before searching, reuse skills when appropriate, and append only methods that have produced evidence-backed value. Skills are search procedures, not conclusions; validate every candidate independently.

## Skill schema
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
- WHY IT WORKED: Benchmark Experiment Tasks **30 and 31** independently benefited from this procedure. Task 30 separated a real fail-closed manager/executor/auditor completion gate from generic checkpointing. Task 31 transferred the same habit to issue-driven coding orchestration by inspecting tracker reconciliation, retry state, workspace boundaries and the validation-to-review/merge transition instead of trusting orchestration marketing.
- EXAMPLES:
  - Benchmark Task 30: `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65`
  - Benchmark Task 31: `openai/symphony@be10a1b79df723d6d7612b5651c8522704dafb2e`
- FAILURE MODES:
  - reviewer prompts exist but the executor can still self-certify completion;
  - validation is advisory and does not gate state transition;
  - retry/backoff state disappears on restart and is mistaken for durable recovery;
  - an "isolated workspace" is overclaimed as a security sandbox;
  - the verifier shares mutable artifacts or correlated assumptions with the executor and independence is overstated.
- NEXT IMPROVEMENT: apply this procedure outside coding-agent systems to scientific campaign authorities, billing/audit approval flows and other human-in-the-loop state machines; measure whether it predicts false-promotion reduction across later benchmark tasks.

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

## Ingestion invariant-triad intersection
- SKILL NAME: Ingestion invariant-triad intersection
- WHEN TO USE: Searching for a data-ingestion platform where connector breadth alone is insufficient and durable history plus source-health truth are commercially important.
- PROCEDURE:
  1. Define three independent axes before searching: **source topology** (multiple heterogeneous provider families), **historical durability** (first/last seen, append/version history, deterministic field diffs), and **run truth** (success/partial/failure or equivalent fail-closed source-health semantics).
  2. Search each axis separately using concrete provider names, table/model names, diff/version fields and run-status symbols rather than product-category keywords.
  3. Intersect candidates only after each axis has independent code evidence; a broad connector project without history, or a history store without run truth, remains a component.
  4. Trace the actual diff/version algorithm and identity key. Do not credit fields named `history` or `changes` until the mutation/comparison path is inspected.
  5. Red-team false-green collection paths: unexpected response shapes, zero-row success, stale cache, skipped files, identity churn and partial errors that can masquerade as “no change.”
  6. Require domain-semantic regression evidence where money/meaningful decisions depend on mapped fields, not merely syntactic schema validation.
- WHY IT WORKED: Benchmark Experiment Tasks **37 and 38** independently validated the method. Task 37 converged on PermitBuild by intersecting municipal connector families, immutable permit versions/diffs and fee-vs-valuation semantic QA. Task 38 transferred the same triad to government acquisition forecasts and found Curatore-v2's multi-source normalization, temporal history/diffs and explicit success/partial/failure orchestration while also surfacing an APFS false-green edge case.
- EXAMPLES:
  - Benchmark Task 37: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d`
  - Benchmark Task 38: `davidlarrimore/curatore-v2@d4e42ac14450a58f84035c31db11b0399713a653`
- FAILURE MODES:
  - counting connector count as data quality;
  - mutable upserts presented as audit history;
  - history arrays that do not expose deterministic old/new semantics;
  - `success` emitted on unexpected or empty source responses;
  - unstable identity keys splitting one evolving record into unrelated rows;
  - schema tests that miss fee/value/status/date semantic swaps.
- NEXT IMPROVEMENT: apply the triad to a non-government ingestion domain such as billing feeds or scientific instruments and measure whether it reduces false promotion versus broad “data platform” search.
