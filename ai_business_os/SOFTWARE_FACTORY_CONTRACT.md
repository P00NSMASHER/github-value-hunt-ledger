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