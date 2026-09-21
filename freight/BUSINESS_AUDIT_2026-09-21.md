# Freight business audit and upgrade — 21 September 2026

## Decision

Build a focused, evidence-led freight audit and assurance service. Use Hunter to improve the reliability and delivery economics of that service. The next growth constraint is an accessible customer entry point, a verified delivery environment, and a paid buyer outcome—not the number of repositories collected.

The business is **pre-validation in the evidence reviewed**. This is a review of available records, not a conclusion that the owner has no revenue elsewhere. No current P&L, bank reconciliation, signed customer contracts, or live CRM was supplied. Do not describe the repository as a revenue-producing SaaS or the $1 million goal as a forecast.

## Evidence and scope

- Initial source snapshot: `P00NSMASHER/github-value-hunt-ledger@522ea934b278b85abd9a0e5a13451f8717ac858d`. The recursive inventory contained 694 entries. Retrieved all freight source, tests and control documents and ran the freight suite. Static review concentrated on commercial qualification, financial learning, reporting, settlement inputs, launch controls and CI. The analysis also used the canonical capability/outcome registries, selected graph/search lineage, business catalogs, learning reports and schemas. This was not a line-by-line review of every freight module, Hunter log or third-party repository.
- The Hunter connection classifies every capability in the canonical registry. That is the practical index into the broader research collection; unregistered or changed capabilities enter review. Merely finding a repository does not install it or prove freight applicability.
- `intelligence/outcomes.jsonl` contains one synthetic Freight PARTIAL record at the reviewed snapshot. Its revenue and customer-value fields are null. There is no direct external paid Freight outcome in that record.
- The saved 18 September `FreightLeak_Sales_Tracker.xlsx` records 104 prospects, 25 first-wave targets, 10 first touches and zero replies at that historical snapshot. Some entries need qualification or were removed. These are not current inbox counts or 104 qualified buyers. No outbound messages were sent during this audit.
- The saved 18 September `freightleak-v0.zip` is historical source, not verified live deployment source. It contains an empty-recipient `mailto:` and an older free-test/contingency offer.
- Browser review on 21 September of `https://freightleak-audit.netlify.app/` displayed Netlify **Site not found**. The connected project still lists that site, SSO for all visitors and disabled Forms. A hostname-derived deploy lookup returned 404 and was not treated as proof of a valid deployment. Public availability and actual access behavior require verification after source/deploy repair.
- Existing deployment evidence says the current customer-data route is BLOCKED and a separate environment is CONDITIONAL pending evidence. This audit did not provision a customer backend, relax access controls, or certify production security.

## Findings and disposition

| Priority | Finding | Business consequence | Disposition |
|---|---|---|---|
| P0 | Public freight URL returns Site not found | Prospects cannot evaluate or request the service there | Recover marketing source under `freight/site/`; configure a verified business inbox and reconnect the correct Netlify deployment before launch |
| P0 | No verified customer-data processing environment | A sales promise can outrun delivery readiness | Keep confidential intake gated; complete the existing separate-environment evidence route before accepting records |
| P0 | Financial inputs accepted nonfinite values, truthy flags and fractional cents | Invalid economics or misleading recovery totals | Hardened commercial inputs, exact settlement cents and boolean evidence flags |
| P0 | Report reconciliation relied too heavily on aggregate totals | A total could appear correct with the wrong finding evidence or attribution | Bind certificates to frozen finding proofs; validate fee attribution per finding; reject non-USD aggregation without an FX basis |
| P1 | Rounded margin could qualify a below-target engagement; free founder labor inflated margins | Revenue growth could consume the owner's time without adequate profit | Compare unrounded economics; require a positive loaded labor cost when hours are planned; reject overflowed figures |
| P1 | Existing settlement store handles reversals, but general report generation uses an in-memory ledger | An old report can overstate net recovery after a returned payment | Before live reporting, implement a snapshot-bound persistent-settlement adapter and reconcile every reversal; do not issue recovery totals from stale snapshots |
| P1 | Public historical offer differs from the newer fixed-fee model | Confused buyers and inconsistent commitments | Version offers; preserve previously agreed terms; new terms require an explicit accepted scope. Public recovery page asks for fit discussion rather than promising a universal price |
| P1 | No direct external commercial validation in reviewed outcome records | Price, acquisition and annual-conversion assumptions remain untested | Run the existing blind pilot with an authorized buyer; record actual delivery time, costs and customer acceptance |
| P1 | Hunter research lacks a concise freight operating view | More research can create work without improving customer outcomes | Add deterministic capability-to-freight mapping, source fingerprints, a ranked review queue and CI summary |
| P2 | Conversion summaries do not establish elapsed time or mature cohorts | Early stage co-occurrence can be mistaken for a reliable forecast | Treat rates as descriptive; retain dates, denominators, observation windows and failed/lost cases before forecasting |
| P2 | Hosted rights, production runtime and signed release evidence remain incomplete | Limits the claims supportable in enterprise diligence | Use the existing rights and release gates; exact component permission and deployment evidence must close each gap |

## Business design

### Customer and offer

Start with one shipper/3PL segment, one mode or carrier population, an identifiable controller/AP owner, accessible controlling agreements, and usable settlement records. Prioritize sufficient volume and complexity to support the fee. The initial $5M spend / 500 monthly invoices signal is a hypothesis, not proof of willingness to pay.

Sell a bounded independent acceptance test: evidence inventory, frozen scope, blind comparison, reviewed findings and an explicit statement of what could not be established. A clean audit is a valid result. A customer may buy monitoring, control assurance or reduced review time without any incremental refund, if that value is measured and accepted.

