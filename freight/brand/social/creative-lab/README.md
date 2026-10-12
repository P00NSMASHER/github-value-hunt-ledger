# RETALLY Visual Studio — Offline Graphics Prototype

**Status:** Design R&D. Not uploaded to Metricool, not scheduled, not publicly released. Two portrait concepts, 1080 × 1350 PNG.

## Goal
Replace repeated text-only cards with subject-specific editorial art: a rate-sheet comparison and a fee-versus-proof evidence chain layered over existing authorized freight photography. Export still-image posts locally and make every item explicitly subject to human creative/brand review.

## Code/research origins
Independent prototype informed by, rather than copied from, these open-source tools:
- [Open Carrusel](https://github.com/Hainrixz/open-carrusel) — MIT; HTML/CSS-to-PNG workflow, drag-to-reorder editorial inspiration. Small project, not a production dependency.
- [Social Carousel Generator](https://github.com/idrsdev/social-carousel-generator) — MIT; 4:5 brand-token and template grammar. Small project, not a production dependency.
- [Playwright](https://github.com/microsoft/playwright) — Apache-2.0; exact Chromium screenshots (the only Python dependency here).
- [Takumi](https://github.com/kane50613/takumi) — MIT/Apache-2.0; future faster batch rendering alternative; browser fidelity chosen for initial test.
- [Sharp](https://github.com/lovell/sharp) — Apache-2.0; future optimization pipeline; intentionally not needed for v0.
- [Lucide](https://github.com/lucide-icons/lucide) — ISC; potential future consistent SVG icons; no copied icons in this prototype.

## Source/approval rules
- `--mode production` checks the original approved wordmark source **SHA-256** and dimensions and reads the photo already committed under the freight site. It does not alter/transform the logo source. Embedding the logo intact for display is not a substitute for human review of the final card or its matte.
- Approved wordmark: `freight/site/assets/brand/retally-wordmark-approved.png` (1619×257, SHA256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`). Never substitute retired WebP derivatives.
- Existing website freight photo: `freight/site/assets/images/terminal-blue-hour.webp`. Confirm original photography rights and intended crop during acceptance review; existing website use is not necessarily a new social license.
- `--mode preview` permits explicitly passed local images **only** for design exploration. Every preview gets a permanent visible "not approved" banner and manifest `preview_only=true`. Preview outputs are not release candidates.
- All document graphics are expressly illustrative; no invented savings, real customer data, carrier identifier, or claim of actual recovery. Exact legal/operational wording remains reviewable.
- The script never contacts Meta, Metricool, marketing APIs, or customer records. Existing October live schedule and November drafts remain unchanged.

## Usage
Run from the existing `P00NSMASHER/github-value-hunt-ledger` checkout. Install `playwright` via your environment's Python package manager, then `python -m playwright install chromium` if required.

```bash
python freight/brand/social/creative-lab/render_social.py \
  --repo-root . --mode production --concept both \
  --output-dir /tmp/retally-social-review
```

Local preview with separately supplied approved/reviewed sample assets:

```bash
python render_social.py --mode preview --concept both \
  --logo /path/to/reviewed-local-wordmark.png --photo /path/to/licensed-photo.png \
  --output-dir /tmp/retally-creative-preview
```

To use a system Chromium executable (e.g. `/usr/bin/chromium`) append `--chromium /usr/bin/chromium`.

## QA and next steps
1. Review full 1080×1350 artworks and at 390px phone width (title, document labels, footer).
2. Run headless export on CI using the true repo assets and verify master source checksum, PNG dimensions, generated asset hashes, no overflow, and visible logo.
3. Add more art directions (full-bleed photography, annotated document, checklist infographic), and use source-linked, human-approved captions.
4. Package as an **offline export-only** production capability only after original photo rights, logo matte/crop, accessibility, and human approval pass. This is not a replacement publisher.

## License
New RETALLY prototype code written specifically for this project. It copies no third-party source code or fonts. Playwright is an external Apache-2.0 dependency. Follow RETALLY's repository licensing and dependency review process before merging.