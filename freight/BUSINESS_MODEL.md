# Freight Recovery — Commercial Operating Model

Updated: 2026-09-23

## Flagship offer

Freight Recovery enters the market with a **free recovery audit and a
success-based recovery engagement**.

- The initial audit costs the customer **$0 upfront**.
- The audit determines whether meaningful recovery opportunities appear to
  exist and whether a recovery engagement is worth considering.
- The customer receives a concise opportunity summary, not a claim-ready
  forensic package or the proprietary recovery playbook.
- If the customer authorizes Freight Recovery to pursue an opportunity, the
  engagement states the applicable contingency percentage before work begins.
- Freight Recovery earns a fee only on fee-eligible funds actually recovered
  for the customer. No recovery means no recovery fee.
- Recovery is never guaranteed.

The working default contingency rate is defined once in
`freight/commercial_terms.py` as `DEFAULT_CONTINGENCY_RECOVERY_RATE = 0.30`.
The public build, calculator, proposal workflow, and settlement arithmetic must
consume that value or an explicit engagement-specific override. It is an
adjustable commercial assumption, not a permanent promise.

Optional fixed-fee forensic work remains available by custom written scope for
buyers who prefer to pay directly and retain all recovered funds. It has no
public self-checkout and is not the launch offer.

## What the free audit includes

The free audit is a bounded qualification and opportunity-assessment service.
It may communicate:

- records and date range reviewed;
- detected opportunity categories;
- number or value of transactions flagged;
- a supportable potential-recovery range;
- confidence and important evidence limitations; and
- the recommended next step.

It does not automatically include every matching rule, exact dispute strategy,
claim-ready schedule, carrier correspondence, complete evidence packet, or
recovery operating instructions. Those artifacts are created and used within
an authorized recovery engagement. This boundary keeps the audit useful while
preventing unlimited free consulting or circumvention.

Potential recovery, approved claim value, and actual recovered funds are three
different states:

| State | Meaning | Fee treatment |
|---|---|---|
| Potential recovery | A screened estimate that still needs validation | Never feeable |
| Approved claim value | A supported amount authorized for pursuit | Never feeable merely because it was submitted |
| Actual recovered funds | A traceable credit, refund, remittance, or other agreed realized benefit received by the customer | Feeable only when the engagement makes it eligible |

## Customer journey

1. A visitor understands the $0-upfront, success-based offer.
2. The visitor completes the short qualification form. The public site requests
   business metadata only and does not accept freight records or credentials.
3. Freight Recovery reviews fit and issues an approved secure intake route when
   appropriate.
4. The customer submits the agreed records through that route.
5. Freight Recovery performs a bounded audit and produces an opportunity
   summary.
6. If no viable opportunity is found, the customer owes nothing.
7. If a viable opportunity exists, Freight Recovery presents scope,
   contingency percentage, authorization, data-use, confidentiality,
   termination, payment-timing, attribution, and anti-circumvention terms.
8. Only after acceptance does detailed claim preparation and recovery execution
   begin.
9. Settlement evidence is reconciled and any recovery fee is calculated only
   from fee-eligible actual recovered funds.

Checkout links and an upfront purchase are intentionally absent from this
entry flow.

## Qualification and capacity protection

The public form collects only the fields needed to route work: contact and
company, annual freight-spend band, monthly shipment band, modes, carrier
count, available history, invoice volume, record types, prior-audit status, and
known or suspected issues.

`freight/lead_qualification.py` maps that metadata to internal states:

- `HIGH_PRIORITY_RECOVERY_CANDIDATE`
- `QUALIFIED`
- `NEEDS_REVIEW`
- `INSUFFICIENT_DATA`
- `LOW_EXPECTED_RECOVERY`

These are routing signals, not customer promises. Analysts may override them
with a reason. Do not expose thresholds or a score that enables gaming.

Before substantial manual work, confirm a named economic buyer, an operational
records owner, a bounded population, accessible invoices and supporting
records, sufficient history, an approved data route, and available review
capacity. Use a representative sample or staged intake when the full population
would create disproportionate cost.

## Fee eligibility and attribution

The recovery-fee base excludes flags, estimates, pending claims, duplicate
amounts, unsupported amounts, pre-existing or incumbent-known efforts,
automatic credits, reversals, and any category excluded by the signed
engagement. `calculate_recovery_fee()` additionally prevents fee-eligible funds
from exceeding actual recovered funds.

Settlement evidence should independently identify the invoice or shipment,
amount, date, recovery path, customer receipt or posted credit, attribution,
and later reversal status. A later reversal requires recalculation and the
contractually appropriate fee credit or refund.

Recovery money belongs to the customer. Freight Recovery recognizes only its
earned fee as revenue. Booked fees, invoiced fees, cash collected, potential
recovery, and customer recovery are separate fields.

## Data, authorization, and evidence controls

The public GitHub Pages site is a static qualification surface. It does not
upload, transmit, or store customer freight files. Ordinary email is used only
to send the prepared qualification summary; the customer is told not to attach
records or credentials. Confidential data may be accepted only through a
route that has passed the applicable launch and security controls.

Customer data remains read-only during the initial analysis unless a separately
approved workflow says otherwise. Carrier contact, claim submission, dispute
activity, settlement acceptance, and money movement each require the authority
defined for that engagement. A marketing form or opportunity summary grants no
such authority.

Every asserted finding must retain source lineage and reviewer support. Missing
or ambiguous authority stays in review and contributes no asserted or feeable
dollars. Technical tests and synthetic demonstrations prove only the behavior
they exercise; they do not prove customer demand, production security,
recovery rate, or revenue.

## Engagement framework

The website describes the commercial workflow but does not fabricate legal
terms. A future agreement workflow must capture at least:

- parties, scope, covered entities, carriers, modes, dates, and exclusions;
- contingency rate and the definition of fee-eligible recovered funds;
- attribution window, pre-existing matters, automatic credits, and reversals;
- authorization for each external action;
- confidentiality, data use, retention, and deletion;
- invoicing, verification, payment timing, and dispute handling;
- termination and treatment of in-flight or later realized recoveries; and
- reasonable protection against use of Freight Recovery findings to avoid the
  agreed fee.

Final language requires qualified legal review. The public engagement framework
is explanatory and is not itself a contract.

## Measurement and learning

Track the funnel with stable names for landing view, free-audit CTA, form start,
form completion, secure data route, data submission, qualification, audit
completion, opportunity identification, engagement start and acceptance, and
actual recovery. Browser events must represent actions that really occurred;
operator and backend milestones are recorded only by the systems that know they
occurred.

For every accepted engagement, measure analyst and reviewer time, direct cost,
records reviewed, finding quality, claim value, actual recovery, fee-eligible
recovery, reversals, days to each stage, and contribution after acquisition and
delivery cost. The free audit must remain economically bounded even when no
recovery results.

Do not publish recovery statistics, testimonials, logos, case studies, security
certifications, or carrier relationships without direct permission and
evidence. The site intentionally reserves a proof area for future verified case
studies.

## Advancement and stop rules

Advance from qualification to audit only when the likely opportunity and
available evidence justify the review budget. Advance from audit to recovery
only when supported value, attribution, authorization, capacity, and expected
contribution justify the work.

Pause or narrow work when sources are unavailable, provenance is lost, scope is
unbounded, the expected recovery cannot support responsible delivery, the
customer will not accept attribution terms, or customer-data controls are not
ready. Never compensate for weak economics with a larger unsupported recovery
estimate.
