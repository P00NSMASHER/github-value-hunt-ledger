"""Adversarial local-only cross-provider Facebook evidence tests."""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from cross_provider_facebook import FB_FIELDS, reconcile

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
PAGE = "1423089780881432"
POST = "122095091163515568"
ID = PAGE + "_" + POST
CAPTION = "Illustrative invoice verification, not a refund.\n\n#FreightAudit"
M_URL = "https://facebook.com/122093247825515568/posts/" + POST
W_URL = "https://www.facebook.com/122093203395515568/posts/" + POST
METRIC = {
    "FBPO01": "20261012", "FBPO03": CAPTION,
    "FBPO04": ID, "FBPO06": M_URL,
    "FBPO08": "0", "FBPO09": "1", "FBPO11": "2",
    "FBPO12": "1", "FBPO13": "0", "FBPO14": "0",
}
WINDSOR = {
    "account_id": PAGE,
    "date": "2026-10-12",
    "post_id": ID,
    "post_message": CAPTION,
    "permalink_url": W_URL,
    "is_published": "True",
    "post_comments_total": 0,
    "post_clicks_by_type_link_clicks": 1,
    "post_impressions": 2,
    "post_impressions_unique": 1,
    "post_reactions_total": 0,
    "post_activity_by_action_type_share": 0,
}


def brand(**kwargs):
    networks = {"facebookData": PAGE, "instagramData": "retallyrecovery",
                "youtubeData": "UCnS99gTJFScnA2gy4wKU_JQ"}
    networks.update(kwargs)
    return {"data": [{"id": 7322512, "label": "Retally", "networksData": networks}]}


def connections(ids=(PAGE,)):
    return {"result": [
        {"id": "facebook_organic",
         "accounts": [{"id": ident, "name": "Page"} for ident in ids]},
        {"id": "instagram",
         "accounts": [{"id": "17841450188230798", "name": "unrelated_personal_handle"}]},
    ]}


def m_export(**updates):
    row = {**METRIC, **updates}
    return {"field_ids": list(FB_FIELDS), "observed_at": "2026-10-13T14:00:00Z",
            "rows": [[row.get(f) for f in FB_FIELDS]]}


def w_export(**updates):
    return {"observed_at": "2026-10-13T14:00:00Z",
            "result": [{**WINDSOR, **updates}]}


