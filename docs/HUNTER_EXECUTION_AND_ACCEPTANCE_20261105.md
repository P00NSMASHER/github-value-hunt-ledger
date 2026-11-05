# Hunter execution handoff: source inspection and independent delivery acceptance

The existing Active Project Technology Scouts workflow retains **all fifteen original cron expressions and role assignments**. A separate GitHub Actions job named candidate-inspection now follows a successful HUNTER-01 through HUNTER-14 scout run, including the scoped push smoke test. The HUNTER-15 integrator remains a digest assembler; it does not inspect or execute upstream code. No extra timer, repository write, paid service, external account action, contact or deployment is authorized.

## Source-inspection evidence
The job uses a read-only token and the existing active-scope Hunter queue. It selects up to three top-ranked candidates. For an eligible source, it resolves the exact Git commit, immutable tree, one implementation file and one test file, checks SHA-1 Git blob identity and captures the file SHA-256 hashes in a 7-day GitHub Actions artifact named hunter-inspection-RUNID-ATTEMPT.

Important status distinctions:

- SOURCE_INSPECTED_NOT_TESTED: exact upstream file contents read and integrity-checked; no untrusted code executed.
- NO_CANDIDATES: queue has no proposed source.
- NO_SOURCE_VERIFIED: no eligible source/test pair passed bounded readback.
- INVALID_QUEUE_BINDING, INVALID_QUEUE_STRUCTURE, STALE_QUEUE_SCOPE, MISSING_QUEUE: integrity failures; inspection job fails closed.

Published SPDX metadata is never treated as clearance for actual source, datasets or assets. Source-inspected means neither test execution nor production integration. GitHub Actions run and artifact identifiers are the external proof that this read-only path actually ran. No V16 activation or assignment claim is created.

## Completed work acceptance
File-based delivery claims, if any, are placed in intelligence/hunter_delivery_receipts/ with .json extension. They must supply:

- schema_version: 1
- worker_id: exact current-scope HUNTER identifier
- target_repository: exactly the assigned target repository
- target_main_sha: full current Git SHA-1 on the target main branch
- merged_pr_number: real merged PR number with at least one changed file
- independent_ci_run_id: an actual successful push-to-main Actions run bound to that SHA
- claimed_outcome: CI_VERIFIED_TARGET_CHANGE

The independent acceptance validator reads the live target main branch, merged PR, and CI run using GitHub REST endpoints. An incorrect worker, obsolete head, failed CI, unmerged PR, duplicate delivery or inflated outcome fails the check; it cannot be silently counted as complete. If no delivery receipts exist, accepted completion remains zero. A passing receipt establishes only a **CI-verified changed target branch**. It does not prove that the discovered candidate was reused, deployed, adopted, profitable, novel or a time saver. Those require their own independently inspectable external evidence and must remain UNKNOWN until checked.

CLI for code checks: python -m unittest tests.test_hunter_source_inspection tests.test_hunter_delivery_acceptance -v

CLI for proof readback: python -m tools.hunter_delivery_acceptance --output hunter-delivery-acceptance.json

## Existing governed adaptive-learning runtime
This change intentionally leaves intelligence/hunter_runtime_policy.json and the V16 benchmark/activation system untouched. Its restart readiness file still records frozen benchmark task gaps (06, 07 and 08). No generated READY/activation/CLAIM is forged. Those original workers remain governed by existing policy; this additional GitHub source-inspection job is not a replacement for the benchmark-gated human/AI worker runtime.

To verify real execution, inspect the post-merge workflow run and independently retrieve its candidate-inspection job/artifact. Green CI or local tests alone are not sufficient evidence.
