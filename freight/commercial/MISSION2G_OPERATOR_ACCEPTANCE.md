# RETALLY | First legitimate customer gate, October 8, 2026
**Internal operating decision. Not an advertisement, legal opinion, signed agreement, approved secure upload or customer intake authorization.**

## Verified now
1. **Website hosting:** The `retally-web` Cloudflare Pages production project reports a successful deployment on `main`; apex redirects HTTP 301 to the canonical `www` hostname. Both custom domains are active. This proves site hosting, not inquiry delivery.
2. **Inquiry capability:** A read-only probe at `https://www.retallyrecovery.com/api/inquiry` returned **HTTP 503** `{"online":false}`. This is expected under production disabled flags, not proof that a customer lead was received or a reason to bypass Turnstile, limits or CSRF.
3. **Email:** Existing connected Gmail shows two controlled non-sensitive messages **sent to** `jay@retallyrecovery.com`; sender-side SENT records do not demonstrate receipt at Zoho. A previous authenticated company-to-Gmail test was documented as passing SPF/DKIM/DMARC. Outbound authentication is not inbound proof.
4. **Pilot workspace:** The September 21 owner-only single-tenant Google Drive manual-review environment policy is designated VERIFIED for an **empty controlled pilot**. This does not verify buyer-specific identity, authorized access, current MFA/device state, retention, NDA, parser approval or permission to upload real freight records.
5. **Financial samples:** `$14,200 gross - $750 reversal = $13,450 net` is arithmetically consistent; published fee-eligible `$11,800` leaves `$1,650` without an independently supported exclusion allocation. Synthetic only, not actual revenue, customer proof or authorized fee basis.

## What RETALLY can safely do today
- Discuss **high-level, non-sensitive** prospective scope via a contact route proven to work for the specific communication. Do not represent a prepared email draft as received.
- Present approved positioning and sample methodology expressly as illustrations; no customer case study or recovered-cash guarantees.
- Qualify: named U.S. business, buyer sponsor, modes, approximate invoice volume, months available, rate terms, incumbent-auditor restrictions and reviewer budget. Do not request bills or contracts yet.
- Prepare a narrow manual-review pilot (up to the existing 20-invoice feasibility model when independently appropriate) with costed reviewer capacity and scope exclusions.

## External decision gates, in order
| Gate | Required evidence | Approval owner | Current outcome |
|---|---|---|---|
| Inbound contact | Real matching message viewed in authorized Zoho inbox, reply path verified | Mailbox/website owner | BLOCKED |
| Business identity | Registered contracting party, trade-name position and legal document identity | Owner and counsel | BLOCKED |
| Free review scope | Customer-specific bounded carriers/modes/period/invoice-count, source requirements, reviewer allocation and acceptance criteria | Operations and buyer | NOT STARTED |
| Commercial fees | Actual percentage, eligibility, reversals, excluded categories, invoice timing, authority, and signed terms; any discount must have a real comparator | Owner, counsel, buyer signer | BLOCKED |
| Confidential intake | Buyer-specific access roster, MFA, access test, retention/deletion, independent security review and written authority for real data | Buyer IT and RETALLY verifier | BLOCKED |
| Claim action | Separate written approval for **each** proposed outside carrier action | Customer authorized delegate | NOT STARTED |
| Actual recovery | Unique posted credit/refund and reversal reconciliation; fee base independently supported | Financial reviewer and buyer | NOT STARTED |

## First three customers: one repeatable operating process
**A. Initial conversation (no confidential files):** confirm buyer identity, freight mode, approximate size and data availability. Record source and contact-receipt evidence; use the current buyer one-pager as methodology material. Stop if verified contact route is absent.

**B. Authorized scoped review:** only after contracting, documentation, data readiness and buyer-specific secure workspace all pass; freeze invoice selection and prior-credit exclusions. Require named independent reviewer, a customer acknowledgment and no parser/AI access outside the approved manual environment.

**C. Findings and financial acceptance:** deliver source-referenced line items, reviewer decisions, missing-evidence table and claim-specific approvals. Record carrier decisions and posted/reversed credits separately. If results are clean or unsupported, report **zero** defensible recovery; never invent avoided spend.

**D. Post-pilot:** return the report and ledger, expire/delete private records per buyer-specific signed terms, and verify deletion. Ask for case-study permission only after independently evidenced actual outcome and separate written permission.

The first-three-customer capacity is a maximum program design, not evidence of filled slots. No general discount claim without an approved standard price and signed buyer-specific rate.

## Machine-readable check
The current factual/policy snapshot lives in `first_customer_acceptance_m2g.json`. Run `python freight/commercial/first_customer_gate.py` to print observed, blocked or evidence-backed states. Use `--require confidential_pilot` to **fail with exit code 2** unless that stage has affirmative reviewer/source/date evidence. A `VERIFIED` string by itself is never enough.

The gate is a conservative internal checklist. It does not test vendor controls or legally authenticate a signature. The existing `freight/pilot_launch_gate.py`, `freight/separate_environment_evidence.py`, `freight/readiness.py`, signed customer terms and actual reviewer authority remain decisive for real intake.

**No website deployment, contact email, carrier outreach, agreement, database change or client file transfer was performed in this mission.**
