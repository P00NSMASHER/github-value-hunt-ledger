# RETALLY inbound inquiry operational acceptance

**Scope:** The public site's existing `/api/inquiry` Cloudflare Pages Function,
D1 `INQUIRY_DB` binding, Cloudflare Turnstile, provider email notification,
Zoho business inbox, and the always-available browser-prepared email fallback.
This is an operations checklist, **not** approval to enable the online feature,
create customer records, change billing, or contact a carrier.

## Verified independent baseline (2026-10-08)

- Production website Cloudflare Pages was deployed on GitHub commit
  `686386d0cb374ddf6d0ba086ac226dc8568daf32`.
- `INQUIRY_DB` is bound, and both `inquiries` and `inquiry_limits` tables exist.
  A read-only aggregate returned **0 inquiries** and **0 pending notifications**.
  Do not read or expose raw lead rows to establish routine health.
- Production `FREIGHT_INQUIRY_ENABLED` and
  `FREIGHT_INQUIRY_MAILBOX_VERIFIED` both contain `0`. Both are intentionally
  disabled; this is not an empty-variable error.
- The production `CLOUDFLARE_EMAIL_API_TOKEN` binding is **absent**. Other named
  dependencies (inquiry D1, Turnstile site key and secret, rate secret,
  Cloudflare account identifier and sender/recipient identifiers) exist.
  Existence does not prove the values or provider permissions work.
- The live mobile home page exposes **"Open My Free Audit Request"**, its
  email-draft fallback, not the online-submit confirmation mode.
- Cloudflare MX records point at Zoho. SPF, Zoho DKIM and DMARC records exist.
  This only establishes DNS configuration, **not mailbox receipt** or provider
  delivery. Email Service sending-domain readiness could not be inspected with
  the connected Cloudflare permission.
- Search Console had 26 sitemap entries with 0 indexed and no sitemap errors.
  Indexing is separately monitored; do not conflate it with intake delivery.

## Four distinct levels of evidence

1. **Form prepared:** Visitor completed browser validation and their email app
   was offered a `mailto:` draft. Unless the visitor independently clicks Send,
   nothing is stored by RETALLY.
2. **Durable receipt:** Online handler returned 202 with
   `received: true` and an `RA-YYYYMMDD-XXXXXXXX` reference **after**
   successful insertion in D1. This does *not* say the email was delivered.
3. **Notification provider accepted:** D1 `notification_status` became
   `provider_accepted`. This only means the provider accepted the request,
   not that Zoho delivered it to the mailbox.
4. **Business inbox received:** A person or directly connected authorized
   mailbox confirms a message with the matching reference is accessible in
   `jay@retallyrecovery.com`, and a real responder can reply. Only this
   completes mail-delivery acceptance.

## Activation prerequisites and operator procedure

1. Confirm control of the RETALLY Zoho inbox and independently test actual
   inbound **and outbound** mail. Check Spam/quarantine too. Do not mark the
   mailbox verified merely because DNS exists.
2. In Cloudflare Email Service, confirm the account may send transactional
   email using the approved RETALLY sender address, and inspect
   sending-domain DNS and provider logs. Cloudflare Email Sending authorization
   requires a Cloudflare API token with the **Email Sending: Edit** permission.
   Existing connected API permission returned **Unauthorized** for sending
   subdomain inspection; do not claim this is configured.
3. Provision a minimally scoped, revocable Cloudflare Email Sending token
   restricted to the correct RETALLY account. Store it **only** as a Cloudflare
   Pages production encrypted `CLOUDFLARE_EMAIL_API_TOKEN` secret. Do not paste
   or commit token values into chat, GitHub, CI logs, sample payloads, or website.
   Do not reuse a broad administrator token.
4. Ensure the verified `INQUIRY_NOTIFY_FROM` is allowed by Cloudflare Email
   Sending and `INQUIRY_NOTIFY_TO` is the approved business mailbox. Do not
   disturb Zoho MX, SPF, DKIM, or DMARC while establishing sender authorization.
5. Verify the production D1 migration, Turnstile hostname/action configuration,
   same-origin protection, bounded payload, rejection of secrets/uploads,
   rate limits and idempotency. Run
   `node --experimental-default-type=module --test freight/site/test_inquiry.mjs`.
6. After (1)–(5) pass, the owner may change
   `FREIGHT_INQUIRY_MAILBOX_VERIFIED` from `0` to `1`, then
   `FREIGHT_INQUIRY_ENABLED` from `0` to `1`.
   Confirm a successful fresh Cloudflare production deployment and the live
   `GET /api/inquiry` returns `online: true` with a public Turnstile site key.
   If not, revert both flags to `0` and keep the manual fallback.
7. Perform **one** authorized, traceable test submission with unmistakably
   synthetic business identifiers, no customer files, and a test email address
   under the operator's control. Complete the real Turnstile challenge in the
   browser. Record the reference and the four evidence levels above.
   Verify D1 count increased once, retries with the same idempotency key do not
   create duplicates, and the real RETALLY inbox contains the matching message.
   Do not place a message to a third-party business as a test.
8. If provider acceptance or mailbox receipt fails, set
   `FREIGHT_INQUIRY_ENABLED` back to `0`, keep the email-draft fallback,
   reconcile the pending database record and inspect provider logs using
   an authorized operator. Do not silently discard or retry customer leads.
9. Document the retention/erasure rule for synthetic QA records and verify
   deletion or scheduled expiry using the approved procedure. Never delete
   genuine client records just to make a dashboard display zero.

## Safe read-only database checks

Run only with properly authorized Cloudflare D1 access. Return **aggregate**
counts, never names, email addresses, notes, references, IPs or entire rows.

```sql
SELECT COUNT(*) AS total,
       SUM(CASE WHEN notification_status = 'pending' THEN 1 ELSE 0 END) AS pending,
       SUM(CASE WHEN notification_status = 'provider_accepted' THEN 1 ELSE 0 END) AS provider_accepted
FROM inquiries;
```

A result of zero pending items does not prove that a mailbox is working; it may
also mean the online service has never been enabled.

## Rollback boundaries

- A problem with email sending does not justify relaxing Turnstile, CSP,
  idempotency, rate limits, same-origin checks, or confirmation semantics.
- Disable only the online intake feature flags when required. Preserve
  `INQUIRY_DB` for reconciliation and leave the trusted manual email-draft
  path intact.
- Do not touch RecoveryOS, commercial terms, active unrelated development
  branches, or scheduled tasks.
- Mark the final state as **email draft only**, **durable online intake**, or
  **end-to-end confirmed**. Never use the three labels interchangeably.
