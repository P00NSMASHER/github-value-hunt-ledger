# RETALLY public image integrity gate — 2026-10-09

## Why the earlier logo defect escaped

The original production release used a **380×60 WebP wordmark** and a visibly
corrupted **110×106 WebP emblem**. The file copies were syntactically present
and builds passed, but source pixel identity, minimum usable dimensions and
individual graphic appearance were not release acceptance criteria.

The approved original wordmark (**1619×257**) and emblem (**805×776**) are
now locked by SHA-256 to the corporate asset register. The former emblem
WebP is not part of the public allowlist. The retired wordmark WebP remains
a deliberate compatibility exception for previously distributed mail links.

## Fail-closed protection

`asset_integrity.py` now checks, without new dependencies:

- All 11 registered freight imagery masters and their 800-pixel responsive
  derivatives: RIFF/WebP structure, dimensions, byte-size floors, source
  registration and consistent aspect ratio.
- All five RecoveryOS marketing images at Cloudflare publication time.
- Both approved PNG logo masters, verifying exact bytes and dimensions.

The freight build **fails before writing a public bundle** if media quality
contracts fail, including when Cloudflare builds directly without GitHub CI.

`test_asset_integrity.py` deliberately demonstrates that a 110×106
image, truncated RIFF payload and one-bit alteration of an approved
emblem are rejected.

These tests cannot prove subjective graphic fidelity or rule out corruption
inside a valid high-resolution raster. Continue independent visual review
at real mobile/desktop dimensions, and never interpret a passing RIFF check
as permission to skip screenshot and human source-art inspections.

## Separate production security improvement

During the independent audit, the Cloudflare zone minimum TLS was raised
from 1.0 to **1.2**; Always Use HTTPS was enabled; a short staged HSTS
header (max-age=86400, no subdomain inclusion, no preload) was enabled; and
X-Content-Type-Options is now `nosniff`. HTTPS and redirects were verified
read-only on `www`, apex, RecoveryOS and approved image URLs. Cloudflare
zone controls are managed outside this repository: review them directly
before increasing HSTS lifetime. Do not upgrade HSTS to preload without
verifying all subdomains and a rollback plan.

Customer inquiry acceptance still correctly fails closed (GET /api/inquiry
returns 503) pending separate verified mail delivery. Do not bypass.
