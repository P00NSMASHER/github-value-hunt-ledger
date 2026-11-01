# Portfolio Brain → RETALLY: cross-shipment invoice-reference review

**Status:** isolated first-party implementation candidate, **not merged, deployed,
integrated into RecoveryOS, or customer validated**. All examples are synthetic.
No customer invoice, authorization document, credential, or payment data is used.

## Evidence, not a licence to copy or a promise of savings

A completed, Cloudflare-origin signed Portfolio Brain research job,
[core #37865121397](https://github.com/P00NSMASHER/portfolio-brain/actions/runs/37865121397),
reported this genuine external source:

- Repository: [Jacob-Met/workflow-checks](https://github.com/Jacob-Met/workflow-checks)
- Exact external commit: `a5fd61b0c361c8a9b8a6737b33ecc9efab46e0ad`
- Inspected module:
  [`freight_packets/freightpkt/invoice_match.py`](https://github.com/Jacob-Met/workflow-checks/blob/a5fd61b0c361c8a9b8a6737b33ecc9efab46e0ad/freight_packets/freightpkt/invoice_match.py)
- Recorded blob: `584bb09b92335a350d9880f55b786baba1960941`,
  source SHA-256: `37a9e0801de948c3b558ca7c9846b3d0eb76ec062703ee3e5132df273ff569ab`.
- Published license metadata: MIT. The finding only justifies inspection;
  it does not authorize unrelated assets, dataset contents, credentials,
  external endpoints, or claims of verified behavior in RETALLY.

The inspected source groups invoices by lowercase carrier and exact invoice
number across loads, emits `DUPLICATE_INVOICE` flags, and does not by
itself verify customer contract scope or payment/rebill causation. Its
separate [upstream hardening test](https://github.com/Jacob-Met/workflow-checks/blob/a5fd61b0c361c8a9b8a6737b33ecc9efab46e0ad/freight_packets/tests/test_freight_hardening.py)
expects **both** duplicate-number load copies to be held during settlement,
not automatically treated as recovered overpayments. This is a static source
and test review, NOT evidence the third-party tests were executed here.

## Existing RETALLY authority

- Exact first-party starting main commit:
  `8a238d1d80241b566f30eb72e7cc59616a0594ee`.
- Existing [`freight/duplicate_charge_review.py`](duplicate_charge_review.py)
  groups repeated charge **lines** within buyer, business unit, shipment,
  customer, carrier, currency, charge code, service date, quantity and billed
  amount. Even exact matching produces `REVIEW`, never validated dollars.
- Existing [`freight/contracts.py`](contracts.py) requires frozen population
  identity and controlling authority before positive financial findings.
- [Freight Recovery Evidence Standard](FREIGHT_RECOVERY_EVIDENCE_STANDARD.md)
  distinguishes candidate discrepancy, validated finding, authorized claim,
  settlement, net realized recovery, and fee eligibility.
- Existing settlement-level ambiguous duplicate claim references are already
  routed to `REVIEW` by `freight/test_settlement_store.py` and must not be
  incorrectly described as absent. The *specific* new candidate is a
  pre-settlement **cross-shipment reuse review lead**, not a missing payment
  reconciliation engine.

## First-party implementation

`review_reused_invoice_references(population, charges)` in the **existing**
`freight/duplicate_charge_review.py` module:

1. Reuses the unchanged, fail-closed frozen-population and charge input
   validation before grouping anything.
2. Looks for exact identical invoice identifiers used for at least two
   **distinct** shipment IDs within the **same** buyer, business unit,
   customer, carrier and currency.
3. Emits a deterministic, content-addressed `REVIEW` candidate with exact
   charge and original source-hash references, preserving input-order stability.
4. Separates different customers/carriers/currencies and different invoice
   references. Reused numbers on one shipment are not misidentified as
   cross-shipment reuse.
5. Reports **zero** validated/recovered dollars and **no amount estimate**.
   Multi-load invoices, carrier rebills, corrected invoices, distinct services
   and credits are possible legitimate explanations.
6. Requires human investigation of invoice lineage, payment status,
   credits/rebills, authorization for consolidated invoices, and service
   distinction before any downstream financial or external action.
7. Does not modify `review_duplicate_charges`, raise an automatic payment
   hold, write production state, contact carriers, trigger fees, or execute
   any third-party source.

The separate `freight/test_invoice_reference_review.py` synthetic tests
exercise a legitimate two-load reference, same-load/nonmatch negative
controls, customer/carrier/currency boundaries, frozen population mismatch,
identity failure, integer/date guards, tamper-sensitive hashes, order
independence, multiple loads, and zero-value claim invariants.

## Success metric and limits

**Measurable technical result**, once this draft's exact SHA has real CI:
one newly identifiable cross-shipment invoice-reference `REVIEW` condition,
with deterministic evidence and no regression in existing line-level review.
The measure is on **designed synthetic cases only**. It is not a statistically
representative real customer false-positive rate, avoided duplicate charge,
commercial user adoption, or demonstrated realized recovery.

The candidate is intentionally not attached to invoice ingestion or a
customer-facing RecoveryOS release. A separately reviewed future consumer
integration must prove exact frozen population provenance, multi-load contract
handling, buyer-safe access controls, actual workflow presentation, human
approval boundaries, and no collateral change in settlement accounting.
A production or commercial value outcome is `NOT_VERIFIED` until those
controls and independently adjudicated real evidence exist.

**Portfolio Brain learning boundary:** this work is a concrete
source-linked implementation *proposal* with a technical test gate, not an
operator-reported `feedback` event. Do not ingest it as `INTEGRATED`,
`USEFUL`, verified customer value or a time-saved number in Brain's durable
learning ledger. Report the exact draft PR and CI evidence separately, then
evaluate integration only if the product release review approves it.
