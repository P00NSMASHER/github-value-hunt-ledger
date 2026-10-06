# Freight Recovery Free Advertisement Engine

Status: ACTIVE

The engine is designed to create buyer conversations without paid media. It treats free acquisition as five separate channels that can be measured and improved independently.

## 1. Outbound email

- Use verified public business contacts only.
- Keep prospect PII and message bodies out of the public repository.
- Start with controlled daily volume and scale gradually.
- Pause if hard bounces reach 3% or higher.
- Use a maximum of two follow-ups; opt-outs are permanent suppression.
- Primary metric: qualified conversation, not opens.

## 2. Organic search

Four high-intent pages are now part of the public build:

- freight-audit-services.html
- freight-invoice-audit.html
- freight-overcharge-recovery.html
- accessorial-charge-audit.html

Each page links to the free audit and to the other resource pages. The sitemap exposes them to search engines.

Next expansion should be driven by observed query demand, not page-count vanity.

## 3. Free business profiles and directories

Priority free profiles:

1. Google Business Profile
2. Bing Places
3. Apple Business Connect
4. LinkedIn Company Page

Use the same Freight Recovery name, site URL, business email and business address everywhere.

Business address:
715 Yorktowne Road
Pottsville, PA 17901

## 4. Referral channel

Target advisors who already have trust with freight-heavy businesses:

- CPA/accounting firms
- fractional CFOs/controllers
- AP automation consultants
- transportation/logistics consultants
- outsourced bookkeeping/AP providers

First offer: introduce a client for a free freight audit. No referral economics should be promised until terms and compliance are reviewed.

## 5. Evidence-led content

Publish practical material that is useful without inventing customer outcomes:

- freight audit checklist
- common accessorial evidence gaps
- duplicate freight invoice controls
- difference between potential recovery and actual recovered funds
- what finance/AP should gather before a freight audit

Cadence: two useful posts per week until actual customer evidence determines which topics generate conversations.

## Attribution

Every externally posted free link should carry UTM parameters. The site preserves UTM source/medium/campaign/content in the browser event stream and includes source tags in the prepared audit-request email without browser storage.

Example:

`?utm_source=linkedin&utm_medium=organic&utm_campaign=freight_audit_launch&utm_content=accessorial_post`

## Daily operating loop

1. Update the aggregate growth snapshot.
2. Run:
   `python -m freight.free_growth_engine freight/fixtures/free_growth_day0.json --format markdown`
3. Execute the highest-priority action.
4. Record only aggregate counts in the public operating ledger.
5. Buyer/prospect identities remain in approved private systems.

## Headline metrics

- verified first touches
- hard-bounce rate
- substantive replies
- qualified buyers
- secure-intake-ready buyers
- authorized audit populations
- organic/search source of each inquiry
- referral source
- actual external revenue and customer recovery

Clicks, impressions, repository commits and content count are supporting telemetry only.
