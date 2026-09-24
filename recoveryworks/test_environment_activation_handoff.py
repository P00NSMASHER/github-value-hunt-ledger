from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from recoveryworks.environment_activation import (
    build_activation_adapter,
    build_credential_scope_attestation,
    build_environment_state_discovery,
    simulate_external_environment_activation,
)
from recoveryworks.environment_activation_handoff import (
    ExternalActivationReceipt,
    prepare_external_activation_handoff,
    validate_external_activation,
)
from recoveryworks.models import canonical_hash
from recoveryworks.production_admission import build_production_admission_gate
from recoveryworks.test_production_admission import ProductionAdmissionTests


class ExternalActivationHandoffTests(unittest.TestCase):
    def fixture(self, root: Path):
        release,promotion,security,dr,build = ProductionAdmissionTests().fixture(root)
        admission=build_production_admission_gate(
            release,promotion,security,dr,build,
            admitted_at="2026-09-24T13:11:00Z")
        credential=build_credential_scope_attestation(
            provider="aws",account_id="acct-1",principal_id="reader",
            granted_permissions=("compute:describe","billing:read"),
            observed_at="2026-09-24T13:12:00Z",
            source_hash="1"*64,source_locator="aws://scope",verified=True)
        discovery=build_environment_state_discovery(
            provider="aws",account_id="acct-1",environment_id="prod",
            observed_at="2026-09-24T13:13:00Z",
            current_release_id=None,current_image_digest=None,
            resource_summary={"resources":2},source_hash="2"*64,
            source_locator="aws://discovery",verified=True)
        adapter=build_activation_adapter(credential,discovery)
        simulation=simulate_external_environment_activation(
            release,admission,credential,discovery,adapter,
            simulated_at="2026-09-24T13:14:00Z")
        fresh=build_environment_state_discovery(
            provider="aws",account_id="acct-1",environment_id="prod",
            observed_at="2026-09-24T13:14:30Z",
            current_release_id=None,current_image_digest=None,
            resource_summary={"resources":2},source_hash="3"*64,
            source_locator="aws://fresh",verified=True)
        handoff=prepare_external_activation_handoff(
            simulation,release,admission,credential,fresh,
            deployer_id="external-deployer",
            issued_at="2026-09-24T13:15:00Z")
        return release,handoff

    def test_separate_activation_receipt_and_post_discovery_verify(self):
        with tempfile.TemporaryDirectory() as d:
            release,handoff=self.fixture(Path(d))
            identity={
                "schema":1,"handoff_id":handoff.handoff_id,
                "handoff_proof_hash":handoff.proof_hash,
                "deployer_id":"external-deployer","provider":"aws",
                "account_id":"acct-1","environment_id":"prod",
                "release_id":release.release_id,
                "release_proof_hash":release.proof_hash,
                "target_image_digest":release.container_image_digest,
                "target_source_commit":release.source_commit,
                "deployed_at":"2026-09-24T13:16:00Z",
                "external_deployment_id":"deploy-1",
                "source_hash":"4"*64,"source_locator":"deployer://deploy-1",
                "verified":True}
            receipt=ExternalActivationReceipt(
                receipt_id="recoveryworks-activation-receipt:"+canonical_hash(identity),
                **{k:v for k,v in identity.items() if k!="schema"})
            post=build_environment_state_discovery(
                provider="aws",account_id="acct-1",environment_id="prod",
                observed_at="2026-09-24T13:17:00Z",
                current_release_id=release.release_id,
                current_image_digest=release.container_image_digest,
                resource_summary={"resources":2},source_hash="5"*64,
                source_locator="aws://post",verified=True)
            validated=validate_external_activation(handoff,receipt,post)
            self.assertEqual(validated.as_dict()["state"],"ACTIVATION_VERIFIED")

    def test_drifted_fresh_recheck_or_wrong_post_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            release,promotion,security,dr,build = ProductionAdmissionTests().fixture(root)
            admission=build_production_admission_gate(
                release,promotion,security,dr,build,
                admitted_at="2026-09-24T13:11:00Z")
            credential=build_credential_scope_attestation(
                provider="aws",account_id="acct-1",principal_id="reader",
                granted_permissions=("compute:describe",),
                observed_at="2026-09-24T13:12:00Z",
                source_hash="1"*64,source_locator="aws://scope",verified=True)
            discovery=build_environment_state_discovery(
                provider="aws",account_id="acct-1",environment_id="prod",
                observed_at="2026-09-24T13:13:00Z",
                current_release_id=None,current_image_digest=None,
                resource_summary={"resources":2},source_hash="2"*64,
                source_locator="aws://discovery",verified=True)
            adapter=build_activation_adapter(credential,discovery)
            simulation=simulate_external_environment_activation(
                release,admission,credential,discovery,adapter,
                simulated_at="2026-09-24T13:14:00Z")
            drift=build_environment_state_discovery(
                provider="aws",account_id="acct-1",environment_id="prod",
                observed_at="2026-09-24T13:14:30Z",
                current_release_id="other-release",current_image_digest="9"*64,
                resource_summary={"resources":2},source_hash="3"*64,
                source_locator="aws://drift",verified=True)
            with self.assertRaisesRegex(ValueError,"changed since activation simulation"):
                prepare_external_activation_handoff(
                    simulation,release,admission,credential,drift,
                    deployer_id="external-deployer",
                    issued_at="2026-09-24T13:15:00Z")


if __name__=="__main__":
    unittest.main()
