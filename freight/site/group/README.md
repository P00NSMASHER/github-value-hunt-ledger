# Freight homepage restoration and RETALLY Group handoffs

The owner-directed release of 2026-10-22 restores the original standalone
freight homepage at **https://www.retallyrecovery.com/**. The Group directory
publishes separately at **https://group.retallyrecovery.com/**. This package no
longer replaces the freight root or adds a portfolio navigation bar to it.

## Production map

| Site | Destination | Publication source |
| --- | --- | --- |
| RETALLY Freight Recovery | https://www.retallyrecovery.com/ | Existing `freight/site` |
| RETALLY Group | https://group.retallyrecovery.com/ | `company_sites/group` |
| RETALLY RecoveryWorks | https://recoveryworks.retallyrecovery.com/ | `company_sites/recoveryworks` |
| PermitPlate | https://permitplate.retallyrecovery.com/ | Separate PermitPlate repository |
| CaptureBrief | https://capturebrief.retallyrecovery.com/ | Separate CaptureBrief repository |

The four operating businesses have distinct websites and navigation. Group
membership does not create a new legal entity, a universal fee or an accepted
engagement. RecoveryWorks' public scope is a managed pilot for vendor
overpayments and missed supplier credits. Other experiments do not appear in
the Group's commercial navigation.

## Restoration and old URLs

`build_group` preserves the established `freight/site/index.html` composition,
its verified audit form, assets, worksheet and public resources. The only root
additions are a compatible contact-status anchor, a discreet Group footer link
and content-derived asset versions. Existing inquiry and chat behavior remain.

Exact redirects send `/recovery/` to the freight root, `/capturebrief/` and
`/permitplate/` to their dedicated sites, `/recoveryos/` to RecoveryWorks, and
`/contact/` to the Group contact section. Slashless and `index.html` variants
receive the same redirects. A fragment-free freight Location preserves legacy
`#start-audit` and `#pricing` links. Static fallback pages keep previews usable.

RehabSignal, SheetHarbor, App Factory, Data Services, ScopeSignal, Contractor
Quote Recovery, Resonance and Market Surveillance have noindex archive pages.
They are outside the current commercial portfolio and acquire no invented
commercial successor. Existing research, product and design source files remain
in the repository; the legacy catalog and page templates are not published by
the restored freight build. Resonance remains outside the RETALLY Group offer.

## Group enquiries

The active Group form and browser client live in `company_sites/group`.
`https://www.retallyrecovery.com/api/group-inquiry` retains the existing private
D1 receipt, rate limiting, verified fixed inbox and notification transport. Its
CORS admission is limited to the exact production Group origin; the freight
`/api/inquiry` route keeps its separate same-origin contract. Previews cannot
submit to production. Cloudflare Turnstile verifies the route-specific action
and the approved originating hostname.

An explicit submission includes name, email, optional company, one of the four
businesses or a general enquiry, a non-sensitive message of at most 800
characters, consent, a challenge token and a request UUID. No documents,
credentials, payment or recovery authority are collected. There is no browser
storage or form-content analytics, and page load never submits an enquiry.

A reference appears only after a valid HTTP 202 saved receipt. Pending
notification is disclosed separately from durable acceptance; a saved reference
is not proof of mailbox delivery. Uncertain responses preserve entered details
and the same request key for a retry. Confirmed receipt locks the submitted
fields. Explicit email-draft and complete manual-copy fallbacks remain available.
Operational handling and retention are documented in
`freight/inquiry_ops/OPERATIONS.md`.

## Verification and publication

Build the existing freight bundle with the verified public business inbox:

```sh
FREIGHT_CONTACT_EMAIL=jay@retallyrecovery.com FREIGHT_CONTACT_VERIFIED=1 \
  python -m freight.site.cloudflare_build
```

The builder refuses an existing nonempty output and publishes only the explicit
allowlist. `python -m pytest -q freight/site/group/test_group.py` checks the
original homepage, compatibility/archive routes, exact redirect destinations,
public-file boundary, anchors and asset versions. Independent company builds
and tests are documented in `company_sites/README.md`.

The inquiry workflow tests freight and Group contracts with mocked transport,
including receipt uncertainty and idempotent retries. Its client tests exercise
the active standalone Group frontend; the old client-test entry point is only
a compatibility launcher. No test sends an enquiry or email.

Visual acceptance serves freight, Group and RecoveryWorks as independent local
sites at five viewport widths. It checks 95 page/viewport combinations, all four
Group destinations, keyboard focus, local handoffs, serious/critical axe results,
compact security-widget clearance and the original freight chat clearance.
Production redirect and security-header checks remain the separate GET-only
live publication verifier. These checks do not establish mailbox delivery,
payment fulfillment or readiness of unlaunched services.

Existing editorial photographs are illustrative, not staff, customer locations,
product screenshots or recovery results. Only named, approved image and font
assets enter each company's output; generation masters and private operations
do not. Preserve the established business mailbox, mail DNS, operational APIs
and previous production deployment throughout the migration.
