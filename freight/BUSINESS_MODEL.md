# Freight Recovery — Commercial Operating Model

Updated: 2026-09-21

## Decision and evidence

Build a supervised freight-invoice review service, prove that customers will pay for a useful report, and offer recurring monitoring where continued value and delivery economics are demonstrated. Hunter supplies reusable methods, evidence standards and measured improvements to this workflow.

The buyer-facing promise is:

> We check a defined set of freight invoices against your agreements and shipment records. You receive a reviewed report showing supported discrepancies, the calculations behind them, and the evidence needed to decide what to do next.

The first product remains the **Blind Freight Audit Acceptance Test**. Its blind comparison measures the incremental result against the customer's existing process. A clean result is a valid report; it is not evidence that money was recovered.

Current evidence limits:

- The structured Hunter outcome ledger records technical rehearsal evidence and **no directly evidenced commercial revenue or customer value**; the structured record's monetary fields are null. Missing commercial evidence is not a measured zero-sales result. This describes that ledger, not every business account.
- Repository benchmarks and passing tests establish only the behavior they exercise. They do not establish installed customer integrations, production readiness, buyer demand or recovery rates.
- Confidential customer-data kickoff remains subject to the current route-specific [Pilot Launch Gate](PILOT_LAUNCH_GATE.md). A commercially attractive deal or paid diagnostic cannot override that gate.
- The previously referenced public address returned site-not-found during the September 21 review. The saved September 18 landing-page artifact is historical, not verified deployed content. Restore and verify the public entry point before directing prospects to it.
- A September 18 sales-tracker snapshot lists 104 prospects, 25 wave-one targets, 10 first touches and zero replies as of that artifact. These are historical records, not a current inbox verification; the universe includes unqualified/removed records. Preserve existing one-touch statuses before any later authorized outreach.

## First customer and scope

Prioritize a regional manufacturer or distributor with a named finance/transportation owner, accessible records and a specific billing-control problem. Roughly $5M annual transport spend or 500 invoices/month is a prioritization signal, not proof of fit.

Qualification must establish:

1. A buyer with authority to purchase and an owner able to supply records.
2. A defined business unit, population, carrier/mode scope, currency and period.
3. Controlling rates/amendments and the shipment evidence needed by selected checks.
4. An existing audit/payment result that can be sealed for a blind comparison.
5. A later credit/refund/remittance source if recovery is part of the objective.
6. An agreed review process, acceptance criteria and value question.
7. A valid data-handling route before confidential files are accepted.

Start with one mode and currency. Select the mode from accessible records and supported checks; do not advertise every freight mode. Freight consultants and independent auditors are prospective referral partners. Their interest and customer access are hypotheses to test.

The [Commercial Playbook](COMMERCIAL_PLAYBOOK.md) contains the bounded pilot envelope, qualification questions, proposal draft and delivery checklist.

## Offer catalog and version control

These bands are **unvalidated commercial hypotheses currently encoded in the internal activation/charter system**, not market-validated pricing or evidence of sales. Earlier $2,500 diagnostic and $3,000/month scenarios are separate planning hypotheses, not active machine-supported pilot offers.

| Internal offer | Current price hypothesis | Buyer receives | Advancement condition |
|---|---:|---|---|
| Data Readiness / Authority Diagnostic | $5,000–$7,500 fixed | Source inventory, missing-authority report and bounded pilot/remediation plan | Buyer needs the work, scope is profitable and actual-record handling is authorized |
| Blind Freight Audit Acceptance Test | $15,000–$25,000 fixed | Frozen population, reproduced expected charges, reviewed findings, blind comparison and source-linked report | Readiness/launch pass; exact scope and fee are agreed |
| Managed Recovery | Optional 15–20% of uniquely attributable realized amounts | Approved case administration and settlement tracking | Separate agreement, approved external actions and independent allocation evidence |
| Continuous Freight Assurance | Historical planning band: $60,000–$150,000 annual base; larger accounts $150,000–$300,000+ | Agreed recurring checks, exception review, credit tracking and reporting | Paid work demonstrates ongoing value, reviewer capacity and recurring margin |

Large-account bands are future hypotheses, not the initial sales target. Recurring pricing is not enforced by the current pilot activation catalog and needs its own explicit scope, agreement and operating readiness.

### Reconcile historical offers before quoting

The saved September 18 landing-page artifact describes a free 20-invoice sample and $0 setup plus 20% contingency. That conflicts with the internal fixed-fee ladder. The artifact does not prove what any prospect accepted.

