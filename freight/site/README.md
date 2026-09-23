# Freight Recovery public sales site

This directory is the reviewed source for a static public marketing page. It is not a customer-data application and it is not evidence of a current production deployment.

The page uses the Freight Recovery name, offers two exact one-time checkout prices, explains the optional 80/20 managed-recovery split, and includes a deterministic controlled synthetic pilot download. Its eleven responsive editorial images are illustrative and contain no customer data. The demo contains fictional inputs and current generated outputs; it does not claim a customer result, external action, production control, component right, or revenue.

The public page is self-contained. Image variants and the Hanken Grotesk / Instrument Serif web fonts are served locally, so the browser does not contact an image CDN, font CDN, analytics service, or other third party. The bundled fonts include their SIL Open Font License 1.1 texts plus a byte-level attribution record.

## Required business and checkout configuration

A **verified business contact email** is required before publication. No inbox is invented. The operator must confirm control of the inbox and independently test that it can receive and reply, then set:

```text
FREIGHT_CONTACT_EMAIL=<verified public business inbox>
FREIGHT_CONTACT_VERIFIED=1
```

The build checks syntax and requires the attestation. It cannot prove mailbox ownership or delivery. The unbuilt source visibly says the contact channel is pending.

Two distinct **live Stripe Payment Links belonging to the Freight Recovery business** are also required. Create one one-time USD link for the $5,000 Readiness Review and one for the $15,000 Base Freight Audit, then set:

```text
FREIGHT_READINESS_CHECKOUT_URL=<live $5,000 Stripe Payment Link>
FREIGHT_AUDIT_CHECKOUT_URL=<live $15,000 Stripe Payment Link>
FREIGHT_CHECKOUT_VERIFIED=1
```

Before attesting, verify the Stripe account's public business name and statement descriptor, each product name and exact price, live mode, one-time billing, receipt behavior, customer support details, and the cancellation/terms link. Adjustable quantity, custom amounts, recurring billing, automatic add-ons, and promotion codes must remain off unless the public offer and tests are deliberately revised. Do not reuse a payment account branded for another business.

The build accepts only canonical `https://buy.stripe.com/...` live links, rejects test links, requires the two links to differ, and fails closed when any checkout setting is absent. Nothing is uploaded or stored by the page. No analytics, backend request, confidential intake, tracking pixel, or customer-data route is present. The only external navigation is the operator-verified Stripe-hosted checkout; actual freight records use a separately approved route after written scope confirmation.

## GitHub Pages release path

The `Freight Recovery Public Site` workflow verifies the site and controlled demo on pull requests. It can deploy only from `main`, only after the verification job passes, and only when all five repository variables above are present. All third-party workflow actions are pinned to full revisions.

Before the first release, the repository owner must:

1. Verify the public business inbox outside this repository.
2. Create and independently review both live Payment Links in the correct Freight Recovery Stripe account.
3. Add the five contact and checkout values above as repository variables.
4. In repository Pages settings, select **GitHub Actions** as the source.
5. Review the `github-pages` environment protection and authorized deployment branch.
6. Merge the reviewed change to `main` (or manually dispatch the workflow from
   `main` after adding variables), then inspect the deployed URL and workflow
   receipt.

The workflow does not deploy a pull request and preserves the last good live site until every owner-controlled setting is complete. Publishing checkout does not authorize customer-file intake, managed recovery, carrier contact, or clear the separate customer-processing launch gate.

## Build the exact public boundary locally

From the repository root, with a real verified inbox and both verified live Payment Links in the environment:

```bash
python freight/site/build.py --output /tmp/freight-recovery-public
```

The output directory must be new or empty, outside the private repository, and not one of its parents. The build follows an exact 33-file allowlist and emits only:

- `index.html`
- `site.css`
- `site.js`
- `_headers`
- `synthetic-pilot-demo.zip`
- `assets/fonts/ATTRIBUTION.json`
- `assets/fonts/LICENSE-HANKEN-GROTESK.txt`
- `assets/fonts/LICENSE-INSTRUMENT-SERIF.txt`
- `assets/fonts/hanken-grotesk-latin.woff2`
- `assets/fonts/instrument-serif-latin.woff2`
- `assets/fonts/instrument-serif-italic-latin.woff2`
- `assets/images/approved-path.webp`
- `assets/images/approved-path-800.webp`
- `assets/images/dock-control.webp`
- `assets/images/dock-control-800.webp`
- `assets/images/freight-network.webp`
- `assets/images/freight-network-800.webp`
- `assets/images/human-review.webp`
- `assets/images/human-review-800.webp`
- `assets/images/invoice-evidence.webp`
- `assets/images/invoice-evidence-800.webp`
- `assets/images/rail-yard.webp`
- `assets/images/rail-yard-800.webp`
- `assets/images/rate-authority.webp`
- `assets/images/rate-authority-800.webp`
- `assets/images/terminal-blue-hour.webp`
- `assets/images/terminal-blue-hour-800.webp`
- `assets/images/trailer-blue-hour.webp`
- `assets/images/trailer-blue-hour-800.webp`
- `assets/images/truck-cab.webp`
- `assets/images/truck-cab-800.webp`
- `assets/images/warehouse-handoff.webp`
- `assets/images/warehouse-handoff-800.webp`

The ZIP is rebuilt from the current controlled scenario, and its SHA-256 is embedded in the page. Nested asset paths are still copied one-by-one from the explicit allowlist. The build does not recurse through the repository, copy customer data, or follow source symlinks.

**Deploy only the generated output directory. Never deploy the repository root, `freight/`, or this source directory.** The source directory contains non-public build documentation and tests.

## Verify locally

```bash
python -m pytest -q freight/test_synthetic_rehearsal.py freight/test_synthetic_pilot_bundle.py freight/site/test_build.py
node --check freight/site/site.js
python -m freight.synthetic_pilot_bundle --verify /tmp/freight-recovery-public/synthetic-pilot-demo.zip
```

The `_headers` file supplies defensive response headers on hosts that implement that convention. GitHub Pages does not promise to interpret it, so the HTML also contains a restrictive Content Security Policy meta tag. Browser-enforced framing protection still depends on an HTTP `frame-ancestors` or equivalent header; this limitation should remain in the deployment review.

Use only fictional details during preview. Check the configured contact, both checkout destinations and prices, Stripe business identity, desktop/mobile layout, calculator math, keyboard navigation, reduced-motion behavior, controlled-demo digest, and download. A generated bundle or successful workflow is not proof that the public URL, mailbox, payment receipt, or refund flow works; record those observations separately after release.
