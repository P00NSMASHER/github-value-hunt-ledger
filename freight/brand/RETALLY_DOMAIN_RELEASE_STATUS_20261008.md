# RETALLY | Website, domain and contact release status

Cloudflare's authenticated resource inventory lists project **retally-web** (not older unused project `retally`), production branch `main`, an existing successful production deployment and active custom domains `retallyrecovery.com` and `www.retallyrecovery.com`.

DNS includes Zoho MX, SPF, DMARC monitoring policy and DKIM selector `zmail`. A real outgoing test from `jay@retallyrecovery.com` reached Gmail with SPF/DKIM/DMARC PASS. Inbound Zoho mailbox receipt from the Gmail-to-RETALLY probe remains **unverified**; do not infer a working inbound inquiry channel from outgoing delivery.

Cloudflare production hosting is already configured independently of this brand finishing PR. The public allowlisted build rebases historic GitHub Pages links in the generated artifact; source HTML retains historic host strings intentionally. Keep the existing public site reachable and do not remove redirect/fallback arrangements until a live incoming inquiry and all links/SEO URLs are tested.

**Unresolved:** inbound email receipt, complete rendered QA of the deployed custom domain, customer contact path, user-approved logo derivatives, appropriate trade-name and contracting-entity clearance. No automatic customer outreach or legal name changes.
