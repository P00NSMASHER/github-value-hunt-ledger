# Governed Autonomous Software Factory — Step 7

The AI Business OS now converts an approved engineering goal into a restart-safe software work
lifecycle while preserving the verification and authority boundaries established in Steps 2 and 6.

## Lifecycle

QUEUED -> RUNNING in an isolated workspace/attempt branch -> VERIFYING through the independent
Step-2 auditor -> READY_FOR_PR -> Step-6 exact PR-create authorization -> PR_OPEN -> Step-6
PRODUCTION_CHANGE merge authorization -> MERGED + manager accepts goal COMPLETE.

Failed implementation or audit attempts retry in fresh workspaces until the configured retry limit
is exhausted, after which the item becomes BLOCKED.

## Hard invariants

1. A factory item must bind to an existing manager-authored Step-2 verification contract.
2. Only the contract-bound executor may claim implementation work.
3. Every attempt receives a unique workspace; every retry receives a new attempt branch.
4. Active implementation attempts use leases and can be reclaimed after worker/process failure.
5. Executor leases stop governing the job once independent audit begins.
6. Submission evidence binds repository, issue, workspace, branch, attempt, commit, tests, and artifacts.
7. READY_FOR_PR requires the exact current submission to receive an independent APPROVED audit.
8. A rejected audit requeues into a fresh implementation attempt or blocks at the retry limit.
9. PR creation requires a persisted Step-6 AUTHORIZED github.pr.create request.
10. The governance request parameters must exactly match work item, repository, branch, base, title, submission hash, and audit hash.
11. A governance authorization can be bound to the factory only once.
12. PR merge requires a separate persisted PRODUCTION_CHANGE authorization for the exact PR, head SHA, merge method, and audit hash.
13. Production merge therefore cannot bypass Step-6 mandatory human approval.
14. Step-6 global/per-agent kill switches can prevent release authorization.
15. The engineering goal becomes COMPLETE only after the governed merge is recorded.
16. Factory lifecycle events are content-addressed and retained as an audit trail.

## Execution boundary

This module is the control/orchestration layer. It does not store credentials or make ungoverned
network calls. A GitHub/coding executor may perform the authorized branch, PR, or merge operation
externally, but the factory accepts the handoff only when the exact persisted governance request
matches the intended operation.

That separation lets more coding work become autonomous without turning repository access into
unrestricted production authority.
## RETALLY Group — no mandatory human reviews

**RETALLY internal source, code and quality reviews use automated evidence-based
verification.** No peer reviewer, external reviewer, owner code-review signature,
or owner artifact-quality sign-off is a required stage for current or future
RETALLY Group work. The RETALLY public catalog and validator enforce that
policy using `internal_human_review_required=false`,
`internal_quality_gate=AUTOMATED_EVIDENCE_QA`, and an
`AUTOMATED_QUALITY_GATE` workflow role. Required checks must bind to an exact
candidate revision/artifact, fail closed on unknown or stale evidence, and record
material defects; no system may claim a human reviewed work that nobody reviewed.

**Review is not authorization.** This policy does not change the implemented
Step-6 mandatory authorization rules for external writes, production changes,
money movements, destructive operations, or policy changes. An exact, authenticated
authorization may still be required to execute one of those actions. It is not
a second person or a discretionary code-quality review. Likewise protected-main
status checks, independent automated auditors, kill switches and budgets remain
enforced. No assistant or bot may forge approval receipts or skip a required
authorization, nor does a passing code check authenticate customer, Stripe,
settlement, source ownership or delivery evidence.

Legal, regulatory and contractual requirements for a qualified human professional
are outside this internal-review policy. If required evidence or external
authorization is unavailable, preserve the relevant hold rather than inventing
or silently granting permission.
