# RETALLY Group website consolidation

This package composes a group homepage, eleven individual business pages and a
contact directory into the existing public-only Cloudflare build. The original
freight homepage moves to `/recovery/`; its scripts, assets, inquiry API, managed
challenge, worksheet and public resources retain their established root paths.

## Release state

On 2026-10-21 the owner clarified that the intended domain is
**retallyrecovery.com**. The canonical production URL is
**https://www.retallyrecovery.com/**. The domain is already connected to the
existing Cloudflare Pages project; no registrar, DNS or mailbox migration is
required. The earlier retally.com access blocker is resolved by this correction.

This is a consolidated marketing site. Existing CaptureBrief and
PermitPlate checkout/fulfillment pages and the Resonance demonstration remain on
their established hosts. The client portal remains an authenticated application.
Those operational systems have not been migrated or proxied under this site.

## Public pages

| Business | Route | Public positioning |
|---|---|---|
| RETALLY Recovery | `/recovery/` | Existing freight audit and authorized recovery |
| CaptureBrief | `/capturebrief/` | Existing public-source review offer |
| PermitPlate NYC | `/permitplate/` | Existing founder-curated membership |
| RehabSignal | `/rehabsignal/` | In development |
| SheetHarbor | `/sheetharbor/` | Workbook preview |
| App Factory | `/app-factory/` | Private evaluation |
| RETALLY Data Services | `/data-services/` | Integration enquiries; availability per service |
| ScopeSignal | `/scopesignal/` | Research concept |
| Contractor Quote Recovery | `/contractor-quote-recovery/` | Research concept |
| Resonance | `/resonance/` | Interactive demonstration |
| Market Surveillance Research | `/market-surveillance/` | Research prototype |

The private planning catalog is not serialized into the website. Public copy is
explicitly curated in `catalog.py`; do not infer commercial availability from a
repository test result. Enquiry links now lead to the shared private contact
form. Only CaptureBrief and PermitPlate expose their existing Stripe checkout
links; research and preview pages do not gain a purchase or upload flow.

## Production publication

1. Publish the tested consolidation through the existing protected source and
   Cloudflare Pages pipeline. Preserve the configured canonical www hostname,
   apex redirect, mail records, inquiry origins and managed-challenge settings.
2. Verify the actual production homepage, all eleven business pages, assets,
   metadata, public resources, security headers and GET-only inquiry status.
   A successful public-page check is not evidence of enquiry email delivery.
3. Keep provider checkout, API and authenticated client applications on their
   working hosts. Their integrations have not been migrated by this release.
4. Reconcile duplicate legacy marketing offers before replacing their entry
   points. Do not redirect an operational purchase or fulfilment path to a page
   that links back to the same old destination.
5. Keep the previous production deployment available for rollback. Preserve the
   existing `jay@retallyrecovery.com` business mailbox and DNS.

## Verification

`python -m pytest -q freight/site/group/test_group.py` exercises the full
allowlisted build, all eleven business routes, file counts, asset paths, fragment
destinations, sitemap/canonical agreement, preserved freight intake and honest
preview/research boundaries. The public-sites workflow runs these checks along
with its existing freight and RecoveryOS release checks.

Build with the existing verified business-mail environment:

```sh
FREIGHT_CONTACT_EMAIL=jay@retallyrecovery.com FREIGHT_CONTACT_VERIFIED=1 \
  python -m freight.site.cloudflare_build
```

Output is `cf-retally-public`, containing only the explicit public allowlist.
The build refuses to overwrite an existing output directory.

## Editorial design release — 2026-10-21

The homepage prioritizes the three existing offers. Eight previews, integrations,
demonstrations and research projects retain separate pages and explicit status.
Grouped navigation, earlier sample links, shared green/cream styling and a local
email composer reduce unnecessary steps without changing operating systems.
The freight chat launcher hides while the intake form is in the viewport.

Five new editorial photographs were created with the built-in image-generation
tool and visually reviewed. They are illustrative, not client locations, staff,
product screenshots or proof of results. Approved RETALLY logos are unchanged.

| Asset | Art direction | Published variants |
|---|---|---|
| research | Sunlit stone desk, green folio, notebooks, unbranded laptop; natural materials | 768×512 and 1536×1024 WebP |
| restaurant | NYC corner café, green frames, warm wood, brick, morning light; no readable branding | 768×512 and 1536×1024 WebP |
| tools | Oak maker bench, ceramics, candles, measuring tools, blank notebook; natural daylight | 768×512 and 1536×1024 WebP |
| hero | Business research studio at blue hour, dark green space and warm desk detail; illustrative city view | 768×512 and 1536×1024 WebP |
| digital | Photorealistic oak/aluminum technology workspace, blank screens, green accents | 768×512 and 1536×1024 WebP |

The ten reviewed filenames form an explicit allowlist. Build validation rejects
extra assets, symlinks, malformed WebP, wrong geometry or any image above 450 KB.
PNG generation masters are not shipped. Responsive image widths, intrinsic
dimensions and lazy loading keep the new photography within a small page budget.

## Shared enquiry integration — 2026-10-22

The contact form checks `GET /api/group-inquiry` before enabling secure intake.
An explicit visitor submission sends name, email, optional company, allowlisted
business, a non-sensitive message of up to 800 characters, consent, a Turnstile
`retally_group` token and a request UUID. The API uses the existing private
storage and notification infrastructure. The freight `/api/inquiry` contract
remains separate. There is no document upload, browser persistence or analytics
of form contents, and no submission occurs on page load.

A saved reference is shown only after a valid HTTP 202 receipt. Notification
pending is disclosed separately; the page never treats it as a failed save or
claims delivery to an inbox. Network uncertainty preserves the entered details
and request key for a safe retry. Fields are locked after a confirmed save.
The email draft and complete manual-copy fallback remain available when the
API, security challenge or clipboard is unavailable. Existing mailto opt-outs
remain intact, and copies are explicitly described as unsent.

`node freight/site/group/test_group_client.mjs` exercises the form with mocked
transport and security verification: idle behavior, business-link compatibility,
offline fallback, exact payload, saved/pending receipts, lost-response retries,
changed request keys, malformed receipts, duplicate clicks and manual copying.
These checks do not send an enquiry or email. A production GET and page readback
verify availability; positive delivery needs a separately authorized live test.

Visual acceptance runs all 13 routes at 1440, 768, 390, 375 and 320 CSS pixels, with
real lazy-image loading, keyboard navigation, email-draft updates and chat
clearance (also at the previously affected 1363×936). Pinned axe-core checks
all five current viewport sizes for serious/critical WCAG rule failures.
These checks do not establish full WCAG conformance, email delivery, payment
fulfillment or commercial readiness of the separately labelled prototypes.


The owner-directed benchmark revision adopts the existing freight Recovery
site's photographic depth, dark green heroes, raised controls and clear offer
panels. The homepage has three current offer cards and eight clearly staged
business entries. All ten other business pages have subject-specific imagery,
source-backed offer details, process steps and explicit scope/resources panels.
Recovery retains its own visual system and working intake.

Content-derived CSS/JavaScript URLs prevent existing browser caches from mixing
new HTML with an old stylesheet or script; the regression changes CSS bytes and
checks that its URL changes automatically.