- Identify each prospect's dated proposal/site version and any acceptance. Preserve terms already offered or agreed; do not retroactively charge a previously offered free sample.
- Confirm the operative offer before a follow-up, quote or invoice. Do not combine fixed and success fees by implication.
- A historical/free 20-invoice sample is bounded feasibility work, not proof of annual savings, an error-rate estimate or subscription value.
- Any new lower-priced pilot requires coordinated changes to the offer definition, activation catalog, charter validation, fixtures and customer-facing copy. Do not bypass fee validation or reuse an existing offer name for materially different terms.
- Accepted engagement changes follow the existing amendment process.

The paid blind-test clock targets **10–15 business days after complete inputs and authorized kickoff**, subject to agreed scope and reviewer capacity. Carrier response and settlement are separate and are not promised within that window.

## The report is the product

Every report contains an executive decision summary, complete invoice disposition register, supported finding packets, unresolved-evidence requests and the blind comparison. Show separate totals for reviewed discrepancies, validated findings, challenger-only validated findings and uniquely attributable realized amounts.

Each supported packet identifies the invoice/shipment, controlling term/effective version, source page/cell/segment, reproducible expected charge, observed charge, exact discrepancy and next decision. Account for clean, unsupported, excluded and unresolved records so a small finding count cannot conceal low coverage.

Review every asserted finding before delivery. Independently review a predeclared sample of non-flagged records to look for missed problems and disclose the sample limits. Missing or ambiguous authority, identity or required evidence remains REVIEW / $0 asserted; uncertain settlement remains $0 realized. Model confidence is never commercial authority. An extractor/rater must not certify its own conclusion without independent review.

Incumbent output remains sealed until buyer-owned truth is frozen. Customer records are read-only during the initial pilot unless a separately approved workflow applies. Carrier contact requires a specific approved action; this model authorizes no external communication or money movement.

## Recurring value and revenue

Recurring work must solve an ongoing problem: review workload, unresolved credits, changing rates, repeat accessorial errors or billing-control gaps. Historical recovery alone does not justify a subscription.

Track these separately:

- **Recovery:** uniquely allocated, externally evidenced credits/refunds/remittances, net of known reversals. Never charge success fees on incumbent-known, automatic/preexisting, unresolved, duplicate or unsupported amounts.
- **Corrected future charges:** observed corrections against agreed authority in an actual later invoice period. Short-sample annualization is not realized savings.
- **Time savings:** measured hours against a declared comparable baseline and agreed cost basis. Keep this separate from recovered dollars and prevent overlap.

Booked fees, cash collected and recurring contracted revenue are different fields. Recovery money belongs to the customer; only an earned agreed fee is Freight revenue. A clean pilot can support paid assurance value if the buyer wants it, but cannot prove recovery performance.

Recurring expansion requires a buyer-confirmed ongoing need, accepted priced scope, measured delivery cost, reviewer capacity and an explicit renewal/exit process.

## Economics and the million-dollar scenario

Use `freight/deal_economics.py` for fixed-fee qualification. Its commercial route does not authorize data access or launch. A diagnostic handling actual customer records needs a valid controlled-data path; metadata-only qualification does not require uploading those records.

- Preserve the current **50% fixed-fee gross-margin planning target** until evidence supports review.
- Cost intake, normalization, review, report revisions, support and founder delivery time at a loaded rate. Unpaid founder work is not zero-cost capacity.
- Measure recurring labor rather than assuming onboarding cost disappears.
- Deduct referral commissions and acquisition costs separately when assessing contribution and cash needs. Success-fee upside cannot rescue fixed-fee economics.
- The calculated analyst-hour budget is a scope limit. Narrow scope, revise a prospective offer through the controlled process or HOLD if expected labor exceeds it.

| Scenario, not forecast | Annualized recurring revenue | Status |
|---|---:|---|
| 28 retained customers × $3,000/month | $1,008,000 | Exploratory lower-scope model; monthly price is not validated |
| 14 retained customers × $6,000/month | $1,008,000 | Within historical annual planning band; willingness to pay unproven |

One-time diagnostics and unearned/variable recovery fees are excluded from recurring revenue. Annualized run rate is not first-year booked or recognized revenue, and revenue is not owner profit. Model churn, collection delay, onboarding capacity and concentration before funding growth.

At 28 customers, six delivery hours/customer/month requires 168 hours; 20 hours requires 560. Both are assumptions to test. Founder oversight, selling and technical upkeep are additional. The design requires paid specialist capacity rather than expecting the founder to perform all delivery alongside employment.

