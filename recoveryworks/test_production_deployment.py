from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.production_deployment import (
    build_production_deployment_contract,
    check_production_health,
    check_production_readiness,
    render_production_compose,
)


class ProductionDeploymentPackagingTests(unittest.TestCase):
    def setup(self, root: Path) -> dict:
        config = root / "config"
        inputs = root / "inputs"
        state = root / "private" / "state"
        reports = root / "private" / "reports"
        for path in (config, inputs, state, reports):
            path.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            state.chmod(0o700)
            reports.chmod(0o700)

        (inputs / "focus.csv").write_text(
            "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
            "BilledCost,BillingCurrency,ResourceId\n"
            "Amazon Web Services,acct-1,EC2,2026-08-31T00:00:00Z,"
            "40.00,USD,i-1\n",
            encoding="utf-8",
        )
        (inputs / "meter.csv").write_text(
            "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
            "M-1,10,i-1,EC2,2026-08-31\n",
            encoding="utf-8",
        )
        (inputs / "rates.csv").write_text(
            "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
            "Included_Units,Unit_Rate\n"
            "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",
            encoding="utf-8",
        )
        pilot = {
            "schema": 1,
            "deployment_id": "production-pilot",
            "client_id": "client-prod",
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
                "exported_at": "2026-09-01T12:00:00Z",
            },
            "cletrics": {
                "focus_csv": str(inputs / "focus.csv"),
                "meter_csv": str(inputs / "meter.csv"),
                "release": "prod-test",
                "commit": "a" * 40,
            },
            "recoveryos": {
                "rates_csv": str(inputs / "rates.csv"),
                "bundle_path": str(state / "bundle.zip"),
                "ledger_path": str(state / "ledger.json"),
                "receipt_registry_path": str(state / "receipts.json"),
                "report_path": str(reports / "assurance.json"),
            },
        }
        (config / "pilot.json").write_text(
            __import__("json").dumps(pilot), encoding="utf-8"
        )
        return {
            "schema": 1,
            "pilot_spec": str(config / "pilot.json"),
            "service": {
                "image_ref": "registry.example/recoveryworks@sha256:" + "b" * 64,
                "user": "65532:65532",
                "command": [
                    "python","-m","recoveryworks.pilot_runner",
                    "--spec","/config/pilot.json",
                    "--base-dir","/workspace",
                ],
                "read_only_root_filesystem": True,
                "privileged": False,
                "host_network": False,
                "network_disabled": True,
                "no_new_privileges": True,
                "cap_drop_all": True,
                "provider_write_credentials": False,
                "remediation_execution_enabled": False,
                "external_actions_enabled": False,
            },
            "volumes": {
                "config": {
                    "host_path": str(config),
                    "container_path": "/config",
                    "read_only": True,
                    "private_required": False,
                },
                "inputs": {
                    "host_path": str(inputs),
                    "container_path": "/inputs",
                    "read_only": True,
                    "private_required": False,
                },
                "state": {
                    "host_path": str(state),
                    "container_path": "/state",
                    "read_only": False,
                    "private_required": True,
                },
                "reports": {
                    "host_path": str(reports),
                    "container_path": "/reports",
                    "read_only": False,
                    "private_required": True,
                },
            },
        }

    def test_health_and_readiness_validate_without_starting_container(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            deployment = build_production_deployment_contract(
                self.setup(root), base_dir=root
            )
            health = check_production_health(deployment)
            ready = check_production_readiness(deployment)
            self.assertTrue(health.passed)
            self.assertTrue(ready.passed)
            self.assertFalse(deployment.provisioning_enabled)
            self.assertFalse(deployment.container_start_enabled)
            compose = render_production_compose(deployment)
            self.assertIn("network_mode: none", compose)
            self.assertIn("read_only: true", compose)
            self.assertIn("cap_drop:", compose)
            self.assertIn("no-new-privileges:true", compose)
            self.assertIn("condition: service_completed_successfully", compose)

    def test_unpinned_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup(root)
            spec["service"]["image_ref"] = "registry.example/recoveryworks:latest"
            with self.assertRaisesRegex(ValueError, "pinned by sha256"):
                build_production_deployment_contract(spec, base_dir=root)

    def test_privileged_or_networked_service_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup(root)
            spec["service"]["privileged"] = True
            with self.assertRaisesRegex(ValueError, "privileged must be false"):
                build_production_deployment_contract(spec, base_dir=root)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup(root)
            spec["service"]["network_disabled"] = False
            with self.assertRaisesRegex(ValueError, "network_disabled must be true"):
                build_production_deployment_contract(spec, base_dir=root)

    def test_shared_or_nonprivate_state_volumes_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup(root)
            spec["volumes"]["reports"]["host_path"] = spec["volumes"]["state"]["host_path"]
            with self.assertRaisesRegex(ValueError, "cannot share host paths"):
                build_production_deployment_contract(spec, base_dir=root)
        if os.name != "nt":
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                spec = self.setup(root)
                Path(spec["volumes"]["state"]["host_path"]).chmod(0o755)
                with self.assertRaisesRegex(PermissionError, "too permissive"):
                    build_production_deployment_contract(spec, base_dir=root)


if __name__ == "__main__":
    unittest.main()
