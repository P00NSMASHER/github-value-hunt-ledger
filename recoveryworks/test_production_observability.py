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
from recoveryworks.test_pilot_runner import LocalPilotRunnerTests
from recoveryworks.pilot_runner import run_local_pilot


class ProductionObservabilityTests(unittest.TestCase):
    def pilot(self, root: Path):
        return run_local_pilot(
            LocalPilotRunnerTests().build_spec(root),
            base_dir=root,
        )

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
