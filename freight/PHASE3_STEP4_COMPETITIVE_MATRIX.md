# RecoveryOS Phase 3 — Step 4 Competitive Supremacy Matrix

Status: **COMPLETE AS A CURRENT EVIDENCE-WEIGHTED MARKET COMPARISON**  
Collected: 2026-10-07  
Refresh deadline: 2027-01-05

Step 4 answers the question we actually care about:

> Is RecoveryOS currently the best freight-audit/payment product overall, and if
> not, exactly where is it ahead and exactly where is it behind?

The answer is not flattering enough for marketing copy, which is precisely why
the matrix is useful.

## Methodology

The canonical competitor set is:

1. Intelligent Audit;
2. Trax;
3. Cass Information Systems;
4. Loop;
5. nVision Global.

Competitor evidence uses current first-party vendor pages. Those statements are
recorded as **vendor public claims**, not as independently audited facts.

RecoveryOS evidence is taken from the current repository, deployed application,
Phase 3 security evidence, performance benchmarks and frozen accuracy benchmark.

Absence of a competitor webpage claim is **not** treated as proof that the
competitor lacks a feature.

Fourteen dimensions are weighted to 100 points. Every vendor receives a 0–5
evidence-weighted score per dimension. This weighting is an internal engineering
decision framework, not a Gartner quadrant with nicer typography.

## Weighted result

| Rank | Product | Weighted score / 100 |
| ---: | --- | ---: |
| 1 | nVision Global | **85.6** |
| 2T | Intelligent Audit | **84.8** |
| 2T | Trax | **84.8** |
| 4 | Cass Information Systems | **83.2** |
| 5 | Loop | **82.8** |
| 6 | RecoveryOS | **56.0** |

**RecoveryOS is not currently #1 overall.**

That conclusion is intentional and machine-enforced. The repository will not
award RecoveryOS an overall-leader claim merely because we own the spreadsheet.

## Where RecoveryOS is currently strongest

RecoveryOS is tied for the highest score in exactly **2 of 14 dimensions**:

### 1. Second-look / incumbent attribution

RecoveryOS score: **5/5**.

The product freezes the incumbent-known universe before assigning challenger
value and explicitly separates:

- challenger-only;
- incumbent-known;
- suppressed;
- review-required.

Pre-existing findings, automatic credits, open claims, known disputes and
duplicate challenger economic issues do not become net-new RecoveryOS value.

The public competitor material reviewed in this snapshot shows strong audit,
recovery, claims and exception handling, but does not establish an equivalent
frozen-incumbent/net-new attribution model.

This is the clearest RecoveryOS product wedge.

### 2. Evidence provenance & recovered-dollar genealogy

RecoveryOS score: **5/5**.

RecoveryOS internally evidences:

- canonical source/record hashes;
- immutable evidence tables;
- per-tenant tamper-evident audit chains;
- explicit human review dispositions;
- finding hashes;
- payment authorization hashes;
- provider-event hash chains;
- deterministic replay;
- explicit candidate -> confirmed -> authorized -> submitted -> accepted ->
  settled -> reversed boundaries.

Competitors publish strong audit trails, explainability, revision history and
payment visibility. This matrix does **not** claim those products lack deeper
internal controls. It records that RecoveryOS's end-to-end cryptographic
financial genealogy is unusually explicit and reproducible in the evidence
available to us.

## Where RecoveryOS is behind

RecoveryOS trails the best evidenced competitor score in **12 of 14 dimensions**.

| Dimension | RecoveryOS | Best evidenced score | Weighted gap |
| --- | ---: | ---: | ---: |
| Real-world accuracy evidence | 2 | 5 | **4.8** |
| Document ingestion & extraction | 2 | 5 | **4.8** |
| Enterprise integrations | 2 | 5 | **4.8** |
| Payment execution / financial rails | 2 | 5 | **4.8** |
| External security assurance | 2 | 5 | **4.8** |
| Audit/rating breadth | 3 | 5 | **4.0** |
| Production scale/reliability | 3 | 5 | **3.2** |
| Global operations/currency | 1 | 5 | **3.2** |
| Cost allocation/accounting | 1 | 5 | **3.2** |
| Analytics/operator UX | 3 | 5 | **2.4** |
| Enterprise identity/access | 2 | 5 | **2.4** |
| Claims/exception automation | 3 | 5 | **1.6** |

The five highest-impact deficits are all boring enterprise infrastructure:
accuracy proof, extraction, integrations, money movement, and security
assurance. Apparently enterprise software buyers continue to care about actually
operating software in enterprises. Inconsiderate, but predictable.

## Pairwise evidence status

A two-point score difference is required before this matrix calls an advantage
"evidenced." A one-point difference is treated as rough parity/unclear.

| Competitor | RecoveryOS advantage | Rough parity / unclear | Competitor advantage |
| --- | ---: | ---: | ---: |
| Intelligent Audit | 2 | 1 | 11 |
| Trax | 1 | 3 | 10 |
| Cass Information Systems | 2 | 2 | 10 |
| Loop | 1 | 4 | 9 |
| nVision Global | 2 | 2 | 10 |

### Intelligent Audit

Intelligent Audit is materially ahead on mature audit breadth, integrations,
reporting, security assurance, SSO/MFA/RBAC, cost allocation and automated
claims/recovery.

