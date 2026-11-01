# RETALLY | Reliable public inquiry acceptance (implementation contract)

**As observed on 2026-10-08:** the same-origin Pages Function exists but intentionally advertises `HTTP 503` / `{"online":false}` on the live `www.retallyrecovery.com` domain. The visitor remains in the browser-prepared email-draft fallback. Neither an email draft nor a sender-side Gmail `SENT` record proves RETALLY received an inquiry. Keep the fallback until verified business inbox receipt and durable online submission are independently established.

## Implemented design and activation requirements

- **Client:** name, work email, company, annual freight-spend band, transport modes and optional high-level non-sensitive context. No invoice upload, carrier rate sheets, contracts, logins or payment details.
- **API:** same-origin Cloudflare Pages Function `POST /api/inquiry`, behind explicit deployment flag. Keep total JSON body size and per-field lengths bounded; reject unsupported keys, invalid email and missing required values.
- **Abuse protections:** Turnstile server-side verification, server-side rate limits, CSRF/origin policy, abuse logging without raw message/body PII, honeypot (if used), no public files, and reasonable retention/deletion controls.
- **Durability:** safely generate a server reference and persist minimal non-sensitive data or enqueue an authenticated transactional notification through a verified provider. Do not return `202` or show 'received' before a durable queue/persistence/confirmed-provider acceptance.
- **Receipt:** provide clear status to the visitor, with fallback to the verified business mailbox if service unavailable. An automatic acknowledgment to a user requires actual receipt, validated address and appropriate consent policy.
- **Security:** no secrets in frontend JS or GitHub; source-control changes to customer-facing privacy notice and backend retention policy. Never allow a Pages deploy to automatically switch from mailto to unfinished backend.

## Evidence required before production

1. Valid initial inquiry reaches the actual approved recipient, checked independently of the browser.
2. Invalid input, missing Turnstile, replay, burst abuse, cross-origin requests and oversized bodies fail closed.
3. Service errors do not show success or create phantom lead records.
4. Document the data owner, expected retention period, access scope, deletion path and contact consent.
5. Publish a rollback route that restores the existing mailto flow in one configuration change.
6. Verify live mobile keyboard/focus and desktop interaction end to end.

**Current state:** Code implemented, D1 and Turnstile infrastructure documented, production online inquiry intentionally DISABLED by flags. Email-provider permissions, Zoho inbound receipt and end-to-end production delivery are not verified. The current GET capability probe returns `503 {"online":false}`; do not interpret disabled-by-policy as a malformed form or enable it without signed operator acceptance. See `freight/site/INQUIRY_PRODUCTION_READINESS.md` and `freight/brand/RETALLY_INQUIRY_LAUNCH_RUNBOOK_20261008.md`.
