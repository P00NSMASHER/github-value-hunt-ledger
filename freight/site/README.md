# RETALLY public freight site

This directory is the allowlisted source for the customer-facing GitHub Pages
bundle at `https://p00nsmasher.github.io/github-value-hunt-ledger/`.

## Flagship commercial path

The public offer is:

1. a **$0-upfront recovery audit**;
2. a concise opportunity summary rather than a claim-execution package;
3. a separately authorized recovery engagement; and
4. a configurable contingency fee charged only against eligible funds actually
   recovered.

The default working rate is owned by `freight/commercial_terms.py`. The build
injects that value into `commercial-config.js`, so changing the approved rate
does not require editing page copy or calculator logic.

Optional fixed-fee forensic work remains available by custom written scope. It
is deliberately secondary and has no public self-checkout.

## Build

Set a verified public business inbox, then build into a new directory outside
the repository:

```text
FREIGHT_CONTACT_EMAIL=<verified business inbox>
FREIGHT_CONTACT_VERIFIED=1
FREIGHT_CONTINGENCY_RECOVERY_RATE=0.30  # optional; defaults to the shared term
python freight/site/build.py --output <new external directory>
```

The build fails closed when the inbox is missing, malformed, unverified, or a
placeholder. It also validates that the configured recovery rate is greater
than zero and less than one.

## What the public form does

The short, single-screen qualification form runs entirely in the browser. It
asks only for contact/company information, an annual freight-spend range, and
freight type; deeper qualification details are optional and progressively
disclosed. It does not upload files, send a network request, or use browser
storage. On submit it prepares a non-sensitive email and opens the visitor's
email app; the visitor still reviews and sends the message from their own
account.

Freight records are accepted only after a human fit review, written scope, and
an approved secure transfer route. The public site must never claim that an
upload occurred or that a lead qualified merely because the form was filled.

## Publication boundary

`build.py` copies only an explicit allowlist of public HTML, CSS, JavaScript,
fonts, images, and trust files. It also generates the controlled synthetic demo
bundle and verifies its digest internally. The checksum is not exposed in the
customer-facing page. It never recurses through or publishes the private
repository.

The GitHub Pages workflow deploys only the built directory. The old payment-link
variables are not deployment gates and are not copied into the site.

## Funnel events

`site.js` exposes `window.FreightRecoveryAnalytics.events` and emits a
`freight:analytics` custom event. If a future analytics loader provides a
`dataLayer`, the same names are pushed there. The public page emits only events
it can truthfully observe. Operational events such as secure data submission,
qualification, audit completion, engagement acceptance, and actual recovery are
reserved for the systems that can verify those state changes.

## Search discovery and identity

The homepage includes structured Organization and Service JSON-LD stating that
Freight Recovery is based in Pottsville and serves U.S. businesses. It does not
claim a storefront, walk-in hours, map-pack eligibility, or completed platform
listings. Only add `sameAs` links after verifying ownership and the live
external company profile; never link a guessed slug or an unrelated business.
See `freight/FREE_PROFILE_ASSET_PACK.md` for eligibility gates and ready copy.

## Required checks

Run the site build tests, commercial-term tests, qualification tests, browser
script syntax checks, and a rendered responsive pass before deployment. Search
the built public directory for legacy checkout prices and links; none should be
present.

## Brand presentation

The original website geometry, fonts, layout, intake and recovery logic are retained. Only the approved RETALLY logos and the emerald/deep-forest color system change. Published wordmark and emblem WebP assets are compact derivatives of the approved original raster artwork. Keep the full-resolution masters in the RETALLY brand starter package. Do not rename the `FreightRecoveryAnalytics` JavaScript API or existing public URLs without a separate migration.

## Public claim release safeguard — Mission 36

The RETALLY site builder and the companion RecoveryOS builder run the
**same fail-closed claim check before writing public output**. It checks
post-templating visible HTML text, SEO metadata, JSON-LD, browser-facing
JavaScript, and root-level text assets for high-confidence unsupported
customer-outcome and freight-audit market assertions.

The closed Mission 35 Lab 14 claim policy supplies the category boundaries.
The public gate blocks invented customer cash recovered, claimed counts of
real invoices processed, unsupported accuracy and recovery success rates,
recoverable TAM fabricated from government industry data, and guaranteed
recoveries. Legitimate service descriptions, the $0-upfront audit offer,
written recovery-contingency terms, and clearly labeled fictional examples
are preserved.

Existing fictional report, example, and calculator labels are required. The
same applies to the broader RecoveryOS illustrative ledger. Deleting a label
or adding an unsupported claim blocks the build even when the synthetic
example calculations remain internally correct.

**This is a high-specificity rule gate, not general semantic fact checking,
a legal review, an independent customer-evidence certification, or marketing
approval.** New results, case studies, testimonials, competitive claims,
market sizing, or actual customer consent require independent human evidence
and the relevant approval path even if they pass these narrow checks.
A public government source digest is not permission to claim customer
recoveries.

The GitHub Pages path has two enforcement layers:

1. Both the RETALLY and RecoveryOS build scripts reject risky public copy
   before they create output directories.
2. The freight-site-pages workflow separately checks both final built
   directories before deploy, including the main-only deployment job.
   The repository-wide release gate runs the adversarial injection tests.

To inspect existing finished bundles locally, run:

    python -m freight.site.public_claim_guard \
      --freight-root /tmp/freight-recovery-public \
      --recoveryos-root /tmp/recoveryos-public

Failures report only the rule code and static relative filename, not any
untrusted or private claim text. No customer records, contact actions,
purchases, scheduled checks, or production updates are introduced.

**Scope limit:** The check covers this repository's GitHub Pages publication
path. It does not automatically cover a separate Cloudflare Pages pipeline,
email, a CMS, social posts, chatbot messages, or any other deployment until
those pipelines are explicitly verified and wired to the same safeguard.
