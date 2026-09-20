# Freight Audit Acceptance Test — Buyer Report Template

## 1. Executive result

**Population:** [buyer / BU / date range / modes / carriers]  
**Population hash:** [SHA-256]  
**Truth manifest hash:** [SHA-256]  
**Incumbent output hash:** [SHA-256]

### Financial totals

| Measure | Amount | Meaning |
| --- | ---: | --- |
| Reviewed discrepancy | $— | Positive differences reviewed, including unresolved cases. **Not savings.** |
| Validated finding | $— | Findings with controlling authority/evidence sufficient for a positive conclusion. **Not yet realized.** |
| Challenger-only validated | $— | Validated findings absent from the frozen incumbent output. |
| Uniquely attributable realized | $— | Later credit/refund/remittance uniquely allocated to validated findings. |
| Fee-eligible realized | $— | Realized amount eligible under the commercial attribution policy after incumbent/preexisting/automatic exclusions. |

Never collapse these rows into one savings number.

## 2. Quality / review metrics

- invoices/shipments in frozen population: —
- total findings: —
- validated findings: —
- challenger-only validated findings: —
- false-positive findings/dollars: —
- unresolved findings/dollars: —
- reviewer touches: —
- reviewer minutes/hours: —
- deterministic replay failures: —
- population/truth/incumbent ordering violations: **0 required**

## 3. Finding register

For every finding include:
- finding ID;
- invoice/shipment/carrier/customer;
- exact controlling authority ID + source locator/hash;
- actual billed;
- independently expected;
- validated variance;
- evidence sufficiency;
- incumbent status;
- buyer review disposition;
- dispute/action state;
- settlement state;
- settlement source/hash;
- realized amount;
- fee-eligible amount;
- recovery certificate hash.

## 4. Incumbent comparison

Report:
- challenger-only validated;
- incumbent-only;
- both found;
- disagreement/review;
- false-positive dollars;
- dollar-weighted recall only where gold truth is defensible.

Finding identity must not be inferred from dollar amount alone.

## 5. Settlement readback

A finding is not realized merely because:
- a dispute was submitted;
- a credit was promised;
- a corrected bill was generated;
- the carrier/provider reports success.

Show buyer-controlled settlement/remittance evidence and exact allocation.

## 6. Limitations

List:
- unresolved authority;
- unavailable shipment proof;
- excluded modes/carriers;
- unsupported rate semantics;
- identity ambiguity;
- missing settlement observability;
- manually reviewed rules;
- any customer-specific assumptions.

## 7. Commercial next step

Choose one:
- no further action / population appears clean;
- targeted recovery follow-through;
- repeat blind acceptance test on a broader population;
- annual continuous assurance proposal.

Annual assurance should be proposed only after the buyer accepts the integrity and economics of the pilot.
