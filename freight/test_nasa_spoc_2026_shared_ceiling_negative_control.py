"""NASA SPOC August/September 2026: duplicate-notice and shared-ceiling control.

Original public issuer sources (human-transcribed, research-only):
NASA, 2026-08-17:
https://www.nasa.gov/news-release/nasa-selects-companies-to-provide-payload-processing-services/
SAM award notice original (2026-08-17, GUID 1cce3da...):
https://sam.gov/workspace/contract/opp/1cce3da03a5c45e08d39016e0872e54f/view
SAM updated award notice (2026-09-09, GUID 7aad873...):
https://sam.gov/opp/7aad873631bf4fe29349c7273fccbb36/view

The later SAM notice repeats the same 2026-08-04 award action and the
same four contract IDs. NASA identifies $100M as one AGGREGATE
multiple-award IDIQ ceiling, not $100M paid to each vendor. The two
notice revisions do not establish $200M in separate new awards.

Sources inspected as public publisher pages / indexed original text on
2026-11-06. No original SAM response-byte custody or SHA, no original
signed transaction records, no resolved contractor-to-PIID assignment,
no individual obligation or modification histories, no source-specific
reuse approval and no customer cash. NOT A VALIDATED AWARD BENCHMARK.
No network, D1, production code or source-file writes from these tests.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import unittest

AGENCY = {
    "issuer": "NASA",
    "office": "NASA Kennedy Space Center",
    "press_release_date": "2026-08-17",
    "ceiling_scope": "AGGREGATE_MULTIPLE_AWARD_IDIQ",
    "aggregate_ceiling_usd": 100_000_000,
    "contractors": (
        "All Points Logistics LLC", "Blue Origin LLC",
        "Firefly Aerospace", "L3Harris Technologies Inc.",
    ),
}
AWARD_IDS = (
    "80KSC026D0004", "80KSC026D0005",
    "80KSC026D0006", "80KSC026D0007",
)
SAM_ORIGINAL = {
    "issuer": "NASA",
    "office": "NASA Kennedy Space Center",
    "opportunity": "80KSC026D000X",
    "related_solicitation": "80KSC022R0020_RevA",
    "notice_guid": "1cce3da03a5c45e08d39016e0872e54f",
    "publication": "2026-08-17",
    "award_date": "2026-08-04",
    "award_id_field": "_".join(AWARD_IDS),
    "award_amount_usd": 100_000_000,
    "contractor_field": "Multiple Awardees",
    "listed_contractors": AGENCY["contractors"],
    "award_modification": None,
}
SAM_UPDATED = {
    **SAM_ORIGINAL,
    "notice_guid": "7aad873631bf4fe29349c7273fccbb36",
    "publication": "2026-09-09",
}
UNKNOWN = "UNKNOWN_SOURCE_OR_IDENTITY"
VALID_AGGREGATE = "AGGREGATE_100M_ONLY_NOT_OBLIGATION"
DUPLICATE_FALSIFIED = "FALSIFIED_200M_FROM_TWO_NOTICES"
PUBLISHER_ABSENT = "UPDATED_NOTICE_NOT_YET_PUBLISHED_ASOF"


def adjudicate_notices(agency, original, updated, *, claimed_total_usd, asof):
    """Only evaluate the specific primary-publisher record, never revenue."""
    if type(asof) is not date or type(claimed_total_usd) is not int:
        return UNKNOWN
    if any(type(row) is not dict for row in (agency, original, updated)):
        return UNKNOWN
    # A publisher record is an identity tuple, not a page count or a
    # concatenated number that may be turned into an invented PIID.
    if (
        agency.get("issuer") != "NASA"
        or agency.get("office") != "NASA Kennedy Space Center"
        or agency.get("ceiling_scope") != "AGGREGATE_MULTIPLE_AWARD_IDIQ"
        or agency.get("aggregate_ceiling_usd") != 100_000_000
        or tuple(agency.get("contractors", ())) != AGENCY["contractors"]
        or original.get("issuer") != agency["issuer"]
        or updated.get("issuer") != agency["issuer"]
        or original.get("office") != agency["office"]
        or updated.get("office") != agency["office"]
        or original.get("opportunity") != "80KSC026D000X"
        or updated.get("opportunity") != original["opportunity"]
        or original.get("related_solicitation") != "80KSC022R0020_RevA"
        or updated.get("related_solicitation") != original["related_solicitation"]
        or original.get("notice_guid") != SAM_ORIGINAL["notice_guid"]
        or updated.get("notice_guid") != SAM_UPDATED["notice_guid"]
        or original.get("award_id_field") != "_".join(AWARD_IDS)
        or updated.get("award_id_field") != original["award_id_field"]
        or original.get("award_date") != "2026-08-04"
        or updated.get("award_date") != original["award_date"]
        or original.get("award_amount_usd") != agency["aggregate_ceiling_usd"]
        or updated.get("award_amount_usd") != original["award_amount_usd"]
        or original.get("contractor_field") != "Multiple Awardees"
        or updated.get("contractor_field") != original["contractor_field"]
        or tuple(original.get("listed_contractors", ())) != agency["contractors"]
        or tuple(updated.get("listed_contractors", ())) != agency["contractors"]
        or original.get("award_modification") is not None
        or updated.get("award_modification") is not None
    ):
        return UNKNOWN
    try:
        first = date.fromisoformat(original["publication"])
        revised = date.fromisoformat(updated["publication"])
        awarded = date.fromisoformat(original["award_date"])
        press = date.fromisoformat(agency["press_release_date"])
    except (TypeError, ValueError):
        return UNKNOWN
    if not awarded < first == press < revised:
        return UNKNOWN
    if asof < first:
        return UNKNOWN
    if asof < revised:
        return PUBLISHER_ABSENT
    if claimed_total_usd == 2 * agency["aggregate_ceiling_usd"]:
        return DUPLICATE_FALSIFIED
    if claimed_total_usd == agency["aggregate_ceiling_usd"]:
        return VALID_AGGREGATE
    return UNKNOWN


class NasaSpoc2026SharedCeilingNegativeControls(unittest.TestCase):
    def test_agency_amount_is_shared_not_two_notice_awards(self):
        self.assertEqual(adjudicate_notices(
            AGENCY, SAM_ORIGINAL, SAM_UPDATED,
            claimed_total_usd=200_000_000, asof=date(2026, 11, 6)),
            DUPLICATE_FALSIFIED)
        self.assertEqual(adjudicate_notices(
            AGENCY, SAM_ORIGINAL, SAM_UPDATED,
            claimed_total_usd=100_000_000, asof=date(2026, 11, 6)),
            VALID_AGGREGATE)
        self.assertEqual(len(SAM_ORIGINAL["award_id_field"].split("_")), 4)
        self.assertEqual(tuple(SAM_UPDATED["award_id_field"].split("_")), AWARD_IDS)
        self.assertNotEqual(SAM_ORIGINAL["notice_guid"], SAM_UPDATED["notice_guid"])

    def test_source_identity_and_amount_mutations_fail_closed(self):
        for target, changes in (
            (1, {"award_id_field": "80KSC026D0004"}),
            (1, {"award_date": "2026-09-09"}),
            (2, {"award_amount_usd": 200_000_000}),
            (2, {"opportunity": "80KSC026D999X"}),
            (2, {"related_solicitation": "80KSC022R9999"}),
            (2, {"listed_contractors": ("Different Company",)}),
            (0, {"aggregate_ceiling_usd": 400_000_000}),
            (0, {"ceiling_scope": "PER_CONTRACTOR"}),
        ):
            with self.subTest(target=target, changes=changes):
                records = [deepcopy(AGENCY), deepcopy(SAM_ORIGINAL), deepcopy(SAM_UPDATED)]
                records[target].update(changes)
                self.assertEqual(adjudicate_notices(
                    *records, claimed_total_usd=200_000_000,
                    asof=date(2026, 11, 6)), UNKNOWN)

    def test_later_notice_cannot_backfill_august_asof(self):
        self.assertEqual(adjudicate_notices(
            AGENCY, SAM_ORIGINAL, SAM_UPDATED,
            claimed_total_usd=200_000_000, asof=date(2026, 8, 16)), UNKNOWN)
        self.assertEqual(adjudicate_notices(
            AGENCY, SAM_ORIGINAL, SAM_UPDATED,
            claimed_total_usd=200_000_000, asof=date(2026, 8, 18)),
            PUBLISHER_ABSENT)

    def test_no_imaginary_vendor_piids_or_payments(self):
        # Four named vendors + four PIIDs does not prove the ordered mapping.
        self.assertEqual(len(AGENCY["contractors"]), len(AWARD_IDS))
        self.assertEqual(SAM_ORIGINAL["contractor_field"], "Multiple Awardees")
        self.assertIsNone(SAM_ORIGINAL["award_modification"])
        self.assertNotIn("vendor_to_award_id", SAM_ORIGINAL)
        for field in ("individual_award_obligation_usd", "recovered_customer_cash_usd",
                      "source_html_sha256", "signed_modification_ledger",
                      "verified_vendor_to_piid_mapping"):
            self.assertNotIn(field, SAM_ORIGINAL)
            self.assertNotIn(field, SAM_UPDATED)


if __name__ == "__main__":
    unittest.main()
