# Repository Release Gate

This workflow is the repository-level release readiness check.

It intentionally runs on **every pull request** and on **every push to main**.
Subsystem-specific workflows may still provide faster local feedback, but none of
them replaces this gate.

Required independent lanes:

1. canonical `ai_business_os` compilation and regression suite;
2. full Freight regression suite plus pilot rights-evidence consistency;
3. full RecoveryWorks regression suite;
4. Technology Intelligence tests plus deterministic ledger validation.

The final `release-gate` job succeeds only if all four lanes succeed.

## Security invariants

- workflow permissions are read-only;
- all third-party GitHub Actions are pinned to exact 40-hex revisions;
- the release gate does not persist generated intelligence;
- the release gate does not deploy products, send messages, move money, or mutate providers;
- the gate contains no secret-dependent path, so pull-request validation remains deterministic.

A production tag or release should not be treated as release-ready unless this
workflow passed for the exact commit.
