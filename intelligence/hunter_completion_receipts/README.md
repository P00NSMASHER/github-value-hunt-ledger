# Hunter completion evidence (fail-closed)

The public scouting digest and read-only source inspection artifacts are **not completed
work**. They cannot create activation packets, claim legacy assignments, or claim
integration, deployment, customer revenue, trading performance, novel discoveries,
or engineering time saved.

This directory is intentionally empty of accepted JSON receipts until a real target
integration exists. Only files ending in .json are evaluated.

For a technical work item to use status COMPLETE, submit a bounded JSON receipt with:

- schema_version: 1
- status: COMPLETE
- worker_id: HUNTER-01 through HUNTER-14
- source_repository and source_exact_revision: public owner/repo and full 40-character SHA
- target_repository: an authorized P00NSMASHER repo
- target_commit_sha: full immutable merged commit SHA
- merged_pr_number: PR that produced precisely target_commit_sha
- test_run_id and verifier_run_id: **different** GitHub Actions runs
- required_test_steps: names of real passing steps in the target test run
- external_outcome: UNKNOWN (or omitted)

The required repository release gate invokes tools/hunter_completion_evidence.py
for every file and independently queries the live GitHub API. It fails closed if
the PR did not actually merge to the specified commit, if either run lacks a
successful exact-head conclusion, if named tests did not pass, or if the two
workflows are not distinct. The verifier accepts code integration evidence only;
it never converts CI success into an external commercial or scientific outcome.

Claiming verified revenue, saved engineering time, trading profitability, social
conversions, or scientific novelty needs **separate provider/source readbacks**
and domain-specific independent acceptance, not a fabricated numeric field.
Such numeric claims are rejected by this gate.

The original adaptive-learning activation policy remains paused until its frozen
benchmark and approval gates are genuinely satisfied. This source-inspection
lane is independent, read-only, and cannot bypass that pause.

**Fleet schedule invariant:** The original Active Project Technology Scouts
workflow retains the same fifteen cron definitions. This additional inspection
workflow is event-driven and creates no new cron trigger.