Keep diagnostic and pilot fees consistent with `BUSINESS_MODEL.md` and the activation code. They are internal offer priors, not market-validated prices. A pricing change must update the commercial documents, activation/charter constraints and customer-facing materials together. Do not silently replace a previously offered free test or signed contingency engagement.

### Acquisition and conversion

Repair the website and verify the request reaches the chosen business inbox before using it in outreach. Qualify existing prospects for actual buyer role, invoice volume, source readiness, incumbent process, urgency and purchasing authority. Count confirmed conversations and authorized populations, not scraped contacts, as traction.

Respect the existing one-touch outreach policy: no second outbound contact without a reply. The audit and code changes create no new outreach authorization. Prepare evidence-backed examples using synthetic or separately permitted data; never turn a demo variance into a customer savings claim.

### Delivery and capacity

Start with one concurrent pilot and a named owner for review, customer communication and settlement reconciliation. Log preparation, analysis, correction and reporting time. Quote scope only when the fixed fee covers loaded delivery cost at the internal margin target. Recovery fees are upside after evidence, not a subsidy for underpriced labor.

When repeatable paid work exceeds available founder hours, fund analyst/reviewer capacity from demonstrated contribution margin. A fractional freight specialist may improve judgment and throughput; AI does not supply missing commercial authority. Hiring or contracting is a later budgeted decision, not an action performed here.

### Cash and retention

Separate contracted fees, recognized service revenue, invoiced receivables and cash collected. Document billing milestones, payment terms, dispute handling and agreed scope changes in each engagement. Forecast cash using actual collection timing; a signed annual contract is not immediate cash.

For retention, review evidence quality, review hours saved, false positives, confirmed findings, net realized recovery, service timeliness and buyer adoption. Earn expansion from demonstrated value in the same population before adding new modes, integrations or business units.

## A transparent route to $1 million

These are arithmetic scenarios, not forecasts or validated prices:

| Model | Example volume | Annualized revenue | Critical constraint |
|---|---|---:|---|
| Continuous assurance | 12 retained accounts at $84,000/year | $1,008,000 recurring run rate | Prove ongoing value and enough delivery/review capacity |
| Project service | 50 pilots at $20,000 | $1,000,000 project revenue | Approximately one new completed pilot each week; heavy selling and delivery burden |
| Recovery-only | 20% of $5,000,000 uniquely attributable realized recovery | $1,000,000 contingent fees | Requires actual collected recovery, attribution and reversal-aware settlement records |

The preferred destination is recurring assurance supported by paid, bounded pilots. Do not count pilot fees twice when credited against annual contracts. Twelve accounts acquired evenly over a year will not produce a full $1.008M of first-year recognized recurring revenue. $1M revenue is also not $1M profit or owner income.

At 50% gross margin, $1M revenue produces $500,000 gross profit before sales, overhead, owner compensation not included in delivery cost, tax and other expenses. For illustration, twelve clients needing twenty delivery hours per month require 240 monthly hours before sales and administration. That is not a passive solo business. Replace all example hours, margins and conversion assumptions with measured cohorts before staffing or spending decisions.

## How Hunter contributes

`HUNTER_CONNECTION.md` documents the working connection. The bridge reads the canonical capability registry, evidence relationships, outcome lineage and gap register; it outputs a review queue. Each applied capability has a freight use, limitation and measurable acceptance test. Evidence changes return the capability to review.

Prioritize extraction quality, controlling authority, deterministic charge calculation, identity resolution, evidence sufficiency, settlement attribution and reliable operational execution. Use search failures and rejected approaches to avoid repeated mistakes. Defer unrelated datasets and technology until a paying workflow exposes a concrete need.

Learning means recording test and customer outcomes and changing priorities after review. It does not mean the software automatically trains a model, imports all third-party code, grants research access to customer files, changes prices or deploys itself. Raw customer records stay in the approved customer environment; only authorized, minimized outcome metrics should enter Hunter.

## Business red-team scenarios

| Challenge | Required response / exit condition |
|---|---|
| A high-confidence extraction uses the wrong contract revision | REVIEW and no asserted entitlement until controlling authority is established |
| The incumbent already identified the same credit | No incremental recovery fee for that finding |
| A payment is reversed after a report | Reconcile persistent net settlement, issue corrected totals and adjust any fee treatment under the agreement |
| The first pilot finds no unique overcharge | Report the clean result; measure assurance/time value and let the buyer decide whether to continue |
| Sales volume rises but analyst cost exceeds the fixed fee budget | Narrow scope, improve a measured bottleneck, revise future pricing or decline work |
| A Hunter result changes or adds a dependency | Review source, applicability, permissions and acceptance evidence before integration |
| The largest customer leaves | Track concentration and cash runway; do not extrapolate one account's economics to the portfolio |
| The founder is unavailable for a week | Maintain a named backup reviewer, customer status record and exception queue before committing to a service level |

## Execution sequence

1. **Launch repair:** choose the business inbox; build the recovered public-only site; identify/reconnect the actual Netlify source and verify public access plus one controlled inquiry. Keep document uploads disabled.
2. **Delivery readiness:** complete the selected controlled environment evidence, exact pilot scope, customer authorization and permitted input route. Integrate persistent net settlements into reports before live recovery reporting.
3. **First proof:** complete one bounded buyer pilot; measure total effort and fixed-fee margin, including founder labor. Record a clean result or defensible findings honestly.
4. **Repeatability:** complete several independent buyer cohorts. Review delivery variance, buyer objections, loss reasons and source availability before changing the offer.
5. **Scale:** sell annual assurance only after ongoing value and capacity are demonstrated. Track retained annual run rate separately from project revenue, collected cash and profit.

The included code changes improve internal controls and research-to-product review. They do not by themselves activate a customer service, produce revenue, sign a customer or repair the hosted site.
