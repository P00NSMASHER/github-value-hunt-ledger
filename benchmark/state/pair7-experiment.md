# Pair 7 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 44: verifier quality is best judged at fail-open boundaries, not from “backup verified” prose. Source/tests that distinguish PASS vs FAIL vs SKIP vs UNKNOWN, and that explicitly refuse to turn missing evidence/environment faults into green success, provided high-signal evidence.
- Task 44: verify the exact operational depth independently of the SPEC/README. `pg_hardstorage` has a real scratch restore plus `pg_verifybackup`, but its current sandbox source explicitly says it does not boot PostgreSQL or run `pg_amcheck`/smoke SQL. Scoping the claim to code prevented an overpromotion.

## Failed search patterns
- Task 44: a broad GitHub repository search for `postgres restore verification pg_amcheck scratch backup recovery verifier` returned no candidates. Product/category phrases were too weak; direct code/protocol signatures and obscure-repository comparisons were materially more productive.

## Useful terminology / signatures
- Task 44: `verify --full`, `pg_verifybackup`, `ManifestCaptured`, `classifySkip`, `Passed/Skipped/UNKNOWN`, `checksum mismatch`, `backup_manifest`, `manifests_unverifiable`, `pickLatestBackup`, Docker/Firecracker sandbox, scratch restore, restore drill.
- Task 44: commit/test phrases around “fabricated skipped exit 0”, “fail open”, “bad bind-mount”, “remote DOCKER_HOST”, “permissions”, and “unverifiable latest” are useful anchors for evidence-verifier archaeology.

## Candidate search skills awaiting second-task confirmation
- FAIL-OPEN BOUNDARY ARCHAEOLOGY (1 validated task: #44): after finding a verifier/auditor, search source tests and commit history for prior bugs where missing evidence, ambiguous state, stale selection, or infrastructure faults were incorrectly treated as skip/success. Require explicit negative regression tests before STRONG. Promote to SEARCH_SKILLS only after success on a second distinct benchmark task or Integrator approval.
