from __future__ import annotations

import unittest

from recoveryworks.provider_connectors import (
    CredentialReferenceKind,
    ProviderConnectorErrorCode,
    ProviderReadOperation,
    build_credential_provider_reference,
    build_provider_discovery_request,
    build_provider_replay_fixture,
    build_readonly_provider_connector,
    classify_provider_connector_error,
    replay_provider_discovery,
)


class ProviderConnectorReadinessTests(unittest.TestCase):
    def test_aws_azure_gcp_readonly_fixture_replay(self):
        refs={
            "aws":CredentialReferenceKind.ROLE_REFERENCE,
            "azure":CredentialReferenceKind.MANAGED_IDENTITY,
            "gcp":CredentialReferenceKind.SERVICE_ACCOUNT_IMPERSONATION,
        }
        for provider,kind in refs.items():
            with self.subTest(provider=provider):
                credential=build_credential_provider_reference(
                    provider=provider,account_id=f"{provider}-acct",kind=kind,
                    principal_reference=f"{provider}-principal-ref",
                    source_hash="1"*64,source_locator=f"{provider}://identity",
                    verified=True)
                connector=build_readonly_provider_connector(credential)
                request=build_provider_discovery_request(
                    provider=provider,account_id=f"{provider}-acct",
                    operation=ProviderReadOperation.DISCOVER_RESOURCES,
                    parameters={"region":"test-region"})
                fixture=build_provider_replay_fixture(
                    request,observed_at="2026-09-24T13:00:00Z",
                    response_payload={"resources":[{"id":"r-1","type":"compute"}]},
                    source_hash="2"*64,source_locator=f"fixture://{provider}",
                    verified=True)
                result=replay_provider_discovery(connector,request,fixture)
                self.assertEqual(result.as_dict()["state"],"OFFLINE_REPLAY_VERIFIED")
                self.assertFalse(result.provider_api_called)
                self.assertFalse(result.secrets_persisted)
                self.assertFalse(connector.live_calls_enabled)
                self.assertFalse(connector.write_operations_enabled)

    def test_secret_material_and_mutation_semantics_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"secret material"):
            build_credential_provider_reference(
                provider="aws",account_id="acct",
                kind=CredentialReferenceKind.ROLE_REFERENCE,
                principal_reference="token=abc123",
                source_hash="1"*64,source_locator="aws://identity",verified=True)
        with self.assertRaisesRegex(ValueError,"mutation semantics"):
            build_provider_discovery_request(
                provider="aws",account_id="acct",
                operation=ProviderReadOperation.DISCOVER_RESOURCES,
                parameters={"action":"delete-instance"})

    def test_fixture_scope_and_request_mismatch_fail_closed(self):
        credential=build_credential_provider_reference(
            provider="aws",account_id="acct",
            kind=CredentialReferenceKind.ROLE_REFERENCE,
            principal_reference="role-ref",source_hash="1"*64,
            source_locator="aws://identity",verified=True)
        connector=build_readonly_provider_connector(credential)
        request=build_provider_discovery_request(
            provider="aws",account_id="acct",
            operation=ProviderReadOperation.DESCRIBE_IDENTITY)
        other=build_provider_discovery_request(
            provider="aws",account_id="acct",
            operation=ProviderReadOperation.DISCOVER_RESOURCES)
        fixture=build_provider_replay_fixture(
            other,observed_at="2026-09-24T13:00:00Z",
            response_payload={"ok":True},source_hash="2"*64,
            source_locator="fixture://aws",verified=True)
        with self.assertRaisesRegex(ValueError,"FIXTURE_MISS"):
            replay_provider_discovery(connector,request,fixture)

    def test_stable_error_taxonomy(self):
        self.assertIs(
            classify_provider_connector_error(http_status=429),
            ProviderConnectorErrorCode.RATE_LIMITED)
        self.assertIs(
            classify_provider_connector_error(http_status=403),
            ProviderConnectorErrorCode.AUTHORIZATION_FAILED)
        self.assertIs(
            classify_provider_connector_error(error_name="request timeout"),
            ProviderConnectorErrorCode.TIMEOUT)
        self.assertIs(
            classify_provider_connector_error(http_status=503),
            ProviderConnectorErrorCode.TRANSIENT_PROVIDER_ERROR)
        self.assertIs(
            classify_provider_connector_error(http_status=400),
            ProviderConnectorErrorCode.MALFORMED_RESPONSE)


if __name__=="__main__":
    unittest.main()