## Referral channel

Test one prospective partner after direct paid work establishes a repeatable deliverable. Initially the partner introduces a qualified buyer, Freight contracts directly with that buyer, and attribution is recorded before the proposal.

A **20% share of collected fixed fees for at most the first 12 months** is an internal negotiation hypothesis, not an offer made. The agreement must define attribution, excluded taxes/refunds, duration, payment timing and reversals. Separate compensation for review/delivery work from referral commission.

Buyer agreement governs partner data access. Partners cannot approve their own disputed findings or authorize carrier contact for the customer. Defer white-label software until multiple paying partners require the same workflow.

Measure qualified opportunities, paid conversions, acquisition effort, contribution after commission, quality, retention and concentration. Six partners producing four customers each is not an established channel.

## Hunter connection and learning

Hunter's capability graph and outcome adapter already exist. Connect specific delivery problems to existing research, then record what actually changed.

| Business need | Hunter assets | Acceptance measure |
|---|---|---|
| Lower intake effort | CAP-001 extraction; CAP-002 identity | Complete-population hours and false accepted facts |
| Defensible charge review | CAP-003 authority; CAP-004 rerating; CAP-005 shipment evidence | Supported findings, unsupported dollars and adjudication time |
| Honest recovery reporting | CAP-006 settlement; CAP-016 accounting; CAP-018 later returns | Unique allocation; duplicates/reversals accounted for |
| Reliable recurring feeds | CAP-007 proof; CAP-019 observation receipts | Missing/failed feeds stay unknown; coverage and freshness |
| Delivery resilience | Recovery-proof and failure catalogs | Verified recoverability of the approved operating path |
| Better commercial decisions | Search attribution, outcome adapter and cohort calibration | Paid conversions, full labor costs, contribution and retention |

Scientific/industrial catalogs can supply transferable methods or negative examples; they do not become freight features merely because they exist. A catalog score is not expected customer return.

For each adoption record the source revision, named gap, affected check, independent evaluation, integration cost, deployment route, rollback condition and target metric. Customer files and identifying findings stay in their controlled environment; only authorized minimized outcome summaries enter Hunter.

The existing [gap register](GAP_REGISTER.json) controls new freight searches. Using the corpus does not authorize a new hunt or widen a gap. Record actual results through [OUTCOME_RECORDING.md](OUTCOME_RECORDING.md).

Preserve the commercial-learning requirement: five unique buyer cohorts, five paid engagements and usable margin evidence from five buyers before automated repricing-review recommendations. Repeated work is collapsed to buyer-level medians; conversion estimates include sample uncertainty. The threshold does not prevent fixing an unsafe workflow, honoring a prior offer or a separately documented prospective offer experiment; none may be labeled empirically validated repricing.

The current calibrator detects recorded stage co-occurrence within buyer cohorts; it does not establish the chronological order or elapsed time of diagnostic-to-pilot-to-annual conversion. Preserve dated stage events and follow-up windows separately before interpreting those ratios as a timed funnel or forecasting retention.

## Advancement and stop rules

1. Reconcile public availability and offer versions; prepare the buyer-safe report and qualification packet.
2. Complete an authorized bounded feasibility review if the prospect accepts its existing terms.
3. Deliver three paid pilots to measure demand, input burden, quality and full cost.
4. Obtain at least two repeat-paying customers for an explicitly scoped ongoing service.
5. Add one tested referral relationship and enough paid reviewer capacity.
6. Expand toward ten retained customers after successive reporting periods demonstrate capacity, margins and retention; then evaluate million-dollar scenarios.

These are internal milestones, not automatic production approvals. Pause and repair the offer when inputs remain unavailable, qualified buyers will not pay, work exceeds the priced budget or recurring reports lack value. Repeated objections require revisiting customer/problem/scope rather than promising higher savings.

Any unsupported dollar claim, lost evidence lineage or material data-handling failure stops affected output until reviewed. Do not hide REVIEW/excluded records to improve metrics. Do not build another TMS, generalized OCR engine, payment service or self-service portal without a named customer need and positive expected economics.

Weekly scorecard: qualified prospects and next steps; offer versions; ready/blocked inputs; paid engagements; labor vs budget; evidence quality; customer decisions; specifically approved external actions; cash collected and unpaid costs.

Monthly recurring scorecard: active paying customers; contracted recurring fees; collections; new/lost/renewed accounts; contribution; partner costs; onboarding/review load; source coverage; reversals; customer-confirmed value and concentration. Every commercial claim links to direct evidence.
