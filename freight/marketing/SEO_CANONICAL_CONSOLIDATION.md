# RETALLY canonical domain consolidation

**Primary search destination:** `https://www.retallyrecovery.com/`. The GitHub Pages path `https://p00nsmasher.github.io/github-value-hunt-ledger/` is an existing, useful fallback, but older search listings show it as a competing site with out-of-date legacy branding. Both hosts had been emitting self-referencing `rel="canonical"`, with separate sitemaps, splitting search signals.

## Fixed without paid tools or redirect risks

Only GitHub Pages **generated output** is retargeted by `freight/site/legacy_pages_canonical.py`, during its separate deploy job. Cloudflare Pages' source, existing production canonicalization, hosted APIs, Turnstile, sitemap, branding, inquiry data, security headers and release checks remain unaffected.

For every indexable root public marketing HTML and the sample report (29 sitemap URLs total):
- Retarget exactly one legacy canonical to the corresponding production **extensionless 200 URL**.
- Update absolute legacy OG/social/JSON-LD identity references to the same official host, preserving original legacy-relative HTML navigation for fallback readers.
- Advertise only official canonicals in the old sitemap and `robots.txt`, and update the public `llms.txt` references.
- Retain legacy-host pages as a functional fallback; no JavaScript auto-redirect, no global `noindex`, no robots crawl block, no CNAME takeover risk.
- Exclude the `404` page and search verification files; never touch compiled JS, binaries or any source in place. Reject missing/malformed HTML, changing sitemap coverage, unexpected canonical hosts or symlinks.

Google's official guidance says cross-domain `rel="canonical"` is a strong consolidation signal, but **not a guarantee**; search engines may take days or weeks to recrawl and update previously indexed obsolete snippets. IndexNow applies to the canonical host only and does not notify Google. This migration must not claim immediate removal of every old result.

## Verification

PR CI runs the new offline regressions and transforms a real published fixture in an isolated `/tmp` directory. The main GitHub Pages deploy transforms its generated output before artifact upload and verifies its canonical home link.

After merge, confirm: (1) GitHub Pages deployment actually succeeded; (2) a fresh public response from both old and official hosts has the official canonical and no forbidden private contact; (3) official Cloudflare Pages retains self-canonical HTTPS, 29 page sitemap, security headers, safe public audit intake; (4) no duplicate artifacts or paid service changes. Retain release evidence; search-result de-duplication may lag.

Official documentation: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