RecoveryOS's best evidence-backed differentiation is second-look attribution
and cryptographic financial genealogy.

### Trax

Trax is materially ahead on global all-mode enterprise audit, document
normalization, ERP integration, cost allocation, global operations and mature
security evidence.

RecoveryOS has the clearer dedicated second-look attribution architecture.
Evidence provenance is closer, because Trax publicly describes audit trails and
compliance history.

### Cass Information Systems

Cass's gap is structural, not cosmetic: it owns a regulated banking operation
and publishes enormous real-world payment volume. RecoveryOS cannot code its way
into pretending that a payment state machine equals a bank.

RecoveryOS remains differentiated in second-look attribution and evidence
genealogy.

### Loop

Loop has the strongest public accuracy evidence in this competitor set because
its 2026 AuditBench uses real-world LTL invoices and publishes separate
production/challenge-set results.

Loop is also materially ahead on document extraction, integrations, payment
execution and modern logistics data-platform breadth.

RecoveryOS remains stronger in its explicit incumbent-challenge accounting
model. Evidence/provenance is closer because Loop publishes explainability,
revision logs and payment trace IDs.

### nVision Global

Under this weighting, nVision has the highest overall score. Its public
materials combine all-mode freight audit/payment, broad ingestion, ERP
integration, three rating engines, custom allocation, global payments,
exception/claims management and a large multinational operating footprint.

RecoveryOS's meaningful advantages remain second-look attribution and explicit
cryptographic evidence genealogy.

## Critical competitor evidence that changed the answer

Several current public facts make it impossible to call RecoveryOS #1 overall:

- Intelligent Audit publicly states 150+ audit points for any mode and publishes
  SAML SSO, MFA, RBAC and SOC/security controls.
- Trax publicly claims 100% invoice coverage across modes/currencies/regions and
  lists named enterprise integrations and data-exchange protocols.
- Cass publicly reports $37B in annual freight spend processed/paid, 35M
  invoices per year, >15,000 carriers and payment in 114 currencies.
- Loop publicly describes 99% no-touch audit workflows, custodial/directed/pay
  file payment models, SOC-II Type 2, and a real-world LTL accuracy benchmark.
- nVision publicly describes all-mode audit/payment, 200+ checkpoints, multiple
  audit/rating engines, global payment and a multinational operations footprint.

RecoveryOS has no honest counter-evidence today for most of those maturity
claims.

## What "number one" would require

To overtake this matrix rather than merely change the weights, RecoveryOS needs
real evidence in the following order:

1. **Blind customer accuracy benchmark.**
   A frozen population independently adjudicated before RecoveryOS output is
   revealed. This closes the most damaging evidence gap.

2. **Production document extraction.**
   PDFs/images/EDI/X12 and supporting-document extraction with measured field
   accuracy, confidence routing and human-review fallback.

3. **Named enterprise connectors.**
   Real ERP/TMS/accounting integrations, not generic adapter primitives.

4. **Real payment rail integration.**
   A bank/payment-provider path with actual status/trace/reconciliation evidence.
   PaymentOS remains the state-control layer rather than pretending to be the
   rail itself.

5. **External security proof.**
   MFA, enterprise SSO, independent penetration testing, SOC 2 Type II and/or
   ISO 27001 evidence, plus provider encryption/restore evidence.

6. **Higher-scale deployed proof.**
   Concurrent multi-tenant HTTP/load tests and a credible production SLO.

7. **GL/SKU allocation.**
   Cost-center/accounting automation comparable with the established FAP
   platforms.

8. **Global execution.**
   Multi-currency and regional operational coverage if the commercial strategy
   genuinely requires it.

## Strategic conclusion

Trying to beat Cass at banking, nVision at worldwide operations, Intelligent
Audit at decades of audit-rule breadth, Trax at enterprise integration maturity
and Loop at AI document automation simultaneously would be a magnificent way to
burn years recreating incumbents.

The shortest credible path to #1 is still:

> **Become the best independent second-look recovery and financial-truth layer,
> then close enterprise infrastructure gaps around that wedge.**

The product already has a defensible lead in the two dimensions most aligned
with that strategy. Step 5 should convert those internal advantages into buyer
proof instead of diluting them into another generic freight-payment platform.

## Evidence artifacts

Canonical Step 4 artifacts:

- `freight/PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json`;
- `freight/PHASE3_COMPETITIVE_MATRIX_2026-10-07.json`;
- `freight/competitive_matrix.py`;
- `freight/test_phase3_competitive_matrix.py`.

The evidence snapshot expires on **2027-01-05**. CI fails after that date until
the public competitor research is refreshed. This prevents a 2026 comparison
from quietly becoming eternal truth, a fate already suffered by far too many
enterprise comparison pages.

## Step 4 verdict

**Step 4 is complete. RecoveryOS is not overall #1 today.**

It is currently strongest in:

1. second-look incumbent attribution;
2. explicit evidence / financial-state genealogy.

Its overall evidence-weighted score is **56.0/100**, versus **82.8–85.6** for
the five mature competitors under this rubric.

That gap is substantial. More usefully, it is now specific, reproducible and
prioritized instead of being a vague ambition.
