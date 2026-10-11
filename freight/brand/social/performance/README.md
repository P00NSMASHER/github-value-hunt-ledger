# RETALLY — Read-only Social Publication & Evidence Review

This is an **offline review utility**, not a publisher, scheduler, Meta login bot, or automated lead counter. It consumes a **saved, pre-publication Metricool scheduled-post JSON snapshot** plus optional human-verified public post permalinks and manually mapped organic analytics. It writes a Markdown and/or JSON report only. No packages beyond Python's standard library are required (Python 3.11+, including zoneinfo data).

## Run

From this directory:

```bash
python -m unittest -v test_social_review.py
python social_review.py --schedule example_metricool_snapshot.json \
  --as-of "2026-10-11T15:00:00Z" --json-output report.json --output report.md
```

To review real RETALLY data instead of the **synthetic** example:

```bash
python social_review.py --schedule metricool-export.json \
  --receipts verified-publications.json --metrics measured-posts.json \
  --output review.md --json-output review.json
```

The `--schedule` file accepts Metricool's JSON `{"data":[...]}`, or its connector wrapper `{"text":"{\"data\":[...]}"}`. Retain stable `uuid` values; Metricool numeric post IDs change after edits.

**Freeze the original pre-publication schedule export for each campaign.** Metricool's `getScheduledPosts` returns scheduled posts rather than a full historical archive. Once published, a post can disappear from a new export. Use the *saved original* `--schedule` file when verifying that campaign later, and supplement it with actual public permalink receipts and dated metrics. A newer export is helpful for the remaining queue but cannot reconstruct vanished published posts. This offline tool never infers success from disappearance.

## Receipt contract: independent verification

Use **only** for a post you personally confirmed at a real public permalink. No permalink can be inferred from a Metricool PENDING status, image URL, or scheduled date. Example:

```json
{
  "verified_publications": [
    {
      "uuid": "FACEBOOK_POST_STABLE_UUID",
      "network": "facebook",
      "permalink": "https://www.facebook.com/Retally/posts/12345",
      "verified_at": "2026-10-12T09:15:00-04:00"
    }
  ]
}
```

The URL above is a **placeholder example, not a claimed real post**. The tool rejects unknown UUIDs, duplicate receipts, mismatched Facebook/Instagram domains, and verification timestamps in the future. A pending post that lacks a public receipt is marked `PUBLICATION_UNVERIFIED` after the intended posting time, **never “failed.”** An optional receipt supplied for an item still marked draft raises a review warning; it does not silently publish or rewrite the draft.

## Measurement contract: no invented numbers

Optional manual file:

```json
{
  "posts": [
    {
      "uuid": "FACEBOOK_POST_STABLE_UUID",
      "reach": 120,
      "impressions": 145,
      "reactions": 6,
      "comments": 2,
      "shares": 1,
      "clicks": 3
    }
  ]
}
```

Use **real, dated post-level organic metrics from the connected platform**. Map to stable UUIDs only after verifying the actual published permalink/caption. For Instagram use `reach`, `impressions` (if actually available), `likes`, `comments`, `shares`, `saves`. **Null and omitted metrics remain unknown, not zero.** The calculated interaction total is left unknown if any required component is absent. `reach` added across posts counts repeated viewers multiple times: it is **not unique audience**.

For content comparison, the script uses a conservative **descriptive** gate (at least four verified posts per platform, at least 100 combined per-post reach, complete interaction components). Passing it is not statistical significance and does not establish that creative, posting time, or algorithm caused any change. Don't optimize based on the October 9 introductory posts' extremely small early reach.

## Static quality-control checks

- Distinguishes active future posts, draft-only posts, verified public receipts, and posts requiring later verification.
- Displays actual **America/New_York** time from Metricool's `Europe/Madrid` local publishing time, including October/November DST differences.
- Warns if a non-draft post has automatic publishing disabled, an active post lacks images or alt text, a Facebook campaign caption lacks a RETALLY tagged destination, or Instagram lacks a bio-link CTA.
- Does not retrieve media, click profile CTAs, test UTM links, check source privacy, fetch engagement metrics, or submit inquiries. Those require separate evidence and human oversight.
- Ignores unrelated networks such as LinkedIn and YouTube when checking Facebook/Instagram; it does not edit those drafts.
- No background schedule, webhook, paid ads, social account write, login, private customer record, external dependency, or network permission is required.

## Release rule

Run an on-demand snapshot after the Oct 12 Facebook and Oct 13 Instagram posts have had time to appear. Use the actual public post URL and provider analytics to validate publication. Do not treat an automatic post schedule, link click, or an email **draft** generated by RETALLY's current form as a received qualified lead. Existing Meta/Metricool publishing setup remains the authoritative delivery mechanism, not this script.

Related: [November Field Notes](../NOVEMBER_FIELD_NOTES_2026.md), [community response guidance](../COMMUNITY_MANAGEMENT_PLAYBOOK.md), and [launch-readiness baseline](../LAUNCH_READINESS_2026-10-11.md).


## Metricool post analytics bridge — strict, offline reconciliation

The companion metricool_join.py reconciles real **post-level analytics rows** from the connected Metricool account against the original frozen scheduled-post baseline. It does not retrieve data over the network, post to social accounts, run in the background, submit inquiries or mark a post published based on a scheduler entry. A Metricool-reported permalink is a **candidate**, not independent proof.

The Metricool getAnalyticsDataByMetrics connector returns rows without column headers. Wrap the returned rows in JSON with a field_ids array in the **exact order requested** and an offset-aware observed_at timestamp. Missing, duplicated, reordered, or malformed fields are not guessed.

