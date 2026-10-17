"""Fail-closed tests for RETALLY Lab 15; no live network is used."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from freight import lab15_acquisition as lab

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
GAO = "https://www.gao.gov/products/b-143246"
PSC = "https://psc.ky.gov/pscecf/2024-00200/folder/test.pdf"
HTML = b"<html><title>GAO freight overcharge opinion</title></html>"
SEED_ROWS = [
    {"url": GAO, "kind": "GAO_DECISION", "title": "GAO published decision"},
    {"url": PSC, "kind": "PUBLIC_REGULATORY_EXHIBIT", "title": "Public exhibit"},
]


def response(url, content=HTML, mime="text/html", status=200, final_url=None):
    return lab.HTTPResult(status, final_url or url, mime, content)


class Lab15Tests(unittest.TestCase):
    def fresh(self):
        return {"schema_version": 1, "records": []}

    def test_offline_is_safe_and_deterministic(self):
        def forbidden(_):
            self.fail("offline mode reached network")
        a, r = lab.run_cycle(self.fresh(), SEED_ROWS, now=NOW, fetch=forbidden,
                             pause=lambda _: None)
        b, r2 = lab.run_cycle(a, SEED_ROWS, now=NOW, fetch=forbidden,
                              pause=lambda _: None)
        self.assertEqual(a, b)
        self.assertEqual(r["seeded"], 2)
        self.assertEqual(r2["seeded"], 0)
        self.assertEqual(r["raw_documents_stored"], 0)
        self.assertEqual(r["commercial_data_admissions"], 0)
        self.assertTrue(all(not rec["commercial_test_approved"] for rec in a["records"]))

    def test_gov_fingerprint_not_an_adjudicated_invoice(self):
        def transport(url):
            self.assertEqual(url, GAO)
            return response(url)
        # Prevent catalogue calls from introducing unsourced records.
        old_searches = lab.SEARCHES
        try:
            lab.SEARCHES = ()
            first, report = lab.run_cycle(self.fresh(), SEED_ROWS, live=True, now=NOW,
                                           fetch=transport, pause=lambda _: None)
            ga = next(r for r in first["records"] if r["kind"] == "GAO_DECISION")
            self.assertEqual(ga["sha256"], hashlib.sha256(HTML).hexdigest())
            self.assertEqual(ga["content_version"], 1)
            self.assertEqual(report["new_fingerprints"], 1)
            self.assertFalse(ga["independent_invoice_error_verified"])
            self.assertFalse(ga["actual_payment_verified"])
            self.assertFalse(ga["raw_document_stored"])
            self.assertEqual(ga["rights"], lab.RIGHTS_HOLD)
            again, r2 = lab.run_cycle(first, SEED_ROWS, live=True, now=NOW,
                                       fetch=transport, pause=lambda _: None)
            ga2 = next(r for r in again["records"] if r["kind"] == "GAO_DECISION")
            self.assertEqual(ga2["content_version"], 1)
            self.assertEqual(r2["new_fingerprints"], 0)
            self.assertEqual(r2["changed_fingerprints"], 0)
        finally:
            lab.SEARCHES = old_searches

    def test_change_receipt_cannot_validate_financial_outcome(self):
        old_searches = lab.SEARCHES
        try:
            lab.SEARCHES = ()
            first, _ = lab.run_cycle(self.fresh(), SEED_ROWS, live=True, now=NOW,
                                      fetch=lambda url: response(url), pause=lambda _: None)
            new_body = b"<html>New government revision</html>"
            second, r = lab.run_cycle(first, SEED_ROWS, live=True, now=NOW,
                                       fetch=lambda url: response(url, new_body),
                                       pause=lambda _: None)
            record = next(a for a in second["records"] if a["kind"] == "GAO_DECISION")
            self.assertEqual(r["changed_fingerprints"], 1)
            self.assertEqual(record["content_version"], 2)
            self.assertFalse(record["recovery_verified"])
        finally:
            lab.SEARCHES = old_searches

    def test_unavailable_source_does_not_erase_previous_receipt(self):
        old = lab.SEARCHES
        try:
            lab.SEARCHES = ()
            baseline, _ = lab.run_cycle(self.fresh(), SEED_ROWS, live=True,
                                         now=NOW, fetch=lambda url: response(url),
                                         pause=lambda _: None)
            second, report = lab.run_cycle(
                baseline, SEED_ROWS, live=True, now=NOW,
                fetch=lambda _: response(GAO, status=403),
                pause=lambda _: None)
            self.assertEqual(baseline, second)
            self.assertEqual(report["fetch_holds"], 1)
        finally:
            lab.SEARCHES = old

    def test_all_private_network_and_redirect_vectors_blocked(self):
        for url in (
            "http://www.gao.gov/products/b-1",
            "https://localhost/invoices",
            "https://127.0.0.1/",
            "https://169.254.169.254/latest/meta-data/",
            "https://gao.gov.evil.test/",
            "https://user:secret@www.gao.gov/",
            "https://www.gao.gov:8080/products/",
            "https://www.gao.gov/file#fragment",
            "https://www.gao.gov/%0d%0ax",
            "https://www.gao.gov/../secrets",
            "https://github.com//../../secret",
            "https://www.gao.gov/a\\b",
            "https://www.gao.gov/\nHello",
        ):
            with self.subTest(url=url), self.assertRaises(lab.EvidenceError):
                lab.safe_url(url, lab.SOURCE_HOSTS)
        self.assertEqual(lab.safe_url(GAO, lab.NETWORK_HOSTS), GAO)

    def test_redirect_and_invalid_pdf_and_oversized_body_rejected(self):
        with self.assertRaises(lab.EvidenceError):
            lab.verify_response(GAO, response(GAO, final_url="https://www.gao.gov/elsewhere"))
        with self.assertRaises(lab.EvidenceError):
            lab.verify_response(GAO, response(GAO, b"NOT_PDF", mime="application/pdf"))
        with self.assertRaises(lab.EvidenceError):
            lab.verify_response(GAO, response(GAO, b"<" * (lab.MAX_DOC_BYTES + 1)))
        with self.assertRaises(lab.EvidenceError):
            lab.verify_response(GAO, response(GAO, b"{}", mime="application/json"))
        with self.assertRaises(lab.EvidenceError):
            lab.verify_response(GAO, response(GAO, b"%PDF-fake", mime="application/pdf",
                                              status=404))

    def test_false_ledger_financial_approval_never_accepted(self):
        x, _ = lab.run_cycle(self.fresh(), SEED_ROWS, now=NOW, pause=lambda _: None)
        for key in (
            "commercial_test_approved", "actual_payment_verified",
            "independent_invoice_error_verified", "recovery_verified",
            "raw_document_stored"
        ):
            changed = copy.deepcopy(x)
            changed["records"][0][key] = True
            with self.subTest(key=key), self.assertRaises(lab.EvidenceError):
                lab.validate_ledger(changed)

    def test_ledger_cannot_spoof_identity_or_digest(self):
        x, _ = lab.run_cycle(self.fresh(), SEED_ROWS, now=NOW, pause=lambda _: None)
        for field, value in (("id", "src-forged"), ("state", "APPROVED"),
                             ("sha256", "0"*64), ("bytes_seen", -3),
                             ("content_version", -4)):
            changed = copy.deepcopy(x)
            changed["records"][0][field] = value
            with self.subTest(field=field), self.assertRaises(lab.EvidenceError):
                lab.validate_ledger(changed)
        changed = copy.deepcopy(x)
        changed["records"].append(copy.deepcopy(changed["records"][0]))
        with self.assertRaises(lab.EvidenceError):
            lab.validate_ledger(changed)

    def test_seed_authority_spoof_and_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "sources.json"
            for row in (
                [{"url":"https://github.com/evil/case","kind":"GAO_DECISION","title":"Fake"}],
                SEED_ROWS * 2,
            ):
                file.write_text(json.dumps({"schema_version":1, "sources":row}))
                with self.assertRaises(lab.EvidenceError):
                    lab.load_seeds(file)

    def test_github_dataset_metadata_parses_with_false_claims_held(self):
        candidates = lab.catalog_leads("github", {
            "items": [
                {"full_name":"open-data/Freight-Invoice-Dataset",
                 "description":"real LTL freight invoice research corpus"},
                {"full_name":"fake/Freight-Demo","description":"synthetic freight invoice template"},
                {"full_name":"bad///x","description":"freight invoice"},
                {"full_name":"private/Payroll","description":"unrelated"}
            ]})
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0],
                         "https://github.com/open-data/Freight-Invoice-Dataset")

    def test_zenodo_and_dataverse_catalogs(self):
        zen = lab.catalog_leads("zenodo", {
            "hits": {"hits": [{"id": 1234, "metadata": {
                "title": "Freight Invoice Audit Ledger"}},
                {"id": 5678, "metadata": {"title": "Synthetic Freight Invoice Demo"}}]}})
        self.assertEqual(zen, [("https://zenodo.org/records/1234",
                                "Freight Invoice Audit Ledger")])
        dv = lab.catalog_leads("dataverse", {"data": {"items": [
            {"type": "dataset", "global_id": "doi:10.7910/DVN/XABC1",
             "name": "Less-than-truckload freight invoice audit research"}
        ]}})
        self.assertEqual(len(dv), 1)
        self.assertTrue(dv[0][0].startswith("https://dataverse.harvard.edu/"))

    def test_live_metadata_discovery_and_cross_run_dedupe(self):
        original = lab.SEARCHES
        try:
            lab.SEARCHES = (("github", "https://api.github.com/search/repositories?q=freight"),)
            def transport(url):
                if url == GAO:
                    return response(url)
                return response(url, json.dumps({"items":[{
                    "full_name": "research/FreightInvoiceAudit",
                    "description": "real LTL freight invoice audit"
                }]}).encode(), mime="application/json")
            first, r = lab.run_cycle(self.fresh(), SEED_ROWS, live=True,
                                      fetch=transport, now=NOW, pause=lambda _: None)
            self.assertEqual(r["discovered"], 1)
            second, r2 = lab.run_cycle(first, SEED_ROWS, live=True,
                                        fetch=transport, now=NOW, pause=lambda _: None)
            self.assertEqual(r2["discovered"], 0)
            self.assertEqual(first, second)
            match = next(x for x in second["records"]
                         if x["discovered_by"] == "GITHUB")
            self.assertEqual(match["state"], "DISCOVERED_METADATA_ONLY")
            self.assertIsNone(match["sha256"])
            self.assertFalse(match["commercial_test_approved"])
        finally:
            lab.SEARCHES = original

    def test_catalog_failure_is_held_without_bad_record(self):
        original = lab.SEARCHES
        try:
            lab.SEARCHES = (("github", "https://api.github.com/search/repositories?q=freight"),)
            def transport(url):
                return response(url) if url == GAO else response(url, b"invalid!",
                                                                 mime="application/json")
            result, r = lab.run_cycle(self.fresh(), SEED_ROWS, live=True,
                                       fetch=transport, now=NOW, pause=lambda _: None)
            self.assertEqual(r["catalog_holds"], 1)
            self.assertEqual(len(result["records"]), 2)
        finally:
            lab.SEARCHES = original

    def test_source_manifest_parses_with_zero_inadvertent_rights(self):
        manifest = lab.load_seeds()
        self.assertGreaterEqual(len(manifest), 6)
        cases, report = lab.run_cycle(self.fresh(), manifest, now=NOW,
                                       pause=lambda _: None)
        self.assertEqual(len(cases["records"]), len(manifest))
        self.assertEqual(report["verified_real_customer_outcomes"], 0)
        self.assertTrue(any(x["kind"] == "PUBLIC_BANKRUPTCY_EXHIBIT"
                            for x in cases["records"]))
        self.assertTrue(all(x["rights"] == lab.RIGHTS_HOLD for x in cases["records"]))

    def test_title_with_contact_is_discarded(self):
        self.assertEqual(lab.scrub_title("Question email foo@bar.com"), "[REDACTED]")
        self.assertEqual(lab.scrub_title("<div>Freight invoice</div>"), "Freight invoice")

    def test_nonutc_timestamp_is_canonical(self):
        self.assertEqual(lab.timestamp(NOW), "2026-10-17T12:00:00Z")
        with self.assertRaises(lab.EvidenceError):
            lab.timestamp(datetime(2026, 10, 17, 12, 0))


if __name__ == "__main__":
    unittest.main()
