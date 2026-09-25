# CEO Command Center Operator Contract

## Purpose

The CEO Command Center is the human-facing orchestration layer for the canonical AI Business OS.
It combines live production status, portfolio planning, natural-language objective intake, and the
existing exact-request approval queue.

It is deliberately **not** an execution bypass.

## Normal-language objective flow

1. A HUMAN supplies an objective in ordinary language.
2. The command center resolves the current production schema and active agent fleet.
3. It converts the objective into a structured proposal containing:
   - target agent role and current active agent ID;
   - goal type and priority;
   - referenced business identities when detectable;
   - possible consequential action class;
   - evidence and governance constraints;
   - a SHA-256 objective hash.
4. Proposal creation is read-only.
5. A HUMAN must activate that exact proposal hash.
6. Activation creates only a `PENDING` internal `agent_goals` record.

Tampering with any proposal field after hashing invalidates activation.

## Consequential actions

Objective activation is not permission to perform an external action.

The command center marks likely action classes such as:

- `EXTERNAL_WRITE`
- `PRODUCTION_CHANGE`
- `MONEY_MOVEMENT`
- `DESTRUCTIVE`

Those actions remain governed by the existing action/approval system.

## Approval flow

The command center may let a HUMAN decide a pending production approval only when:

- the exact `request_key` resolves to one current PENDING request;
- the supplied `intent_hash` matches that row;
- the human principal is explicit;
- the decision is APPROVE or REJECT;
- a non-empty reason is supplied.

The actual state transition uses the existing
`ai_business_os_prod.approval_decide(...)` procedure.

The command center does **not** call `approval_consume`, manufacture execution receipts, or execute
the approved external action. Approval consumption remains the responsibility of the governed
executor after a real execution receipt exists.

## Status surface

The operator dashboard combines:

- live schema fingerprint;
- current command-center snapshot;
- canonical businesses;
- pending approvals;
- deterministic portfolio planning output.

No live private payload is copied into the public repository.

## Authority boundary

The operator may:

- read production status;
- create hashed proposals;
- create a PENDING internal goal after explicit human activation;
- record an exact human approval decision through the existing production procedure.

It may not:

- start an objective automatically;
- claim Hunter leases;
- send email or messages;
- open or merge pull requests;
- deploy code;
- move money;
- delete resources;
- change governance policy;
- consume approvals;
- fabricate execution receipts.

All later consequential work remains subject to the existing governance, verification, Hunter, and
software-factory contracts.
