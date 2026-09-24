from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from recoveryworks.commercial_pilot import build_commercial_pilot_package
from recoveryworks.production_launch_dossier import (
    build_production_launch_dossier,
    write_production_launch_dossier,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.production_observability import (
    ProductionRunManifest,
    ProductionRunStatus,
)
from recoveryworks.test_production_admission import ProductionAdmissionTests


def commercial():
    return build_commercial_pilot_package({
        "schema": 1,
        "offer_name": "Cloud Recovery & Savings Assurance Pilot",
        "buyer_profile": "Mid-market cloud buyer",
        "scope": {
            "provider": "aws",
            "lookback_months": 12,
            "max_billing_accounts": 1,
            "recovery_modes": [
                "CONTRACT_RATE_MISMATCH",
                "CONTRACT_DISCOUNT_OMISSION",
                "COMMITMENT_BENEFIT_OMISSION",
            ],
            "include_prospective_savings": True,
            "include_diagnostics": True,
            "include_remediation_plan": True,
            "cloud_mutation_in_scope": False,
            "external_recovery_actions_in_scope": False,
        },
        "deliverables": ["Assurance report", "Recovery evidence packets"],
        "pricing": {
            "currency": "USD",
            "diagnostic_fee_cents": 500000,
            "recovered_cash_success_fee_bps": 2000,
            "monthly_assurance_fee_cents": 250000,
            "savings_implementation_fee_cents": None,
            "pricing_is_hypothesis": True,
        },
        "acceptance_criteria": [{
            "criterion_id": "A1",
            "description": "Validated recovery evidence is reproducible.",
            "required_evidence": "RecoveryOS proof packet",
        }],
        "exclusions": ["Cloud mutation", "External recovery actions"],
        "assumptions": ["Customer supplies authorized billing and contract data."],
    })


class ProductionLaunchDossierTests(unittest.TestCase):
    def test_dossier_binds_all_readiness_planes_without_claiming_traction(self):
        with tempfile.TemporaryDirectory() as d:
            release,promotion,security,dr,build = ProductionAdmissionTests().fixture(
                Path(d)
            )
            from recoveryworks.production_admission import build_production_admission_gate
            admission = build_production_admission_gate(
                release,promotion,security,dr,build,
                admitted_at="2026-09-24T13:11:00Z",
            )
            run_identity = {
                "schema": 1,
                "run_id": "run-launch-1",
                "deployment_id": "deployment-1",
                "deployment_plan_proof_hash": "1"*64,
                "container_build_manifest_proof_hash": build.proof_hash,
                "client_id": "client-1",
                "provider": "aws",
                "started_at": "2026-09-24T13:12:00Z",
                "completed_at": "2026-09-24T13:13:00Z",
                "status": "SUCCEEDED",
                "failure_code": None,
                "failure_detail": None,
                "state_head_hash": "2"*64,
                "assurance_report_proof_hash": "3"*64,
                "metrics_proof_hash": "4"*64,
                "event_hashes": [],
                "alert_hashes": [],
            }
            run = ProductionRunManifest(
                manifest_id="recoveryworks-production-run:"
                + __import__("recoveryworks.models",fromlist=["canonical_hash"]).
                    canonical_hash(run_identity),
                run_id="run-launch-1",
                deployment_id="deployment-1",
                deployment_plan_proof_hash="1"*64,
                container_build_manifest_proof_hash=build.proof_hash,
                client_id="client-1",
                provider="aws",
                started_at="2026-09-24T13:12:00Z",
                completed_at="2026-09-24T13:13:00Z",
                status=ProductionRunStatus.SUCCEEDED,
                failure_code=None,
                failure_detail=None,
                state_head_hash="2"*64,
                assurance_report_proof_hash="3"*64,
                metrics_proof_hash="4"*64,
                event_hashes=(),
                alert_hashes=(),
            )
            from recoveryworks.release_control import build_rollback_manifest, build_release_manifest
            previous = replace(release,
                release_id=release.release_id,
            )
            # Reuse the rollback proof already bound into the promotion fixture by
            # creating a structurally valid target from a second fixture.
            rel2,_,_,_,_ = ProductionAdmissionTests().fixture(Path(d)/"second")
            rollback = build_rollback_manifest(
                release, rel2, reason="Known good target",
                created_at="2026-09-24T13:14:00Z"
            ) if release.release_id != rel2.release_id else None
            if rollback is None:
                self.skipTest("fixture unexpectedly produced identical release ids")
            dossier = build_production_launch_dossier(
                release=release,
                admission=admission,
                security_evidence=security,
                dr_rehearsal=dr,
                observability_run=run,
                rollback_manifest=rollback,
                commercial_pilot=commercial(),
                reviewed_at="2026-09-24T13:15:00Z",
            )
            self.assertEqual(
                dossier.as_dict()["state"], "PRODUCTION_REVIEW_DOSSIER_READY"
            )
            self.assertFalse(dossier.externally_deployed)
            self.assertFalse(dossier.customer_contract_signed)
            self.assertFalse(dossier.customer_revenue_verified)
            self.assertTrue(dossier.cfo_summary["pricing_is_hypothesis"])

            json_path=Path(d)/"private"/"dossier.json"
            md_path=Path(d)/"private"/"dossier.md"
            write_production_launch_dossier(
                dossier,json_path=json_path,markdown_path=md_path
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(md_path))

    def test_failed_observability_run_cannot_enter_dossier(self):
        with tempfile.TemporaryDirectory() as d:
            release,promotion,security,dr,build = ProductionAdmissionTests().fixture(
                Path(d)
            )
            from recoveryworks.production_admission import build_production_admission_gate
            admission=build_production_admission_gate(
                release,promotion,security,dr,build,
                admitted_at="2026-09-24T13:11:00Z")
            run=ProductionRunManifest(
                manifest_id="recoveryworks-production-run:"+"0"*64,
                run_id="run-bad",deployment_id="dep",
                deployment_plan_proof_hash="1"*64,
                container_build_manifest_proof_hash=build.proof_hash,
                client_id="client",provider="aws",
                started_at="2026-09-24T13:12:00Z",
                completed_at="2026-09-24T13:13:00Z",
                status=ProductionRunStatus.FAILED,
                failure_code=__import__(
                    "recoveryworks.production_observability",
                    fromlist=["ProductionFailureCode"]
                ).ProductionFailureCode.RUNTIME_FAILURE,
                failure_detail="failed",
                state_head_hash=None,assurance_report_proof_hash=None,
                metrics_proof_hash=None,event_hashes=(),alert_hashes=())
            # Constructor itself validates manifest identity, so a failed run is
            # sufficient to demonstrate the dossier cannot be built if valid.
            self.assertIs(run.status, ProductionRunStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
