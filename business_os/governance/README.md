# Upgrade 7 — Runtime Governance

The runtime governance layer is the permission and safety boundary between an
agent deciding what it wants to do and any external tool actually being called.

## Controls

- **Tool allowlists** use explicit patterns per agent.
- **Risk policies** decide `ALLOW`, `APPROVAL`, or `DENY` for each action class.
- **Daily and per-action budgets** are rechecked before authorization.
- **Independent approval** is required for configured consequential actions;
  the requesting agent cannot approve its own request.
- **Global and per-agent kill switches** dominate ordinary policy decisions.
- **Append-only audit events** record policy, requests, approvals, denials,
  authorizations, and kill-switch changes.

The default risk policy allows read and low-risk internal writes, requires
approval for external communication, production, financial and legal actions,
and denies destructive actions.

## Critical invariant

An approval is not a stale blank check. At approval time the control plane
rechecks the current kill switch, tool policy, per-action cap and remaining
daily budget before issuing an authorization receipt.
