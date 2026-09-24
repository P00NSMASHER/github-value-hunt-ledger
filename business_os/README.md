# AI Business OS

A governed control plane for persistent AI workers that can research, build, sell, measure outcomes and improve while keeping consequential actions behind explicit verification and permission boundaries.

This lives inside the Hunter ledger initially so it inherits version history, CI and the evidence discipline already developed there. It contains no credentials or customer secrets.

## Nine-upgrade implementation sequence

1. ✅ **Persistent agents** — durable goals, leases, heartbeat and crash recovery.
2. ✅ **Independent Auditor brain** — Manager → Executor → Auditor acceptance contracts.
3. ✅ **Verifier-gated self-improvement** — candidate skills require held-out evidence before promotion.
4. ✅ **Value-weighted memory** — retrieval uses relevance × observed value × confidence × recency.
5. ✅ **Knowledge graph** — business/repo/capability/customer/outcome relationship model.
6. ✅ **Entity canonicalization** — merge aliases/duplicates while retaining provenance.
7. ✅ **Runtime governance** — tool permissions, budgets, approvals, audit and kill switch.
8. ✅ **Autonomous software factory** — issue → isolated implementation → tests → PR.
9. Evidence/truth engine — explicit proof obligations and next-best-evidence actions.

## Completion policy

No upgrade is marked complete merely because documentation exists. Each upgrade must have a concrete implementation, regression tests or deterministic validation, and a failure mode that prevents false success.

Current completed upgrades on this branch: **8/9**.
