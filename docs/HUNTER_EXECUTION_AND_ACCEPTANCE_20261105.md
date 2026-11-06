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

Recovery-dispatch run `42168125358` subsequently exercised the provider-visible identity `HUNTER-01 slot=2026-11-06T02:07:00Z` against protected-main commit `cc5a48f5f80d36f14a53817435e545a3d42e0ed4`. Its scout, candidate-inspection and proposal-submission jobs succeeded. Artifact `13480012090` (`hunter-evidence-HUNTER-01-42168125358-1`, SHA-256 `32b6d31ea8eb53224c90bf38667c9ce4e8b69af41358e256cad9b79de51947f3`) and artifact `13479364209` (`hunter-inspection-42168125358-1`, SHA-256 `4c51bd6dd3297ca56112331f0f774e9c56b459b0f1bfd944fb8de93e3b4e5264`) were retained. This closes the recovery-dispatch `scheduled_slot` observation for that worker/slot only.

Native schedule run `42194306963` then executed on exact protected-main commit `baaa486e9a69ad202fecfe9c6d8cf798f8e72f73` with provider-visible title `Hunter 15 2,14 * * * slot=native`. The job log independently binds cron `15 2,14 * * *` to `HUNTER-02`; scout, candidate-inspection and proposal-submission jobs succeeded. Artifact `13491456838` (`hunter-evidence-HUNTER-02-42194306963-1`, SHA-256 `7e812d63b57bcb4172fd1eb0f373ff8e302adc445bbf15826a814f27e784eb5e`) and artifact `13491286713` (`hunter-inspection-42194306963-1`, SHA-256 `14491a41106cc71148c880420fe8ba70e5aa630546ec72e6df9256d2bec43b8c`) were retained. This closes one native schedule-event observation with source-backed worker resolution; the title's `15` is the cron minute, not the worker number.\n\nCreation of the integrator-specific artifact remains unverified. Its step was correctly skipped in the HUNTER-01 recovery/source-push runs and this HUNTER-02 native run. Cancelled or differently routed runs receive no execution or delivery credit. The remaining integrator observation must not be inferred from green CI, successful worker runs or the merged workflow definition.

## Existing governed adaptive-learning runtime
Protected-main `benchmark/SCOREBOARD.md` now freezes all **50/50 matched tasks and 100 independently scored arms** with the final 50-task conclusion. The benchmark has no remaining task gaps. Completion grants no activation authority: the adaptive Hunter runtime remains **PAUSED / AWAITING_EXPLICIT_USER_APPROVAL**, and no generated READY, activation or CLAIM may be forged. This GitHub source-inspection path is not a replacement for the separately governed worker runtime.

To verify real execution, inspect the applicable post-merge workflow run and independently retrieve its job/artifact. Green CI or local tests alone are not sufficient evidence.
