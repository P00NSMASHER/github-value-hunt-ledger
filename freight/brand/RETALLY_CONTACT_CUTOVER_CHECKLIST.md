# RETALLY domain, business email and customer-contact cutover

Status: BLOCKED until external mail and legal readiness are independently verified.

## Read-only observations, 2026-10-08
- `retallyrecovery.com` is an active Cloudflare zone.
- Updated Cloudflare zone inspection: Zoho MX (`mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com`), SPF (`v=spf1 include:zohomail.com ~all`), and DMARC (`v=DMARC1; p=none`) records are now present, as well as the Zoho verification TXT. Independent public DNS resolved the three MX values. DKIM was **not visible** in the zone listing; selector and service validation still require Zoho Mail administrator evidence. DNS presence does not establish a working mailbox.
- Cloudflare Pages project `retally` exists with preview hostname `retally-8kr.pages.dev`; project creation does not prove a deployed production website.
- Draft PR #282 is a deployment *proposal*, not approval to activate DNS or release new site.
- Catalyst by Zoho integration is **not** Zoho Mail administration; do not infer mailbox readiness from its presence.

## Cutover sequence
1. Confirm RETALLY naming/trademark/business registration requirements with an appropriate reviewer; do not change the legal contracting entity implicitly.
2. Verify domain in Zoho Mail. Provision an actual mailbox in its admin dashboard and confirm region-specific MX/DKIM instructions. Do not guess or add MX based on generic articles.
3. Publish provider-specified MX, one consolidated SPF, DKIM selector TXT/CNAME and staged DMARC record; check authoritative DNS propagation and service-side verification.
4. Send and receive real test email externally using the actual company mailbox; inspect SPF, DKIM and DMARC authentication results.
5. Validate signature in Gmail/Apple Mail/Outlook (fallback live text if blocked images); all sender details must be real.
6. Test Cloudflare Pages preview with correct environment variables, revised canonical and social metadata, all static assets and the buyer contact flow.
7. Confirm end-to-end form's current workflow: it opens an email draft and **does not** submit a lead. Only claim a lead was received after the sender actually sends and it appears in the verified inbox.
8. Update site URLs, sitemap, canonical, schema, OG/Twitter image and old public link redirects in one verified controlled release.
9. Run rollback exercise and preserve old working routes until new routes succeed.

## Publishing rules
No fabricated email addresses, phone numbers, office hours, reviews, or storefronts. Keep the working customer route available until all gates pass. Do not copy secrets into PRs.

## Human-required acceptance
[ ] Business-name/legal clearance
[ ] Real mailbox provisioned and verified
[ ] MX, SPF, DKIM, DMARC confirmed
[ ] External send/receive PASS
[ ] Pages preview PASS
[ ] Contact route PASS
[ ] Correct company entity displayed in signed terms
[ ] Approved production switch and rollback
