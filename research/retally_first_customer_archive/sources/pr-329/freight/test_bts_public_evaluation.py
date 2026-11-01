"""Checks for a small factual public-source PARSER evaluation, never fraud labels."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import fields
from decimal import Decimal
from pathlib import Path

from freight import bts_public_evaluation as bts


class BTSObservedReferenceTests(unittest.TestCase):
    def modified(self, old: str, new: str, *, expect: str, pin: bool = False):
        original = bts.DATA_PATH.read_text(encoding="utf-8")
        self.assertIn(old, original)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "sample.csv"
            candidate.write_text(original.replace(old, new, 1), encoding="utf-8")
            with self.assertRaisesRegex(bts.PublicReferenceError, expect):
                bts.load_observations(candidate, verify_pinned_blob=pin)

    def test_source_git_blob_identity(self):
        raw = bts.DATA_PATH.read_bytes()
        observed_sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual(observed_sha, bts.PINNED_FIXTURE_BLOB)

    def test_all_twenty_rows_and_four_carrier_groups(self):
        records = bts.load_observations()
        self.assertEqual(len(records), 20)
        self.assertEqual({x.carrier_code for x in records}, {"2E", "2F", "4W", "7H"})
        self.assertEqual(sum(x.freight_present for x in records), 12)
        self.assertEqual(sum(not x.freight_present for x in records), 8)

    def test_reported_fields_grounded_in_pinned_mirror(self):
        rows = {x.source_row: x for x in bts.load_observations()}
        self.assertEqual(rows[5].freight_pounds, Decimal("2649.00"))
        self.assertEqual(rows[5].mail_pounds, Decimal("1846.00"))
        self.assertEqual((rows[104].origin, rows[104].destination), ("ADQ", "ANC"))
        self.assertEqual(rows[104].freight_pounds, Decimal("127.00"))
        self.assertEqual(rows[105].freight_pounds, Decimal("4301.00"))

    def test_zero_freight_with_positive_mail_is_not_freight(self):
        record = next(x for x in bts.load_observations() if x.source_row == 3)
        self.assertEqual(record.freight_pounds, Decimal("0.00"))
        self.assertEqual(record.mail_pounds, Decimal("345.00"))
        self.assertIs(record.freight_present, False)

    def test_exact_grouped_holdout_prevents_same_carrier_training_leakage(self):
        train, validation = bts.carrier_disjoint_eval(bts.load_observations())
        self.assertEqual(len(train), 15)
        self.assertEqual(len(validation), 5)
        self.assertFalse({x.carrier_code for x in train} & {x.carrier_code for x in validation})
        self.assertEqual({x.carrier_code for x in validation}, {"7H"})

    def test_modified_valid_number_rejected_by_integrity_pin(self):
        self.modified("5,2013,1,2E,HOM,SOV,2649.00", "5,2013,1,2E,HOM,SOV,2650.00",
                      expect="integrity mismatch", pin=True)

    def test_derived_freight_presence_must_match_reported_weight(self):
        self.modified("5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,F,1",
                      "5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,F,0",
                      expect="contradicts source value")

    def test_cannot_create_positive_target_from_zero_freight(self):
        self.modified("3,2013,1,2E,HOM,KEB,0.00,345.00,26.00,30.00,F,0",
                      "3,2013,1,2E,HOM,KEB,0.00,345.00,26.00,30.00,F,1",
                      expect="contradicts source value")

    def test_missing_or_duplicate_source_row_rejected(self):
        self.modified("5,2013,1,2E,HOM,SOV", "3,2013,1,2E,HOM,SOV",
                      expect="source row IDs/order changed")

    def test_published_vintage_cannot_be_silently_changed(self):
        self.modified("5,2013,1,2E,HOM,SOV", "5,2024,1,2E,HOM,SOV",
                      expect="outside pinned January 2013")

    def test_unknown_airport_identifier_rejected(self):
        self.modified("5,2013,1,2E,HOM,SOV", "5,2013,1,2E,HOM,ABC!",
                      expect="invalid airport")

    def test_unsupported_carrier_and_class_rejected(self):
        self.modified("5,2013,1,2E,HOM,SOV", "5,2013,1,unknown,HOM,SOV",
                      expect="invalid carrier")
        self.modified("5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,F,1",
                      "5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,Z,1",
                      expect="unrecognized T-100 service")

    def test_invalid_precision_or_negative_weight_rejected(self):
        self.modified("5,2013,1,2E,HOM,SOV,2649.00",
                      "5,2013,1,2E,HOM,SOV,2649.123",
                      expect="exact two-decimal")
        self.modified("5,2013,1,2E,HOM,SOV,2649.00",
                      "5,2013,1,2E,HOM,SOV,-1.00",
                      expect="exact two-decimal")

    def test_extra_column_rejected(self):
        self.modified("5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,F,1",
                      "5,2013,1,2E,HOM,SOV,2649.00,1846.00,16.00,71.00,F,1,unauthorized",
                      expect="malformed BTS subset")

    def test_no_invoice_or_recovery_training_labels(self):
        self.assertEqual(set(bts.ReportedAirfreight.__dataclass_fields__), {
            "source_row", "year", "month", "carrier_code",
            "origin", "destination", "freight_pounds", "mail_pounds",
            "distance_miles", "departures_performed", "service_class",
            "freight_present",
        })
        self.assertIn("NOT_INVOICE_GROUND_TRUTH", bts.load_observations()[0].evidence_class)
        self.assertNotIn("overcharge", {f.name for f in fields(bts.ReportedAirfreight)})

    def test_holdout_refuses_incomplete_population(self):
        records = bts.load_observations()
        with self.assertRaisesRegex(bts.PublicReferenceError, "missing rows"):
            bts.carrier_disjoint_eval(records[:-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
