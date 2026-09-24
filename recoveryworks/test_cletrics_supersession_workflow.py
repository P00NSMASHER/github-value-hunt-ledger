from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.integrations.cletrics_continuous import run_continuous_cletrics_scan
from recoveryworks.integrations.cletrics_registry import CletricsReceiptRegistry
from recoveryworks.integrations.cletrics_supersession_workflow import (
    apply_cloud_supersession,
    approve_cloud_supersession_preview,
    prepare_cloud_supersession_preview,
)
from recoveryworks.test_cletrics_final_cycle import make_bundle, write_rates


class ReviewedCloudSupersessionTests(unittest.TestCase):
    def test_changed_rate_supersedes_old_finding_without_double_counting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv", "2.00")
            state = root / "ledger.json"
            registry = root / "receipts.json"
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "cletrics_bundle": "bundle.zip",
                    "rates_csv": "rates.csv",
                    "charge_source_verified": True,
                    "meter_source_verified": True,
                    "rate_source_verified": True,
                },
            }
            first = run_continuous_cletrics_scan(
                config,
                state_path=state,
                registry_path=registry,
                base_dir=root,
            )
            self.assertEqual(first.scan.report.totals["validated_cents"], 1000)
            old_id = first.scan.added_finding_ids[0]

            write_rates(root / "rates.csv", "1.80")
            changed = run_continuous_cletrics_scan(
                config,
                state_path=state,
                registry_path=registry,
                base_dir=root,
            )
            candidate = changed.supersession_candidates[0]
            preview = prepare_cloud_supersession_preview(
                candidate,
                config,
                state_path=state,
                base_dir=root,
            )
            self.assertEqual(len(preview.bindings), 1)
            self.assertEqual(preview.bindings[0].incumbent_finding_id, old_id)
            self.assertIsNotNone(preview.bindings[0].replacement_finding_id)

            approval = approve_cloud_supersession_preview(
                preview,
                reviewer_id="reviewer-supersession",
                review_note="Reviewed amended cloud rate authority.",
                approved_at="2026-09-25T04:00:00Z",
            )
            applied = apply_cloud_supersession(
                preview,
                approval,
                state_path=state,
                registry_path=registry,
            )
            self.assertEqual(applied.superseded_finding_ids, (old_id,))
            self.assertEqual(len(applied.replacement_finding_ids), 1)
            self.assertEqual(applied.report.totals["validated_cents"], 1200)
            self.assertEqual(applied.report.totals["potential_cents"], 1200)
            self.assertEqual(applied.report.totals["superseded_cents"], 1000)
            self.assertEqual(
                applied.report.case_states["SUPERSEDED"]["potential_cents"], 1000
            )
            receipts = CletricsReceiptRegistry(registry).receipts()
            self.assertEqual(len(receipts), 1)
            self.assertEqual(
                receipts[0].job_fingerprint,
                candidate.proposed_job_fingerprint,
            )

    def test_authorized_incumbent_cannot_use_supersession_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv", "2.00")
            state = root / "ledger.json"
            registry = root / "receipts.json"
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "cletrics_bundle": "bundle.zip",
                    "rates_csv": "rates.csv",
                    "charge_source_verified": True,
                    "meter_source_verified": True,
                    "rate_source_verified": True,
                },
            }
            first = run_continuous_cletrics_scan(
                config,
                state_path=state,
                registry_path=registry,
                base_dir=root,
            )
            from recoveryworks.store import LocalBundleStore
            store = LocalBundleStore(state)
            ledger = store.load()
            finding_id = first.scan.added_finding_ids[0]
            ledger.approve(
                finding_id,
                "reviewer",
                "approved",
                occurred_at="2026-09-25T03:58:00Z",
            )
            ledger.authorize(
                finding_id,
                "auth-1",
                occurred_at="2026-09-25T03:59:00Z",
            )
            store.save(ledger, expected_head_hash=first.scan.state_head_hash)

            write_rates(root / "rates.csv", "1.80")
            changed = run_continuous_cletrics_scan(
                config,
                state_path=state,
                registry_path=registry,
                base_dir=root,
            )
            preview = prepare_cloud_supersession_preview(
                changed.supersession_candidates[0],
                config,
                state_path=state,
                base_dir=root,
            )
            with self.assertRaisesRegex(
                ValueError, "only REVIEW/VALIDATED incumbents"
            ):
                approve_cloud_supersession_preview(
                    preview,
                    reviewer_id="reviewer-2",
                    review_note="try replacement",
                    approved_at="2026-09-25T04:01:00Z",
                )


if __name__ == "__main__":
    unittest.main()
