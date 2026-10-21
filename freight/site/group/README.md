# RETALLY Group website consolidation

This package composes a group homepage, eleven individual business pages and a
contact directory into the existing public-only Cloudflare build. The original
freight homepage moves to `/recovery/`; its scripts, assets, inquiry API, managed
challenge, worksheet and public resources retain their established root paths.

## Release state

Prepared for preview on 2026-10-21. The requested target is **retally.com**.
The currently connected production domain is **www.retallyrecovery.com**.
The authenticated hosting inventory does not contain a retally.com zone or a
retally.com custom domain. Do not claim that the target domain is connected.

The preview is a consolidated marketing site. Existing CaptureBrief and
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

## Domain cutover requirements

1. Obtain authorized DNS/registrar access for the exact `retally.com` domain.
   Its ownership elsewhere is not resolved by absence from this hosting account.
   Do not purchase or transfer it without separate bounded instructions.
2. Inventory and preserve its existing DNS, mail, verification and security
   records. Add the intended web hostname to the existing Pages project using
   the hosting provider's required validation. Verify TLS before changing links.
3. Update the canonical origin, SEO validation, first-party host allowlists,
   inquiry browser host detection, server Origin checks, managed-challenge
   hostname configuration, production audit URLs and search-discovery files as
   one tested migration. Do not merely search/replace the business mailbox.
4. Use a target-domain preview to verify every page, asset, source URL, security
   header, customer entry point and inquiry path. A preview email-draft fallback
   is not evidence of production notification delivery.
5. Deploy the verified source, then verify the exact live revision. Only after
   successful target-domain validation add path-preserving redirects from the
   old marketing destinations. Keep provider checkout, API and authenticated
   client applications on their working hosts until individually migrated.
6. Keep the previous production deployment available for rollback. Preserve the
   `jay@retallyrecovery.com` mailbox and its DNS unless a separate mail migration
   is actually completed and verified.

Do not redirect the existing sites to an unconnected domain. This branch is
intentionally reviewable before the domain-access blocker is resolved.

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
