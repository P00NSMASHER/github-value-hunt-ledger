# Freight Recovery — Data Readiness / Authority Diagnostic

Updated: 2026-09-20

This is the delivery specification for the **$5,000–$7,500 fixed** first offer.

## Purpose

Determine whether a buyer can support a defensible Blind Freight Audit Acceptance Test before analysis effort is spent inventing missing truth.

The diagnostic is not an audit and does not claim recovery dollars.

## Machine assessment

Run:

```bash
PYTHONPATH=. python freight/readiness.py buyer_readiness.json
```

The output contains:
- `status`: BLOCKED | CONDITIONAL | READY;
- `score`: 0–100 planning score;
- `blockers`: hard pilot blockers;
- `conditions`: source-coverage conditions;
- `recommended_offer`.

**The score is never allowed to override a hard blocker.**

**Buyer/data readiness is not deployment launch authorization.** A READY result
only means the proposed population can support the audit method. Before any
confidential buyer data is accepted, the actual data-handling path must also
pass `freight/pilot_launch_gate.py`.

## Hard readiness questions

The buyer must answer/prove:
1. Is authorization to use the selected data documented?
2. Can the pilot run read-only?
3. Can the population be frozen reproducibly?
4. Can incumbent findings remain sealed until buyer-owned truth is frozen?
5. Can later credit/refund/remittance outcomes be observed?
6. Can controlling commercial authority be reconstructed?
7. Is customer identity stable?
8. Is carrier identity stable?
9. Is retention defined?
10. Is deletion defined?

## Coverage measures

Measure, do not guess:
- invoice-source coverage;
- controlling-authority-source coverage;
- shipment/supporting-evidence coverage.

The current planning thresholds for direct pilot readiness are:
- invoice source: **>=95%**;
- authority source: **>=90%**;
- shipment/supporting evidence: **>=80%**.

A buyer below these thresholds may still be commercially valuable, but the first engagement remains the Data Readiness Diagnostic or the pilot population must be narrowed to a supported subset.

## Deliverable

### Executive result
- status;
- readiness score;
- recommended next offer;
- proposed pilot population definition.

### Source inventory
For each source:
- system/owner;
- export/API/file method;
- date coverage;
- identifiers;
- effective-date/version fields;
- source health/completeness;
- read-only status;
- retention/deletion treatment.

### Authority gaps
List every unresolved:
- contract/rate-card version;
- RateCon;
- amendment/addendum;
- incorporated tariff;
- accessorial schedule;
- fuel authority;
- effective/supersession boundary.

### Identity gaps
List unresolved customer/carrier/shipment/invoice joins. Do not resolve uncertain identity merely to improve the score.

### Settlement observability
State exactly how later recovery would be proven:
- credit memo;
- rebill/corrected invoice;
- EDI 812/820;
- remittance;
- payment/refund ledger;
- other buyer-controlled evidence.

### Normalization plan
For each blocking/conditional gap:
- current source;
- missing field/authority;
- proposed normalization;
- human review required;
- whether the gap is internal engineering, rights diligence, customer data, or a future connector.

## Commercial routing

- **BLOCKED** → sell/perform Data Readiness Diagnostic only; do not start blind audit.
- **CONDITIONAL** → diagnostic + remediation/narrowing plan; blind audit starts only after gate passes.
- **READY** → the buyer may be quoted for the Blind Freight Audit Acceptance Test, but confidential-data handling does not begin until the final Pilot Launch Gate is READY for the chosen data path.

## Research routing

A diagnostic finding does **not** automatically authorize GitHub hunting.

If it exposes a genuinely unsupported connector/capability:
1. update `freight/GAP_REGISTER.json`;
2. change that exact gap to `ACTIVE_SEARCH`;
3. record the paying-customer/EXP-001 evidence;
4. set allowed trigger and stop condition;
5. only then may a freight hunter search.

This makes customer evidence—not repository novelty—the source of the freight research roadmap.
