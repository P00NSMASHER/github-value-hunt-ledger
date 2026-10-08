# RETALLY | Final Commercial Launch Control Memorandum

**Evidence date:** 2026-10-08. **Decision authority:** Business owner, buyer-specific authorized reviewers and appropriately qualified counsel. **Status: LIMITED MARKETING READINESS; NO-GO for confidential customer intake, carrier recovery and recovery-fee invoicing.**

**This is the authoritative release-decision register.** The companion `RETALLY_FINAL_LAUNCH_HANDOFF_20261008.md` supplies operator context but does not independently authorize customer activity. Final decision evidence and GO/NO-GO gates in this file take precedence over stale draft assumptions. Reuse this existing source and release candidate, not additional laboratories, CRMs, questionnaires, parallel release branches or automatic customer-payment systems. Update evidence here when an independent owner actually closes a gate. Repository CI and synthetically rehashed evidence cannot certify external signatures, bank postings, legal registration or customer outcomes.

## A. Confirmed live facts, not future promises

| Area | Verified observation | What this does not prove |
|---|---|---|
| Marketing site | Cloudflare Pages project retally-web serves RETALLY-branded domains; successful canonical deployment at https://f1fc54e1.retally-web.pages.dev on October 8 | That forms can deliver leads, or that user-visible commercial changes on this draft are live |
| Client application | Floot Freight RecoveryOS is published at https://freight-recoveryos.floot.app; Floot lists no attached custom domain | That payment/settlement processing, tenant isolation or production financial integrations have passed acceptance |
| Direct online inquiry | Pages production FREIGHT_INQUIRY_ENABLED=0 and FREIGHT_INQUIRY_MAILBOX_VERIFIED=0. Cloudflare sending API token absent. Turnstile and D1 bindings are present | That the endpoint may accept real leads; do not silently enable either flag |
| Email draft | Public browser supports a user-prepared email to the RETALLY business address, and integrated PR #329 improves mobile fallback and displays recipient | That the visitor sent mail, that Zoho received it or that an inbox was reviewed |
| Commercial rate | freight/commercial_terms.py has a **30% standard working default**; draft public site renders it without JavaScript and shows it to buyers | A signed, buyer-specific rate, exclusion schedule, legal identity or earned receivable |
| Source safeguards | This branch integrates qualified lead routing, prior-auditor suppression, correct freight scope, strict consent, proof-bound nonbillable recovery-fee calculations | The security, quality or accuracy of the live Floot application or buyer/accounting authenticity |
| Collateral | Original PR #300 was closed without merge after its assets and source were consolidated in still-open draft PR #327. PDF/DOCX tests and visual review do not clear customer publication. | That the inherited synthetic scenario is a verified customer recovery or that every dollar is allocated |
| Financial software | Staging kernel PR #299 and later isolated PostgreSQL/QA acceptance work exist | That guarded transactions are wired to production RecoveryOS or that SETTLED equals cash received |

**Precise meaning of 'ready':** RETALLY may display accurate, non-sensitive marketing and have founder-led discovery conversations. A lead, signed engagement, confirmed recovery and paid customer are four different states. None of the last three may be claimed without evidence.

## B. Source-control map and single release candidate

**Integration PR:** https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/329 (DRAFT, target main; source review only). The PR consolidates:
- PR #311: qualifying an actual invoice population, identifiable carrier and mode, explicit prior-auditor status, human overlap review and rejection of nonboolean evidence.
- PR #320: optional fixed-fee Charter, Amendment and engagement resolution rejecting false-string consent, unsupported states and spoofed authority.
- PRs #317 and #326: actual 30% contingency engagement requiring valid buyer/RETALLY consent, frozen audit identity and claim chronology; settlement proof computes a **nonbillable** candidate record with billing_authorized=false.
- PR #305: configurable rate included in statically built HTML, including no-JavaScript and search previews.
- **Merged PR #330:** preserves unresolved inquiry records by removing request-time automatic deletion. This integration explicitly reconciles that already-merged hotfix with PR #307's safer provider-recipient acknowledgement. Do not reintroduce unconditional 90-day row purges. Separate PRs #321 and #332 contain draft retention/case operator security changes that are NOT production-approved and are not automatically merged here.
- PR #307: proposed **up-to-20 eligible invoice** free-audit copy, bounded staff time, verified-recipient notification handling, email fallback, and regression tests. The provider token and production flags remain OFF.
- Mission 2G/2H evidence and zero-upfront cost models already present in this integration branch: reusable **internal synthetic HOLD** models only. Hypothetical 20% rate examples in that research are NOT the working 30% customer rate or a real discount.

