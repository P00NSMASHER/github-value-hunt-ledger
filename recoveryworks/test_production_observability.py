from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.production_observability import (
    ProductionFailureCode,
    ProductionRunHistoryStore,
    build_success_observability,
    classify_production_failure,
    write_observability_bundle,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.pilot_runner import run_local_pilot


def pilot_spec(root: Path) -> dict:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "AWS,acct-1,compute,2026-08-31T00:00:00Z,40.00,USD,i-1\n",
        encoding="utf-8",
    )
    (inputs / "meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-1,10,i-1,compute,2026-08-31\n",
        encoding="utf-8",
    )
    (inputs / "rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "AWS,compute,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    return {
        "schema": 1,
        "deployment_id": "obs-pilot",
        "client_id": "client-1",
        "currency": "USD",
        "provider": "aws",
        "security": {
            "cloud_access_mode": "READ_ONLY",
            "recoveryos_provider_write_credentials": False,
            "remediation_execution_enabled": False,
            "external_actions_enabled": False,
            "private_state_required": True,
        },
        "period": {
            "start": "2026-08-01",
            "end": "2026-08-31",
            "exported_at": "2026-09-01T01:00:00Z",
        },
        "cletrics": {
            "focus_csv": "inputs/focus.csv",
            "meter_csv": "inputs/meter.csv",
            "release": "test",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": "inputs/rates.csv",
            "verification": {
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
            },
            "bundle_path": "private/bundle.zip",
            "ledger_path": "private/ledger.json",
            "receipt_registry_path": "private/receipts.json",
            "report_path": "private/pilot-report.json",
        },
    }


class ProductionObservabilityTests(unittest.TestCase):
    def pilot(self, root: Path):
        return run_local_pilot(pilot_spec(root), base_dir=root)

    def test_success_bundle_exposes_metrics_events_and_private_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, metrics, events, alerts = build_success_observability(
                run_id="run-001",
                deployment_id="prod-001",
                pilot=self.pilot(root),
                container_build_manifest_proof_hash="a" * 64,
                started_at="2026-09-24T12:00:00Z",
                completed_at="2026-09-24T12:01:00Z",
            )
            self.assertEqual(metrics.recovery["validated_cents"], 1000)
            self.assertEqual(len(events), 5)
            self.assertEqual(events[-1].previous_hash, events[-2].event_hash)
            paths = write_observability_bundle(
                manifest=manifest,
                metrics=metrics,
                events=events,
                alerts=alerts,
                directory=root / "private" / "obs",
            )
            self.assertTrue(all(private_permissions_verified(path) for path in paths))
            history = ProductionRunHistoryStore(
                root / "private" / "run-history.json"
            )
            head = history.record(
                manifest, recorded_at="2026-09-24T12:02:00Z"
            )
            self.assertEqual(len(head), 64)
            self.assertEqual(len(history.entries()), 1)
            self.assertTrue(private_permissions_verified(history.path))

    def test_history_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, *_ = build_success_observability(
                run_id="run-001",
                deployment_id="prod-001",
                pilot=self.pilot(root),
                container_build_manifest_proof_hash="b" * 64,
                started_at="2026-09-24T12:00:00Z",
                completed_at="2026-09-24T12:01:00Z",
            )
            history = ProductionRunHistoryStore(root / "private" / "history.json")
            history.record(manifest, recorded_at="2026-09-24T12:02:00Z")
            payload = json.loads(history.path.read_text(encoding="utf-8"))
            payload["entries"][0]["run_id"] = "tampered"
            history.path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch|chain mismatch"):
                history.entries()

    def test_failure_taxonomy_is_stable(self):
        self.assertIs(
            classify_production_failure(
                ValueError("customer authorization has expired")
            ),
            ProductionFailureCode.AUTHORIZATION_INVALID,
        )
        self.assertIs(
            classify_production_failure(
                ValueError("provider scope does not match")
            ),
            ProductionFailureCode.PROVIDER_SCOPE_MISMATCH,
        )
        self.assertIs(
            classify_production_failure(
                ValueError("bundle hash mismatch")
            ),
            ProductionFailureCode.EVIDENCE_INTEGRITY,
        )


if __name__ == "__main__":
    unittest.main()
