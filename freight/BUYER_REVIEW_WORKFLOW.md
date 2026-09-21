# Buyer Review Workflow

The buyer review workflow is the controlled human-decision boundary after review routing.

It accepts decisions **only** for cases whose exact case hashes appear in the canonical routing layer's `buyer_review_case_hashes`. Those cases are positive, validated findings with the `REVIEW_VALIDATED_FINDING` action.

Evidence-remediation cases cannot be manually confirmed, dismissed, or promoted through this workflow. They must be corrected upstream and the audit rerun, producing new proof objects if the evidence changes.

## Decision inputs

Each submitted decision specifies:

- the exact review `case_hash`;
- one typed disposition: `CONFIRMED`, `FALSE_POSITIVE`, or `UNRESOLVED`;
- reviewer minutes;
- a timezone-aware review timestamp.

The batch also carries the buyer reviewer role.

## Proof binding

For every accepted decision the workflow:

1. re-verifies the review packet and canonical review routing;
2. verifies the frozen truth hash and finding proof hashes;
3. confirms the case is buyer-review-ready;
4. confirms the finding is a positive `VALIDATED` finding;
5. confirms the case's finding proof matches frozen truth;
6. creates the existing proof-bound `FindingReview`;
7. preserves the resulting review hash in a case-level review record;
8. hashes the complete buyer-review batch.

Decision input order does not change the batch proof; output follows the canonical buyer-review case order.

## States

- `NO_BUYER_REVIEW_READY` — routing contains no buyer-ready cases.
- `PARTIAL` — at least one buyer-ready case still lacks a decision.
- `COMPLETE` — every buyer-ready case has a proof-bound decision.

A COMPLETE buyer review is still **not** external-action authorization. Carrier contact, dispute submission, settlement acceptance, credentials, account changes, and money movement remain separately controlled.
