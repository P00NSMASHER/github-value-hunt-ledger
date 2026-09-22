from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    freeze_population,
    freeze_truth,
    make_finding,
)
from recoveryworks.runner import run_scan360_config


def write_truth(root: Path, *, buyer_id="buyer-1"):
    population = freeze_population(
        buyer_id,
        "BU-1",
        "all invoices",
        (PopulationRow(
            invoice_id="INV-1",
            shipment_id="SHIP-1",
            customer_id="CUST-1",
            carrier_id="Carrier A",
            currency="USD",
            source_hash="invoice-hash",
        ),),
    )
    authority = AuthorityRef(
        authority_id="AUTH-1",
        buyer_id=buyer_id,
        business_unit="BU-1",
        customer_id="CUST-1",
        carrier_id="Carrier A",
        currency="USD",
        source_hash="authority-hash",
    )
    finding = make_finding(
        finding_id="F-1",
        buyer_id=buyer_id,
        business_unit="BU-1",
        invoice_id="INV-1",
        shipment_id="SHIP-1",
        customer_id="CUST-1",
        carrier_id="Carrier A",
        currency="USD",
        authority_id="AUTH-1",
        expected_cents=10000,
        actual_cents=15000,
        status="VALIDATED",
    )
    truth = freeze_truth(population, (authority,), (finding,))
    (root / "truth-manifest.json").write_text(
        json.dumps(asdict(truth)),
        encoding="utf-8",
    )


class Scan360FreightRunnerTests(unittest.TestCase):
    def test_existing_freight_truth_flows_into_shared_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_truth(root)
            config = {
                "client_id": "buyer-1",
                "currency": "USD",
                "freight": {
                    "truth_manifest_json": "truth-manifest.json",
                },
            }
            state = root / "state.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.branches["freight"]["validated_cents"], 5000)
            self.assertEqual(first.report.totals["validated_cents"], 5000)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_freight_buyer_scope_must_match_scan_client(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_truth(root, buyer_id="different-buyer")
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "buyer-1",
                        "freight": {
                            "truth_manifest_json": "truth-manifest.json",
                        },
                    },
                    state_path=root / "state.json",
                    base_dir=root,
                )

    def test_freight_job_requires_exactly_one_artifact_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "buyer-1",
                        "freight": {},
                    },
                    state_path=root / "state.json",
                    base_dir=root,
                )
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "buyer-1",
                        "freight": {
                            "truth_manifest_json": "a.json",
                            "audit_bundle_zip": "b.zip",
                        },
                    },
                    state_path=root / "state.json",
                    base_dir=root,
                )


if __name__ == "__main__":
    unittest.main()
