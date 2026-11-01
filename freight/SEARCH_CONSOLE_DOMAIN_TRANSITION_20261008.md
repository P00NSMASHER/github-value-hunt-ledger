# RETALLY search-indexing domain transition: evidence ledger

## October 8 continuation: new-domain Google Search Console property VERIFIED and sitemap submitted

**Evidence time:** 2026-10-08 12:48–12:55 UTC. This section supersedes the *earlier-in-the-day* "currently blocked" status further below, which is retained as a historical record of the migration process. Do not retroactively rewrite the October 7 baseline.

- The Google account already authorized for Search Console now returns **siteOwner** for the verified **Domain property** `sc-domain:retallyrecovery.com` (covers www and apex).
- Added the verified property to the connected GSC Wizard dashboard. Original URL-prefix GitHub Pages property remains registered, active, and unchanged.
- Submitted the exact already-published `https://www.retallyrecovery.com/sitemap.xml` under the Domain property. The Google Search Console API confirmed **accepted/submitted**, timestamp **2026-10-08T12:50:47.112Z**; **pending download/processing**, reported warnings=0/errors=0 *at submission time*. This is not evidence of indexing or successful Google download.
- Registered all **26** production sitemap URLs in a separate new-domain Indexing Tracker. ID `ec6987bb-919e-42f0-9aa4-b6cbfca72a90`, active with automatic checks and email digest enabled.
- Independently called **Google URL Inspection** on all **26** `www.retallyrecovery.com` final extensionless production URLs, including the homepage and all original nine priority commercial pages. Result: **26/26 successful API inspections, 0 inspection API errors**. Google's verdict for every URL: `NEUTRAL`; coverage: `URL is unknown to Google`; last crawl: absent; indexing state: unspecified. **No new-domain URLs are confirmed indexed at this checkpoint.** These are normal initial discovery-stage observations; do not call them robots-blocked or failed crawls.
- Ran immediate tracked-URL checks for each of the 26 URLs so the new tracker reflects **0 indexed, 26 not indexed (unknown to Google), 0 pending, 0 errors**. Most recent tracker check: **2026-10-08T12:55:49.555Z**. Hourly future tracker checks are built into the connected service; no separate ChatGPT task was created.
- The new domain's recent Search Console performance endpoint returned no settled-through data boundary or usable query/page rows. **Do not report zero traffic as a confirmed settled historical metric**, and do not infer rankings from the lack of early Search Console rows.
- Previous independent production HTTP audit (after Cloudflare deployment of main `2cd91eaf076a6f3415ee3f8a1c551dd920376b0c`) established that all **26** sitemap URLs load directly, are self-canonical, and show no explicit `noindex` or legacy-host/`.html` internal links. Apex-to-www 301 and legacy GitHub Pages fallback were verified; those are **live-site tests**, separate from Google indexing evidence.

**Side-by-side checkpoints:**

| Measure | October 7 old-host baseline | October 8 old-host follow-up | October 8 new-domain checkpoint |
| --- | --- | --- | --- |
| Google property | Verified URL prefix | Verified, retained | **Verified Domain property**, `siteOwner` |
| Sitemap | Accepted, pending | Old sitemap still pending | **New sitemap accepted, pending download** |
| Inspection | Homepage indexed; nine initial commercial URLs unknown | Separate 26-URL tracker | **26/26 Google URL Inspection complete**, all unknown |
| Tracked URLs | Ten initial priority URLs | 26 tracked | 26 tracked |
| Confirmed indexed among tracked | Homepage confirmed indexed | **4/26 indexed, 22 not indexed** | **0/26 currently reported indexed**, 26 unknown |
| Errors, penalties or disallowed robots | Not established for unknown URLs | No tracker errors | No tracker errors; unknown means Google's crawl/robots verdict is not yet available |
| Organic impressions, clicks and positions | No initial query evidence | Historical baseline preserved | Settled performance not yet established |

**Remaining external/search-engine actions:** Google must discover, download, crawl, choose its canonical, and index URLs on its own timetable. Recheck new sitemap after download for genuine warnings and submitted/indexed counts. Indexing requests via Google's Search Console UI are not equivalent to successful indexing; the URL Inspection API does not provide a general-purpose request-indexing action for ordinary service pages. Avoid repeatedly resubmitting the same sitemap or inventing new indexes. Do not decommission the original host or property based only on new sitemap acceptance.

---

**Opened:** 2026-10-08 UTC. **Status:** Cloudflare serves company-owned hosts; an independent live-browser audit exposed mismatched commercial canonicals and sitemap URLs. The fix is developed separately for the Cloudflare-only build. The Google Search Console property for the new domain has **not** yet been confirmed as verified, and the production sitemap has **not** yet been submitted to that property.

## Scope and hard boundaries

