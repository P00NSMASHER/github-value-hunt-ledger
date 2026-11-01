# Golden Goose: Hydrovac proof-to-invoice exception audit

**Research-only synthetic proof of concept, October 29, 2026. NOT an authorized customer audit.** Candidate notes: https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863 . Leaves existing integrator priorities, worker leases, commercial controls and protected main unchanged.

## Hypothesis and service-first wedge
An independent **read-only** audit that joins approved field tickets, signed disposal manifests, effective-dated rates, posted invoice lines, waivers and credits might find missed billable components *across systems*, even when a contractor already uses field-service software.

Potential monetization, not a sale: one **hypothetical $100 authorized fixed-price diagnostic** would reach $100 gross; ten genuine $100 purchases would reach $1,000 gross before costs. No customer contact, offer, permission to access business data, contract, sale or payment has occurred.

**Competition is meaningful.** [Aimsio](https://aimsio.com/industries/hydrovac/) and [Spira](https://www.spiradata.com/hydrovac-software) already advertise integrated hydrovac ticket-to-invoice workflows. [Rove](https://rovedispatch.com/) advertises $299/month Pro and $599/month AI tiers for roll-off/waste operations. These are vendor statements/prices, **not independent evidence of buyer demand for this narrower gap audit**, nor evidence that existing solutions miss gaps.

## Exactly measured, wholly constructed example
Frozen cohort: 100 synthetic jobs, 70 clean, 12 planted discrepancies (4 entirely unbilled invoices; 4 short hours; 4 omitted disposal fees) and 18 deliberate human-review controls (3 each missing signoff, missing rate authority, recent within arbitrary 30-day grace, waiver, existing credit, disputed scope).

Fictional rate: $175/hour; approved 4-hour job; $180 per dump. These values are *not* market estimates.

| Check | Observed local result | Limit |
| --- | ---: | --- |
| Planted gaps detected | **12/12** | Designed in-sample fixtures, not predictive accuracy |
| Clean rows falsely marked monetary candidate | **0/70** | Synthetic controls only |
| Ambiguous controls routed to review | **18/18** | No automated monetary assertion |
| Naive “missing whole invoice” toy baseline | **4/12** | Not a comparison to actual vendor products |
| Gross constructed variance | **$4,940** | Not a recoverable or collectible amount |
| Actual customers and earnings | **0 / $0** | No activity with customers |

The prototype never returns collectible amounts: it emits REVIEW, POTENTIAL or CLEAR states, and every result carries collectible_usd = null. **POTENTIAL** is a document-reconciliation hypothesis requiring actual signed contract and source review, not an invoice demand, customer liability or permission to collect.

Run from this directory: python -m unittest -v test_hydrovac_reconcile

**Local checks:** 24/24 test methods passed with the frozen 100-row dataset on 2026-10-29. Not independent CI, real-data acceptance or an out-of-sample result. Files were uploaded to an unmerged draft branch.

## Adversarial and authority gaps
- An arbitrary 30-day grace, synthetic hourly/disposal rates, and signed/approved flags are illustrative, not contractual facts.
- The offline engine cannot authenticate signed evidence, source-page contents, later amendments, permitted fee waivers, discounts, reconciled credits, tax, overpayment refunds, or identity matching across ERP systems.
- A single invoice-line ID collision is blocked; duplicates across distinct IDs and cross-account joins need more controls.
- AI extraction of field tickets and manifests is a possible later accelerator, **not implemented or validated** in this version. Human interpretation and approval must remain authoritative.
- Do not import real invoices, customer/personal data or execute collection claims without explicit authorization and applicable privacy controls.

## Falsifier and next test
Before sales claims, test independently generated holdout cases: split invoices, correct signed waivers, effective-dated rate changes, post-bill credits and duplicate field tickets. Later, only with fresh authorization, run a blind **100 completed job** read-only historical diagnostic with customer-provided signed rate and field evidence plus independently sealed incumbent reconciliation. Measure **incremental, contract-supported, finally collectible** gaps *above* incumbent findings and customer review effort. Reject if no meaningful incremental value or the buyer cannot authorize the data. No customer WTP has been established.

**Disposition: WATCH / locally tested synthetic demonstrator, NOT market-validated. Verified collectible $0, realized revenue $0.** No hunter claim, integrator promotion, protected-main merge, outreach, filings, paid services, subscriptions, trades, or Work credits.

