# RETALLY — Lead response, retention and evidence operations
Revision: 2026-10-17. Source of truth for **non-sensitive** free-audit inquiries.

### Provenance and reporting accuracy
- The owner-verified one-time live delivery test `RA-20261017-26F3BC58` is
  stored in an additive, append-only `inquiry_qa_registry` provenance ledger.
  Only that exact reference with its synthetic identity and delivered status
  can enter the registry. It stays in D1; it is **not** deleted or closed.
- Aggregate reporting now reconciles `raw_inquiry_total = business_inquiry_total +
  synthetic_qa_excluded`. Every real and unclassified lead remains in the
  alert queue. Unknown, duplicate or inconsistent QA status fails closed.
- New synthetic exemptions require independently reviewed source and data
  evidence, a new migration and tests. Broad `test` names, campaign tags or
  domain patterns must **never** silently classify customer leads as QA.
- The currently available Cloudflare Access application protects both
  `/api/internal/inquiry-case` and `/api/internal/inquiry-response` on
  `retallyrecovery.com` and `www.retallyrecovery.com`, preserving the existing
  exact email, IdP and MFA policy. This is defense in depth, not proof of two
  separately enrolled authorized staff identities.


## Operating boundary and true status
- Public prospect intake is **OFF** until the full operator access, staffed monitoring,
  privacy-notice, legal/reviewer and customer launch gates are independently cleared.
  The website email-draft fallback remains available.
- The single controlled `RA-20261017-26F3BC58` QA request had verified D1
  storage, Resend acceptance and independently viewed Zoho inbox delivery.
  It is not a real customer lead and **not** evidence of an actual staff reply.
- No proposed commercial registration, insurance purchase, automated customer
  contact, freight-document transfer or recovery authority is created here.
- D1 is restricted to non-sensitive contact + broad freight metadata. Do not put
  invoices, rates, contracts, banking data, customer access credentials or files
  into the form, chat, logs, GitHub or these proof receipts.

## Confirmed states: never conflate
1. `pending`: D1 committed receipt; notification delivery attempt not accepted.
2. `provider_accepted`: Resend accepted API request; no Zoho proof yet.
3. `delivery_verified`: matching message actually located in Zoho; still NO
   staff acknowledgment or response.
4. `ACKNOWLEDGED`: signed reviewer has taken ownership of the reference;
   this is not a sent reply.
5. `REPORTED`: signed reviewer asserts a real message was sent and gives
   a SHA-256 digest of a retained, authorized source receipt. It is not proof
   the message was delivered to a prospect.
6. `VERIFIED`: distinct Access-authenticated approver examined the original
   Zoho sent-message evidence and recorded a separate evidence digest.
7. `WAIVED`: distinct Access-authenticated approver approved a no-contact
   disposition: SPAM, INVALID_CONTACT, WITHDRAWN, DO_NOT_CONTACT or OUT_OF_SCOPE.
   Waived is **never** counted as a human reply.
8. `CLOSED`: requires verified response or approved waiver; it alone does
   not authorize record deletion. A hold can remain attached to a closed case.

## Roles, security and release
- Primary inbox: the authorized operator for `jay@retallyrecovery.com`.
  A real human must be designated and must actively check this mailbox.
- Reviewer: a named, MFA-protected Cloudflare Access principal who may
  ACKNOWLEDGE, RECORD_RESPONSE, SET_HOLD and CLOSE.
- Approver: a **different** verified Access principal who may VERIFY_RESPONSE,
  WAIVE_RESPONSE, RELEASE_HOLD and APPROVE_PURGE. Do not fabricate a second
  identity. Do not enable operator API until Access application, real IdP,
  MFA policy, role allowlists, JWT validation and revocation are tested.
- Operator POST endpoints: `/api/internal/inquiry-case` and
  `/api/internal/inquiry-response`. Both fail closed unless
  `RETALLY_CASE_WRITES_ENABLED=1` **and**
  `RETALLY_CASE_POLICY_APPROVED=1`, plus signed Access and audience checks.
- No API action reads raw case contents, sends outbound prospect email or
  performs deletion. Stored digest text is an evidence *claim* until separately
  compared against authorized, independently viewed source records.
- Administrator-level SQL is more powerful than these JWT checks. Restrict
  D1 write scope, maintain access audit and never call this cryptographically
  tamper-proof against a privileged database administrator.

## Response workflow (internal targets, NOT customer promises)
- Coverage: review at business-day opening, midday and before close
  (Mon–Fri, 9 AM–5 PM America/New_York). Until named coverage and backup are
  confirmed, do not assert an operational response SLA.
- Aim for acknowledgment within 4 staffed business hours and a first real
  human response within 1 staffed business day. Read-only alarms at
  4/24 **elapsed** hours are earlier warning indicators, not exact business
  calendar calculations; weekends/holidays need operator interpretation.
