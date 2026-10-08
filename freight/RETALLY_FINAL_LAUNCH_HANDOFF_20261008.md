# RETALLY | Final Unified Commercial and Release Handoff

**Version:** Final integration review, October 8, 2026  
**Source-control home:** [Integrated Commercial Controls, PR #329](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/329)  
**Final independent verdict:** **NOT READY FOR LIVE CUSTOMER DATA, CARRIER CLAIMS, COLLECTIONS, OR PRODUCTION RECOVERYOS FINANCIAL OPERATIONS.**  
**Permitted now:** owner-led market research, nonconfidential discovery preparation, internal synthetic demonstrations, and controlled code review. No customer data is authorized by this file.

This document is a **supplementary operator handoff**. The canonical go/no-go decisions, release owners and current launch gate register are controlled by [RETALLY Final Launch Control](RETALLY_FINAL_LAUNCH_CONTROL_20261008.md). It is not a new platform, dashboard, laboratory, sales campaign, or production change. Use the existing source modules and PRs. Any updated fact requires dated source evidence; a green GitHub check or the word VERIFIED in a self-authored JSON file is not itself external proof.

## A. Actual business to sell

**Positioning:** Independent retrospective review of selected U.S. domestic **LTL** freight invoices for multi-location distributors already using AP, a TMS or an incumbent audit provider. Complement their current controls instead of proposing wholesale replacement.

**First offer:** Qualified **$0-upfront**, bounded diagnostic, initially **up to 20 eligible invoices** with a **2–3-hour preliminary analyst/reviewer budget**, subject to documentary fit and reserved qualified reviewer capacity. Results are a decision-oriented opportunity summary, not a carrier-ready claim package or guaranteed recovery.

**Five separations that every buyer must be able to verify:**

1. Frozen audit population versus excluded and incumbent-known economic issues.
2. Candidate discrepancy versus independently reconstructed contract/rate-backed finding.
3. Human-supported finding versus **separately approved** carrier dispute action.
4. Carrier's response or software SETTLED event versus **actually posted customer cash/credit**, net of reversal.
5. Net attributable recovery versus a fee base approved under **signed buyer-specific** terms. No verified posted customer recovery means no fee eligibility.

The `freight/commercial_terms.py` working default of **30%** is **not** evidence of a signed price. The separate zero-upfront underwriting fixture uses **20% as a hypothetical sensitivity assumption**, not a live quote. Existing optional fixed-fee pilot-charter machinery is NOT the default flagship service.

## B. Verified integration already completed in PR #329

Rather than open another parallel architecture, this branch integrates the pre-existing, independently reviewed commercial work:

- PR #311: strict lead qualification, carrier/mode evidence and explicit incumbent-overlap review.
- PR #320: buyer/RETALLY acknowledgments and invalid-consent rejection in optional fixed-fee charter/amendment workflows.
- PRs #317/#326: proof-bound recovery engagement and contingency-fee calculations, no fee purely from estimates, caller-supplied amounts or unverified postings; `billing_authorized=false` remains explicit.
- PR #327: copied existing first-customer evidence gate, controlled no-upfront underwriting, eight source files and fixture/docs into this same branch. The original PR is preserved, not merged or deleted.
- Integrated cross-boundary synthetic regression: `freight/commercial/test_final_commercial_boundary.py` checks that a high-volume already-audited lead is routed for human overlap review, and that unsupported contact/contract/intake, modeled revenue and unresolved sample finance **cannot authorize kickoff**.
- The existing `Freight Commercial Contracts` workflow runs the first-customer gate, zero-upfront tests and assembled smoke. No new scheduler, billing system or public portal was created.

**Independent local execution:** first-customer gate 8/8 tests passed; no-upfront underwriting 18/18 passed. Integrated test requires GitHub exact-head CI; do not infer a pass until its run finishes. The evaluator currently returns `all_customer_pilot_gates_ready=false`, `contact.ready=false`, `confidential_pilot.ready=false`, `claims_recovery.ready=false`, and `sample_publication.ready=false`.

## C. Production and review lanes, no duplicate merges

| Lane | Source | Verified current classification | Release dependency |
|---|---|---|---|
| Live website/branding | PR [#298](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/298) | **Merged** to main; visual/Trust Center remediation source exists | Independently confirm deployed revision, mobile views and real inquiry behavior; a merge does not certify deployed output |
| Public inquiry hotfix | PR [#330](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/330) | **Merged** to main; original unattended `DELETE FROM inquiries WHERE accepted_at < ?` removed | Verify production Pages revision and retention exception process |
| Online inquiry offer and provider ack | PR [#307](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/307) | Draft, not production active | Reconcile merged #330 source; read exact diff before merge |
| Retention + case deletion guard | PR [#321](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/321) | Stacked draft on #307; real disposable D1 QA, **not deployed** | Reviewed/legal-approved migration; no duplicate hotfix |
| Cloudflare Access operator actions | PR [#332](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/332) | Stacked draft on #321; synthetic JWT and D1 QA, **not deployed** | Verify real MFA/IdP, access app, separate humans and privileged SQL controls |
| Read-only inquiry aging | PR [#313](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/313) | Independent draft | Integrate with case disposition; avoid parallel CRM or scheduler |
| Commercial qualification, consent, cash proof and economics | **PR [#329](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/329)** | Unified synthetic/source-review candidate | Exact-head CI and contract/qualified reviewer approval |
| Customer material generators | PR [#300](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/300) | Draft, synthetic collateral; master asset transfer and actual financial eligibility are separate gates | Controlled legal/financial/brand sign-off before external publication |
| Public rate rendering | PR [#305](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/305) | Draft | Coordinate with current merged site build and contractual rate source |
| Pilot scope/evidence gate | PR [#327](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/327) | Source now partly assembled into #329, retained independently | Avoid double-merging identical files; qualify actual buyer |
| Financial staging | [#306](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/306) → [#315](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/315) → [#318](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/318) → [#325](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/325) → [#331](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/331) | Unpublished staging; 331 hosted-staging-access gate **failed** | Staging HTTP access, financial/tenant/reversal/fee authority, migrations and rollback all require independent confirmation |
| 14 laboratories and historical findings | PR [#297](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/297) and descendants | Synthetic code-path QA; original 26 historical findings not blanket-closed | Research cannot certify vendor money, shipping contracts, claim recoverability or real tenant data |

**Engineering failure detail:** GitHub M11 staging job `hosted-staging-access-gate` failed because the external runner received **HTTP 403 / sandbox access denied** from the unpublished Floot staging endpoint. Its separate `financial-integrity` job passed. Do not call this success at hosted HTTP parity, or fabricate a customer-payment failure. Resolve supported CI-to-staging access and rerun the exact authenticated request suite before production review.

## D. Current live configuration boundary

Direct Cloudflare account inspection on October 8:

- Pages project `retally-web` is linked to `P00NSMASHER/github-value-hunt-ledger` main, with apex and www custom domains present.
- `FREIGHT_INQUIRY_ENABLED=0` and `FREIGHT_INQUIRY_MAILBOX_VERIFIED=0`; Cloudflare Email Sending API token absent. `INQUIRY_DB` binding and Turnstile secret are configured. D1 `retally-inquiries` returned **zero stored inquiries** at inspection time.
- The operator case-write approval/enable settings were not configured. Only the production D1 database remained after disposable QA cleanup.
- Source PR evidence records custom-domain production availability, but direct independent public-page retrieval in this consolidation was unsuccessful. Do **not** declare the website unreachable on that basis or claim a newly validated live response.
- Gmail sender-side SENT tests do **not** prove the Zoho mailbox received the company email. A browser-generated mailto draft is **not** a submitted/received lead.

Nothing in this final integration changes any Cloudflare flags, DNS, credentials, customer data, task schedule, inbox, Floot production code or actual carrier state.

## E. Single P0 release ledger: owner, real evidence and decision

| Gate | Accountable owner | Evidence required before verified status | Current verdict |
|---|---|---|---|
| Legal contracting identity/trading name | RETALLY owner + qualified counsel | Registered legal identity, authorized trade-name use, counsel-approved business scope and contract signatory | **BLOCKED** |
| Signed commercial terms | RETALLY owner + qualified counsel + buyer | Exact recovery-fee rate, attributable net receipt definition, excluded claims, refunds/reversals, timing, taxes, authorization and termination provisions | **BLOCKED** |
| Actual inbound business contact | Mailbox owner | Open Zoho inbox and match two permitted controlled message IDs, headers, timestamp and content; no freight data | **BLOCKED** |
| Contact route | Web/inquiry owner | True received status: either actual buyer-delivered email or correlated consented form HTTP receipt → D1 → provider outcome → verified Zoho arrival → operator acknowledgment | **BLOCKED** |
| Confidential buyer records | Buyer IT/records owner + RETALLY privacy reviewer | Buyer-specific written scope, an approved single-tenant read-only workspace, MFA/access, subprocessors, retention/deletion, incident route, and independent evidence of controls | **BLOCKED** |
| Qualified freight reviewer and capacity | RETALLY operations owner | Named reviewer, independent check, 20-invoice scope cap, 2–3-hour diagnostic budget and ability to decline uneconomic work | **BLOCKED** |
| Incumbent overlap | Buyer truth owner + reviewer | Frozen prior auditor outputs, already-filed disputes, credits, duplicate economic identities, rate/contract authority and no conflicting exclusivity | **BLOCKED FOR ANY ACTUAL BUYER** |
| Case operator and retention | Security/privacy owner | Approved production Access application, authenticated distinct human reviewers/approvers, legal/hold policy, actual 0002/0003 migration acceptance, restricted DB permissions and audit | **BLOCKED** |
| Live financial and claim controls | RecoveryOS release authority + independent financial verifier | Full production-representative authenticated HTTP suite, ledger migration/rollback, valid source/actor identities, tenant/currency and cash/credit/reversal consistency; actual receipts | **BLOCKED** |
| Carrier interaction authority | Buyer action approver | Separate specific written authority and approved packet for each action, with identified carrier and appropriate evidence | **BLOCKED** |
| Sample financial eligibility | Independent forensic reviewer | Source-level allocation explaining gross $14,200 minus reversals $750 equals net $13,450, but only $11,800 called fee-eligible; **$1,650 currently unexplained** | **BLOCKED FOR CUSTOMER CLAIMS** |
| First paid outcome and repeatability | Buyer controller + RETALLY CFO | Completed genuine engagement, posted cash/usable credit and reconciliation, fee invoice, labor/CAC and contribution-margin evidence | **NO REAL CUSTOMER PROOF** |

An owner must supply specific records and independently review them before changing any `PENDING` status to `VERIFIED`. Generic notes, an internal test SHA, a private fixture and a signed synthetic JSON file do not substitute for genuine external authorization.

## F. Exact first-customer operating sequence

**Before real customer material:**

1. Prepare an unsent, tailored introduction for an appropriate distribution CFO/controller. Confirm a real business decision-maker from public or authorized contact sources.
2. Conduct only **non-sensitive** qualification: legal company and freight owner, domestic LTL use, number of invoices, period, incumbent auditor, available rate source and current disputes; do not ask for raw invoices in email.
3. Run the existing `lead_qualification.py`; a known prior auditor, unknown carrier, unknown mode, unverified contract authority or malformed boolean evidence triggers review, not a fast-path approval.
4. Use the existing first-customer gate: `python freight/commercial/first_customer_gate.py`. `--require confidential_pilot` must exit 2 while mandatory evidence is missing.
5. Estimate analyst and independent reviewer effort with `zero_upfront_underwriting.py`. Include full loaded founder time, an actual loss cap, zero-recovery cost and program downside; the synthetic 20% fee rate must never become a customer quote.
6. Obtain reviewed legal and buyer-specific consent to the limited confidential transfer route, and reserve the named reviewer.
7. Only after buyer scope, safe records route and privacy evidence pass: freeze population and pre-existing claims/credits; calculate and separately review authoritative rate discrepancies.
8. Present candidate and supported findings clearly distinguished from guaranteed cash. Do not contact carriers until the buyer separately approves each recovery action.
9. Track carrier claims, receipts/credits, reversals and disputed claims. Never treat a software status or modeled saving as customer-posted cash.
10. Reconcile actual externally supported eligible net recovery and contractual contingency rate. Record customer benefit and invoicing eligibility only after the evidence is independently accepted. Preserve full operating hours, acquisition costs, success/failure and dispute cycle.
11. Close or retain records through approved human operator decisions and legal holds, not a blanket 90-day deletion.

**Manual pilot restriction:** If the buyer-specific controlled manual Google Drive route passes security/legal approvals, RETALLY can provide a **human-led service** with clearly documented manual controls; it does not depend on the unsafe live RecoveryOS financial lane. Do not connect production financial API payments to such a pilot until independently certified.

## G. Next-owner handoff without additional missions

**No new labs, tasks, production deployment, prospect emails or parallel releases were authorized or created.** Review this unified integrated commercial PR once, then resolve external requirements against the existing gate/PR locations. Existing scheduled tasks must remain unchanged.

Review order:
1. Confirm production SHA of merged #298/#330, inspect canonical site and fallback, preserve inquiry disabled state.
2. Review #329 integrated commercial gate and acceptance tests; adopt it as the one operational commercial source rather than separately merging overlapping #311/#320/#317/#326/#327.
3. Review website inquiry #307 after merged hotfix; reconcile its stacked #321/#332 and optional #313 with source conflicts before considering any D1 migration.
4. Accept #300 customer materials only after original assets, eligibility and independent finance/legal checks pass. Integrate #305 only after one approved fee policy and site preview.
5. Keep research/Floot financial chain #331 in draft until actual sandbox access, source provenance, authenticated HTTP and ledger/cash validation are reproduced independently. Do not confuse 26 historical lab findings with fixed production defects.
6. Obtain a real buyer and separately approved records/workspace/legal authorization for a capped **manual** LTL pilot. Do not activate the public software merely to obtain the first engagement.

**Single final decision as of October 8, 2026:** **NOT READY, WITH CLEAR BLOCKING DEFECTS** for accepting confidential customer invoices, making carrier claims, issuing contingency invoices, or processing live financial activity. RETALLY **is ready for non-sensitive market discovery and source-controlled preparation**. The reason to win its first legitimate customer is to offer a narrowly scoped independent review with independently traceable contract proof and customer-controlled recoveries, not to claim superiority to established freight auditors without measured results.

**Evidence caveat:** This is a dated snapshot. New merges, Cloudflare deploys, actual legal/email approvals or CI results require a fresh source check before any GO determination.
