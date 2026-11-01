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

## Live release audit: Cloudflare HTTP 504 classification

The site has a daily scheduled, read-only independent live release audit.
**Do not treat sampled raw `EdgeResponseStatus=504` totals as visitor-facing
downtime.** Cloudflare Pages automatically issues Early Hints cache probes:
a cache miss can log `504` with `OriginResponseStatus=0` without affecting
the visitor's final response. Workers Cache API misses can do the same.
The correct detailed-log filter uses the request source
(`earlyHintsCache`, `edgeWorkerCacheAPI`), **not** a user-agent guess.
An `eyeball` 504 or a failed independent public GET must still be investigated.

On October 19, 2026, read-only Cloudflare adaptive-sample analytics showed
many internal-looking 504s and the original RETALLY live-audit user agent.
During the October 20 UTC production release audit, all 13 sampled monitor
504 entries had successful HTTP 200 entries for the same path and user agent
within one second. That is compelling cache-miss evidence, but does **not**
prove every edge 504 was harmless. Detailed request-source logs were not
accessible with the current account role.

The independent `freight.site.verify_production_site.fetch` therefore
retries only an actual HTTP 504 from its GET request, at most twice
(with 0.25s / 0.5s delays and an 18s timeout per try). The last 504 still
fails the existing inspection. HTTP 404, intentional inquiry GET 503,
HTTP redirects, transport exceptions, invalid security headers, stale HTML,
incorrect media hashes, and unsafe links remain fail-closed. No POST requests,
customer-data access, Cloudflare configuration changes, or background jobs
are introduced. The push-specific outer deployment-grace retries remain
unchanged, as does the daily scheduled audit.

Authoritative references:
- https://developers.cloudflare.com/pages/configuration/early-hints/
- https://developers.cloudflare.com/logs/faq/504-origin-status-0/

## Recovery

If Cloudflare Pages content or delivery is broken, revert the most recent Pages deployment using the Cloudflare dashboard or its rollback API, and detach/reconfigure the custom domain DNS only after checking the replacement is usable. Preserve the old GitHub Pages deployment as a temporary independent fallback until the new public domain is stable.

Do not expose customer freight records or private repository files as public assets. Do not publish a public claim of operating or security compliance based solely on CI or a successful Pages deployment.
