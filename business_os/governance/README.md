# Upgrade 7 — Runtime Governance

Status: **IMPLEMENTED**

This is the authority boundary between an agent wanting to act and a tool
actually being permitted to act.

The engine is default-deny. Roles need an explicit grant for an exact
tool/action pair, and request risk cannot exceed the grant.

Risk classes are READ, WRITE_LOW, CONSEQUENTIAL and DESTRUCTIVE.
CONSEQUENTIAL and DESTRUCTIVE actions can never be auto-approved: they require
a human approval bound to one exact request hash. Approvals are single-use.

Paid actions can be attached to named budgets. Estimated cost is checked before
authorization and actual spend is recorded separately without allowing the
limit to be crossed.

A global kill switch overrides every grant, approval and budget. When enabled,
all actions, including reads, are denied.

Every authorization attempt creates an append-only audit row containing the
exact request hash, role, tool/action, risk, budget, decision and reason.

This independently implements the core runtime-control requirements identified
in Hunter's preloop research: permissions, budgets, approvals, audit and an
emergency stop.
