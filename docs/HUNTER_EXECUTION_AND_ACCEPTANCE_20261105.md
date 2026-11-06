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

## Schedule/recovery identity delivery boundary

PR #1059 merged schedule/recovery slot labeling and the integrator-receipt path at commit `30212c153d0d4329802ed9cdba44ea8d33e964e0`. Its exact-head Active Scout Scope Guard, main-only policy and repository release jobs passed. Post-merge run `42154864214` then exercised the `SOURCE_PUSH` path on that exact main revision: scout, tests, candidate inspection and delivery-acceptance checks succeeded, and artifacts `hunter-evidence-HUNTER-01-42154864214-1` plus `hunter-inspection-42154864214-1` were retained.

This proves the merged source-push smoke path and its source-inspection receipt. It does **not** yet prove a native schedule-event invocation using the new provider-visible slot label, a recovery-dispatch invocation carrying `scheduled_slot`, or creation of the integrator-specific artifact; that integrator step was correctly skipped in the HUNTER-01 source-push run. Those three observations remain pending and must not be inferred from green CI or the merged workflow definition.

## Existing governed adaptive-learning runtime
Protected-main `benchmark/SCOREBOARD.md` now freezes all **50/50 matched tasks and 100 independently scored arms** with the final 50-task conclusion. The benchmark has no remaining task gaps. Completion grants no activation authority: the adaptive Hunter runtime remains **PAUSED / AWAITING_EXPLICIT_USER_APPROVAL**, and no generated READY, activation or CLAIM may be forged. This GitHub source-inspection path is not a replacement for the separately governed worker runtime.

To verify real execution, inspect the applicable post-merge workflow run and independently retrieve its job/artifact. Green CI or local tests alone are not sufficient evidence.
