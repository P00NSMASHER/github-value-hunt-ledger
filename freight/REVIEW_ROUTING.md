# Review Routing

Freight Recovery separates reviewer work into buyer-ready findings and evidence remediation before downstream action.

## Routes

Every deterministic Reviewer Work Packet is classified into exactly one route:

- **NO_REVIEW** — there are no non-clear cases.
- **BUYER_REVIEW_READY** — every queued case is a validated finding backed by verified controlling authority and is ready for the buyer's proof-bound review.
- **EVIDENCE_REMEDIATION_REQUIRED** — every queued case requires authority/rule/evidence work before it can become final.
- **MIXED_REVIEW_AND_REMEDIATION** — the run contains both buyer-review-ready findings and remediation cases.

## Remediation cases

The remediation bucket includes:

- `VERIFY_CONTROLLING_AUTHORITY` — the calculation is available, but the matched authority has not been verified as controlling;
- `ADD_APPLICABLE_RULE` — no applicable rule has been established;
- `RESOLVE_RULE_AMBIGUITY` — multiple applicable rules prevent one supported expected amount;
- `INVESTIGATE_EVIDENCE` — another evidence issue prevents buyer-ready treatment.

Any remediation case sets `rerun_required=true`. Correcting authority/rule/evidence inputs can change rule hashes, findings, truth, queue ordering, packet proofs and the canonical audit-run hash, so those cases must be re-derived rather than manually promoted in place.

## Buyer-review cases

`REVIEW_VALIDATED_FINDING` cases are routed to the buyer-review bucket. Routing does not confirm them. The buyer's later review remains a separate proof-bound decision tied to the exact finding proof.

## Integrity

Routing verifies both:

1. the outer Reviewer Work Packet hash; and
2. every individual review-case hash before using its action hint.

The routing artifact is itself deterministically hash-bound to the exact packet and ordered case hashes. It cannot authorize carrier contact, disputes, settlement, money movement, or claim that a discrepancy is realized savings.


## Remediation handoff

Cases in the remediation bucket feed the deterministic Evidence Remediation Plan. The plan maps each exact case hash to the evidence category required and the rerun action. Routing itself never supplies or changes evidence.
