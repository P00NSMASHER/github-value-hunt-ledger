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

Related: [November Field Notes](../NOVEMBER_FIELD_NOTES_2026.md) (separate PR pending), [community response guidance](../COMMUNITY_MANAGEMENT_PLAYBOOK.md), and [launch-readiness baseline](../LAUNCH_READINESS_2026-10-11.md).
