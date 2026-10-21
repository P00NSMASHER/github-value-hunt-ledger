"""Test Lab 15 source-bound triage; no internet, external invoices or real cash."""
from __future__ import annotations

import copy
import json
import unittest

from freight import lab15_acquisition as acquisition
from freight import lab15_triage as triage


class TriageChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = acquisition.read_ledger()
        cls.annotations = json.loads(triage.ANNOTATIONS.read_text(encoding="utf-8"))

    def test_source_bound_and_approval_safe(self):
        output = triage.build_queue(self.ledger, self.annotations)
        self.assertEqual(output["source_count"], len(self.ledger["records"]))
        self.assertEqual(output["annotated_sources"], len(self.annotations["annotations"]))
        self.assertEqual(output["sources_with_complete_approved_real_case"], 0)
        self.assertTrue(all(not e["reuse_rights_cleared"] for e in output["entries"]))
        self.assertTrue(all(not e["invoice_error_independently_verified"] for e in output["entries"]))
        self.assertTrue(all(not e["real_cash_recovery_verified"] for e in output["entries"]))
        triage.validate_queue(output, self.ledger, self.annotations)

    def test_highest_priority_real_invoice_plus_quote(self):
        output = triage.build_queue(self.ledger, self.annotations)
        entry = output["entries"][0]
        self.assertIn("document.epiq11.com", entry["source_url"])
        self.assertIn("effective_customer_rate_quote", entry["reported_evidence"])
        self.assertIn("original_carrier_invoice", entry["reported_evidence"])
        self.assertIn("independent_payment_or_credit_receipt", entry["evidence_not_reported"])
        self.assertFalse(entry["complete_original_document_chain_verified"])

    def test_stable_and_independent_of_wall_clock(self):
        a = triage.build_queue(self.ledger, self.annotations)
        b = triage.build_queue(copy.deepcopy(self.ledger), copy.deepcopy(self.annotations))
        self.assertEqual(a, b)

    def test_reject_unregistered_source_and_duplicate(self):
        bad = copy.deepcopy(self.annotations)
        bad["annotations"][0]["url"] = "https://github.com/unknown/unreviewed"
        with self.assertRaises(acquisition.EvidenceError):
            triage.build_queue(self.ledger, bad)
        bad = copy.deepcopy(self.annotations)
        bad["annotations"].append(copy.deepcopy(bad["annotations"][0]))
        with self.assertRaises(acquisition.EvidenceError):
            triage.build_queue(self.ledger, bad)

    def test_reject_auto_approval_and_invalid_labels(self):
        for key, value in [
            ("reuse_rights_cleared", True),
            ("customer_permission_verified", True),
            ("invoice_error_independently_verified", True),
            ("payment_verified", True),
        ]:
            bad = copy.deepcopy(self.annotations)
            bad["annotations"][0][key] = value
            with self.subTest(key=key), self.assertRaises(acquisition.EvidenceError):
                triage.build_queue(self.ledger, bad)
        bad = copy.deepcopy(self.annotations)
        bad["annotations"][0]["review_state"] = "VERIFIED_REAL_CUSTOMER"
        with self.assertRaises(acquisition.EvidenceError):
            triage.build_queue(self.ledger, bad)

    def test_reject_unsorted_duplicate_or_unknown_evidence(self):
        for labels in [
            ["original_carrier_invoice", "original_carrier_invoice"],
            ["original_carrier_invoice", "effective_customer_rate_quote"],
            ["original_carrier_invoice", "recovered_cash"],
            [],
        ]:
            bad = copy.deepcopy(self.annotations)
            bad["annotations"][0]["reported_evidence"] = labels
            with self.subTest(labels=labels), self.assertRaises(acquisition.EvidenceError):
                triage.build_queue(self.ledger, bad)

    def test_catalog_results_cannot_auto_claim_original_invoices(self):
        catalog_rows = [r for r in self.ledger["records"] if r["kind"] == "DATASET_CATALOG_LEAD"]
        if not catalog_rows:
            self.skipTest("No catalog records yet")
        bad = copy.deepcopy(self.annotations)
        bad["annotations"].append({
            "url": catalog_rows[0]["url"],
            "reported_evidence": ["original_carrier_invoice"],
            "review_state": triage.REVIEW_STATE,
        })
        with self.assertRaises(acquisition.EvidenceError):
            triage.build_queue(self.ledger, bad)

    def test_tampering_with_output_never_promotes_to_truth(self):
        output = triage.build_queue(self.ledger, self.annotations)
        output["entries"][0]["invoice_error_independently_verified"] = True
        with self.assertRaises(acquisition.EvidenceError):
            triage.validate_queue(output, self.ledger, self.annotations)

    def test_report_tracks_changing_ledger_without_promoting(self):
        expanded = copy.deepcopy(self.ledger)
        link = "https://github.com/research-archive/ltl-audit-dataset"
        expanded["records"].append(acquisition.source_record(
            link, "DATASET_CATALOG_LEAD", "2026-10-17T12:00:00Z",
            discovered_by="GITHUB", title="freight invoice dataset",
        ))
        a = triage.build_queue(self.ledger, self.annotations)
        b = triage.build_queue(expanded, self.annotations)
        self.assertEqual(b["source_count"], a["source_count"] + 1)
        self.assertNotEqual(a["source_ledger_sha256"], b["source_ledger_sha256"])
        self.assertEqual(b["sources_with_complete_approved_real_case"], 0)


if __name__ == "__main__":
    unittest.main()
