# Freight Recovery public site

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

## Required checks

Run the site build tests, commercial-term tests, qualification tests, browser
script syntax checks, and a rendered responsive pass before deployment. Search
the built public directory for legacy checkout prices and links; none should be
present.
