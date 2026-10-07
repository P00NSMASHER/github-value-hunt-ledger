# Freight Recovery — buyer experience audit

Audit date: October 7, 2026

The public freight website now presents a coherent, professional service: navy and white, readable sans-serif headings, consistent controls, clear fees, and directly accessible sample work. The remaining confidence gaps are operational identity and inquiry delivery, plus publication and authenticated testing of the portal draft.

## Reviewed scope

Reviewed the freight homepage and supporting-page design system, inquiry flow, pricing calculator, Trust Center, privacy/about/engagement content, worked audit example, fictional recovery dashboard, public download build, wider RecoveryOS marketing page, portal login and workspace source, outbound/referral templates, buyer-report template, and a small sample of recent sent email. This is an assessment of accessible customer touchpoints; it does not certify operational capacity, security compliance, or actual recovery performance.

## Findings and work completed

| Touchpoint | Buyer concern | Improvement |
| --- | --- | --- |
| Main website | Long page with repeated explanations and inconsistent visual hierarchy | Consolidated repeated sections; calmer copy; useful sample links before downloads; expanded resources behind one disclosure |
| Supporting pages | Large narrow headlines push substantive content below the screen | Shared readable headings, compact hero areas, consistent navigation and spacing |
| Pricing | Configuration language feels unfinished | Clear fee illustration; agreed rate and exclusions remain subject to written terms |
| Sample dashboard | Separate beige/Arial styling breaks the company identity | Shared navy header, readable financial cards, clear fictional-data notice |
| Inquiry | A buyer could confuse a prepared email with a submitted request | Preserved explicit email-app handoff, copy/edit fallbacks, and non-sensitive first step; no false sent confirmation |
| Trust and engagement | Defensive prose and implementation terminology create uncertainty | Shorter task-oriented explanations; no invented credentials, certifications, customers, or guarantees |
| Broader RecoveryOS page | Different green/acid palette, oversized serif headings, tiny labels | Matching navy/white/cobalt presentation; readable cards and form; recovery-area availability must be scoped before engagement |
| Portal draft | Tiny text, opaque headings, tablet navigation reduced to unlabeled dots | Readable type, labeled tablet navigation, clear task headings, company/support links on login |
| Portal review wording | Static “Verified contract term” suggests verification the display did not establish | Changed to “Source authority requires review” with a concrete review instruction |
| Outbound/referral templates | Internal audit terminology obscures the offer | Plain explanation of past-invoice review, evidence, and actual-recovery fee; retained opt-out and pre-send controls |
| Buyer-report template | Hashes and machine statuses precede the buyer's decision | Decision-at-a-glance, named owner, report date and next action first; traceability moved to an appendix |

## Remaining priorities

| Priority | Gap | Concrete next step |
| --- | --- | --- |
| High | Public address contains an unrelated GitHub username/repository; business contact is personal Gmail | Establish a company-owned domain and matching mailbox. Keep existing URLs and email operational during migration. No domain purchase or mailbox change was made in this audit. |
| High | Inquiry delivery depends on the buyer configuring and sending from an email app | Add a managed intake endpoint with validation, abuse controls, durable routing, delivery monitoring, and an honest confirmation state. Until then retain the clear current handoff. |
| High | Portal visual draft remains unpublished | Review the pre-existing import/economic-guard backend draft together with the visual draft, then deploy a coherent tested release. The publisher releases the entire draft; publishing visual work alone was unavailable. |
| High | Authenticated portal, secure intake, claims, and settlement journey were not exercised | Run a synthetic customer acceptance journey in an authorized test workspace: invitation, sign-in, records, review, authorization, export and status. Do not use live customer files or initiate payment/claim actions merely to test appearance. |
| Medium | Recent sampled emails use a personal sender identity and dense technical copy; public customer-support routing appears in outreach | Adopt one verified sender display name and company signature; use the revised concise templates and account-level pre-send gate. Prefer the correct freight/finance business owner rather than customer-service queues. No messages were sent. |
| Medium | Several closely spaced messages appeared in sent-email search results | Reconcile recipient aliases and account-level history before another touch. The search observation alone does not establish a duplicated campaign or opt-out violation. |
| Medium | Generated operational reports have not been visually accepted as a complete customer package | Use the revised executive template and shared sample presentation to standardize real exports; review a synthetic full report before promising a production format. |
| Medium | Mobile and tablet responsive rules were reviewed in source, but this browser did not expose viewport resizing | Complete real device visual acceptance at 390, 768 and 1024 px; check no horizontal page scrolling, visible navigation labels, readable tables and 44 px controls. Do not call source review a rendered mobile test. |

## Company presentation standard

- Use the same navy, white, cobalt and sans-serif hierarchy in web, portal, proposals, reports, and email signatures.
- Put the buyer's question, supported result, and next action before methodology or technical identifiers.
- Use real named contacts and verified company routes. Keep full sender identity and postal address in outbound correspondence.
- Distinguish candidate discrepancies, reviewed findings, authorized claims, settlement and fee eligibility in every financial presentation.
- Label synthetic data clearly. Add customer proof only with evidence and appropriate permission.
- Show what happens next: responsible person, requested action, agreed timing, and a reliable support route. Do not invent response-time promises.
- Preserve written engagement boundaries and existing authorization controls; visual polish must not imply capabilities or approval that do not exist.

## Verification record

- Freight Pages release: 64 pytest tests and 20 subtests passed locally; outreach guard and reservation integration checks passed; JavaScript syntax checks passed; exact public build allowlist passed.
- GitHub pull request #265 passed all checks and merged; updated freight homepage and worked example were inspected live after rollout.
- Additional product-page/template changes are separately verified and released, with live inspection recorded in the final handoff.
- Portal visual draft typechecked clean. It was checkpointed, not published; authenticated runtime behavior remains unverified.
- No customer records were uploaded, no claims/payments were initiated, and no outbound messages were sent during this audit.
