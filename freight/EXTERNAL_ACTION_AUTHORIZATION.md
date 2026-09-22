# Freight Recovery — External Action Authorization

Updated: 2026-09-21

This control converts the standing rule **"separate buyer approval required"**
into a machine-checkable, revocable authorization for one narrowly enumerated
carrier action.

## Allowed action types

- `SUBMIT_DISPUTE`
- `REQUEST_CREDIT_REVIEW`
- `REQUEST_DOCUMENTATION`
- `REQUEST_STATUS`

The authorization layer does not include settlement acceptance, payment
instructions, account changes, credential use, or general carrier/vendor
communication.

## Preconditions

An authorization can be issued only when:

- the authoritative Engagement State Resolver is exactly `ACTIVE`;
- the operative Charter is hash-valid and matches that resolution;
- the buyer action-approver role matches the Charter;
- every selected finding is positive and `VALIDATED`;
- every selected finding has buyer review disposition `CONFIRMED`;
- every selected finding matches the target carrier and currency;
- the authorized dollar cap does not exceed the selected validated findings.

## Exact action binding

Authorization binds:

- engagement-resolution hash;
- operative-Charter hash;
- action type;
- target carrier;
- hashed recipient/routing reference;
- exact outbound payload/evidence-package hash;
- exact finding set + finding proof hashes;
- currency;
- maximum authorized cents;
- buyer approver role;
- issue/expiry dates.

Changing any of those requires a new authorization.

The default internal validity ceiling is **30 days**. This is an internal
risk-control setting, not an industry benchmark.

## Explicit non-authority

Every authorization records all of the following as false:

- money movement;
- settlement acceptance;
- account changes;
- credential use;
- general contact authority;
- automatic execution.

Creating the authorization does **not** send anything.

## Revocation

Buyer approval can be revoked through a separate hash-bound revocation artifact.
The same approver role is required.

At or after the revocation date the authorization evaluates to `REVOKED` and
the execution guard rejects the action.

## Downstream execution rule

Before any carrier integration or human-assisted sender executes an authorized
action, it should call `assert_action_allowed(...)` using the exact action
type, carrier, recipient-routing hash, payload hash, finding set, currency and
requested amount.

Any mismatch, expiry or revocation fails closed.


## Proof-bound buyer reviews

A CONFIRMED finding used for an external action must now carry a review proof bound to the exact `finding_proof_hash`, reviewer role, review timestamp and reviewer effort. The authorization stores the resulting review hashes alongside the finding proof hashes.

Legacy unbound review rows can still be used for descriptive pilot reporting, but they cannot authorize a carrier-facing action. If the finding changes, the prior review no longer matches and a new review is required.


## Customer/payee identity binding

External action authorization is now bound to both the target carrier and the target customer/payee identity. Every selected finding must match the authorized carrier, customer/payee and currency.

This prevents one carrier/currency authorization from being reused across different customer identities. Downstream action checks require the same customer/payee identity before an action is considered within scope.


## Canonical action-payload binding

The preferred upstream path now generates a canonical carrier-action payload from the exact recovery claims. Buyer approval binds the resulting payload hash. If the rendered subject/body, action type, invoice/reference, amount or proposal facts change, the payload hash changes and the prior approval no longer matches.


## Authorization is not execution

An ACTIVE authorization only establishes the allowed scope. Carrier Action Execution Proof separately records a pre-send intent and external execution evidence. No authorization object is treated as evidence that a carrier action was submitted or delivered.


## Persisted/imported authorization verification

Authorization and revocation hashes are integrity checks, not a substitute for re-validating the authorization semantics.

Before an authorization is evaluated or used downstream, verification independently rechecks:

- allowed `ActionType`;
- non-empty buyer/engagement/target/currency/approver fields;
- SHA-256 shape for resolution, Charter, recipient, payload, finding-proof and buyer-review proofs;
- a non-empty, sorted, unique finding set;
- one finding proof and one buyer-review proof for every finding ID;
- exact positive integer cents (booleans are not accepted as integers);
- issue/expiry chronology;
- the same 30-day internal validity ceiling used at issuance;
- every explicitly forbidden capability remains exactly `false`;
- the complete authorization hash after those semantic checks.

Revocation verification likewise rechecks required fields, authorization/revocation proof hashes, approver binding, and that a revocation cannot predate the authorization's issue date.

This prevents a self-consistent object from becoming acceptable merely because someone recomputed its hash after changing a business-critical field. These deterministic hashes still do not function as digital signatures; source authenticity remains a deployment/access-control concern.
