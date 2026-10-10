# RETALLY Research Lab — Mission 5 Source Change Radar

**Status:** research-only, review-stage source change analysis on the existing Lab 14 chain. PR 366 is stacked on draft PRs 365, 364, 363 and the original 14-lab Phase 4 research chain. No new lab, recurring task, external notification, production API or customer/financial capability.

## Why it exists

A frozen source excerpt may be correct when written but misleading after a carrier tariff changes, a competitor adjusts its offer, a classification supplement takes effect, or a source goes offline. Earlier missions built dated source and claim registries, an evidence-fidelity gate and six falsifiable oppositional decisions. Mission 5 adds the missing **time/change dimension**.

It separates five questions:

1. Was a source deliberately captured on an approved list?
2. Did the visible preview change between two supplied captures?
3. Did the raw body hash change without an altered visible preview?
4. Which observations and strategic decisions depend on that source?
5. Which checks must a human perform before making any new conclusion?

A checksum can establish **internal consistency of a submitted receipt**. It cannot prove the original HTTP transaction occurred, authenticate the publisher, independently verify a raw body that was not retained, or establish a legal or contractual conclusion. This is stated in every machine report.

## Components

- freight/research_change_impact.py: offline receipt validation, deterministic snapshot comparison, dependent-claim/decision mapping, source review backlog, HTML and JSON reports.
- freight/test_research_change_impact.py: mocked captures; invalid URL, fake approvals, tampering, reversal of time, source failures, visible/drift distinction, expired sources, escaped HTML.
- Existing freight/lab_phase4_director.py: the existing Lab 14 includes the freshness queue and enforces no unattended source activity.
- Existing freight/lab_phase4_control_center.py: produces a Source Change Radar link plus an offline current-date refresh queue.
- Existing .github/workflows/retally-research-intelligence.yml: read-only CI, mocks only, and offline artifact upload.

No source URLs, legal facts or competitor rankings were automatically changed by this work.

## Using the workbench without network activity

Run from repository root, Python 3.11 or later:

    PYTHONPATH=. python -m pytest -q freight/test_research_change_impact.py
    PYTHONPATH=. python -m freight.research_change_impact --as-of-date 2026-10-10 --out /tmp/retally-source-radar
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-phase4

Offline refresh-only outputs:

- research_refresh_queue.json: prioritized source review debt, expiry days, linked claims and decisions.
- research_refresh.html: mobile-friendly internal static report.

These are queues, not externally checked facts or executed source-capture runs.

## Compare two manually authorized capture receipts

The existing Mission 3 collector can be invoked **only with its explicit execute flag**, and only on a small approved public-source list. Capture source IDs must match the manifest. The collector returns short previews, original-body digests and candidate-only receipt records. It does not save full copyrighted pages.

Example comparison after two separately obtained receipts exist:

    PYTHONPATH=. python -m freight.research_change_impact \
      --before /path/to/older-candidate.json \
      --after /path/to/newer-candidate.json \
      --as-of-date 2026-10-10 \
      --out /tmp/retally-comparison

Output adds research_source_changes.json and a comparison section to research_refresh.html. No source is fetched by this command.

**Do not label a test fixture as a live capture.** CI injects synthetic response bytes through the test transport, and the hashes cannot independently authenticate the purported source.

## Distinguish statuses precisely

- NOT_CHECKED_THIS_RUN: newer receipt intentionally omitted that approved source. This does **not** mean the page is down.
- SOURCE_FETCH_FAILED_REVIEW: newer collector explicitly returned an error. This does **not** mean prior facts have been disproven.
- BASELINE_CAPTURE_UNREVIEWED: a first successful capture without a comparable earlier run. No source claim is verified.
- SOURCE_REAPPEARED_UNREVIEWED: prior fetch failed, latest was successful.
- RAW_BODY_UNCHANGED: detached receipts contain the same original-body checksum. No content verification follows.
- RAW_CHANGED_PREVIEW_UNCHANGED: body hash differs, but the bounded visible preview did not. Full context still needs review.
- VISIBLE_PREVIEW_CHANGED: limited visible excerpt differs. This is a review flag, not a factual correction.
- EXPIRED_SOURCE_HOLD: source expiration date is past as-of. A new detached capture does **not** renew the authority of the older research claim without review.

Selected source IDs must be manifest-approved, source URL/publisher/lane preserved, timestamps strictly ordered for comparable captures, original excerpts bounded, MIME supported, digest structure intact, failed responses clearly separated, and all claimed verification/authorization flags false.

## Prioritization

The review queue ranks each existing source using:
- its highest dependent claim importance (internal ordinal level 1 to 5),
- number of impacted research decisions,
- additional attention for primary carrier/regulatory sources,
- overdue/near-expiry urgency.

The resulting points are **internal ordering only**. They are neither a probability of a true billing error nor estimated recovery dollars, customer demand, quality scores or revenue.

## Regulatory and customer controls

The NMFTA bulletin on October 9, 2026 did not itself cause the future December 12, 2026 supplement to become effective. A changed version of any carrier tariff must be evaluated against the actual shipment date and the customer's controlling agreement. Historical published federal text and search-index snippets remain specifically qualified until legally reviewed.

This workflow does not contact carriers, buyers, competitors or regulators. It does not read real freight invoices, process payments, create claims, update production, send notifications, change schedules, merge code, sign a contract, or promote external source content into verified RETALLY marketing claims.

Before engaging customers or filing claims, RETALLY's existing buyer-authorization, legal, confidential intake, source-authority and independent cash-reconciliation release controls remain applicable.

## Further opportunity

After manual source reviews demonstrate useful accuracy, an approved public-source provider could create fresh one-shot receipts (without unsupervised claim promotion). To justify recurring monitoring, RETALLY would first need a reviewed cost, reliability, terms-of-use, permission and alert-noise analysis. None is authorized by this mission.
