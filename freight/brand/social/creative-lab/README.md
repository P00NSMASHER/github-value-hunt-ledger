# RETALLY Creative Studio v2 — premium social graphics, review-only

**Status: draft R&D under PR #399.** This studio renders locally only. It never
posts to Facebook, Instagram, LinkedIn, YouTube or Metricool, never changes an
existing schedule, and does not record customer freight data. Output is not
approved for publication without actual human review.

## Actual improvement

The October 11 visual audit of three RETALLY Metricool artworks identified a
recurring all-text structure: headlines were readable, but freight subject
matter, document comparison, foreground depth and action-oriented information
were weak. This version produces three separate **1080 × 1350** layouts with:

- Actual approved RETALLY wordmark (raw master SHA-256 enforced), never AI-
  reconstructed or retired WebP logo derivatives.
- Controlled subject photography, photographic depth, gloss, restrained emerald
  lighting, beveled 3D-style cards, and bigger mobile-first headline hierarchy.
- Illustrative freight evidence with differentiated layouts:
  `rate_versions` (two rate schedules), `accessorial_proof` (liftgate evidence),
  `credit_chain` (original bill → credit memo → replacement).
- **390 × 488** iPhone-feed review images and automatic non-clipping / image-
  fidelity / network-free / source-integrity gates.
- A fail-closed manifest carrying SHA-256 of the original logo, input photo,
  all exported PNGs and phone previews, plus release status.

Illustrative graphics **never imply** a charge is wrong, a carrier owes money,
RETALLY has processed a real customer case, or money has been recovered. The
product offer must be explained accurately in a separate human-approved caption.

## Research references and reuse decision