**Other dependent work remains separate:**
- PR #298: merged visual/trust updates. Do not overwrite its current-main changes.
- PR #300: closed without merge and superseded by open draft PR #327 for collateral and commercial acceptance. Financial sample reconciliation, approved legal identity and customer-facing distribution signoff remain blocked. PR #327 is not merged and its collateral should not be confused with the first-customer gate files copied into PR #329.
- PR #303: earlier customer-readiness register. Its 25-invoice initial hypothesis does not override the latest proposed **20-invoice cap** in the current integration offer.
- PR #312 (and research ancestors): exact-cent profitability model, **not** real recovery probability, operating budget approval or customer revenue.
- PR #299 (plus related staged database work): independent financial integrity staging, **not** a production DB migration, cash attestation, or authority to issue an invoice.

**Release safety:** An integration PR can mix marketing-site and Python commercial changes. Merging into main can trigger GitHub/Cloudflare publication or other deployment workflows. Do NOT merge this draft casually or as a substitute for release approval. Do not separately merge overlapping #305/#307 sources without reconciling their files and rerunning CI. No old draft should be auto-deleted merely because its changes were copied.

## C. Final release gates

| ID | Decision / allowed work | Verified closure evidence | Current verdict | Responsible owner |
|---|---|---|---|---|
| G0 | Public informational marketing | Canonical HTTPS Pages deployment and accurate sample/pricing terms | **GO** for informational website only | Site owner |
| G1 | Reliable business-contact intake | Approved sender service; least-privilege server-only token; two same-reference submissions matched end-to-end HTTP/D1/provider/**actual Zoho inbox**; mobile/desktop QA and human pending-review ownership | **NO-GO** for direct POST; prepared email only, receipt unverified | Business mailbox owner / site engineer |
| G2 | Verified legal contracting and 30% commercial scope | Registered legal identity, permitted trading name, counsel-reviewed signed terms, actual agreed 30% or separately authorized rate, eligible recovery definition, prior-auditor exclusion, reversal/termination, invoice timing and authority | **NO-GO** for signing on unreviewed templates | Business owner / counsel / buyer signer |
| G3 | Customer-specific confidential manual workspace | Buyer permission, correct entity/scope, named access roster, MFA, data locality, device and storage checks, controlled transfer, retention/deletion, independent reviewer reservation and buyer-approved launch-gate receipt | **NO-GO** for real invoices today; empty baseline environment is not authorization | Buyer IT + RETALLY security reviewer |
| G4 | Bounded free review | G2/G3 where required for document access; selection frozen to <=20 eligible invoices, one supported mode, normally no more than two carriers, 2–3 prelim analyst/reviewer hours or separately approved cap; signed scope and no incumbent overlap | **NOT STARTED** for real buyer | Commercial + qualified freight reviewer |
| G5 | Approved recovery actions | Unique evidence-backed invoice/rate findings, incumbent suppression, written claim-specific buyer approval before EACH carrier communication | **NO-GO** absent real agreement and delegation | Buyer approver + operations |
| G6 | Customer settlement / earned fee | Buyer-ledger-confirmed posted cash or usable credit, carrier remittance/credit, unique attribution, payment/return conservation, no duplicate prior-auditor fee, later reversal updates, independent financial review | **NO-GO** absent real buyer funds; Floot SETTLED or synthetic fixture is not proof | Buyer AP/controller + independent finance reviewer |
| G7 | Billing / live financial automation | G2–G6; exact once-only invoice ledger and contractual fee approval, posted-cash source attestation, production-representative concurrency/integration QA, explicit owner release | **NO-GO**; source fee record explicitly billing_authorized=false | Finance owner + engineering release authority |
| G8 | Customer collateral publication | Independent arithmetic and attribution validation, original approved brand assets, permissioned actual outcomes if any; sample plainly labeled illustrative; signed distribution release | **NO-GO** for unapproved financial claims | Brand lead + CFO/controller |

**Financial sample blocker:** The illustrative scenario originating in closed PR #300 and carried into open draft PR #327 shows $14,200 gross less $750 reversal = $13,450 net, while $11,800 is designated fee-eligible, leaving an **unexplained $1,650**. Until a source-bound allocation explains the gap, keep that fee-eligibility claim out of external materials. Arithmetic consistency does not certify attribution.

**The economic gate is also human:** The zero-upfront model must include founder/analyst/reviewer labor, acquisition, admin time, zero-recovery exposure and three-pilot cumulative downside. The research what-if model and 30% software default are not signed pricing or realized profits. Do not change price or guarantee returns based on simulated margin.

## C1. Final external-gate evidence check (2026-10-08)

**Decision: retain G1 and G2 as NO-GO.** This is the actual owner's shortest
verification path, not another technical subproject or an inferred approval.

### G1: company email receipts

- A fresh scoped search of the connected Gmail account for
  `to:jay@retallyrecovery.com after:2026/10/06` returned the two
  October 8 controlled messages **only with Gmail SENT labels**:
  "RETALLY inbound verification | controlled test 2026-10-08" and
  "RETALLY inbox delivery test | October 8". Gmail SENT is sender evidence,
  **not** evidence of Zoho delivery or recipient acknowledgment.
- **Independent read-only Cloudflare DNS inspection:** active zone
  `retallyrecovery.com` has Zoho MX records `mx.zoho.com` (priority 10),
  `mx2.zoho.com` (20) and `mx3.zoho.com` (50); Zoho-containing SPF,
  a `zmail._domainkey` DKIM TXT selector and a `_dmarc` record
  are present. This establishes configured mail-routing/authentication
  DNS records only. It **does not** prove mailbox acceptance, active
  internal Zoho user provisioning, SPF/DKIM authentication of any sent
  individual email, or arrival of either test message.
- The Zoho Mail inbox itself is not connected to an available read-capable
  account tool. A connector-directory lookup surfaced Zoho CRM but no direct
  Zoho Mail inbox connector; other mailbox connectors do not grant access to
  this business mailbox. Do not change MX, claim actual receipt, or use
  another mailbox's SENT folder as a substitute.
- **Owner action:** open the actual Zoho Mail Inbox (and Spam/All Mail)
  for `jay@retallyrecovery.com`. Locate both subjects and record exact
  sender, recipient, message ID, received timestamp and delivery header,
  without exposing message credentials. If neither is present, investigate
  the existing Zoho mailbox configuration using only the authorized owner
  interface. After authentic recipient evidence, the site operator still
  must separately prove API sender permission, stable D1/provider/Zoho
  reference correlation and mobile/browser experience before setting either
  direct-online-submission flag to `1`.
- **Gate remains blocked:** no recipient-side evidence was obtained in this
  execution. No new test message was sent or online intake enabled.

### G2: legal contracting and brand/trade-name use

- Public official Pennsylvania references:
  https://www.pa.gov/agencies/dos/programs/business/information-services/record-searches
  and https://file.dos.pa.gov/search/business .
  Pennsylvania says its business filing search provides registered entity/file
  number, precise name, status and filing details. The official
  automated page returned **HTTP 403** to public web retrieval; an
  attempted separate public browser lookup was unavailable. Neither
  an exact-name registered RETALLY entity nor a zero-result name-availability
  finding was established.
- The USPTO official mark search is https://tmsearch.uspto.gov/ .
  No completed live query/result set or confusion assessment was
  obtained in this execution; absence of search-engine hits is **not**
  trademark clearance. Similar names, actual commercial use and
  overlapping services require qualified legal review.
- **Owner/counsel action:** identify the actual contracting legal entity
  and supply the authoritative PA entity/file number or formation proof;
  confirm whether RETALLY is an approved legal name or registered fictitious
  name; separately perform documented USPTO and state mark clearance and
  approve the exact customer-facing seller name and signature block.
  Do not state an entity is registered, a mark is available, or contracts
  are enforceable without reviewed evidence.
- **Gate remains blocked:** no new formation, fictitious-name registration,
  trademark application, paid search/certificate or legal engagement was
  executed or authorized.

### Stop condition

These evidence gates require **owner, counsel and the actual Zoho recipient**
to verify records. GitHub source commits, self-reported attestations,
sample screenshots, generated legal language, DNS configuration and model
reasoning cannot close them. Leave production inquiry and customer-data
permissions disabled until their corresponding independent acceptance
criteria are met. Do not create further parallel missions or software systems
to substitute for this finite verification.

## D. One repeatable first-customer operating sequence

1. **Find and discuss, not assume:** Research a business with relevant freight operations. Speak about broad freight spend, carrier modes, existing auditor, buyer authority and document availability using non-sensitive metadata only. Do not equate a researched company with a qualified customer.
2. **Verify contact and seller:** Confirm the actual communication was received and answered, and settle the contracting party and lawful terms before making contractual commitments.
3. **Qualify and cap:** Explicitly resolve prior auditor status. Identify a freight mode, billed carrier, invoice period, governing rate sources and source owner. Apply the existing qualification function; treat any eligible result as routing, not approval. Reserve a bounded labor budget.
4. **Secure the exact records:** After buyer/IT/RETALLY authorized controls, freeze the agreed sample at up to 20 invoices, ordinarily one mode/two carriers, with governing agreements/amendments and payment/source records. Avoid files in public forms or ordinary email.
5. **Deliver the free summary:** Reviewer records how many invoices were checked, potential error categories, missing sources, confidence and limits. Potential opportunities and approved claims are never recovered cash. No unlimited claim-ready consulting for free.
6. **Obtain an accepted recovery agreement:** Signed scope and approved rate/eligibility; suppress incumbent-known or automatic credits; customer and RETALLY acceptance must be independently authenticated. This is **not** the optional fixed-fee Pilot Charter workflow.
7. **Seek separate buyer action approval:** Only submit explicitly authorized, evidence-supported carrier claims. Track communications, denials, expiry and attribution.
8. **Reconcile customer money:** Match paid refunds/posted credits, reversals and exclusions; independent controller confirms net and allocated amount. Do not treat unverified provider events as received cash.
9. **Calculate, then separately authorize billing:** Generate a proof-bound fee proposal, reconcile signed agreement, avoid duplicate invoices and apply contract-specific refunds. Charge only after recorded authorization and real settlement. The present Python result remains nonbillable.
10. **Measure and learn:** Record actual founder hours, independent review costs, lead time, disputed/settled value, customer-retained value and collected RETALLY fee. A signed pilot is not a paying customer until a legitimate RETALLY fee has been earned and collected.

## E. Finite implementation and release sequence; no more missions

**Step 1: Exact integrated-head CI.** Five PR #329 workflows have already passed at `c7c1c29e87e194872098479ecc970445939dc73b`: Freight Commercial Contracts, RecoveryOS Public Sites, RETALLY Inquiry CI, Visual Acceptance, and Repository Release Gate. The visual job explicitly skipped hosted staging, live iOS Safari submission, and WCAG rule checks, so these remain separate gates. Any subsequent commit needs new exact-head CI before code acceptance. No production deployment was performed from the draft.

**Step 2: Independent source & visual acceptance.** Compare final PR against current main, especially merged #298, and independently inspect mobile/desktop browser behavior. Review consent invariants and security of any contract/fee code. Approve only if all checks pass; preserve the default 30% fee and sample disclaimers.

**Step 3: Commercial external evidence, not more code.** Business owner and counsel resolve legal identity/contract; mail owner proves actual Zoho receipt or formally selects a working and authorized fallback; buyer IT signs exact workspace; qualified reviewer and controller accept scope, rates and cash provenance. These require real people and evidence, not more tests.

**Step 4: Controlled production release decision.** Only after separate authorized approvals for website and commercial software, review merge/deployment blast radius, establish rollback and make one bounded release. Keep direct inquiry disabled until G1 and payment/financial operations unavailable until G6–G7. Never silently change production environment flags.

**Step 5: First real customer review.** Execute a single permitted manual bounded engagement, then use observed cost and recovered-funds evidence to decide whether to open the second and third founder pilot slots. Do not launch subscriptions or a broad carrier automation lane prematurely.

## F. Outcome and stop condition

**Go for:** Approved non-sensitive marketing, source-code QA, sales research and preparing buyer/owner checklists.

**No-go for:** Claiming a fully operational paid recovery service, enabling direct online form acceptance, receiving confidential buyer files, carrier disputes, live settlement instructions or contingency invoicing without their independently accepted gates.

The implementation ends at a **reviewable integration release candidate** plus this single register. It is not a real-customer launch certificate. The next changes should be corrections to failed acceptance evidence or legally authorized activation, not another prompt or project.
