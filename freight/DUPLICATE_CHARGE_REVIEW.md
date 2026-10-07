# Duplicate charge review boundary

`duplicate_charge_review.py` closes a narrow product gap between normalized
invoice ingestion and the governed finding factory. It looks for charge lines
that are identical on buyer scope, shipment, customer, carrier, currency,
charge code, service date, quantity and billed amount while carrying distinct
charge IDs.

The output is deliberately a **REVIEW candidate**, never a `Finding` and never
`VALIDATED` dollars. Identical lines may be legitimate corrections, rebills,
split services or credits. Each candidate therefore records these unresolved
evidence requirements:

- invoice lineage;
- credit/rebill status;
- payment status;
- proof that the services are not distinct.

Candidates and batches are content-addressed from the frozen population and
source-bound charge lines. Input order cannot change the result. The candidate
excess amount is a triage measure equal to the repeated copies only; it is not
a recovery, settlement or fee claim.

The detector fails closed on duplicate internal charge IDs, out-of-population
charges, buyer/business-unit mismatches, identity mismatches, malformed dates,
and non-integer money or quantity values. Near matches are not grouped.