- Canonical public host: `https://www.retallyrecovery.com/`.
- Cloudflare Pages project: `retally-web`, connected to `P00NSMASHER/github-value-hunt-ledger` branch `main`, built with `python -m freight.site.cloudflare_build` into `cf-retally-public`.
- Original independently published GitHub Pages site: `https://p00nsmasher.github.io/github-value-hunt-ledger/`.
- Do **not** delete/unpublish the original property or its sitemap, rewrite its original build URLs, remove its tracker, or claim indexing from a successful deployment, sitemap submission, or URL inspection request.
- Build output remains a strict public allowlist. Do not publish any other repository files. Cloudflare DNS changes must not interfere with Zoho mail.
- The original HTTP origin is GitHub-controlled and lies outside RETALLY's Cloudflare DNS zone. No Cloudflare configuration on `retallyrecovery.com` can issue 301 redirects from `p00nsmasher.github.io`.

## October 7 baseline: original property (preserve indefinitely)

Source: `freight/SEARCH_CONSOLE_INDEXING.md` dated 2026-10-07.

| Item | Confirmed on 2026-10-07 |
| --- | --- |
| URL-prefix property | `https://p00nsmasher.github.io/github-value-hunt-ledger/`, verified |
| Registered sitemap | `https://p00nsmasher.github.io/github-value-hunt-ledger/sitemap.xml` |
| Sitemap result | Submission accepted; pending download/processing, **not proof of indexing** |
| Homepage inspection | PASS, submitted and indexed, last crawl 2026-10-07 00:53:28 UTC |
| Nine initially selected commercial-page inspections | NEUTRAL / URL unknown to Google; no last crawl |
| Search query performance | No query rows in initial inspection window |

The nine initial commercial pages were `freight-audit-services.html`, `freight-invoice-audit.html`, `second-look-freight-audit.html`, `freight-audit-methodology.html`, `freight-invoice-audit-checklist.html`, `duplicate-freight-charges.html`, `freight-overcharge-recovery.html`, `founding-program.html`, and `trust.html`.

**October 8 separate observation:** The legacy property's connected Indexing Tracker has 26 tracked URLs: four indexed and 22 not indexed (principally URL unknown), last checked 2026-10-08 12:00:33 UTC. The indexed four are:
- `/`
- `/freight-invoice-audit.html`
- `/freight-overcharge-recovery.html`
- `/freight-audit-companies.html`

This later checkpoint is an update, not a retroactive alteration of the October 7 baseline. The old sitemap remained **pending** with no reported warnings/errors in the available submission record.

## October 8 observed public delivery BEFORE clean-path fix

| Check | Evidence |
| --- | --- |
| `https://www.retallyrecovery.com/` | HTTPS 200, self-referencing www canonical, `index,follow` |
| `https://retallyrecovery.com/` | 301 -> `https://www.retallyrecovery.com/`, HTTPS 200 |
| Cloudflare DNS / custom domains | Both custom domains reported active, CNAME proxied to `retally-web.pages.dev` |
| Apex redirect | Active zone dynamic-redirect rule: 301, path/query preserved, host becomes www |
| `/robots.txt` | HTTPS 200, allows crawling and points at www sitemap |
| `/sitemap.xml` | HTTPS 200, 26 www URLs, **but internal `.html` paths** |
| `/freight-audit-services.html` | 308 -> `/freight-audit-services`, final 200, **canonical points to redirecting `.html`** |
| `/trust.html` and `/freight-invoice-audit-checklist.html` | Same extensionless final path vs `.html` canonical mismatch |
| Old GitHub Pages homepage | HTTPS 200, original old-domain self-canonical, **not redirected** |

The conflicting directions (sitemap/canonical `.html` vs actually served final extensionless URL) are a demonstrable SEO configuration defect and create needless redirects for ordinary internal links. They are *not* evidence that Google has indexed the new domain.

## Fix applied exclusively to generated Cloudflare deployment bundle

The source and original GitHub Pages production build remain unchanged.

- `freight/site/rebase_public_urls.py`: after replacing the old absolute origin with www, normalize all known root-level commercial `.html` paths to the Cloudflare extensionless HTTP 200 destination within canonical tags, sitemap, absolute social/structured metadata URLs, and root-level HTML navigation links. Preserve actual HTML files, Google verification file, images, and nested RecoveryOS relative links.
- `freight/site/cloudflare_build.py`: fail the Cloudflare publication build if the sitemap does not enumerate **exactly** every known root-level indexable final URL once, if any included page lacks its correct self-canonical, or if robots fails to advertise the correct production sitemap.
- `freight/site/test_rebase_public_urls.py`: fixture-based regression tests cover canonical and sitemap consistency, duplicate/missing entries, internal link cleanup, binary/verification-file preservation, nested links, symlink failure and absent old origin.
- No Cloudflare redirect-rule mutation is necessary. The existing apex -> www 301 is correct.
- **Publication rule:** Merge to main only after tests and actual Cloudflare artifact build pass. Verify a successful later Cloudflare production deployment and recheck public page, sitemap, robots, canonicals, and links. An open PR or green test alone is not a production fix.

