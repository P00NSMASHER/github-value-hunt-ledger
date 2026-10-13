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
