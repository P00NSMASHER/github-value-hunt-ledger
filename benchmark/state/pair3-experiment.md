# Pair 3 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 16: For broad operational-engine targets, code-level capability conjunctions outperformed title/README search. The useful conjunction was constrained solver (`OR-Tools`/`CP-SAT`) + domain legality (`FAR117`/duty) + passenger/rebooking terms + replay/determinism. This surfaced `mizuharaa/olus`, while obvious “airline disruption optimizer” searches mostly surfaced narrower aircraft-only or demo systems.
- Task 16: Deterministic-replay engineering is a high-signal maturity discriminator when it is evidenced by both an explicit nondeterminism inventory and golden tests that cross a persistence/restart boundary. `olus` pins mutable event fields, captured weather, RNG inputs and CP-SAT replay settings, then tests byte-identical replay output excluding documented wall-clock timing.
- Task 16: README integration claims must be traced into the exact optimization model. `olus` claims FAR117 hard constraints in its main recovery optimizer, but source inspection showed the main aircraft CP-SAT model audits legality post-solve; hard FAR117 filtering exists in the separate crew-overbooking CP-SAT. This distinction prevented an inflated evaluation.
- Task 17: Capability-conjunction search transferred successfully from airline recovery to financial reconciliation. The useful conjunction was exact Decimal money + canonical multi-source normalization + fee/refund semantics + split-group matching + idempotency/dedupe + explicit ambiguity/exception states. This surfaced and validated `Etherlabs-dev/multi-processor-reconciliation`, while generic reconciliation searches produced dashboards, assessments, and narrower explainable matchers missing part of the requested capability set.
- Task 17: For money-bearing engines, verify the same invariant at three layers when available: algorithm-level tests, persistence/database constraints, and CI/benchmark execution. In `multi-processor-reconciliation`, Python tests cover matching semantics, PostgreSQL rejects duplicate raw events and unbalanced journals, and the exact head revision has a successful CI run that executes schema/seed, pytest, n8n import, workflow validation and a synthetic reconciliation benchmark.
- Task 17: “Reference implementation” should not be treated as an automatic reject or as production proof. The repository explicitly disclaims verified client deployment, but source/tests/schema/CI substantiate a real engine. The correct calibration was STRONG for benchmark capability and NOT verified for enterprise scale.

## Failed search patterns
- Generic repository-title queries such as “airline disruption optimizer/recovery” produced many aircraft-only projects, UI demos, or agent wrappers without the requested crew legality + passenger recovery + uncertainty + replay combination.
- Research-paper repositories can look unusually deep but must be checked for the actual imported implementation. `kahyakursat1-cloud/hybrid-cpsat-qiga-airline-recovery` had strong paper/experiment claims, but inspected experiment scripts imported `src.*` modules that were absent from the repository tree, so it was not accepted as the engine result.
- Task 17: Generic “reconciliation platform/engine” search produced many invoice dashboards, assessment projects, and accounting demos with duplicate/unmatched labels but no fee-aware + refund + split-settlement semantics backed by tests.
- Task 17: Explainability/property-testing alone is not enough for this benchmark. `dylanpulver/recon` is technically disciplined but explicitly limits grouping to many-to-one and does not supply the full refund/fee/multi-source semantics requested.

## Useful terminology / signatures
- Operational replay: `NONDETERMINISM.md`, `golden replay`, `deterministic=True`, `num_search_workers=1`, fixed `random_seed`, frozen weather/input snapshots, persistence/restart equality.
- Airline recovery conjunction: `CrewLegalityEngine`, `FAR117`, `crew_overbooking`, `rebooking`, `CP-SAT`, `uncertain horizon`, `regret`, `cascade predictor`.
- Red-team signature: compare README phrase “hard constraint” against actual `model.add(...)` / candidate-variable construction and solution extraction.
- Financial reconciliation conjunction: `Decimal`, `fee_aware`, `partial_refund`, `split_payment`, `ambiguous_candidates`, `ambiguous_split`, `duplicate_input`, `idempotency_key`, `CursorConflict`, `recon_exceptions`.
- Money-engine verification signature: successful CI at exact head revision + database invariant tests + deterministic/synthetic benchmark result, not README business-outcome claims.

## Candidate search skills
### Capability-Conjunction Search + Claim Tracing — evidence 2/2; eligible for promotion
WHEN TO USE: Broad systems benchmarks where the target is defined by several rare co-occurring capabilities and repository names are likely generic.
PROCEDURE: Search code for 3–4 rare implementation signatures from different requirement families; deep-inspect the candidate; trace every integration-critical README claim into solver/source/tests; inspect persistence/CI evidence when the domain has money, safety, compliance or reproducibility boundaries.
WHY IT WORKED: Task 16 found a 1-star generic-named airline recovery engine with the requested capability spread and exposed a material README overstatement. Task 17 independently transferred the same method to finance, where a conjunction of Decimal + refund/fee + split + dedupe + exception semantics surfaced a low-attention exact-fit reconciliation engine and red-team review preserved its bounded-split/non-production caveats.
STATUS: Evidence threshold is now satisfied on two distinct benchmark tasks. Eligible for SEARCH_SKILLS promotion, but not promoted in this run; leave central skill-file changes to a subsequent explicit promotion step or Hunt 15 review.

### Three-Layer Money-Invariant Verification — evidence 1/2
WHEN TO USE: Financial/reconciliation/billing systems where a README can easily overstate reliability.
PROCEDURE: Verify each critical money invariant in (1) executable algorithm tests, (2) persistence/database constraints or idempotency boundaries, and (3) CI/benchmark execution at the exact revision. Treat synthetic benchmarks as capability evidence, not production-scale evidence.
WHY IT WORKED: Task 17 separated a genuinely implemented reconciliation engine from architecture-only financial demos and prevented production-scale overclaiming.
STATUS: Do not promote to SEARCH_SKILLS.md yet. Requires success on at least one additional distinct benchmark task or Hunt 15 approval.
