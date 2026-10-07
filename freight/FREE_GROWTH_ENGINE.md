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

**Eligibility-first, not citation-count-first (reviewed 2026-10-07).** The
business is currently presented as remote-first B2B freight auditing. A
Pottsville postal address does **not** establish face-to-face customer service
or walk-in hours. Do not invent in-person meetings, storefronts, business
phones, categories, or customer reviews to qualify for map listings.

Prioritize, after searching for and claiming any existing matching profile:

1. **LinkedIn Company Page — eligible free business page.** Authorized owner
   must use an authentic individual LinkedIn account. Match the current public
   offer, national service reach, and Pottsville base. Premium is unnecessary.
2. **Apple Business — eligible free business/brand registration**, including
   online-only and remote-service businesses. An Apple Maps *location place
   card* is not automatically promised merely by creating the brand.
3. **BBB Business Profile — free claim/request path, subject to BBB review.**
   A free profile is not BBB Accreditation; do not claim accredited status.
4. **Clutch Basic — free B2B service-provider profile, subject to service
   category fit and platform approval.** Do not force a freight auditor into
   an inaccurate agency/consulting category or purchase Verified.
5. **Manta Free Company Listing — free plan available, but verify the
   actual non-storefront service eligibility and address/privacy settings
   inside the application before submitting.** Lower priority than a
   relevant B2B profile.

**Hold/do not create:** Google Business Profile requires in-person customer
interaction during stated business hours. Bing Places requires an address
open to customers or employees who travel to customers. Neither is established
for Freight Recovery today; do not create a pretend service-area profile.
Yelp explicitly disfavours primarily B2B businesses. The Schuylkill Chamber
directory requires paid membership, which is not authorized for this free lane.

Search for the exact name **plus Pottsville and postal address** before any
registration, and claim a matching existing profile rather than duplicate it.
Public search not finding a listing does not prove none exists in an account
or pending verification queue. Track **proposed, submitted, verified and live**
as distinct statuses. See `freight/FREE_PROFILE_ASSET_PACK.md` for copy,
source policies, channel links, and an application-state checklist.

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
