# Carrier Action Workflow

The Carrier Action Workflow removes manual re-keying between proof-bound recovery claims and the existing External Action Authorization control.

## Proposal generation

Confirmed recovery claims are grouped deterministically by:

- carrier / payer;
- customer / payee;
- currency.

Each proposal binds:

- recovery-claim batch hash;
- truth hash;
- buyer-review batch hash;
- exact claim IDs;
- exact finding IDs;
- finding proof hashes;
- buyer review hashes;
- total claim amount;
- incumbent/fee-disqualified claim count and amount;
- carrier, customer/payee and currency.

Two claims for the same carrier and currency but different customer/payee identities **must not** share a proposal.

Creating a proposal does not authorize contact or execute an action.

## Separate buyer authorization

A proposal can be passed to `authorize_carrier_action_proposal` only after a separate approval supplies:

- exact proposal hash;
- action type;
- recipient/routing reference hash;
- exact action-payload hash;
- buyer approver role;
- issue and expiry dates;
- optional authorized amount not exceeding the proposal total.

The wrapper re-verifies the recovery-claim batch, buyer-review linkage and canonical proposal before calling the existing External Action Authorization control.

External authorization is now bound to **carrier + customer/payee + currency + exact finding set + exact payload + exact recipient + dollar ceiling + validity window**.

It still does not authorize:

- money movement;
- settlement acceptance;
- account changes;
- credential use;
- general carrier/vendor contact;
- automatic execution.

No message is sent by this workflow.


## Canonical payload handoff

After a proposal is selected, `carrier_action_payload.py` derives the exact carrier-facing subject/body and payload hash from the proposal and recovery claims. Separate buyer approval must bind that exact payload hash before the authorization wrapper accepts it. The payload remains a preview and is never sent by this workflow.


## Execution proof handoff

After authorization, `carrier_action_execution.py` can create a pre-send intent with a stable idempotency key and later record external FAILED/SUBMITTED/DELIVERED evidence. Authorization is never treated as proof that an action was actually sent.
