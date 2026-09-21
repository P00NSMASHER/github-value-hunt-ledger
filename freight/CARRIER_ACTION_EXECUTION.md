# Carrier Action Execution Proof

Freight Recovery separates **authorization**, **pre-send preparation**, **submission evidence**, **delivery evidence**, and **settlement/recovery**.

This module does not send anything itself.

## Pre-send execution intent

An active External Action Authorization plus its exact canonical payload can produce a deterministic execution intent.

The intent binds:

- authorization hash;
- carrier-action proposal hash;
- canonical payload hash;
- recipient/routing reference hash;
- carrier + customer/payee + currency;
- exact finding set and requested amount;
- prepared timestamp;
- exact subject/body;
- a stable execution/idempotency key.

The execution key excludes preparation time, so rebuilding the same authorized action later produces the same idempotency key while a new intent proof reflects the new preparation timestamp. A sender integration should use this key as its idempotency token when supported.

Preparing an intent does **not** mean the action was submitted or delivered.

## Execution evidence

Post-attempt evidence records one of three outcomes:

- **FAILED** — the attempt did not submit the action.
- **SUBMITTED** — an external system accepted/submitted the action, but delivery is not confirmed.
- **DELIVERED** — external evidence confirms delivery.

A receipt requires:

- the exact execution key;
- timezone-aware execution timestamp;
- execution channel;
- external reference hash;
- external evidence-source hash;
- executor role.

The evidence source must be external to the existing authorization/proposal/payload proof objects.

## Fail-closed rules

Before recording a receipt, the product:

1. re-verifies the canonical payload from recovery claims;
2. re-verifies the execution intent;
3. re-checks the authorization at the actual execution date;
4. applies revocations and expiry;
5. requires execution time to be after preparation;
6. validates the external evidence hashes;
7. derives submitted/delivered booleans from the outcome rather than trusting caller booleans.

Receipts are self-verifying. Execution history rejects multiple successful submitted/delivered receipts sharing one idempotency key.

Multiple FAILED attempt receipts may exist for the same idempotency key because no action was submitted.

## Claim boundary

A SUBMITTED receipt does not prove delivery.

A DELIVERED receipt does not prove:

- the carrier agreed with the claim;
- a credit was issued;
- money was received;
- settlement occurred;
- realized savings.

Those remain downstream settlement evidence states.


## Buyer/business-unit scope

Execution intents, idempotency keys and execution receipts are explicitly bound to the buyer and business unit from the External Action Authorization / Carrier Action Proposal. The same carrier/customer/payload facts in a different buyer or business unit produce a different execution key.

## Asynchronous delivery confirmation

Some channels can prove submission before they can prove delivery. A SUBMITTED execution receipt can therefore receive a later, separate delivery confirmation.

The delivery confirmation:

- references the exact execution key and submitted execution-receipt hash;
- must occur at or after the submission timestamp;
- carries a delivery reference hash and new external delivery-evidence hash;
- rejects reuse of the authorization/proposal/payload/submission evidence as delivery evidence;
- is self-verifying and tenant scoped;
- permits at most one delivery confirmation per execution key/submitted receipt in a validated history.

A FAILED execution cannot receive delivery confirmation. An execution receipt that already recorded DELIVERED does not get a second delivery receipt.

Delivery confirmation still does not prove settlement, credit issuance, cash receipt, recovery or realized savings.
