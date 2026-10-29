"""Synthetic negative controls plus source-curated correspondence checks."""
import copy
import json
import unittest
from pathlib import Path
from verify_sample import evaluate, report

DOC = json.loads(Path(__file__).with_name("2026-10-29_sample.json").read_text())
GWA, NTUA = DOC["signals"]
BID, NTUA_BID, PARTS, REHAB, GROUNDS = DOC["procurement"]


class Tests(unittest.TestCase):
    def test_one_curated_source_match(self):
        self.assertEqual(evaluate(GWA, BID), ("SOURCE_MATCH", "curated_exact_scope_with_dated_primary_notice_receipt", 665))

    def test_secondary_date_is_review(self):
        self.assertEqual(evaluate(NTUA, NTUA_BID), ("REVIEW", "publication_date_not_issuer_confirmed", 1009))

    def test_same_plant_parts_no_strong_match(self):
        self.assertEqual(evaluate(GWA, PARTS)[0], "REVIEW")

    def test_same_plant_rehab_no_strong_match(self):
        self.assertEqual(evaluate(GWA, REHAB)[0], "REVIEW")

    def test_unrelated_grounds_not_match(self):
        self.assertEqual(evaluate(GWA, GROUNDS)[0], "NO_MATCH")

    def test_wrong_agency(self):
        altered = copy.deepcopy(BID); altered["agency"] = "other-utility"
        self.assertEqual(evaluate(GWA, altered)[1], "agency")

    def test_wrong_facility(self):
        altered = copy.deepcopy(BID); altered["facility"] = "other-plant"
        self.assertEqual(evaluate(GWA, altered)[1], "facility")

    def test_before_announcement(self):
        altered = copy.deepcopy(BID); altered["issue_date"] = "2023-12-31"
        self.assertEqual(evaluate(GWA, altered)[0], "NO_MATCH")

    def test_bad_or_missing_dates(self):
        altered = copy.deepcopy(BID); altered["issue_date"] = "2026-99-99"
        self.assertEqual(evaluate(GWA, altered)[0], "REVIEW")
        del altered["issue_date"]
        self.assertEqual(evaluate(GWA, altered)[0], "REVIEW")

    def test_spoofed_issuer_source(self):
        altered = copy.deepcopy(BID); altered["url"] = "https://guamwaterworks.org.evil.example"
        self.assertEqual(evaluate(GWA, altered)[1], "bid_source")

    def test_spoofed_epa_source(self):
        altered = copy.deepcopy(GWA); altered["url"] = "https://epa.gov.evil.example"
        self.assertEqual(evaluate(altered, BID)[1], "signal_source")

    def test_document_does_not_infer_revenue(self):
        rows = report(DOC)
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(x["status"] == "SOURCE_MATCH" for x in rows), 1)
        self.assertTrue(all("revenue" not in x for x in rows))


    def test_generic_issuer_homepage_cannot_prove_date(self):
        altered = copy.deepcopy(BID)
        altered.pop("issuer_notice")
        altered["url"] = "https://guamwaterworks.org/"
        altered["issue_date"] = "2026-08-10"
        self.assertEqual(evaluate(GWA, altered), ("REVIEW", "missing_issuer_notice", 923))

    def test_issuer_index_alone_not_enough(self):
        altered = copy.deepcopy(BID)
        altered.pop("issuer_notice")
        self.assertEqual(evaluate(GWA, altered)[1], "missing_issuer_notice")

    def test_forged_government_hostname(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["url"] = "https://notices.guam.gov.attacker.example/notice_detail/7837"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_source")

    def test_government_homepage_not_specific_notice(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["url"] = "https://notices.guam.gov/"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_not_specific")

    def test_notice_query_cannot_substitute_evidence(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["url"] += "?fake=1"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_not_specific")

    def test_issuer_date_disagreement(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["published_on"] = "2025-11-26"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_date_conflict")

    def test_notice_title_mismatch(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["title"] = "Bid for landscaping"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_title")

    def test_missing_bid_identifier(self):
        altered = copy.deepcopy(BID)
        altered.pop("bid_number")
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_title")

    def test_unobserved_future_publication(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["observed_on"] = "2025-11-24"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_date")

    def test_wrong_source_kind(self):
        altered = copy.deepcopy(BID)
        altered["issuer_notice"]["source_kind"] = "search_result_snippet"
        self.assertEqual(evaluate(GWA, altered)[1], "issuer_notice_kind")

    def test_epa_homepage_cannot_prove_scope(self):
        altered = copy.deepcopy(GWA)
        altered["url"] = "https://www.epa.gov/"
        self.assertEqual(evaluate(altered, BID)[1], "signal_not_specific")

    def test_noncanonical_date_is_review(self):
        altered = copy.deepcopy(BID)
        altered["issue_date"] = "2025-11-25T08:42"
        self.assertEqual(evaluate(GWA, altered)[1], "date")

if __name__ == "__main__":
    unittest.main()
