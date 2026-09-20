# Freight Recovery — Blind Pilot Protocol

Updated: 2026-09-20

## Objective

Prove whether the challenger finds **defensible, incremental freight leakage** that the buyer's incumbent process missed, without contaminating truth or overstating savings.

## Stage 0 — Buyer authorization and scope

Before data transfer:
- define buyer entity/business unit;
- define date range and included carriers/modes;
- define exact invoice population selection rule;
- define allowed data sources and retention;
- define incumbent output to remain sealed;
- define settlement evidence the buyer can later supply;
- define false-positive-dollar ceiling and review process;
- define who on the buyer side owns gold truth and who can approve findings.

No outreach, disputes, carrier contact or money-moving action is performed without buyer approval.

## Stage 1 — Data-readiness gate

Required classes:
1. invoice/EDI actuals;
2. controlling contract/rate/rate-confirmation authority;
3. amendments/addenda/tariff references where applicable;
4. shipment identity and operational truth;
5. POD/BOL/appointment/weight/telematics evidence where required;
6. incumbent findings/output, sealed;
7. settlement/credit/remittance source capable of proving later outcomes.

Fail the readiness gate if:
- controlling authority cannot be reconstructed;
- material customer/carrier identity remains unresolved;
- the population cannot be frozen reproducibly;
- the incumbent output cannot remain sealed;
- later outcome evidence is impossible to observe.

## Stage 2 — Freeze population

Create a manifest containing:
- buyer + BU;
- invoice IDs and source hashes;
- shipment IDs and source hashes;
- source-date range;
- population-selection query/rule;
- manifest SHA-256.

No row may silently enter or leave after freeze. Any change creates a new population/version.

## Stage 3 — Freeze buyer-owned truth

Before opening the incumbent output:
- resolve controlling authority and effective version;
- preserve source page/cell/segment references;
- calculate independent expected charges;
- record unsupported/ambiguous cases as REVIEW;
- freeze the truth manifest/hash.

The challenger may use multiple independent comparators, but no component may certify its own source extraction, rating and final commercial conclusion without an independent check.

## Stage 4 — Open incumbent output

Only after Stage 3:
- record incumbent output hash/version;
- compare finding identity, reason and dollars;
- classify:
  - incumbent found;
  - challenger-only validated;
  - incumbent-only;
  - disagreement/review.

Do not score a different population than the frozen population.

## Stage 5 — Review and action

For every challenger-only validated finding:
- show exact authority;
- show deterministic expected calculation;
- show observed invoice;
- show required supporting evidence;
- show contradiction checks;
- show the reason the case is not REVIEW;
- obtain buyer approval before external dispute/action.

## Stage 6 — Settlement readback

A finding becomes **realized** only when later evidence supports:
- settlement source identity;
- amount/currency;
- exact allocation to the finding/invoice(s);
- no duplicate/preexisting/automatic credit ownership;
- source hash and timestamp/period.

Partial credits accumulate only to the validated amount. Ambiguous many-to-many allocation stays unresolved until uniquely supported.

## Pilot acceptance criteria

Minimum commercial pass:
- zero unsupported asserted-recovery dollars;
- no population/truth/incumbent ordering violation;
- deterministic replay of frozen cases;
- false-positive dollars within buyer-agreed ceiling;
- at least one challenger-only validated finding, unless the population is genuinely clean;
- for "recovery proven" status: at least one unique finding reaches issued credit/refund/remittance with unambiguous allocation.

A clean population may still prove audit quality, but it does not prove a recovery thesis.

## Buyer report

Report four separate totals:
1. reviewed discrepancy dollars;
2. validated finding dollars;
3. challenger-only validated dollars;
4. uniquely attributable realized dollars.

Never collapse these into one "savings" number.
