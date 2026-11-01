"""Fail-closed RETALLY social connector identity tests, synthetic fixtures only."""
from __future__ import annotations

import copy
import json
import unittest

from social_source_identity import review


def metricool(**kwargs):
    networks = {
        "facebookData": "1234567890",
        "instagramData": "retallyrecovery",
        "youtubeData": "UCnS99gTJFScnA2gy4wKU_JQ",
    }
    networks.update(kwargs)
    return {"data": [{"id": 7322512, "label": "Retally",
                      "networksData": networks}]}


def windsor():
    return {"result": [
        {"id": "facebook_organic",
         "accounts": [{"id": "1234567890", "name": "Retally"}]},
        {"id": "instagram",
         "accounts": [{"id": "2000", "name": "other_personal_account"}]},
        {"id": "youtube",
         "accounts": [{"id": "53705", "name": "other@example.invalid"}]},
    ]}


class SourceIdentityTest(unittest.TestCase):
    def test_realistic_mismatch_blocks_ig_yt(self):
        result = review(metricool(), windsor())
        self.assertEqual(result["platforms"]["facebook"]["state"], "IDENTITY_MATCH")
        self.assertEqual(result["platforms"]["instagram"]["state"], "IDENTITY_MISMATCH")
        self.assertEqual(result["platforms"]["youtube"]["state"], "NOT_VERIFIED")
        self.assertEqual(result["platforms"]["linkedin"]["state"], "NOT_VERIFIED")
        self.assertFalse(result["platforms"]["instagram"]["cross_source_aggregation_allowed"])
        self.assertIsNone(result["platforms"]["youtube"]["exact_matched_account_id"])

    def test_exact_instagram_handle_match(self):
        src = windsor()
        src["result"][1]["accounts"][0]["name"] = "RETALLYRECOVERY"
        result = review(metricool(), src)
        self.assertEqual(result["platforms"]["instagram"]["state"], "IDENTITY_MATCH")
        self.assertEqual(result["platforms"]["instagram"]["exact_matched_account_id"], "2000")

    def test_at_prefix_ignored_in_handle(self):
        result = review(metricool(instagramData="@retallyrecovery"),
                        {"result": [{"id": "instagram", "accounts": [
                            {"id": "2000", "name": "@RetallyRecovery"}]}]})
        self.assertEqual(result["platforms"]["instagram"]["state"], "IDENTITY_MATCH")

    def test_suffix_not_accepted_as_handle(self):
        src = windsor()
        src["result"][1]["accounts"][0]["name"] = "oldretallyrecovery"
        self.assertEqual(review(metricool(), src)["platforms"]["instagram"]["state"],
                         "IDENTITY_MISMATCH")

    def test_youtube_identity_requires_exact_channel_id(self):
        src = windsor()
        src["result"][2]["accounts"][0]["id"] = "UCnS99gTJFScnA2gy4wKU_JQ"
        result = review(metricool(), src)
        self.assertEqual(result["platforms"]["youtube"]["state"], "IDENTITY_MATCH")

    def test_youtube_login_email_proves_nothing(self):
        src = windsor()
        src["result"][2]["accounts"][0]["name"] = "Retally Recovery"
        result = review(metricool(), src)
        self.assertEqual(result["platforms"]["youtube"]["state"], "NOT_VERIFIED")

    def test_extra_connected_fb_account_never_mixed(self):
        src = windsor()
        src["result"][0]["accounts"].append({"id": "9999", "name": "Other Page"})
        result = review(metricool(), src)
        self.assertEqual(result["platforms"]["facebook"]["exact_matched_account_id"],
                         "1234567890")
        self.assertEqual(result["platforms"]["facebook"]["other_accounts_ignored"], 1)

    def test_missing_fb_connection_not_negative_evidence(self):
        src = windsor()
        src["result"][0]["accounts"] = []
        self.assertEqual(review(metricool(), src)["platforms"]["facebook"]["state"],
                         "NOT_CONNECTED")

    def test_broken_brand_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, "brand"):
            review({"data": []}, windsor())
        with self.assertRaisesRegex(ValueError, "brand"):
            review({"data": [{"id": 7322512, "label": "Wrong Brand",
                              "networksData": {}}]}, windsor())

    def test_duplicate_brand_id_rejected(self):
        data = metricool()
        data["data"].append(copy.deepcopy(data["data"][0]))
        with self.assertRaisesRegex(ValueError, "Exactly one"):
            review(data, windsor())

    def test_duplicate_connector_type_rejected(self):
        src = windsor()
        src["result"].append(copy.deepcopy(src["result"][1]))
        with self.assertRaisesRegex(ValueError, "Duplicate Windsor connector"):
            review(metricool(), src)

    def test_duplicate_account_id_rejected(self):
        src = windsor()
        src["result"][0]["accounts"].append(copy.deepcopy(src["result"][0]["accounts"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate connected account"):
            review(metricool(), src)

    def test_bad_account_identity_fails_closed(self):
        src = windsor()
        src["result"][0]["accounts"][0]["id"] = True
        with self.assertRaisesRegex(ValueError, "Malformed Windsor account"):
            review(metricool(), src)

    def test_metricool_text_wrapper_supported(self):
        wrapper = {"text": json.dumps(metricool())}
        result = review(wrapper, windsor())
        self.assertEqual(result["platforms"]["facebook"]["state"], "IDENTITY_MATCH")

    def test_no_secret_or_unmatched_account_details_in_report(self):
        src = windsor()
        src["result"][2]["accounts"][0]["name"] = "topsecret@example.invalid"
        src["result"][1]["accounts"][0]["secret"] = "not-for-output"
        text = json.dumps(review(metricool(), src))
        self.assertNotIn("topsecret", text)
        self.assertNotIn("not-for-output", text)
        self.assertNotIn("other_personal_account", text)

    def test_no_mutations(self):
        a,b=metricool(),windsor()
        ca,cb=copy.deepcopy(a),copy.deepcopy(b)
        review(a,b)
        self.assertEqual((a,b),(ca,cb))

    def test_malformed_source_never_assumed_empty(self):
        with self.assertRaisesRegex(ValueError, "Windsor"):
            review(metricool(), {})
        with self.assertRaisesRegex(ValueError, "Metricool"):
            review({}, windsor())

    def test_brand_id_override_cannot_use_wrong_brand(self):
        with self.assertRaises(ValueError):
            review(metricool(), windsor(), brand_id="no such brand")


if __name__=="__main__":
    unittest.main()
