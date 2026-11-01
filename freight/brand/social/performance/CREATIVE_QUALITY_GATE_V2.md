# RETALLY social creative quality gate (read-only)

This gate audits an exported Metricool scheduled-post JSON: Facebook, Instagram, and YouTube, while recognizing restricted LinkedIn drafts. It never posts, pauses, edits, schedules, verifies publication, contacts customers, ingests invoices, or establishes a real recovery.

The existing social_review.py and queue_preflight.py separately handle verified public receipts and schedule drift. This additive checker evaluates:

- Canonical RETALLY HTTPS links, proper platform-specific UTM attribution, and matching public source-page routes. Reject links directly to the #start-audit route while customer intake remains unverified.
- Missing images/alternative text, suspicious media hosts, topic mismatches between leading text and the artwork description, unsupported recovery claims and unlabeled illustrative timestamps.
- Duplicate platform/time slots, bad timezones or nonexistent local times, provider error states, and automatic-publishing settings.
- Instagram save/share/profile CTA diversity, repeated art use, and YouTube video/title/audience requirements.

HIGH findings require review before release. WARN means desirable improvement; INFO is context. A zero-high result is not proof of a live website response, rendered artwork quality, carrier refund or social publication.

## Run

From the repository root:

    python3 -m unittest discover -s freight/brand/social/performance -p 'test_*.py'
    python3 freight/brand/social/performance/creative_quality_gate.py --schedule /path/to/metricool-current-export.json --json-output /tmp/creative-quality.json --fail-on-high

The export accepts a Metricool data array or a connector text wrapper. Keep unposted source snapshots private if they contain confidential or account-identity details. Never store customer freight documents, tokens or account credentials in the repository.

## Boundaries and provenance (October 13, 2026)

At review, the real RETALLY planner held 42 entries: 24 Facebook, 16 Instagram, one YouTube and one unactivated LinkedIn draft. All 41 active entries were set for automatic scheduling; provider PENDING is not independent proof of public delivery.

The immutable historical October 12 creative baseline still contains an old Facebook #start-audit deep link. The live planner's October 16 post was corrected to a source-backed educational route on October 13. Historical evidence is deliberately not rewritten. The existing read-only social-evidence workflow exercises this historical failure as a regression test.

The public site already preserves first-party UTM context on internal educational navigation in freight/site/site.js. A click is not a qualified lead, and no customer onboarding, legal registration, real settlement, or paid campaign is authorized here.

The existing .github/workflows/retally-social-evidence.yml has pull-request and manual triggers only: do not add a recurring run. Human review must still inspect actual rendered artwork at iPhone size and verify every link's live HTTP state separately; the gate only checks repository-backed paths and planner metadata.

## Current public campaign asset acceptance — October 13, 2026 (read-only)

A sanitized snapshot of the connected Metricool **40 active Facebook/Instagram entries** was saved as `observations/retally-public-target-inventory-2026-10-13.json` (no private captions, customer files, or credentials). The new preflight validates all the original source URLs before collapsing duplicate **HTTP route probes**: **24 individually tracked Facebook URLs** with distinct campaign/content combinations, **28 unique CDN artwork URLs**, **11 distinct educational landing page routes**. Route sampling never deduplicates attribution records.

**Observed GitHub-runner results on the exact PR head of October 13:**

- `RETALLY social evidence review` [Actions run 38422452709](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/38422452709): **134/134 unit tests passed** and the read-only campaign HTTP probe completed.
- **11/11 campaign landing pages** returned HTTP 200 with RETALLY HTML from the runner. **28/28 scheduled unique creative assets** returned valid image headers, decoded dimensions at acceptable feed resolution, and non-landscape orientation.
- A preceding read-only attempt [run 38421466854](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/38421466854) returned **8 pages at 200 and three 500 responses** for `/freight-recovery-evidence-standard`, `/privacy`, and `/second-look-freight-audit`. Repeated subsequent checks on **both the canonical domain and the owned Pages.dev host** returned HTTP 200 twice for all three routes. That supports a *transient network/edge observation*, not a proven code-level root cause. No social links were moved because the recheck succeeded; monitor rather than silently routing content elsewhere.
- Public GET checks used bounded body sizes, no redirects, no cookies, no authentication, no form submissions, and no external customer actions. Additional source tests cover bad UTM, missing alt text, URL allowlists, staged 500/429/timeout recovery, 404 hard failure, and bounded concurrent requests.
- Media HTTP success is **not visual/editorial approval** and cannot establish a published Facebook/Instagram permalink. Production live-route success is **not a conversion, prospect, sales or cash recovery event**. Publisher state and performance remain separate, independently verifiable evidence streams.

This is **PR/manual-only** QA, not a new recurring monitoring task. Retain the user-approved publishing schedule and the restricted LinkedIn draft. Maintain strict pre-launch commercial authorization boundaries.
