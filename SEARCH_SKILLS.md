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
