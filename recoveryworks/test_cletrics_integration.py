from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from recoveryworks.branches.cloud import audit_cloud_billing
from recoveryworks.engine import RecoveryEngine
from recoveryworks.integrations.cletrics import (
    CLETRICS_BUNDLE_TYPE,
    load_cletrics_bundle,
)
from recoveryworks.models import FindingState
from recoveryworks.runner import run_scan360_config


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bundle(
    path: Path,
    *,
    client_id: str = "client-1",
    charge_csv: bytes | None = None,
    meter_csv: bytes | None = None,
    manifest_charge_hash: str | None = None,
) -> Path:
    charges = charge_csv or (
        b"Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,"
        b"Actual_Amount,Provider_Line_ID,Resource_ID,Region\n"
        b"C-1,AWS,acct-1,compute,2026-08-31,40.00,li-123,"
        b"i-abc,us-east-1\n"
    )
    meter = meter_csv or (
        b"Charge_ID,Meter_Record_ID,Usage_Units,Resource_ID\n"
        b"C-1,M-1,4,i-abc\n"
        b"C-1,M-2,6,i-abc\n"
    )
    source_billing_hash = _sha(
        b"raw-provider-billing-export"
    )
    source_meter_hash = _sha(
        b"raw-provider-meter-export"
    )
    manifest = {
        "schema": 1,
        "bundle_type": CLETRICS_BUNDLE_TYPE,
        "client_id": client_id,
        "provider": "aws",
        "billing_account_id": "payer-123",
        "currency": "USD",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "exported_at": "2026-09-23T21:00:00-04:00",
        "cletrics": {
            "release": "phase1-test",
            "commit": "a" * 40,
            "image_digest": "sha256:" + "b" * 64,
        },
        "entries": [
            {
                "role": "invoice_charges",
                "path": "billing/charges.csv",
                "sha256": (
                    manifest_charge_hash
                    or _sha(charges)
                ),
                "size_bytes": len(charges),
                "transformation_id": (
                    "cletrics-focus-to-recoveryos-charge-v1"
                ),
                "source": {
                    "kind": "provider_billing_export",
                    "locator": (
                        "aws-cur://payer-123/2026-08"
                    ),
                    "sha256": source_billing_hash,
                    "acquired_at": (
                        "2026-09-23T20:55:00-04:00"
                    ),
                },
            },
            {
                "role": "meter_usage",
                "path": "usage/meter.csv",
                "sha256": _sha(meter),
                "size_bytes": len(meter),
                "transformation_id": (
                    "cletrics-meter-to-recoveryos-v1"
                ),
                "source": {
                    "kind": "provider_meter_export",
                    "locator": (
                        "cloudwatch://acct-1/2026-08"
                    ),
                    "sha256": source_meter_hash,
                    "acquired_at": (
                        "2026-09-23T20:56:00-04:00"
                    ),
                },
            },
        ],
    }
    manifest_raw = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr("manifest.json", manifest_raw)
        archive.writestr(
            "billing/charges.csv", charges
        )
        archive.writestr("usage/meter.csv", meter)
    return path


