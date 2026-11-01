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


    def test_import_rejects_authority_identity_mismatch_even_with_rehashed_manifest(self):
        from freight.contracts import canonical_hash
        for field, different in (
            ("customer_id", "UNRELATED-CUSTOMER"),
            ("carrier_id", "UNRELATED-CARRIER"),
            ("currency", "EUR"),
        ):
            with self.subTest(field=field):
                forged = truth_payload()
                forged["authorities"][0][field] = different
                # A manifest-level SHA is not a trusted identity proof: simulate
                # a reserializing importer that recomputes its own truth hash.
                forged["truth_hash"] = canonical_hash({
                    "schema": 3,
                    **{key: value for key, value in forged.items() if key != "truth_hash"}
                })
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "truth-manifest.json"
                    source.write_text(json.dumps(forged), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "authority identity mismatch"):
                        load_freight_truth_manifest(source)

    def test_import_rejects_duplicate_finding_ids_even_when_manifest_rehashed(self):
        from freight.contracts import canonical_hash
        forged=truth_payload()
        forged["findings"] = list(forged["findings"]) + [dict(forged["findings"][0])]
        forged["truth_hash"]=canonical_hash({
            "schema":3,
            **{key:value for key,value in forged.items() if key!="truth_hash"}
        })
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"truth-manifest.json"
            source.write_text(json.dumps(forged),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"duplicate freight finding_id"):
                load_freight_truth_manifest(source)

    def test_direct_bridge_refuses_changed_amount_or_wrong_authority(self):
        from dataclasses import replace
        from recoveryworks.branches.freight import from_freight_finding
        from freight.contracts import AuthorityRef
        payload=truth_payload()
        from freight.contracts import Finding
        finding=Finding(**payload["findings"][0])
        authority=AuthorityRef(**payload["authorities"][0])
        valid=RecoveryEngine().evaluate(from_freight_finding(finding,authority))
        self.assertIs(valid.state, FindingState.VALIDATED)
        with self.assertRaisesRegex(ValueError,"proof hash mismatch"):
            from_freight_finding(replace(finding,actual_cents=999999),authority)
        for field,different in (("customer_id","DIFFERENT-CUSTOMER"),
                                ("carrier_id","DIFFERENT-CARRIER"),
                                ("currency","EUR")):
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"authority identity mismatch"):
                from_freight_finding(finding,replace(authority,**{field:different}))
        # With no evidence reference, the consumer must HOLD, not imply a claim.
        held=RecoveryEngine().evaluate(from_freight_finding(finding,None))
        self.assertIs(held.state,FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