## New-domain Search Console: currently blocked

The connected Google account in GSC Wizard has Google Search Console (`webmasters`) authorization. Attempts to register `https://www.retallyrecovery.com/` and `sc-domain:retallyrecovery.com` report that **neither property exists in its accessible Search Console**. The existing old GitHub Pages property is already registered and remains visible.

No Google verification TXT token is present in the inspected public DNS TXT inventory, and no invented token should be inserted. The existing published Google HTML file `/google738a4fc9a0997cd0.html` is available as a potential verification method for the URL-prefix property, but only Google's successful ownership-verification response can establish whether that token authorizes the new property. An independent authenticated browser action was attempted but was blocked by unavailable browser credits; no successful property creation or verification should be inferred.

**Authorized user-account completion steps:**
1. Sign in to [Google Search Console](https://search.google.com/search-console) using the connected Google account and use **Add property**. Prefer a Domain property `retallyrecovery.com` to cover apex/www; this requires the exact DNS TXT verification token **generated by Google**. Keep existing Cloudflare MX, SPF, Zoho verification, DKIM, and DMARC records intact. A URL-prefix `https://www.retallyrecovery.com/` is an alternative if verification via Google's requested HTML file (and its exact expected content/path) succeeds. Keep the original GitHub Pages property as well.
2. After Search Console explicitly confirms ownership and the connected API recognizes the new property, submit **`https://www.retallyrecovery.com/sitemap.xml`**, but only after it lists final 200 extensionless URLs.
3. Use Google URL Inspection under the new property for homepage and priority commercial URLs below. Record exactly the Google verdict, canonical chosen by Google, discovery/crawl status, crawl timestamp, and indexing exclusions. API inspection is read-only and cannot request indexing through Google's Indexing API for ordinary marketing pages.
4. In the Search Console UI, request indexing selectively for priority pages when appropriate. Treat requests as requests, not indexing confirmations. Reinspect only after Google reports crawl/index changes. Review sitemap download warnings and submitted/indexed totals separately.

**Priority final 200 new-host URLs (not yet GSC-inspected on new property):**

```
https://www.retallyrecovery.com/
https://www.retallyrecovery.com/freight-audit-services
https://www.retallyrecovery.com/freight-invoice-audit
https://www.retallyrecovery.com/second-look-freight-audit
https://www.retallyrecovery.com/freight-audit-methodology
https://www.retallyrecovery.com/freight-invoice-audit-checklist
https://www.retallyrecovery.com/duplicate-freight-charges
https://www.retallyrecovery.com/freight-overcharge-recovery
https://www.retallyrecovery.com/founding-program
https://www.retallyrecovery.com/trust
```

## Migration metrics: do not collapse unlike stages

| Stage | Old property baseline | New property |
| --- | --- | --- |
| Property verification | Verified 2026-10-07 | Not confirmed |
| Sitemap submission | Accepted 2026-10-07, pending processing | Not submitted |
| Inspection | Homepage indexed; nine priority pages unknown on 2026-10-07 | Not available |
| 26-page tracker status | Four indexed, 22 not indexed on 2026-10-08 | Tracker not established |
| Confirmed indexed pages | Old-domain four according to Oct8 tracker | **Unknown, not zero** |
| Impressions, clicks, CTR, position | Query rows not available on initial read | Not measurable via GSC until property accessible |

Record weekly settled performance independently per property, page and query where available. A live page is not indexed merely because its URL responds 200; a sitemap accepted by Google does not guarantee discovery, and an inspection request does not guarantee indexing or ranking.

## Legacy-origin policy

Keep the old URL-prefix property, old host content, old sitemap and Indexing Tracker intact while the new-domain property is inaccessible. The legacy origin remains **independently accessible**, so it has not been 301-redirected. This is acceptable as a deliberate short-term fallback but introduces duplicate-content/canonical competition; after the new GSC property, sitemap and primary URLs are independently verified, plan an intentional old-origin canonical or true redirect transition if the hosting environment supports it. Do not claim an HTTP redirect is configured on GitHub Pages because changing RETALLY's Cloudflare apex settings cannot affect GitHub-owned URLs.

## Acceptance evidence to attach once available

1. GitHub PR and exact-head CI run links.
2. Cloudflare Pages production deployment ID/commit and successful build/deploy stages.
3. Verified `www` sitemap 26 final 200 URLs with no redirecting `.html` entries; each corresponding page self-canonical and `index,follow`.
4. Verified apex -> www 301 preserving a deep path and query string; GitHub Pages remains 200 with its unchanged older canonical.
5. Google-owned new property exact verified state and new sitemap entry/pending/download result, or explicit blocker.
6. New-domain URL Inspection results and separate index statuses, preserving October 7 and October 8 old-property baselines.
