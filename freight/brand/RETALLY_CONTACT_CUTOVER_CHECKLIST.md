# RETALLY domain, business email and customer-contact cutover

Status: BLOCKED until external mail and legal readiness are independently verified.

## Read-only observations, 2026-10-08
- `retallyrecovery.com` is an active Cloudflare zone.
- Updated Cloudflare inspection (2026-10-08): all three Zoho MX entries (`mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com`), SPF (`v=spf1 include:zohomail.com ~all`), DMARC (`v=DMARC1; p=none`), Zoho verification TXT, and **DKIM public-key TXT** at `zmail._domainkey.retallyrecovery.com` are present. The user reports completing the Zoho DKIM setup. An actual outgoing test from `jay@retallyrecovery.com` reached Gmail on October 8. Gmail `Authentication-Results` showed **SPF=pass, DKIM=pass (selector zmail), and DMARC=pass** for the company domain. This establishes authenticated outbound delivery to Gmail. **Incoming delivery to Zoho and production website contact requests have not been verified**.
- Gmail has sent a controlled, non-sensitive test to `jay@retallyrecovery.com` (subject: `RETALLY inbox delivery test | October 8`). Gmail recorded the message in **SENT**; successful **receipt inside Zoho remains unconfirmed** and must not be marked PASS on the basis of sending alone.
- Actual production project is `retally-web`, with active custom domains `retallyrecovery.com` and `www.retallyrecovery.com`. Cloudflare lists a successful production deployment on `main` (2026-10-08). This proves deployment, not lead delivery or confidential document intake.
- Live read-only GET of `https://www.retallyrecovery.com/api/inquiry` returned `503 {"online":false}`; the online handler is intentionally disabled. The public form prepares a browser email draft instead of claiming a durable receipt. No POST or external customer message was sent during this verification.
- Catalyst by Zoho integration is **not** Zoho Mail administration; do not infer mailbox readiness from its presence.

## Cutover sequence
1. Confirm RETALLY naming/trademark/business registration requirements with an appropriate reviewer; do not change the legal contracting entity implicitly.
2. Verify domain in Zoho Mail. Provision an actual mailbox in its admin dashboard and confirm region-specific MX/DKIM instructions. Do not guess or add MX based on generic articles.
3. Publish provider-specified MX, one consolidated SPF, DKIM selector TXT/CNAME and staged DMARC record; check authoritative DNS propagation and service-side verification.
4. Send and receive real test email externally using the actual company mailbox; inspect SPF, DKIM and DMARC authentication results.
5. Validate signature in Gmail/Apple Mail/Outlook (fallback live text if blocked images); all sender details must be real.
6. Test Cloudflare Pages preview with correct environment variables, revised canonical and social metadata, all static assets and the buyer contact flow.
7. Distinguish **offline fallback** (`GET /api/inquiry` advertises `online:false`, visitor may open an email draft) from **durable online receipt** (server returns `202` with a persisted reference), **provider acceptance**, and **confirmed Zoho inbox delivery**. In offline mode, pressing the CTA alone cannot be counted as an inquiry received. Never enable durable POST before the gated production acceptance in `freight/site/INQUIRY_PRODUCTION_READINESS.md`.
8. Update site URLs, sitemap, canonical, schema, OG/Twitter image and old public link redirects in one verified controlled release.
9. Run rollback exercise and preserve old working routes until new routes succeed.

## Publishing rules
No fabricated email addresses, phone numbers, office hours, reviews, or storefronts. Keep the working customer route available until all gates pass. Do not copy secrets into PRs.

## Human-required acceptance
[ ] Business-name/legal clearance
[ ] Real mailbox provisioned and verified
[x] MX, SPF, DKIM, DMARC configured; external outbound Gmail authentication PASS
[ ] Inbound Zoho receipt from an external sender PASS (outbound Gmail receipt/authentication already verified)
[ ] Pages preview PASS
[ ] Contact route PASS
[ ] Correct company entity displayed in signed terms
[ ] Approved production switch and rollback
