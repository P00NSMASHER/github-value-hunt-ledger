# RETALLY | Cloudflare inquiry launch and recovery runbook

**Status on 2026-10-08: NOT ACTIVATED.** The existing browser-created email draft remains the public contact route. Merging this implementation must not claim successful receipt or automatically replace mailto.

## Installed infrastructure
- Production project: `retally-web`, sourced from `P00NSMASHER/github-value-hunt-ledger` branch `main`.
- D1: `retally-inquiries` (United States jurisdiction), binding `INQUIRY_DB` on production.
- SQL: `freight/site/migrations/0001_inquiry.sql`; live schema created 2026-10-08.
- Managed Turnstile: `RETALLY Free Recovery Audit`, bound only to `retallyrecovery.com` and `www.retallyrecovery.com`. The server secret resides in encrypted Pages production environment values, never in source.
- `FREIGHT_INQUIRY_ENABLED=0` and `FREIGHT_INQUIRY_MAILBOX_VERIFIED=0` are explicit production fail-closed gates. The GET endpoint advertises online submission only when every credential, storage binding and gate is present. No active email API token has been installed.
- Existing contact address remains `jay@retallyrecovery.com`. Never replace its Zoho MX records with Cloudflare Email Routing or change existing fallback contact links.
- A controlled Gmail probe was sent from the connected company owner's Gmail to the company Zoho mailbox on 2026-10-08; Gmail's SENT status is **not evidence** that the Zoho inbox received it.
- Cloudflare Email Sending API `GET /accounts/{id}/email/sending/limits` returned authorization error 2036. This is an unresolved provider/permission gate, not permission to enable a form or purchase any service.

## Durable acceptance and guarantees
1. Same-origin HTTPS POST only; 8 KiB JSON cap; exact allowed keys and enumerated fields. An upload or unsupported key is rejected, not stored.
2. Mandatory real Turnstile verification on the server, action `retally_audit`, approved hostname, short-lived single-use token; no Turnstile bypass in production.
3. D1 atomic per-IP keyed-hash bucket limits (5/hour and 20/day) and SHA-256 content fingerprint; no raw client IP stored. Browser holds an unpredictable idempotency UUID; replay with same fields returns its prior reference, changed fields return HTTP 409. No second email is attempted for the duplicate.
4. The server generates an `RA-YYYYMMDD-XXXXXXXX` reference and writes the record to D1 before answering `202 received:true`. Database failure never yields success.
5. Notification then attempts a *server-side* Cloudflare Email Service send to the fixed RETALLY mailbox; provider acceptance is stored as `provider_accepted`. A provider error leaves `pending` for manual operator reconciliation. **Provider acceptance is not proof that Zoho delivered the message.**
6. No public endpoint reads the inquiry table. The site never claims a lead is qualified, an audit accepted, or carrier authority granted.

## Remaining activation gates (do not skip)
- **Inbound Zoho proof:** open the actual Zoho mailbox and independently match a controlled message's subject, timestamp, sender and body. A sender-side Gmail SENT copy or no bounce is insufficient.
- **Notification permission:** use an existing approved no-purchase Cloudflare Email Service setup; confirm outbound eligibility and configure a *server-side* least-privilege API token with Email Sending: Edit in `CLOUDFLARE_EMAIL_API_TOKEN` (encrypted Pages environment). Verify allowed sender and the fixed recipient without altering Zoho MX or SPF/DKIM.
- **Controlled live verification:** with non-sensitive synthetic identity details, complete a challenge at the actual domain and check that HTTP 202, D1 receipt reference, provider acceptance, and *actual incoming Zoho message* have the same reference. Run two different submissions to rule out one-off success. Only after these checks, change `FREIGHT_INQUIRY_MAILBOX_VERIFIED=1` and `FREIGHT_INQUIRY_ENABLED=1` in production settings and redeploy.
- **Negative paths:** invalid enum/email, unknown keys, no challenge, expired/replayed challenge, >8 KiB payload, burst traffic, wrong origin, provider outage, D1 outage, and duplicate idempotency. No negative test may show a success screen.
- **Mobile:** test actual iOS Safari portrait focus/keyboard, challenge, submit spinner, no double-tap, error fallback and screen-reader status; also desktop keyboard navigation and responsive layout.
- **Rollback:** set the single flag `FREIGHT_INQUIRY_ENABLED=0` in Cloudflare Pages production environment and redeploy. The frontend's GET capability check then returns offline and reverts to the established mailto method. Existing receipts remain in D1, so reconcile pending inquiries before any restart. Do not disable hosting, Zoho or other services.

## Retention, access and reconciliation
- Data owner: RETALLY. Purpose: respond to commercial Free Recovery Audit inquiries, not take freight files or grant collections authority.
- D1 table stores restricted name, business email, company, broad modes/spend bands, selected optional context, timestamps and delivery state; no file bytes, secrets or raw IP. Cloudflare account administrators only. Do not include raw PII in public access logs or CI artifacts.
- Normal qualification retention: up to 90 days unless superseded by a documented engagement/legal obligation. The POST handler opportunistically removes rows older than 90 days but this is **not** a guaranteed cron job. Account owner must perform a scheduled monthly purge or add an independently verified scheduled cleanup task before activation. Delete old `inquiry_limits` rows too.
- Example operator commands through Cloudflare D1 console (never run from browser): `SELECT reference, accepted_at, notification_status FROM inquiries WHERE notification_status='pending' ORDER BY accepted_at;`; `DELETE FROM inquiries WHERE accepted_at < strftime('%s','now') - 7776000;`; `DELETE FROM inquiry_limits WHERE expires_at < strftime('%s','now');`.
- Verify actual inbox receipt before marking `delivery_verified`; provider HTTP 200 is insufficient.
- Customer correction/deletion requests go to `jay@retallyrecovery.com`, with the returned receipt reference. Keep deletion audit evidence without retaining raw request contents.
- Email provider token, Turnstile secret and rate-limit pepper belong only in Cloudflare environment secrets; never commit, print, or expose in HTTP responses.
- Avoid unlimited retry loops: failed notifications remain durable pending and require operator review, not automatically replayed by a visitor.
- No purchase, external outreach, new MX records or automatic customer acknowledgments are authorized by this implementation.

## CI and evidence
Run `node --experimental-default-type=module --test freight/site/test_inquiry.mjs` and `node --check freight/site/site.js`. RETALLY Inquiry CI runs the same assertions. The mocked suite is **not** a substitute for production inbox proof or actual mobile-browser testing.