| Repository | License | Use in this version |
| --- | --- | --- |
| [Open Carrusel](https://github.com/Hainrixz/open-carrusel) | MIT | Reusable carousel UI concept reviewed; no copied source |
| [Social Carousel Generator](https://github.com/idrsdev/social-carousel-generator) | MIT | Brand/token workflow reviewed; no copied source |
| [Playwright](https://github.com/microsoft/playwright) | Apache-2.0 | **Actual rendering dependency**, with pinned Python version in CI |
| [Takumi](https://github.com/kane50613/takumi) | MIT/Apache-2.0 | Potential batch-render substitute only; not installed |
| [Sharp](https://github.com/lovell/sharp) | Apache-2.0 | Potential optimized media outputs; not installed |
| [Lucide](https://github.com/lucide-icons/lucide) | ISC | Potential future icon set; none copied |

No whole-app migrations or copyleft code are required.

## Exact asset rules

- Wordmark: `freight/site/assets/brand/retally-wordmark-approved.png`, exact
  SHA-256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`
  and native geometry 1619×257. `validate_logo()` runs in **both** preview and
  production mode. This source is never rewritten, vectorized, upscaled or
  cropped in place; the page embeds its bytes for display.
- Approved emblem checksum `bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043`
  is registered for future uses but not yet rendered.
- Production photo is the existing repository image
  `freight/site/assets/images/terminal-blue-hour.webp`. This existing website
  image **still needs separate usage-rights / target-crop review for social**;
  website presence does not prove broad commercial licensing.
- Preview images may use explicitly provided locally owned/generative photo
  research, but are watermarked **NOT APPROVED FOR PUBLICATION** and are never
  promoted to released status by the renderer.
- Generated demo photo art was not committed to GitHub and was not passed off
  as an actual carrier, truck operator, customer, invoice or case result.

## Local use

From the repository root on a Python 3.11+ environment with Chromium:

```bash
python -m pip install playwright==1.57.0
python -m playwright install chromium
python -m unittest discover -s freight/brand/social/creative-lab -p 'test_*.py' -v
python freight/brand/social/creative-lab/render_social.py \
    --repo-root . --mode production --concept all \
    --output-dir /tmp/retally-studio-review
```

Preview mode requires the original verified logo **and** an explicit local photo:

```bash
python freight/brand/social/creative-lab/render_social.py \
    --repo-root . --mode preview --concept all \
    --photo /path/to/nonproduction-concept-photo.png \
    --output-dir /tmp/retally-preview
```

The `--logo` flag exists for checking an alternate local *copy of the original
master* in preview mode; its SHA-256 must still match exactly. Production mode
rejects all user-supplied photo/brand overrides. `--chromium /usr/bin/chromium`
selects a system Chromium if Playwright's bundled browser isn't available.

The `all` setting renders all three cards. The previous `both` setting remains
accepted for command-line compatibility and currently resolves to all three.

## Automated QA contract

- 1080×1350 PNG plus 390×488 scaled feed screenshot **for each** concept.
- Browser check: wordmark natural dimensions, text/document bounding boxes,
  headline/pill visible above the overlay, no card horizontal overflow.
- Image files: signature and exact output dimensions. Each SHA-256 recorded.
- HTML: data-only source imagery; no scripts, forms, remote CSS, fonts,
  analytics, trackers or HTTP requests. Runtime observes network requests.
- Brand: non-exact master SHA fails **before** creating an output folder.
- Claims: no fabricated savings, sample results, testimonials or implied actual
  recoveries. Required visible `ILLUSTRATIVE ONLY` and `NO CUSTOMER DATA` labels.
- CI path-limited pull-request workflow runs the tests and renders review-only
  assets from canonical repository assets. The artifacts are **not releases**.

## Human release acceptance still required

1. Open all three 1080px originals and all three 390px previews. Examine body
   copy legibility, photo crop, logo matte, headline spacing and mobile visual
   hierarchy. Machine clipping checks are necessary but not sufficient.
2. Confirm website photo has appropriate permission for social publication;
   review original image license and absence of real customer/driver data.
3. Review exact freight wording: whether rate authority, bill/correction and
   any applicable credits are adequately distinguished. Add platform-specific
   alt text and copy only after subject-matter review.
4. Check new captions and any links in an isolated draft. Do not replace the
   **13 protected October posts** or activate the **four November drafts**.
5. Obtain specific approval for a creative and a publication operation. No
   renderer command is authorization to post, merge PR #399 or spend money.

## Deliverable boundaries

This is a graphics engine prototype with real local tests and draft PR code, not
a claim that production content has been published, that the October calendar
has been modified, that an image license has been fully cleared, or that any
conversion metric has changed.

---

## Field Notes v3: six differentiated new social graphics (October 13)

The studio now prepares **nine topic-specific 1080×1350 images and 390px phone-size previews**: three prior v2 concepts plus six v3 additions. The new six use separately registered website hero photographs, not one repeated truck image.

| New visual topic | Original onsite hero image | Matching educational page |
| --- | --- | --- |
| Audit scope and previous credits | freight-network.webp | /freight-invoice-audit-checklist |
| Fuel surcharge rate authority | rate-authority.webp | /carrier-rate-audit |
| Detention timestamp example | warehouse-handoff.webp | /accessorial-charge-audit |
| Proof package before disputes | invoice-evidence.webp | /freight-overcharge-dispute-process |
| Approved claim versus usable credit | approved-path.webp | /freight-recovery-evidence-standard |
| Invoice/data handling safety | dock-control.webp | /privacy |

Command from repository root:

    python freight/brand/social/creative-lab/render_social_v3.py --repo-root . --mode production --concept all --output-dir /tmp/retally-fieldnotes-v3-review

Here *production* selects canonical image inputs, not permission to publish. Output manifests mark every item as an unapproved draft. The approved original RETALLY wordmark must pass exact SHA-256 validation before any rendering. Every photo filename and checksum is recorded separately; public website inclusion is NOT proof of broader social reuse rights.

The companion v3_draft_captions.json holds 12 distinct platform captions (six Facebook, six Instagram), source-backed educational links, unique Facebook UTM content codes, and usable alt text. They are content proposals, NOT an additional active publishing queue. The illustrative detention example is labelled NOT A CUSTOMER RESULT.

The existing pull-request/manual-only creative CI now renders and checks all nine topics, including full-size export geometry, 390px phone screenshots, no network/scripts, document overflow, claims/disclosures and prohibited approval states. Human visual acceptance and rights verification remain release blockers. No customer data, scheduled ChatGPT tasks, paid campaigns or social account operations are involved.

---

## V4 large-type swipe carousels — quality-first expansion

The earlier six v3 cards were technically valid but packed three pieces of evidence into a single feed image. On an actual 390px phone preview, the headlines remained readable while small evidence labels competed for space.

V4 adds **six 4-slide educational carousels (24 originals and 24 phone screenshots)** using the same six verified-source topics. Each is a distinct sequence: **1. Topic hook, 2. Three evidence checks, 3. Evidence-versus-assumption decision, 4. Specific takeaway + educational reading link**. Each evidence check has its own large horizontal panel; swipe slides reserve much more room for type than the earlier three-column card layout.

- Render locally: `python freight/brand/social/creative-lab/render_carousels_v4.py --repo-root . --output-dir /tmp/retally-v4-carousels --concept all`.
- Output: six independent sets of slide1–slide4 PNGs at 1080×1350, plus matching 390×488 screen-size previews. `manifest-v4.json` includes per-slide checksums, exact wordmark checksum, unique source-photo identity, descriptive slide-specific alt text, topic-aligned educational page and explicit publication holds.
- Authentic RETALLY wordmark is enforced at its original SHA/geometry. Each topic reuses its distinct, registered site photography without modifying image bytes. **Social-use licensing still requires clearance**.
- Visual gates prohibit overflow, clipped panels, hidden hero text, scripts, remote calls, ordinary forms and markup injection. No trust in a rendered PNG alone: exact screenshots need human source/art review.
- Cover slide and finale use a full-bleed editorial photo, while steps use oversized numbered evidence rows and the comparison slide uses two stacked decision panels. The illustrative detention scenario is visibly labelled, and no hypothetical figure is represented as a real refund.
- `v3_draft_captions.json` remains an unposted reference for the same six topics, with exactly corresponding Facebook and Instagram copy. Captions, alternative text and the final educational page require final pre-publication review.
- No Metricool entries were created, edited, moved or published by this renderer. Existing 41 active automatic posts and the LinkedIn restricted draft remain as-is. No paid activity, customer outreach, real invoices, purchases, business registration or recurring tasks.

## Phone-first single-panel alternative (v4, October 13)

The previous six v3 covers were recognizably branded but **too dense in 390px feed previews**: three narrow document columns displayed low-priority labels at approximately 6px and made the evidence workflow harder to read.

The additive v4 design preserves all six v3 themes, original approved logo bytes, six registered hero photos, claim disclaimers and caption proposals but changes the evidence section to **three horizontally full-width numbered rows**. Only the essential record/category and next verification step appear on each row. Small status/label scaffolding is removed from the artwork rather than squeezed smaller. The full evidence explanation stays in the platform caption.

- Card headings have a 40px minimum at 1080px source size (about **14.4px in a 390px feed**); row actions have a 28px minimum (about **10.1px in a 390px feed**). Document-row alignment, visible text, non-overflow, headline and illustrative-label size are checked in the browser before screenshot export.
- Every v4 graphic has its own 1080×1350 original and 390×488 iPhone review preview. If any text clips, a card fails its size threshold, or a row overlaps, the render **fails**, rather than silently producing a publishable-looking image.
- Keep the original v3 files and the 24 carousel slides intact for visual comparison. The v4 single panels are supplementary cover/reference candidates, **not replacements to scheduled social posts**.
- All release holds remain: photo rights and human visual review, wording, platform-specific alt descriptions, branded social preview, independently confirmed posting eligibility, and strict pre-registration/customer-data authorization.

Run from repository root:

    python freight/brand/social/creative-lab/render_social_v4.py --repo-root . --mode production --concept all --output-dir /tmp/retally-v4-phonefirst

Here `production` selects registered source graphics; it is **not** a publication, approval, launch, or deployment command.
