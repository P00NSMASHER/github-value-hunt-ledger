from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.environment_activation import (
    build_activation_adapter,
    build_credential_scope_attestation,
    build_environment_state_discovery,
    simulate_external_environment_activation,
)
from recoveryworks.production_admission import build_production_admission_gate
from recoveryworks.test_production_admission import ProductionAdmissionTests


class EnvironmentActivationSimulationTests(unittest.TestCase):
    def release_and_admission(self, root: Path):
        fixture = ProductionAdmissionTests()
        release,promotion,security,dr,build = fixture.fixture(root)
        admission = build_production_admission_gate(
            release,promotion,security,dr,build,fixture.package_integrity,
            admitted_at="2026-09-24T13:11:00Z",
        )
        return release,admission

    def test_aws_azure_gcp_simulation_is_provider_neutral_and_non_mutating(self):
        for provider, permission in (
            ("aws","compute:describe"),
            ("azure","resource:read"),
            ("gcp","resource:read"),
        ):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as d:
                release,admission=self.release_and_admission(Path(d))
                credential=build_credential_scope_attestation(
                    provider=provider,account_id=f"{provider}-acct",
                    principal_id="read-only-principal",
                    granted_permissions=(permission,"billing:read"),
                    observed_at="2026-09-24T13:12:00Z",
                    source_hash="1"*64,
                    source_locator=f"{provider}://credential-scope",
                    verified=True,
                )
                discovery=build_environment_state_discovery(
                    provider=provider,account_id=f"{provider}-acct",
                    environment_id=f"{provider}-prod",
                    observed_at="2026-09-24T13:13:00Z",
                    current_release_id=None,current_image_digest=None,
                    resource_summary={"resources":3,"mode":"read-only-discovery"},
                    source_hash="2"*64,
                    source_locator=f"{provider}://environment-state",
                    verified=True,
                )
                adapter=build_activation_adapter(credential,discovery)
                simulation=simulate_external_environment_activation(
                    release,admission,credential,discovery,adapter,
                    simulated_at="2026-09-24T13:14:00Z",
                )
                self.assertEqual(simulation.as_dict()["state"],"SIMULATION_ONLY")
                self.assertFalse(simulation.live_mutation_allowed)
                self.assertFalse(simulation.deployment_performed)
                self.assertFalse(simulation.provider_api_calls_performed)

    def test_mutation_permission_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"mutation-capable"):
            build_credential_scope_attestation(
                provider="aws",account_id="acct",principal_id="principal",
                granted_permissions=("compute:describe","compute:write"),
                observed_at="2026-09-24T13:12:00Z",
                source_hash="1"*64,source_locator="aws://scope",verified=True,
            )

    def test_provider_or_account_mismatch_fails_closed(self):
        credential=build_credential_scope_attestation(
            provider="aws",account_id="acct-a",principal_id="principal",
            granted_permissions=("compute:describe",),
            observed_at="2026-09-24T13:12:00Z",
            source_hash="1"*64,source_locator="aws://scope",verified=True,
        )
        discovery=build_environment_state_discovery(
            provider="azure",account_id="acct-b",environment_id="prod",
            observed_at="2026-09-24T13:13:00Z",
            current_release_id=None,current_image_digest=None,
            resource_summary={"resources":1},source_hash="2"*64,
            source_locator="azure://state",verified=True,
        )
        with self.assertRaisesRegex(ValueError,"provider mismatch"):
            build_activation_adapter(credential,discovery)


if __name__=="__main__":
    unittest.main()
