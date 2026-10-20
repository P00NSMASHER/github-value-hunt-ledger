# RETALLY R3 — defensible independent accuracy (release hold)

Two separately frozen manifests contain model predictions and the independent
truth owner's adjudications. Their full exact case payloads are hash-sealed
before joint reveal, with distinct roles and chronological freeze checks.

Eligibility to enter the scored confusion matrix requires ALL of: original
invoice proof, shipment-specific controlling rate, independent payment proof,
independent adjudication, distinct hashes, source completeness, a positive or
negative label, and matching case identities. Unknown and incomplete labels
stay unscored, never silently become true negatives.

The evaluator computes abstentions separately, counts abstentions in
recall/false-positive denominators, returns 95% Wilson bounds and includes
zero-denominator NULL values rather than fake 100% rates. Synthetic rehearsals
are categorically not external accuracy proof. Even with complete data the
separate existing freight.audit_acceptance buyer-pilot validator, true external
reviewer independence and owner/governance approval are required before any
public claim.

The currently examined 110 GlobalTranz and ArcBest invoices have ZERO fully
linked independent overcharge/negative truth labels. They remain UNKNOWN;
this PR creates scoring and study integrity capability, not those missing
evidence objects. No external correspondence or customer action occurred.