- For every new reference: match it to the actual Zoho inbox message, check
  deliverability, validate metadata only, assign signed reviewer and record
  `ACKNOWLEDGE`. No customer is accepted for a service merely by this step.
- Before replying, check consent, suppression/no-contact requests, fit,
  existing agreements, and relevant business registration/insurance gates.
  Human authorization is required for a prospect contact; never have AI,
  the website, a bot or cron silently send a prospect message.
- After a real authorized reply from Zoho: preserve private Zoho sent-message
  receipt (message ID, time, recipient, subject, delivery/failure evidence).
  Reviewer records `RECORD_RESPONSE` with SHA-256 of that source receipt.
  Independent approver inspects that source and records `VERIFY_RESPONSE`
  using their own evidence digest. Only then may the case be closed as replied.
- Spam, withdrawn, out-of-scope or no-contact: record an explicit
  `WAIVE_RESPONSE` with reason and independent approver, then CLOSE. Never
  misreport a waiver as contact, conversion or recovery.
- Never copy names, message bodies, secrets or customer data into GitHub CI
  artifacts, terminal reports, or public issue comments.

## Monitoring and escalation
- Read-only command (Node 22+): `node freight/inquiry_ops/reconcile.mjs --dry-run`
  or `--live` with an approved, read-only Cloudflare API token supplied via
  a secure credential manager. It runs five fixed aggregate SELECT statements,
  with gross receipt count, verified QA exclusions, real-lead counts and
  bounded age/retention aggregates; no names, emails or body content are returned.
- P0: pending-notification over 1 elapsed hour, an unacknowledged case over
  4 elapsed hours, response evidence incomplete after 24 elapsed hours,
  closed-without-verified-reply corruption, or expired unresolved retention.
- P1: ANY unacknowledged lead, pending provider confirmation, open lead or
  reported-but-unverified reply, even if recent.
- Manual on-call action: inspect the exact reference in restricted tools and
  Zoho, reconcile the real outcome, and retain an operator-only evidence link.
  Do not retry a possibly accepted email blindly or create duplicate leads.
- If D1 query errors or gives malformed aggregates, status is **UNKNOWN**,
  never `0 leads`. Escalate and retain the disabled public-intake fallback.
- No recurring monitor, scheduler or notification sender is installed by
  this code. Establish an authorized scoped read-only credential, real staffing
  and separately verified monitoring before a public SLA or always-on launch.

## Retention, privacy and erasure
- Qualification records have a normal **90-day review point** measured from
  D1 `accepted_at`, not a promise of automatic deletion on day 90.
- At or before day 75, reviewer assesses closed status, ongoing legitimate
  purpose, no-contact/deletion requests, active claims and legal holds.
  Nonessential details should not be retained without a documented reason.
- An unresolved, still-open, disputed or legally held record may require
  a documented exception. Escalate it; never silently purge it to meet a
  deadline. Document purpose, responsible operator and review date in the
  approved private case file. Consult counsel if a deletion obligation conflicts
  with preservation requirements.
- A purge is eligible ONLY if: verified CLOSED state, >=90 full days since
  receipt, required retention date passed, no hold, independent purge approval,
  and a targeted approved D1 action. The D1 deletion trigger must reject
  all other cases and write a minimal, append-only purge receipt atomically.
- No automatic bulk deletion. Review the exact reference, obtain recorded
  approval, use a scoped admin query against one eligible case and check audit
  count. Early lawful erasure requests require a separate reviewed exception,
  not disabling the guard.
- Purge does not erase copies already sent by email providers or immutable
  security event receipts. Account for Zoho, Resend, exports, backups and their
  separately documented retention/deletion controls. Protect metadata in
  action audits as pseudonymous, still potentially linkable information.
- Periodically review access to D1 and Zoho, remove departed operators,
  and document any provider/backup retention commitments before accepting
  actual customer inquiries.

## Safe deployment and proof
1. Keep public form OFF, run Node/SQLite/retention checks on an isolated
   database; ensure real Turnstile, sender credentials and Zoho untouched.
2. Apply additive migrations 0002, 0003 then 0004 to D1 under explicitly
   reviewed change control. Never replay ALTER statements blindly.
3. Prove old records are conserved, guard triggers exist, permitted scoped
   operations work only with signed roles, invalid/outdated operations fail,
   and read-only aggregate report has no personal information.
4. Independently configure actual Cloudflare Access application + MFA and two
   real principals. Test real JWTs, same-origin, expired token and revocation.
5. Validate actual authorized outbound lead response evidence, manual rota,
   deletion/privacy request triage and provider storage obligations.
6. Only after all steps, consider online public-intake enablement via separate
   release. Keep rollbacks limited to public flags; never discard D1 records.

## Current acceptance meaning
Passing synthetic signed JWTs, SQLite tests or a migrated schema establishes
**technical enforcement only**. It does NOT demonstrate staffed response,
independent real human approval, policy/legal review, automated SLA monitoring,
production prospect communication authorization or actual data erasure.
