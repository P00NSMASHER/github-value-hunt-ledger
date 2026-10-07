# Freight Audit Acceptance Test — Buyer Report Template

## 1. Executive result

**Population:** [buyer / BU / date range / modes / carriers]

**Prepared for:** [named business owner / title]

**Prepared by:** [reviewer / contact]

**Report date:** [date]

**Recommended next step:** [no further action / request records / authorize defined recovery scope]

**Summary:** [Two sentences explaining what was reviewed, what is supported, and what remains unresolved.]

### Decision at a glance

- Records reviewed: [count and review period].
- Findings supported by evidence: [count and value; not recovered funds].
- Funds actually received or credited: [amount, settlement date, and source].
- Your next action: [specific decision or requested records, owner, and agreed target date].


### Financial totals

| Measure | Amount | Meaning |
| --- | ---: | --- |
| Reviewed discrepancy | $— | Positive differences reviewed, including unresolved cases. **Not savings.** |
| Validated finding | $— | Findings with controlling authority/evidence sufficient for a positive conclusion. **Not yet realized.** |
| Challenger-only validated | $— | Validated findings absent from the frozen incumbent output. |
| Uniquely attributable realized | $— | Later credit/refund/remittance uniquely allocated to validated findings. |
| Fee-eligible realized | $— | Realized amount eligible under the commercial attribution policy after incumbent/preexisting/automatic exclusions. |

Never collapse these rows into one savings number.

## 2. Method integrity and sample design

- population size: —
- sample size: —
- finite-population required sample size at 95% / configured margin: —
- sampling method: [CENSUS / STRATIFIED_RANDOM]
- frozen random seed when sampled: —
- declared strata: —
- strata meeting target: — / —
- distinct truth owner / reviewer A / reviewer B / RecoveryOS operator: **required**
- truth owner saw RecoveryOS before truth freeze: **NO required**
- RecoveryOS team saw truth before output freeze: **NO required**
- sample selected before RecoveryOS output: **YES required**
- population/truth/RecoveryOS/incumbent ordering violations: **0 required**

## 3. Statistical quality / review metrics

Report both point estimates and the required uncertainty bounds:

- adjudicated cases: —
- positive truth cases: —
- negative truth cases: —
- unresolved truth cases: —
- automatic decisions: —
- review/abstention decisions: —
- automatic coverage: —
- review rate: —
- population-weighted automatic coverage: —
- population-weighted review rate: —
- true positives / true negatives: —
- false positives / false negatives: —
- precision: — ; **95% Wilson interval: —**
- false-positive case rate: — ; **95% Wilson interval: —**
- false-negative case rate: — ; **95% Wilson interval: —**
- auto-decision accuracy: —
- population-weighted precision: —
- population-weighted false-positive rate: —
- population-weighted false-negative rate: —
- dual-reviewed cases: —
- reviewer raw agreement: —
- reviewer Cohen's kappa: —
- expected calibration error (ECE): —
- Brier score: —
- unsupported automatic decisions: **0 required**

## 4. Dollar-integrity metrics

- predicted-positive dollars: —
- independently adjudicated positive dollars: —
- false-positive dollars: —
- false-negative dollars: —
- false-positive dollar share: —
- false-negative dollar share: —
- truth-positive dollars routed to human review: —
- auto-decision mean absolute dollar error: —
- auto-decision net dollar bias: —
- exact-dollar rate: —
- incumbent-known dollars incorrectly credited as net-new: **$0 required**
- duplicate economic-issue dollars incorrectly credited twice: **$0 required**
- population-weighted false-positive dollar share: —
- population-weighted false-negative dollar share: —
- population-weighted mean absolute dollar error: —
- population-weighted net dollar bias: —

A small case error with a large dollar impact is not hidden by an attractive
ordinary accuracy percentage.

## 5. Stratum report

For every pre-registered stratum include:

- population count;
- sample target;
- sampled count;
- adjudicated count;
- false positives;
- false negatives;
- review count.

Do not omit a weak carrier, mode, source type, business unit, or spend band merely
because the overall metric passes.

## 6. Finding register

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

## 7. Incumbent comparison

Report:
- challenger-only validated;
- incumbent-only;
- both found;
- disagreement/review;
- false-positive dollars;
- dollar-weighted recall only where gold truth is defensible.

Finding identity must not be inferred from dollar amount alone.

## 8. Settlement readback

A finding is not realized merely because:
- a dispute was submitted;
- a credit was promised;
- a corrected bill was generated;
- the carrier/provider reports success.

Show buyer-controlled settlement/remittance evidence and exact allocation.

## 9. Limitations

List:
- unresolved authority;
- unavailable shipment proof;
- excluded modes/carriers;
- unsupported rate semantics;
- identity ambiguity;
- missing settlement observability;
- manually reviewed rules;
- any customer-specific assumptions.

## 10. Commercial next step

Choose one:
- no further action / population appears clean;
- targeted recovery follow-through;
- repeat blind acceptance test on a broader population;
- annual continuous assurance proposal.

Annual assurance should be proposed only after the buyer accepts the integrity and economics of the pilot.

## Appendix — traceability and method status

**Population hash:** [SHA-256]

**Sample hash:** [SHA-256]

**Truth manifest hash:** [SHA-256]

**RecoveryOS output hash:** [SHA-256]

**Incumbent output hash:** [SHA-256]

**Acceptance policy:** recoveryos-blind-audit-acceptance-v2

**Method status:** [INVALID_METHOD / INSUFFICIENT_EVIDENCE / QUALITY_GATE_FAILED / AUDIT_QUALITY_PROVEN]


Explain the method status in plain language beside its code. Keep the hashes and acceptance policy available for independent verification. Do not present an incomplete or failed method as proven audit quality.
