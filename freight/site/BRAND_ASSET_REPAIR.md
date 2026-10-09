# RETALLY brand asset repair — October 8, 2026

The previous bitmap wordmark was **380 × 60 px**. The previous R emblem was **110 × 106 px** and visibly corrupted in the source. Neither was a suitable canonical brand master.

Canonical logos: `assets/brand/retally-wordmark.svg` and `assets/brand/retally-emblem.svg`; the `favicon.svg` app/browser icon uses the same R motif. All are standalone SVG paths without embedded bitmaps, fonts, remote dependencies, or scripts.

New public-facing HTML and manifest use vector assets. The corrupt emblem bitmap is excluded from the public build. The old wordmark WebP remains temporarily as a backward-compatible email signature fallback, since SVG images do not work uniformly in email clients. Build regression tests catch old references and embedded bitmap content.
