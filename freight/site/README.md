# Freight Recovery public sales site

This directory is the reviewed source for a static public marketing page. It is not a customer-data application and it is not evidence of a current production deployment.

The page uses the Freight Recovery name, publishes the current offer starting points with explicit qualification, and includes a deterministic controlled synthetic pilot download. The demo contains fictional inputs and current generated outputs; it does not claim a customer result, external action, production control, component right, or revenue.

## Required business configuration

A **verified business contact email** is required before publication. No inbox is invented. The operator must confirm control of the inbox and independently test that it can receive and reply, then set:

```text
FREIGHT_CONTACT_EMAIL=<verified public business inbox>
FREIGHT_CONTACT_VERIFIED=1
```

The build checks syntax and requires the attestation. It cannot prove mailbox ownership or delivery. The unbuilt source visibly says the contact channel is pending.

The inquiry tool prepares text locally in the visitor's browser. Nothing is submitted, uploaded, stored, or sent by the page. No analytics, backend request, confidential intake, tracking pixel, or customer-data route is present. When a verified inbox is configured, the visitor can open an email draft and send it themselves.

## GitHub Pages release path

The `Freight Recovery Public Site` workflow verifies the site and controlled demo on pull requests. It can deploy only from `main`, only after the verification job passes, and only when both repository variables above are present. All third-party workflow actions are pinned to full revisions.

Before the first release, the repository owner must:

1. Verify the public business inbox outside this repository.
2. Add `FREIGHT_CONTACT_EMAIL` and `FREIGHT_CONTACT_VERIFIED=1` as repository variables.
3. In repository Pages settings, select **GitHub Actions** as the source.
4. Review the `github-pages` environment protection and authorized deployment branch.
5. Merge the reviewed change to `main` (or manually dispatch the workflow from
   `main` after adding variables), then inspect the deployed URL and workflow
   receipt.

The workflow does not deploy a pull request and is inert until those owner-controlled settings are complete. Publishing this static page does not authorize customer-file intake or clear the separate customer-processing launch gate.

## Build the exact public boundary locally

From the repository root, with a real verified inbox in the environment:

```bash
python freight/site/build.py --output /tmp/freight-recovery-public
```

The output directory must be new or empty, outside the private repository, and not one of its parents. The build follows an exact allowlist and emits only:

- `index.html`
- `site.css`
- `site.js`
- `_headers`
- `synthetic-pilot-demo.zip`

The ZIP is rebuilt from the current controlled scenario, and its SHA-256 is embedded in the page. The build does not recurse through the repository, copy customer data, or follow source symlinks.

**Deploy only the generated output directory. Never deploy the repository root, `freight/`, or this source directory.** The source directory contains non-public build documentation and tests.

## Verify locally

```bash
python -m pytest -q freight/test_synthetic_rehearsal.py freight/test_synthetic_pilot_bundle.py freight/site/test_build.py
node --check freight/site/site.js
python -m freight.synthetic_pilot_bundle --verify /tmp/freight-recovery-public/synthetic-pilot-demo.zip
```

The `_headers` file supplies defensive response headers on hosts that implement that convention. GitHub Pages does not promise to interpret it, so the HTML also contains a restrictive Content Security Policy meta tag. Browser-enforced framing protection still depends on an HTTP `frame-ancestors` or equivalent header; this limitation should remain in the deployment review.

Use only fictional details during preview. Check the configured contact, mobile layout, keyboard navigation, controlled-demo digest, download, and every local inquiry action. A generated bundle or successful workflow is not proof that the public URL or mailbox works; record those observations separately after release.
