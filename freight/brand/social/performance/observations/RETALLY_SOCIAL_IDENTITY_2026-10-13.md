# RETALLY — Social account provenance and organic signal review
_Observed October 13, 2026; read-only connected-provider results. Not an assurance of delivered posts or customer inquiries._

## Cross-connector identity reconciliation

| Platform | Metricool RETALLY identity | Windsor.ai connection | Account-level reconciliation |
| --- | --- | --- | --- |
| Facebook | RETALLY Page | Same Page ID observed | MATCHED on exact account identity; cross-provider metrics must still be joined by the individual post with dated evidence |
| Instagram | RETALLY @retallyrecovery | Connected Instagram account bears a different name | **IDENTITY MISMATCH.** Do not use Windsor Instagram data as RETALLY performance |
| YouTube | RETALLY channel URL/channel ID | Connector exposes a separate generic account identifier, not matching the channel ID | **NOT VERIFIED.** Never assume the YouTube login/connector is the channel |
| LinkedIn | No confirmed connected company account in Metricool | No connected matching account observed | **NOT CONNECTED / RESTRICTED.** Keep LinkedIn content a draft |

Source: read-only Metricool brand 7322512 and Windsor connected-account listing, queried on Oct 13. The source account identities themselves are not credentials or proof of publishing.

## Observed provider-reported organic performance, not a creative experiment

Direct Metricool post-analytics rows requested for Oct 9–13 (timestamps reported by provider):

- **Facebook: 2 rows** dated October 9 and October 12. Reported post reach 2 + 1 = **3 summed post reach** (not unique audience); 11 + 2 = **13 total impressions**; **1 outbound post link click** reported across the two rows. A separate organic-reach field returned zeros and should **not** be silently substituted for the standard reach field; provider metric definitions and lag require investigation.
- **Instagram: 1 row** dated October 9. Reported **5 reach, 10 post views, zero likes/comments/saves**; shares was null/unknown and must not be recoded as zero.
- Provider-reported post URLs are **candidate permalinks**; the evidence join remains unverified without an independent live-public-post check. No confirmed inquiries, qualified prospects, or actual recoveries can be inferred.
- This sample is far below the existing decision threshold in social_review.py: **4 independently verified posts per platform, cumulative post reach 100 or more, and complete interaction components**. It is not defensible to declare any theme, artwork variant, or publishing time a winner.

## Oct 13 actions and next acceptance

1. **15 Facebook post CTAs updated** to the directly relevant educational pages (invoice audit, duplicate billing, accessorials, rates, evidence, privacy, pricing and second-look) while preserving existing UTM attribution, media, stable UUIDs, time, provider and automatic publishing. These are scheduled-post changes, not claims of published content.
2. Keep the organic calendar on the existing schedule. Do **not** add paid promotions, post automation, LinkedIn activations, audience scraping, automatic DMs, or subscriber imports.
3. Do not combine Windsor Instagram/YouTube analytics with RETALLY posts while identity remains mismatched or unverified. The new social_source_identity.py performs exact-match allowlisting from fresh connector exports; it does not contact providers.
4. Obtain independent, dated public Facebook and Instagram post permalinks and reconcile against exact-caption Metricool post rows using metricool_join.py and social_review.py. Missing posts are **unverified**, not proof of failure.
5. Social URLs and page routes are checked against current website source, but a repository file or search result does not certify present live HTTP availability. Before a campaign is promoted, verify live landing pages from a public browser.
6. A qualified lead requires a **received and reviewed** inquiry. A homepage form start, email draft, page view, link click, or pending Metricool post is not a lead.

No personal connected-account names, mailbox identifiers, tokens, customer data or raw private connector exports are stored in this note. Source results may change and must be refreshed before future inference.
