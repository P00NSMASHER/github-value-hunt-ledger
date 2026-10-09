# RETALLY original-logo asset recovery — 2026-10-08

## Verified publication defect
The website's PR #276 shipped a **380×60** WebP wordmark and a **110×106** WebP R emblem. The latter already contained visible pixel corruption. The approved source artworks had never been correctly brought through to the public site.

## Exact approved originals now committed without re-encoding
- `assets/brand/retally-wordmark-approved.png`: 1619×257 px; SHA-256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`.
- `assets/brand/retally-emblem-approved.png`: 805×776 px; SHA-256 `bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043`.

Both exact masters came from the `RETALLY_Mission2D_Approved_Master_Transfer.zip` archive; the matching GitHub blobs were reused from branch `mission2b/customer-collateral-financial-proof-v1` without pixel modification.

## Publication boundaries
Public HTML, organization schema and email signature references point at the exact approved source PNGs. The corrupted emblem WebP and rejected candidate/redrawn SVG artwork are excluded from the public allowlist; the old wordmark WebP remains temporarily only to avoid breaking previously sent email signatures. No redesign, typeface substitution, or alpha matte has been approved here.

Browser tab icon uses the exact original emblem PNG. **A square mobile app icon is not claimed approved**: the brand standards require a separate human acceptance pass for a padded/cropped favicon variant.

Regression tests check full-file SHA-256, native pixel dimensions, page/manifest references and absence of the retired sources. GitHub Actions retain fail-closed source and publication checks with allowed-set-derived counts.
