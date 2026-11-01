"""Regression: original source and JSON proof must match recorded bytes at every read/review boundary.
No real customers, external calls, claims, or money transfers.
"""
import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.seven_branch_simulation import seed
from recoveryworks.workbench import Workspace


class OriginalEvidenceIntegrityTests(unittest.TestCase):
    def test_tampered_original_csv_rejected_before_read_review_or_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            ws, tokens = Workspace.create(Path(d) / "client", "synthetic-client")
            content = "ID,Supplier,Invoice,Total,Date\np1,v,i1,100,2026-01-01\n"
            mapping = {"Payment_Number": "ID", "Vendor": "Supplier",
                       "Invoice_Number": "Invoice", "Amount": "Total",
                       "Payment_Date": "Date"}
            receipt = ws.upload(tokens["customer"], "ap", "payments_csv", content, mapping)
            original = ws.root / ("sources/" + receipt["id"] + ".original")
            original.write_text("TAMPERED", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.read_source(tokens["customer"], receipt["id"])
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.review_source(tokens["reviewer"], "ap", "payments_csv",
                                 receipt["normalized_sha256"], "synthetic review")
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.upload(tokens["customer"], "ap", "payments_csv", content, mapping)
            self.assertIsNone(ws._intake()["sources"]["ap/payments_csv"]["review"])
            original.unlink()
            with self.assertRaisesRegex(ValueError, "original or normalized evidence missing"):
                ws.read_source(tokens["customer"], receipt["id"])

    def test_tampered_original_document_rejected_before_review_and_action(self):
        with tempfile.TemporaryDirectory() as d:
            ws, tokens = seed(Path(d) / "client")
            ws.scan(tokens["operator"])
            finding_id = ws.cases(tokens["customer"])["cases"][0]["finding_id"]
            content = json.dumps({"kind": "synthetic_review_only"})
            receipt = ws.upload_document(tokens["customer"], finding_id, "authorization", content)
            original = ws.root / ("sources/" + receipt["id"] + ".original")
            original.write_text("TAMPERED", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.read_source(tokens["customer"], receipt["id"])
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.review_document(tokens["reviewer"], receipt["id"],
                                   receipt["normalized_sha256"], "synthetic review")
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws.upload_document(tokens["customer"], finding_id, "authorization", content)
            original.write_bytes(content.encode("utf-8"))
            ws.review_document(tokens["reviewer"], receipt["id"],
                               receipt["normalized_sha256"], "synthetic review")
            self.assertEqual(ws._reviewed_document(receipt["id"], finding_id, "authorization"),
                             {"kind": "synthetic_review_only"})
            original.write_text("TAMPERED AGAIN", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "original evidence bytes changed"):
                ws._reviewed_document(receipt["id"], finding_id, "authorization")


if __name__ == "__main__":
    unittest.main()
