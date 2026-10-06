# Monetization Execution Sprint — 2026-10-06

Status: ACTIVE execution contract.

## Objective

Convert the Hunter portfolio into the first externally verified commercial outcome. Repository count, internal tests, synthetic savings and architecture work are not success metrics.

## Portfolio order

1. Freight Recovery — primary commercialization lane.
2. AP Supplier-Credit Recovery — fallback lane if the Freight acquisition gate fails.
3. Partner / Commission Payout Assurance — hold until either Freight or AP produces external buyer evidence.
4. Recovery Proof SLA — hold until a named buyer or channel appears.
5. All other Hunter opportunities — no product build unless a paying workflow exposes a concrete gap.

## Primary success condition

The sprint is successful only when the outcome ledger contains an independently evidenced external buyer outcome tied to a specific initiative. Revenue and recovered-customer-value remain zero until supported by the existing outcome/settlement evidence rules.

## Freight execution sequence

### Gate F0 — public acquisition surface
**Status: PASSED 2026-10-06. Day 0 starts 2026-10-06.**

Evidence: main-branch `RecoveryOS Public Sites` run 37475067758 passed verification and deployment; the public site was independently opened at `https://p00nsmasher.github.io/github-value-hunt-ledger/`; its CTA targets `jayp19386@gmail.com`; and a controlled non-sensitive inquiry was delivered to that inbox.

Required:
- business contact selected: `jayp19386@gmail.com`;
- `FREIGHT_CONTACT_EMAIL=jayp19386@gmail.com` is already configured in GitHub Actions variables;
- confirm `FREIGHT_CONTACT_VERIFIED=1` is present;
- successful `freight-site-pages.yml` verification and deployment;
- controlled inquiry proving the public CTA reaches the configured inbox.

The contact is owner-approved and the email variable is already configured. F0 still requires the verification flag plus a successful deployment and controlled inquiry.

Until F0 passes:
- do not claim the site is live;
- do not accept customer freight records by ordinary email;
- continue only non-sensitive qualification preparation.

### Gate F1 — qualified buyer
Target ICP:
- shipper or 3PL with material freight spend/volume;
- identifiable freight/AP/controller decision owner;
- invoices plus supporting rate/contract/shipment evidence available;
- prior-audit/active-claim conflicts known;
- willingness to use an approved secure intake route.

Qualification uses `freight/lead_qualification.py`. Interest alone is not qualification.

### Gate F2 — secure intake
Before confidential records:
- approved customer-data environment;
- written bounded scope;
- buyer/records owner identified;
- exact date/population/mode/carrier scope;
- permitted transfer route;
- reviewer capacity reserved.

### Gate F3 — blind audit
Freeze and hash:
- population;
- controlling authority;
- independent expected output;
- incumbent output before opening it for comparison.

No unresolved authority, identity or evidence may create asserted recovery dollars.

### Gate F4 — authorized recovery
Only buyer-approved supported findings proceed. Pre-existing, incumbent-known, duplicate, automatic, unsupported and excluded amounts are not fee eligible.

### Gate F5 — settlement and first commercial outcome
Require buyer-verifiable credit/refund/remittance or other engagement-approved realized benefit, unique attribution, reversal handling and outcome-ledger evidence.

## Acquisition operating rule

Do not build more Freight features merely to avoid selling.

For each candidate buyer, record only non-sensitive operating metadata in the approved private state:
- source;
- buyer role confirmed?;
- records owner confirmed?;
- approximate spend/volume band;
- source readiness;
- prior audit/claim state;
- qualification state;
- next permitted action;
- stage timestamps.

Do not put prospect PII or raw messages in the public repository.

## 30-day decision clock

Day 0 begins when F0 passes.

By day 7:
- at least 20 ICP-fit candidates reviewed;
- at least 10 first-touch attempts through permitted channels;
- every response classified through the qualification contract.

By day 14:
- target at least 3 real buyer conversations or equivalent substantive inbound qualification exchanges;
- at least 1 candidate at secure-intake readiness.

By day 21:
- target at least 1 explicitly authorized bounded audit population.

By day 30:
- target at least 1 completed real audit with buyer-reviewed disposition.

These are operating targets, not claims of expected conversion.

## AP fallback trigger

Activate AP Supplier-Credit Recovery as the primary acquisition lane if, after F0 + 30 calendar days:
- there is no authorized Freight audit population, OR
- repeated qualified-buyer feedback shows the Freight offer/data burden is the dominant blocker.

Do not trigger AP merely because Freight has not yet produced a recovery. Sales-cycle latency and lack of buyer access are different failures.

## AP first offer

Read-only Credit Balance & Statement Recovery Diagnostic:
- historical AP/ERP exports;
- supplier statements where available;
- no ERP writeback;
- deterministic duplicate/overpayment/unapplied-credit/debit-balance checks;
- independent entitlement review;
- realized value only after supplier credit/refund/allocation evidence.

Use file/DBA exports first. Do not delay the first paid diagnostic for live ERP integrations.

## Engineering freeze

Until F1 or the AP fallback trigger:
- no new horizontal platform;
- no speculative connectors;
- no new vertical product UI;
- no broad repository hunt justified as commercialization;
- no customer-data ingestion into an unverified environment.

Allowed engineering:
- fix a blocker that prevents F0-F5;
- reduce measured delivery/review time;
- fix a false-positive or evidence-integrity defect;
- implement a connector explicitly required by an active qualified buyer.

## Weekly scorecard

Track:
- F0 status;
- ICP candidates reviewed;
- permitted first touches;
- substantive responses/conversations;
- qualified buyers;
- secure-intake-ready buyers;
- authorized audit populations;
- audits completed;
- buyer-supported findings;
- authorized recoveries;
- realized customer recovery;
- invoiced fee;
- collected revenue;
- analyst/reviewer hours;
- blocker category.

The only headline commercial metrics are external outcomes, realized customer value and collected/contracted revenue under the canonical evidence rules. Internal repository activity is supporting telemetry only.

## Immediate blockers

1. F0 is closed. The public acquisition surface is live and the controlled contact path is verified.
2. Buyer-specific authorization is still required before confidential intake, even though the verified separate single-tenant environment is available.
3. No external buyer outcome is currently recorded in `OUTCOMES.md`; acquisition and qualification are now the active bottleneck.

## Stop rule

Once a real buyer exposes a concrete missing capability, reopen targeted Hunter work for that named gap. Until then, commercialization outranks discovery.