class CrossProviderEvidenceTest(unittest.TestCase):
    def report(self, metricool=None, windsor=None, ids=(PAGE,), brand_data=None):
        return reconcile(brand() if brand_data is None else brand_data,
                         connections(ids), m_export() if metricool is None else metricool,
                         w_export() if windsor is None else windsor,
                         as_of=NOW)

    def test_exact_match_never_public_visibility_proof(self):
        r = self.report()
        self.assertEqual(r["matched_provider_post_candidates"], 1)
        post = r["candidates"][0]
        self.assertEqual(post["state"], "CROSS_PROVIDER_REPORTED_PUBLISHED")
        self.assertTrue(post["page_alias_paths_differ"])
        self.assertEqual(post["post_id_suffix"], POST)
        self.assertTrue(post["same_underlying_post_id"])
        self.assertFalse(post["independently_visible_to_public"])
        self.assertFalse(post["verified_customer_lead"])
        self.assertEqual(r["independently_verified_public_posts"], 0)
        self.assertTrue(r["not_verified"])
        self.assertEqual(post["counter_disagreements"], [])

    def test_caption_unicode_whitespace_normalization(self):
        r = self.report(windsor=w_export(post_message="Illustrative invoice verification, not a refund.  #FreightAudit"))
        self.assertEqual(r["matched_provider_post_candidates"], 1)

    def test_wrong_account_blocks_every_join(self):
        r = self.report(ids=("999999999999",))
        self.assertEqual(r["state"], "ACCOUNT_IDENTITY_BLOCKED")
        self.assertEqual(r["checked_posts"], 0)

    def test_missing_fb_account_blocks_every_join(self):
        r = self.report(ids=())
        self.assertEqual(r["state"], "ACCOUNT_IDENTITY_BLOCKED")

    def test_unrelated_page_rows_ignored(self):
        x = w_export()
        x["result"].append({**WINDSOR, "account_id": "9876543210",
                            "post_id": "9876543210_" + POST,
                            "post_message": "Not RETALLY and must be ignored"})
        r = self.report(windsor=x)
        self.assertEqual(r["ignored_unrelated_page_rows"], 1)
        self.assertEqual(r["matched_provider_post_candidates"], 1)
        self.assertNotIn("9876543210", str(r))

    def test_same_post_id_different_caption_rejected(self):
        r = self.report(windsor=w_export(post_message="A different piece of content"))
        self.assertEqual(r["matched_provider_post_candidates"], 0)
        self.assertIn("POST_CAPTION_MISMATCH", [x["reason"] for x in r["skipped"]])

    def test_stale_or_wrong_date_rejected(self):
        r = self.report(windsor=w_export(date="2026-10-09"))
        self.assertIn("POST_DATE_DISAGREEMENT", [x["reason"] for x in r["skipped"]])

    def test_missing_companion_record_does_not_mean_unpublished(self):
        r = self.report(windsor={"observed_at": "2026-10-13T14:00:00Z", "result": []})
        self.assertEqual(r["matched_provider_post_candidates"], 0)
        self.assertIn("NO_MATCHING_SECOND_PROVIDER", [x["reason"] for x in r["skipped"]])

    def test_provider_says_false_not_published(self):
        r = self.report(windsor=w_export(is_published="False"))
        self.assertEqual(r["candidates"][0]["state"], "WINDSOR_REPORTS_NOT_PUBLISHED")
        self.assertTrue(r["not_verified"])

    def test_provider_published_flag_unknown_fails_closed(self):
        r = self.report(windsor=w_export(is_published=None))
        self.assertEqual(r["candidates"][0]["state"], "PUBLISH_STATE_UNKNOWN")

    def test_cross_provider_counter_lag_review_not_fabricated_truth(self):
        r = self.report(windsor=w_export(post_impressions=17))
        comparison = r["candidates"][0]["counter_comparison"]["post_impressions"]
        self.assertEqual(comparison["metricool"], 2)
        self.assertEqual(comparison["windsor"], 17)
        self.assertEqual(comparison["state"], "RECHECK_PROVIDER_LAG_OR_DEFINITION")

    def test_missing_counter_is_unknown(self):
        r = self.report(windsor=w_export(post_impressions=None))
        self.assertEqual(r["candidates"][0]["counter_comparison"]["post_impressions"]["state"],
                         "NOT_COMPARABLE")

    def test_invalid_count_rejected_not_coerced(self):
        r = self.report(windsor=w_export(post_impressions="-1"))
        self.assertIn("INVALID_COUNTER", [x["reason"] for x in r["skipped"]])
        self.assertFalse(r["candidates"])

    def test_wrong_link_post_id_rejected(self):
        wrong = "https://facebook.com/100/posts/122099999999999999"
        r = self.report(windsor=w_export(permalink_url=wrong))
        self.assertIn("INVALID_POST_PERMALINK", [x["reason"] for x in r["skipped"]])
        self.assertFalse(r["candidates"])

    def test_forged_external_link_rejected(self):
        r = self.report(windsor=w_export(permalink_url=W_URL.replace("www.facebook.com", "facebook.com.evil.test")))
        self.assertIn("INVALID_POST_PERMALINK", [x["reason"] for x in r["skipped"]])

    def test_metricool_other_account_rejected(self):
        r = self.report(metricool=m_export(FBPO04="111111111_" + POST))
        self.assertIn("ACCOUNT_OR_POST_ID_MISMATCH", [x["reason"] for x in r["skipped"]])
        self.assertFalse(r["candidates"])

    def test_duplicate_metricool_id_fails_closed(self):
        x = m_export()
        x["rows"].append(copy.deepcopy(x["rows"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate Metricool"):
            self.report(metricool=x)

    def test_duplicate_windsor_id_fails_closed(self):
        x = w_export()
        x["result"].append(copy.deepcopy(x["result"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate Windsor"):
            self.report(windsor=x)

    def test_metricool_missing_field_fails_closed(self):
        x = m_export()
        x["field_ids"] = x["field_ids"][:-1]
        with self.assertRaises(ValueError):
            self.report(metricool=x)

    def test_future_observation_rejected(self):
        x = w_export()
        x["observed_at"] = "2026-10-16T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            self.report(windsor=x)

    def test_unscoped_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "offset-aware"):
            reconcile(brand(), connections(), m_export(), w_export(),
                      as_of=datetime(2026, 10, 15))

    def test_input_immutability(self):
        a, b, c, d = brand(), connections(), m_export(), w_export()
        saved = copy.deepcopy([a, b, c, d])
        reconcile(a, b, c, d, as_of=NOW)
        self.assertEqual([a, b, c, d], saved)


if __name__ == "__main__":
    unittest.main()
