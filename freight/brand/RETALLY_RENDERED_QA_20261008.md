# RETALLY rendered website and interaction QA

**Date:** 2026-10-08  
**Status:** PASS for *tested color-only candidate*; NOT a domain/mail/legal launch authorization.

## Method and comparison
- Headless Google Chrome on an authorized connected Windows device; test scripts used a temporary isolated clone of PR #283 (at source head `80f2baaf7e9f779fac51b1e8be6ae5996500ed36`).
- Compared live GitHub Pages homepage to a localhost copy of `freight/site/index.html` and `foundry.css`.
- The local preview served the same **30% commercial rate display fixture** as the live build. The raw source deliberately carries an unbuilt placeholder; judging screenshots from raw source without injection generates a false long pricing card.
- The preview did not route mail, expose a live production inbox, or create a customer lead. No confidential records were handled.

## Responsive visual checks
Tested viewport widths: **320, 353, 375, 390, 428, 768, 1280 and 1440 CSS pixels**.

At all eight widths:
- HTTP response 200; typography assets loaded.
- No missing images, duplicate IDs, JavaScript page errors or page-wide horizontal overflow.
- Header, hero typography, CTA position/size, and final page height matched the live page after the rate fixture.
- Mobile sticky CTA remains disabled; main hero CTA remains accessible.
- Color differences are intentional: dark ink/charcoal replaces large forest-green regions; emerald remains the interaction accent.
- Test browser screenshots were captured and inspected locally, including full mobile and tablet pages. These are **local review artifacts**, not deployed or source-of-truth customer files.

## Interactive smoke checks
Widths **320, 390, 768, 1440**:
- Mobile navigation toggle opened and closed at relevant sizes.
- Calculator fixture: $100,000 recovered at 30% gives $30,000 recovery fee and $70,000 customer remainder.
- Submitting an empty inquiry shows `Complete the required fields before continuing.`
- No horizontal overflow or page errors.

**Do not misinterpret the simulated test rate as a new contract offer or change business logic.** Existing commercial terms govern the public build.

## Outstanding gates
- Confirm approved logo derivatives including alpha matte, dark-mode white plate, favicon at 16px, printer grayscale; algorithmic alpha is not an approved source master.
- Independently verify Zoho DKIM record, real mailbox readiness, and external inbound/outbound tests; do not change site contact routes until proven.
- Brand/name and legal entity review before relying on RETALLY as a contracting entity.
- Cloudflare Pages preview deployment and full custom-domain DNS/canonical/redirect check are separate from this color-only page comparison (see PR #282).
- Run required exact-head GitHub Actions after any branch changes; human visual approval still required before production switch.

This document deliberately records observed passes and unresolved checks separately.
