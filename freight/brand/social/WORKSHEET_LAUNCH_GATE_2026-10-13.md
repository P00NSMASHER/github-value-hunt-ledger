# RETALLY — Free invoice review worksheet / social distribution gate

**Status: DRAFT / NOT PUBLISHED.** October 13, 2026. No real customer records and no business-registration action.

## What the buyer gets

The existing canonical [freight invoice audit checklist](https://www.retallyrecovery.com/freight-invoice-audit-checklist) gains a practical printable in-browser worksheet. A buyer can enter **anonymous or sample totals** (invoiced amount, governing-rate expected total, related existing credits) and see the arithmetic unresolved **question**—never a carrier claim, verified refund or actual recovery. The page also contains 15 evidence checks, space for unresolved questions, a sample values button and clean print mode.

All input processing occurs in first-party browser JavaScript with no network, persistent storage, form submission, account creation, advertising identifiers or confidential-document request. Sharing copies **only the canonical public worksheet URL**, not amounts. No data from this widget can legitimately be counted as a lead. RETALLY's actual customer intake remains separately gated.

## Conversion purpose

Instead of asking an unfamiliar B2B audience to immediately hire a pre-launch freight recovery provider, offer a useful **evidence checklist** people can save, print, forward to finance/procurement and use to identify which questions require rate authority. This adds a practical outcome to previously purely educational content without claiming results.

## Source-controlled distribution pack

The JSON pack at `freight/brand/social/performance/retally-worksheet-social-drafts-20261013.json` contains **20 review-only posts**: 8 Facebook, 8 Instagram and 4 restricted LinkedIn company-page drafts, across eight distinct real buyer problems. Facebook and LinkedIn links are tagged and point to the single canonical worksheet section. Instagram copy contains no non-clickable URL; direct profile link must be reviewed before any release.

These are **not in Metricool**, do not occupy future slots, and do not edit or supplant the existing 41 auto-scheduled posts. All suggested graphics are briefs only; pending asset rights and genuine visual approval. Do not use the historical corrupted brand logo.

## Release acceptance

1. Existing freight public build/tests plus the new Python markup/bundle, Node arithmetic/DOM/privacy and social-pack tests must pass on exact PR head. Any unrelated CI failure must be identified honestly rather than labeled green.
2. Visually inspect the live 390px, tablet and desktop worksheet; confirm text and fields do not clip and no external media loads. Print-preview on Letter-sized black/white and confirm evidence checks are readable.
3. Verify that both Cloudflare production canonical and existing GitHub Pages fallback build expose the worksheet and first-party script without a CSP violation; no information is posted to `/api/inquiry` by worksheet interactions. Do not turn on dormant online intake.
4. Confirm the original user-approved brand master remains identical. Treat the illustrative example's $125 difference as a **question, not money recovered**; check credits against governing source.
5. Inspect each Facebook/LinkedIn UTM link and anchor after the site release, and review Instagram profile link navigation. Do not publish content for a page that hasn't been released.
6. Separately confirm social media account identity and access before ever activating LinkedIn. A draft is not permission to publish.
7. Do not count a shared link, page view, print button, copied URL or local arithmetic interaction as a qualified lead. Qualified lead means a real received and reviewed business inquiry.

**No new recurring task, paid spending, private invoice upload, customer outreach or registration was created by this PR.**