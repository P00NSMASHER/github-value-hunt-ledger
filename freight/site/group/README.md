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
repository test result. New enquiry links only prepare an email draft. There is
no new tracking, upload, payment, waitlist subscription or outbound message flow.

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
