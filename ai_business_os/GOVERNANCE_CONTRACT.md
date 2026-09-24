# Runtime Governance Contract — Step 6

The AI Business OS now has a fail-closed control plane between an agent's intent and any real tool
execution. This layer authorizes actions; it does not execute them.

## Action classes

- READ
- INTERNAL_WRITE
- EXTERNAL_WRITE
- PRODUCTION_CHANGE
- MONEY_MOVEMENT
- DESTRUCTIVE
- POLICY_CHANGE

High-consequence classes require human approval by default.

## Authorization path

agent intent
-> exact immutable action request
-> policy/class/allowlist/denylist check
-> kill-switch check
-> rolling budget check
-> optional human approval
-> final recheck
-> single-use ALLOW receipt
-> external tool executor

## Hard invariants

1. Agents with no policy fail closed.
2. Governance policies can only be changed through an authenticated HUMAN principal boundary.
3. Global and per-agent kill switches override all normal permissions, including READ.
4. Allowed action classes never override an explicit action-key denylist.
5. A non-empty action allowlist blocks unknown action keys.
6. External writes, production changes, money movement, destructive actions, and policy changes can be configured to require human approval.
7. High-consequence approval tickets must come from a HUMAN principal.
8. Approval is bound to one exact request/intent hash; changing target, amount, or parameters requires a new approval.
9. Approval tickets expire and are single-use.
10. Authorized requests are terminal and cannot be replayed to consume budgets or execute twice.
11. Rolling action-count, cost-unit, and money-movement budgets are checked before final authorization.
12. Kill switches and budgets are rechecked immediately before authorization.
13. Every ALLOW, DENY, and REQUIRE_APPROVAL decision creates a SHA-256-bound audit receipt.
14. Policy changes are versioned and content-addressed.
15. This module treats HUMAN identity as a trusted caller assertion; production deployment must bind it to an authenticated identity provider/session rather than user-supplied text.

## Default philosophy

Broad read/analysis access can be safe and productive. Consequential writes should have narrower
permissions, bounded budgets, and stronger approval requirements. More capability should come from
better tools and evidence, not from removing all controls.
