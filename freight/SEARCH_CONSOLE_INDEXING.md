# Freight Recovery Search Console / Indexing Setup

Updated: 2026-10-06

## Current state

- GSC Wizard connection is authenticated to jayp19386@gmail.com with Search Console scopes.
- No Search Console property is currently registered for:
  https://p00nsmasher.github.io/github-value-hunt-ledger/
- Attempting to register the URL in GSC Wizard returns:
  "Site ... not found in your Google Search Console account. Add it to GSC first, then retry."
- Direct URL-prefix property creation through GSC Wizard also fails because there is no existing registered parent property whose Google account owns the domain.
- The marketing site already publishes robots.txt and sitemap.xml and allows indexing.

## Required one-time external verification

Add this exact URL-prefix property in Google Search Console:

https://p00nsmasher.github.io/github-value-hunt-ledger/

Then verify ownership using a method supported by the GitHub Pages URL-prefix property.

Once the property is verified, the remaining execution path is mechanical:

1. Register the verified property in GSC Wizard.
2. Add sitemap:
   https://p00nsmasher.github.io/github-value-hunt-ledger/sitemap.xml
3. Inspect the homepage.
4. Inspect priority commercial pages:
   - /freight-audit-services.html
   - /freight-invoice-audit.html
   - /second-look-freight-audit.html
   - /freight-audit-methodology.html
   - /freight-invoice-audit-checklist.html
   - /duplicate-freight-charges.html
   - /freight-overcharge-recovery.html
   - /founding-program.html
   - /trust.html
5. Add those URLs to the indexing tracker.
6. Create a topic cluster for the freight-audit query family.
7. Track clicks, impressions, CTR, and average position.
8. Use actual query data for title/content changes rather than guessing.

## Target query cluster

- freight audit services
- freight invoice audit
- freight bill audit
- freight post audit
- second look freight audit
- freight overcharge recovery
- duplicate freight charges
- carrier rate audit
- accessorial charge audit
- ltl freight audit
- parcel audit
- freight invoice audit checklist

## Success ladder

DISCOVERED -> CRAWLED -> INDEXED -> IMPRESSIONS -> TOP 20 -> TOP 10 -> TOP 5 -> #1

Do not treat sitemap submission or an indexing request as proof of ranking.