Request **Facebook** post-level fields in this order:

FBPO01, FBPO03, FBPO06, FBPO08, FBPO11, FBPO12, FBPO13, FBPO14, FBPO23

These are post date, caption, post link, comments, impressions, reach, reactions, shares, post clicks. General post clicks are **not** equivalent to outbound website clicks; track FBPO09 separately if it is truly needed and do not sum the two.

Request **Instagram** post-level fields in this order:

IGPO01, IGPO03, IGPO06, IGPO08, IGPO13, IGPO14, IGPO15, IGPO27

These are post date, caption, post permalink, comments, likes, organic reach, saves and shares. Do not substitute account reach or paid reach.

Example (deliberately synthetic; not a real post):

~~~json
{
  "field_ids": ["FBPO01","FBPO03","FBPO06","FBPO08","FBPO11","FBPO12","FBPO13","FBPO14","FBPO23"],
  "observed_at": "2026-10-14T15:00:00Z",
  "rows": [["20261012","SYNTHETIC EXAMPLE — not a real post","https://www.facebook.com/SYNTHETIC_EXAMPLE/posts/SYNTHETIC_FB_001","0.0","5.0","4.0","0.0","0.0","0.0"]]
}
~~~

Run this from the repository root with exported **real** data:

~~~bash
python3 freight/brand/social/performance/metricool_join.py \
  --schedule freight/brand/social/performance/baselines/retally-2026-10-11.json \
  --facebook-export /path/to/facebook-export.json \
  --instagram-export /path/to/instagram-export.json \
  --json-output /tmp/retally-candidates.json \
  --verified-metrics-output /tmp/retally-confirmed-only.json \
  --output /tmp/retally-candidates.md
~~~

Inspect each candidate on the real public Facebook or Instagram platform. Create a separate independent-publication receipt file using the existing social_review.py receipt schema, then rerun the bridge with --receipts /path/to/verified-publications.json. Only an exact match to an independent public permalink unlocks report-ready metrics in --verified-metrics-output. Without such independent receipts, the verified-metrics file has an empty posts list. Feed confirmed metrics into social_review.py --metrics together with the same receipts and frozen schedule.

Safety and quality rules: Match **unique**, exactly Unicode/whitespace-normalized captions on the same network and within ±1 day of the intended Eastern publication date; forbid malformed or lookalike/public-profile URLs; reject duplicate or ambiguous analytics rows; treat null as unknown, not zero; reject negative, fractional, missing and future-dated evidence. Ignore unrelated introductory posts not contained in the frozen October campaign instead of assigning their results to another post.

Test with the included fixture-facebook-metricool-SYNTHETIC.json and fixture-instagram-metricool-SYNTHETIC.json, both explicitly fictional. The existing repository workflow runs all performance tests and verifies that 2 synthetic provider matches yield **0 independently verified publications and 0 exportable verified metric rows**. No scheduled task or external credentials are added.


## October pre-publication queue-drift check (on demand; no automation)

Use **queue_preflight.py** to compare the immutable October 11 source-of-truth launch snapshot with a fresh, independently retrieved Metricool getScheduledPosts JSON export. It extends the existing social_review workflow and is not a parallel publication tracker. Source post IDs are matched by stable UUID, never Metricool's mutable numeric IDs.

From the repo root:

~~~bash
python3 freight/brand/social/performance/queue_preflight.py \
  --baseline freight/brand/social/performance/baselines/retally-2026-10-11.json \
  --current /path/to/fresh-metricool-planner.json \
  --as-of "2026-10-11T15:00:00Z" \
  --output /tmp/retally-queue-preflight.md \
  --json-output /tmp/retally-queue-preflight.json \
  --fail-on-risk
~~~

Save a fresh getScheduledPosts result covering **Oct 11–Nov 10** to the current input file. Export may be a plain JSON object with a data array or the connector JSON string inside text. **Do not silently substitute the October 11 baseline for the current export** when running a real prelaunch check. The PR-only unit workflow deliberately compares baseline to itself to verify the parser safely without accessing external accounts.

The comparison detects:
- **HIGH**: missing future active post, changed UTC publishing instant (including DST errors), disabled autopublish, draft made active, unapproved new live post, changed media, provider error, missing Facebook tracking link or changed format (for example, Reel).
- **WARN**: changed caption, altered or missing alternative text, missing Instagram bio-link instruction or a review draft absent from the latest upcoming feed.
- **INFO**: additional review-only drafts, nonerror provider state change or scheduled post disappearing after its due date.

**Important:** Disappearance after a post's due time is not evidence of successful publication or failure. This tool does not check live public-platform permalinks, diagnose a queued-post outage, or open website forms. Continue using social_review.py and metricool_join.py with independently observed publication links and post-level analytics for actual publication and performance. An all-clear preflight means only that the compared upcoming schedule contained no detected high-risk changes, not that Facebook or Instagram accepted the post.

The tool never makes network requests, changes schedule entries, updates Facebook/Instagram, reads customer records or creates recurring tasks. The --fail-on-risk flag exits with code 2 on HIGH-severity findings; without it the tool always emits a report for manual inspection. No tokens or account credentials are required. Preserve the source export date and compare before the first scheduled Oct 12 9 AM Eastern Facebook slot, then inspect actual publication on the live page.

The fresh getScheduledPosts result may include unrelated YouTube/LinkedIn items. Those are explicitly ignored by the Facebook/Instagram drift check. The two additional November Field Notes drafts beyond the frozen source should appear as informational additions, never permission to publish.