class CletricsBundleTests(unittest.TestCase):
    def test_bundle_maps_billing_and_meter_to_existing_models(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            path = _bundle(Path(d) / "cletrics.zip")
            bundle = load_cletrics_bundle(
                path,
                charge_source_verified=True,
                meter_source_verified=True,
            )

            self.assertEqual(
                bundle.client_id, "client-1"
            )
            self.assertEqual(bundle.provider, "aws")
            self.assertEqual(bundle.currency, "USD")
            self.assertEqual(
                len(bundle.bundle_sha256), 64
            )
            self.assertEqual(
                len(bundle.manifest_sha256), 64
            )

            self.assertEqual(len(bundle.charges), 1)
            charge = bundle.charges[0]
            self.assertEqual(charge.charge_id, "C-1")
            self.assertEqual(
                charge.counterparty_id, "AWS"
            )
            self.assertEqual(
                charge.account_id, "acct-1"
            )
            self.assertEqual(
                charge.service_id, "compute"
            )
            self.assertEqual(
                charge.actual_cents, 4000
            )
            self.assertTrue(charge.verified)
            self.assertTrue(
                charge.source_locator.endswith(
                    "billing/charges.csv#row=2"
                )
            )
            self.assertEqual(
                charge.metadata["provider_fields"][
                    "Provider_Line_ID"
                ],
                "li-123",
            )
            self.assertEqual(
                charge.metadata[
                    "provider_source_locator"
                ],
                "aws-cur://payer-123/2026-08",
            )

            self.assertEqual(len(bundle.usage), 1)
            usage = bundle.usage[0]
            self.assertEqual(
                usage.charge_id, "C-1"
            )
            self.assertEqual(usage.units, "10")
            self.assertTrue(usage.verified)
            self.assertEqual(
                usage.metadata["meter_record_count"], 2
            )
            self.assertEqual(
                usage.metadata[
                    "provider_source_locator"
                ],
                "cloudwatch://acct-1/2026-08",
            )

    def test_bundle_integrity_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            path = _bundle(
                Path(d) / "tampered.zip",
                manifest_charge_hash=_sha(
                    b"different-normalized-charge-file"
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "hash mismatch"
            ):
                load_cletrics_bundle(path)

    def test_duplicate_meter_identity_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            meter = (
                b"Charge_ID,Meter_Record_ID,"
                b"Usage_Units\n"
                b"C-1,M-1,4\n"
                b"C-1,M-1,6\n"
            )
            path = _bundle(
                Path(d) / "duplicate-meter.zip",
                meter_csv=meter,
            )
            with self.assertRaisesRegex(
                ValueError, "duplicate meter record"
            ):
                load_cletrics_bundle(path)

    def test_bundle_cannot_self_verify_evidence(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            path = _bundle(
                Path(d) / "unverified.zip"
            )
            bundle = load_cletrics_bundle(path)
            self.assertFalse(
                bundle.charges[0].verified
            )
            self.assertFalse(
                bundle.usage[0].verified
            )

            from recoveryworks.branches.contract_billing import (
                ContractRate,
            )

            rate = ContractRate(
                counterparty_id="AWS",
                service_id="compute",
                effective_from="2026-01-01",
                effective_to=None,
                fixed_cents=1000,
                included_units="0",
                unit_rate_micros=2_000_000,
                source_hash=_sha(
                    b"reviewed-contract"
                ),
                source_locator=(
                    "file://reviewed-rates.csv#row=2"
                ),
                verified=True,
            )
            batch = audit_cloud_billing(
                client_id="client-1",
                charges=bundle.charges,
                rates=(rate,),
                usage=bundle.usage,
            )
            finding = RecoveryEngine().evaluate(
                batch.observations[0]
            )
            self.assertIsNotNone(finding)
            self.assertIs(
                finding.state, FindingState.REVIEW
            )


class CletricsRunnerTests(unittest.TestCase):
    def test_scan360_bundle_uses_reviewed_rates_and_cloud_math(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _bundle(root / "cletrics.zip")
            (root / "cloud_rates.csv").write_text(
                "Counterparty,Service_ID,"
                "Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,"
                "Unit_Rate\n"
                "AWS,compute,2026-01-01,,"
                "10.00,0,2.00\n",
                encoding="utf-8",
            )
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "cletrics_bundle": (
                        "cletrics.zip"
                    ),
                    "rates_csv": (
                        "cloud_rates.csv"
                    ),
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "meter_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(
                config,
                state_path=state,
                base_dir=root,
            )
            self.assertEqual(first.exceptions, ())
            self.assertEqual(
                len(first.added_finding_ids), 1
            )
            self.assertEqual(
                first.report.totals[
                    "validated_cents"
                ],
                1000,
            )
            self.assertEqual(
                first.report.branches["cloud"][
                    "validated_cents"
                ],
                1000,
            )

            second = run_scan360_config(
                config,
                state_path=state,
                base_dir=root,
            )
            self.assertEqual(
                second.added_finding_ids, ()
            )
            self.assertEqual(
                second.state_head_hash,
                first.state_head_hash,
            )
            self.assertEqual(
                second.report.as_dict(),
                first.report.as_dict(),
            )

    def test_scan360_rejects_bundle_scope_mismatch(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _bundle(
                root / "wrong-client.zip",
                client_id="someone-else",
            )
            (root / "cloud_rates.csv").write_text(
                "Counterparty,Service_ID,"
                "Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,"
                "Unit_Rate\n"
                "AWS,compute,2026-01-01,,"
                "10.00,0,2.00\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError, "client_id"
            ):
                run_scan360_config(
                    {
                        "client_id": "client-1",
                        "currency": "USD",
                        "cloud": {
                            "cletrics_bundle": (
                                "wrong-client.zip"
                            ),
                            "rates_csv": (
                                "cloud_rates.csv"
                            ),
                        },
                    },
                    state_path=root / "ledger.json",
                    base_dir=root,
                )


if __name__ == "__main__":
    unittest.main()
