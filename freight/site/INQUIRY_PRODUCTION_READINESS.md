# RETALLY inbound inquiry operational acceptance

**Scope:** The public site's existing `/api/inquiry` Cloudflare Pages Function,
D1 `INQUIRY_DB` binding, Cloudflare Turnstile, provider email notification,
Zoho business inbox, and the always-available browser-prepared email fallback.
This is an operations checklist, **not** approval to enable the online feature,
create customer records, change billing, or contact a carrier.

## Current Resend integration checkpoint (2026-10-17, PR #466)

- Resend sending subdomain `notify.retallyrecovery.com` is verified in the
  operator's Resend dashboard. Existing Zoho MX stays unchanged.
- Cloudflare Pages `retally-web` production has an encrypted `RESEND_API_KEY`
  binding (existence confirmed, token value neither read nor disclosed).
- The Pages function routes notification attempts to
  `https://api.resend.com/emails` with a fixed sender
  `audit@notify.retallyrecovery.com` and recipient `jay@retallyrecovery.com`.
  A stable `Idempotency-Key` uses the inquiry reference, and success requires
  HTTP 200 plus a valid provider email UUID.
- **The previous Cloudflare Email Sending API is no longer used by the candidate
  handler.** Resend may accept an API request without delivering to Zoho.
- `FREIGHT_INQUIRY_ENABLED=0` and `FREIGHT_INQUIRY_MAILBOX_VERIFIED=0`
  deliberately remain in production. Mailbox delivery, human follow-up, and
  live end-to-end acceptance have not been proven by a secret binding or CI.
- This remains a draft, unmerged source change. No direct public submissions,
  paid service, or confidential freight files have been authorized.

## Historical independent baseline (2026-10-08; Cloudflare email provider)

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

## Activation prerequisites and operator procedure (Resend)

1. In the Resend account, confirm the sending subdomain is **Verified** and
   API key is scoped to sending from that subdomain. Avoid uploading customer
   files or exposing the API key. Keep the Zoho mailbox and existing MX records.
2. Confirm the encrypted `RESEND_API_KEY` exists **only** in the Cloudflare
   Pages `retally-web` production secrets. Do not paste it into chat, source,
   GitHub Actions, a client-side script, or CI logs. Do not enable either
   online-inquiry flag merely because the secret is present.
3. Conduct an owner-approved **non-sensitive direct provider email test**
   from `audit@notify.retallyrecovery.com` to `jay@retallyrecovery.com`.
   Inspect Resend's send/delivery status and independently open the matching
   message in Zoho (including Spam/quarantine). An API 200 or a Resend
   "sent/delivered" status alone does not prove a message is accessible to
   a human in Zoho. Verify an outbound reply works.
4. Review provider data-processing/retention implications for non-sensitive
   business lead details. Confirm the existing D1 table and read-only
   reconciliation access; preserve qualified case retention, holds and
   auditability. Confirm a real accountable staff inbox reviewer.
5. Run the source CI and isolated visual acceptance for secure D1 storage,
   Turnstile, same-origin policy, 8KiB JSON bounds, restricted fields,
   no uploads, 5/hour and 20/day rate limits, provider error paths,
   stable idempotency, duplicate defense and truthful UI notification status.
   Automated fixtures must never be described as proof of real email delivery.
6. **After steps 1–5 pass**, a narrowly scoped, operator-approved live
   synthetic test may be staged using `FREIGHT_INQUIRY_MAILBOX_VERIFIED=1`
   then `FREIGHT_INQUIRY_ENABLED=1`. This change requires an independently
   reviewed production release/deployment and a rollback plan. The live
   `GET /api/inquiry` must return `online:true` before proceeding.
7. Complete the actual Turnstile and submit a synthetic company/contact
   request on RETALLY's website. Prove the `RA-` reference is durably stored
   once in D1, Resend accepted its notification, and the exact same reference
   was actually received in the Zoho inbox and can be replied to. Do not send
   an inquiry to a prospect or introduce real customer information as a test.
   Check mobile form behavior, invalid/expired verification, rate limits,
   duplicate retry and accessible status messages.
8. If provider or Zoho receipt fails at any point, immediately restore
   `FREIGHT_INQUIRY_ENABLED=0`, preserve the email-draft fallback, and
   reconcile saved pending records before any retry. A D1 `provider_accepted`
   state means API acceptance only; set `delivery_verified` only after
   independent evidence of actual recipient mailbox receipt.
9. Confirm the complete retention, access, erasure and notification
   reconciliation procedure before allowing genuine public submissions.
   Do not delete real pending inquiries to make dashboards green.

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
