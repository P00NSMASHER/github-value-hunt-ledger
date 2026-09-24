from recoveryworks.test_support import source_hash as H
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    freeze_population,
    freeze_truth,
    make_finding,
)
from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.freight_io import (
    load_freight_audit_result_bundle,
    load_freight_truth_manifest,
)


def truth_payload(*, validated=True):
    population = freeze_population(
        "buyer-1",
        "BU-1",
        "all invoices",
        (PopulationRow(
            invoice_id="INV-1",
            shipment_id="SHIP-1",
            customer_id="CUST-1",
            carrier_id="Carrier A",
            currency="USD",
            source_hash=H("invoice-source"),
        ),),
    )
    authority = AuthorityRef(
        authority_id="AUTH-1",
        buyer_id="buyer-1",
        business_unit="BU-1",
        customer_id="CUST-1",
        carrier_id="Carrier A",
        currency="USD",
        source_hash=H("contract-source"),
    )
    finding = make_finding(
        finding_id="F-1",
        buyer_id="buyer-1",
        business_unit="BU-1",
        invoice_id="INV-1",
        shipment_id="SHIP-1",
        customer_id="CUST-1",
        carrier_id="Carrier A",
        currency="USD",
        authority_id="AUTH-1" if validated else None,
        expected_cents=10000,
        actual_cents=15000,
        status="VALIDATED" if validated else "REVIEW",
    )
    truth = freeze_truth(
        population,
        (authority,) if validated else (),
        (finding,),
    )
    return asdict(truth)


class FreightImportTests(unittest.TestCase):
    def test_truth_manifest_import_preserves_validated_authority(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "truth-manifest.json"
            path.write_text(json.dumps(truth_payload()), encoding="utf-8")
            batch = load_freight_truth_manifest(path)

            self.assertEqual(batch.buyer_id, "buyer-1")
            self.assertEqual(len(batch.observations), 1)
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 5000)
            self.assertEqual(finding.metadata["freight_finding_id"], "F-1")

    def test_review_freight_finding_remains_review(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "truth-manifest.json"
            path.write_text(json.dumps(truth_payload(validated=False)), encoding="utf-8")
            batch = load_freight_truth_manifest(path)
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)

    def test_tampered_finding_proof_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            payload = truth_payload()
            payload["findings"][0]["actual_cents"] = 999999
            path = Path(d) / "truth-manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_freight_truth_manifest(path)

    def test_tampered_truth_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            payload = truth_payload()
            payload["truth_hash"] = "bad"
            path = Path(d) / "truth-manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_freight_truth_manifest(path)

    def test_audit_result_bundle_verifies_truth_entry_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            truth_raw = (json.dumps(truth_payload(), sort_keys=True) + "\n").encode()
            manifest = {
                "schema_version": 1,
                "product": "Freight Recovery",
                "bundle_type": "AUDIT_RESULT",
                "entries": [{
                    "path": "truth-manifest.json",
                    "size_bytes": len(truth_raw),
                    "sha256": hashlib.sha256(truth_raw).hexdigest(),
                }],
            }
            bundle = root / "audit.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("truth-manifest.json", truth_raw)
                archive.writestr(
                    "RESULT_BUNDLE_MANIFEST.json",
                    json.dumps(manifest),
                )

            imported = load_freight_audit_result_bundle(bundle)
            finding = RecoveryEngine().evaluate(imported.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)

            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("truth-manifest.json", truth_raw + b" ")
                archive.writestr(
                    "RESULT_BUNDLE_MANIFEST.json",
                    json.dumps(manifest),
                )
            with self.assertRaises(ValueError):
                load_freight_audit_result_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
