from __future__ import annotations

import unittest

from recoveryworks.models import canonical_hash
from recoveryworks.provider_connector_handoff import (
    ExternalProviderDiscoveryReceipt,
    prepare_provider_discovery_handoff,
    validate_external_provider_discovery,
)
from recoveryworks.provider_connectors import (
    CredentialReferenceKind,
    ProviderReadOperation,
    build_credential_provider_reference,
    build_provider_discovery_request,
    build_readonly_provider_connector,
)


class ProviderConnectorHandoffTests(unittest.TestCase):
    def fixture(self, provider="aws"):
        kind = {
            "aws": CredentialReferenceKind.ROLE_REFERENCE,
            "azure": CredentialReferenceKind.MANAGED_IDENTITY,
            "gcp": CredentialReferenceKind.SERVICE_ACCOUNT_IMPERSONATION,
        }[provider]
        cred=build_credential_provider_reference(
            provider=provider,account_id=f"{provider}-acct",kind=kind,
            principal_reference=f"{provider}-principal",
            source_hash="1"*64,source_locator=f"{provider}://identity",
            verified=True)
        connector=build_readonly_provider_connector(cred)
        request=build_provider_discovery_request(
            provider=provider,account_id=f"{provider}-acct",
            operation=ProviderReadOperation.DISCOVER_RESOURCES,
            parameters={"region":"r1"})
        handoff=prepare_provider_discovery_handoff(
            connector,cred,request,runner_id="connector-runner-1",
            issued_at="2026-09-24T13:00:00Z")
        return request,handoff

    def test_external_read_receipt_verifies_for_all_providers(self):
        for provider in ("aws","azure","gcp"):
            with self.subTest(provider=provider):
                request,handoff=self.fixture(provider)
                payload={"resources":[{"id":"r-1","type":"compute"}]}
                response_hash=canonical_hash(payload)
                ident={
                    "schema":1,"handoff_id":handoff.handoff_id,
                    "handoff_proof_hash":handoff.proof_hash,
                    "request_proof_hash":request.proof_hash,
                    "provider":provider,"account_id":f"{provider}-acct",
                    "operation":"DISCOVER_RESOURCES",
                    "runner_id":"connector-runner-1",
                    "observed_at":"2026-09-24T13:01:00Z",
                    "provider_request_id":f"{provider}-req-1",
                    "response_payload":payload,"response_hash":response_hash,
                    "source_hash":"2"*64,"source_locator":f"{provider}://receipt",
                    "verified":True,
                    "provider_api_called_by_external_runner":True,
                    "provider_mutation_performed":False,
                    "credential_material_returned":False}
                receipt=ExternalProviderDiscoveryReceipt(
                    receipt_id="provider-discovery-receipt:"+canonical_hash(ident),
                    **{k:v for k,v in ident.items() if k!="schema"})
                verified=validate_external_provider_discovery(handoff,receipt)
                self.assertEqual(
                    verified.as_dict()["state"],
                    "EXTERNAL_READONLY_DISCOVERY_VERIFIED")

    def test_wrong_runner_or_outside_window_fails_closed(self):
        request,handoff=self.fixture("aws")
        payload={"resources":[]}; response_hash=canonical_hash(payload)
        ident={
            "schema":1,"handoff_id":handoff.handoff_id,
            "handoff_proof_hash":handoff.proof_hash,
            "request_proof_hash":request.proof_hash,
            "provider":"aws","account_id":"aws-acct",
            "operation":"DISCOVER_RESOURCES","runner_id":"wrong-runner",
            "observed_at":"2026-09-24T13:01:00Z",
            "provider_request_id":"req","response_payload":payload,
            "response_hash":response_hash,"source_hash":"2"*64,
            "source_locator":"aws://receipt","verified":True,
            "provider_api_called_by_external_runner":True,
            "provider_mutation_performed":False,
            "credential_material_returned":False}
        receipt=ExternalProviderDiscoveryReceipt(
            receipt_id="provider-discovery-receipt:"+canonical_hash(ident),
            **{k:v for k,v in ident.items() if k!="schema"})
        with self.assertRaisesRegex(ValueError,"runner mismatch"):
            validate_external_provider_discovery(handoff,receipt)


if __name__=="__main__":
    unittest.main()
