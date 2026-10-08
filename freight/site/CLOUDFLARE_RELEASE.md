# RETALLY Cloudflare Pages release and rollback

## Publication path

Production Pages project: `retally-web` (Git-connected to this repository, `main`).
Build command: `python -m freight.site.cloudflare_build`.
Build output: `cf-retally-public`.

The build entry point generates **only** the Freight public allowlist and the RecoveryOS public allowlist. The rest of the repository must never be used as a deployment directory. The configured mail address is validated as `jay@retallyrecovery.com` before publication. The generated bundle rebases absolute links and SEO canonical URLs from the former GitHub Pages URL to `https://www.retallyrecovery.com/`.

## Configuration and release checks

- Cloudflare Pages must provide build-time `FREIGHT_CONTACT_EMAIL=jay@retallyrecovery.com` and `FREIGHT_CONTACT_VERIFIED=1`.
- CI must pass all `freight/site/test_build.py` and `freight/site/test_rebase_public_urls.py` tests and execute the actual 69-file Cloudflare build.
- Before external cutover, a successful Pages deployment and browser HTTP/content smoke test are required.
- Attach `www.retallyrecovery.com` only after a successful staging deployment; add the apex root domain if needed and make `www` the canonical version.
- DNS MX (priority 10/20/50), SPF, Zoho DKIM selector and initial DMARC are operated independently of Pages and must not be overwritten for the web cutover.
- Independently confirm inbound and outbound Zoho mail. Successful SPF/DKIM/DMARC on one outgoing test does not guarantee good inbox placement.
- Domain ownership and availability are not proof of trademark clearance. A legal/name clearance review remains separate.

## Recovery

If Cloudflare Pages content or delivery is broken, revert the most recent Pages deployment using the Cloudflare dashboard or its rollback API, and detach/reconfigure the custom domain DNS only after checking the replacement is usable. Preserve the old GitHub Pages deployment as a temporary independent fallback until the new public domain is stable.

Do not expose customer freight records or private repository files as public assets. Do not publish a public claim of operating or security compliance based solely on CI or a successful Pages deployment.
