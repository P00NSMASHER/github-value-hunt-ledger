# Independent Verification Contract — Step 2

The AI Business OS uses three separate roles for consequential task completion:

- **Manager** — defines the goal and acceptance criteria, then accepts independently verified work.
- **Executor** — performs the work and submits concrete evidence.
- **Auditor** — independently checks every criterion and records PASS, FAIL, or UNKNOWN.

## Hard invariants

1. Manager, executor, and auditor must be three distinct agent identities.
2. The executor owns the goal but cannot approve its own work.
3. Every acceptance criterion must receive an explicit audit verdict.
4. A missing or UNKNOWN required criterion is non-passing.
5. Failed required criteria return the goal to ACTIVE for revision.
6. Approved audit reports are SHA-256 bound to their exact criterion results and evidence.
7. The persistent runtime refuses VERIFYING -> COMPLETE without an approved verification contract.
8. The manager may accept only the exact approved contract bound to that goal.
9. Optional criteria may remain non-passing without blocking completion; required criteria may not.
10. Audit evidence is preserved in the append-only agent event history.

This layer verifies task completion. It does not yet grant runtime permissions, money movement,
production deployment, outbound messaging, or self-improvement promotion authority.
