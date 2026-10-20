"""Offline security contract for GitHub -> OCI read-only federation.

No test signs into OCI, requests an OIDC token, invokes cloud operations, or charges a provider.
"""
import base64
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from unittest.mock import patch

path = Path(__file__).with_name("retally_oci_readonly.py")
spec = importlib.util.spec_from_file_location("retally_oci_readonly", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def env():
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": m.REPOSITORY,
        "GITHUB_REPOSITORY_ID": m.REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER_ID": m.OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": m.EXPECTED_WORKFLOW_REF,
        "GITHUB_EVENT_NAME": "schedule",
        "ACTIONS_ID_TOKEN_REQUEST_URL": "https://pipelines.actions.githubusercontent.com/a?x=1",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "private-github-token",
        "RETALLY_OCI_IDENTITY_DOMAIN_URL": "https://idcs-example.identity.oraclecloud.com",
        "RETALLY_OCI_OAUTH_CLIENT_ID": "client-abc",
        "RETALLY_OCI_OAUTH_CLIENT_SECRET": "private-client-secret",
    }


def claims():
    return {
        "iss": m.ISSUER,
        "aud": m.AUDIENCE,
        "sub": m.EXPECTED_SUB,
        "repository": m.REPOSITORY,
        "repository_id": m.REPOSITORY_ID,
        "repository_owner_id": m.OWNER_ID,
        "ref": "refs/heads/main",
        "workflow_ref": m.EXPECTED_WORKFLOW_REF,
        "environment": m.ENVIRONMENT,
        "event_name": "schedule",
        "iat": 1760000000,
        "exp": 1760000250,
    }


def jwt(data):
    def enc(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    return enc({"alg": "RS256"}) + "." + enc(data) + "." + "a" * 50


class FakeOCI:
    baseline = {
        "name": m.BUCKET,
        "public_access_type": "NoPublicAccess",
        "storage_tier": "Standard",
        "versioning": "Disabled",
        "object_events_enabled": False,
        "replication_enabled": False,
        "object_lifecycle_policy_etag": None,
        "auto_tiering": None,
    }

    def __init__(self, pages=None, changes=None):
        self.calls = []
        self.pages = pages if pages is not None else [([], None)]
        self.bucket = S(**(self.baseline | (changes or {})))

    def get_namespace(self):
        self.calls.append("get_namespace")
        return S(data="testnamespace")

    def get_bucket(self, ns, bucket):
        self.calls.append("get_bucket")
        assert ns == "testnamespace" and bucket == m.BUCKET
        return S(data=self.bucket)

    def list_objects(self, ns, bucket, **kwargs):
        self.calls.append("list_objects")
        assert ns == "testnamespace" and bucket == m.BUCKET
        ix = self.calls.count("list_objects") - 1
        names, next_start = self.pages[ix]
        return S(data=S(objects=[S(name=n) for n in names], next_start_with=next_start))


class IdentitySecurity(unittest.TestCase):
    def test_main_repo_and_allowed_event(self):
        m.require_runtime(env())
        data = env()
        data["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        m.require_runtime(data)

    def test_unapproved_repo_branch_and_pr_are_rejected(self):
        for key in ("GITHUB_ACTIONS", "GITHUB_REPOSITORY", "GITHUB_REPOSITORY_ID",
                    "GITHUB_REPOSITORY_OWNER_ID", "GITHUB_REF", "GITHUB_WORKFLOW_REF",
                    "GITHUB_EVENT_NAME"):
            data = env()
            data[key] = "pull_request"
            with self.subTest(key=key), self.assertRaises(m.Refused):
                m.require_runtime(data)

    def test_missing_secrets_and_endpoint_refused(self):
        for key in ("ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
                    "RETALLY_OCI_IDENTITY_DOMAIN_URL", "RETALLY_OCI_OAUTH_CLIENT_ID",
                    "RETALLY_OCI_OAUTH_CLIENT_SECRET"):
            data = env()
            data[key] = ""
            with self.subTest(key=key), self.assertRaises(m.Refused):
                m.require_runtime(data)

    def test_reject_untrusted_identity_hosts_and_paths(self):
        for url in ("http://idcs-example.identity.oraclecloud.com",
                    "https://idcs-example.identity.oraclecloud.com.evil.tld",
                    "https://idcs-example.identity.oraclecloud.com@evil.tld",
                    "https://evil.example.com",
                    "https://idcs-example.identity.oraclecloud.com/other",
                    "https://idcs-example.identity.oraclecloud.com?redirect=true",
                    "https://idcs-example.identity.oraclecloud.com:8443"):
            with self.subTest(url=url), self.assertRaises(m.Refused):
                m.validate_endpoint(url)
        self.assertEqual(m.validate_endpoint("https://idcs-example.identity.oraclecloud.com"),
                         "https://idcs-example.identity.oraclecloud.com/oauth2/v1/token")
        with self.assertRaises(m.Refused):
            m.validate_endpoint("https://evil.tld/t", github=True)
        self.assertEqual(
            m.validate_endpoint("https://pipelines.actions.githubusercontent.com/a?x=1",
                                github=True),
            "https://pipelines.actions.githubusercontent.com/a?x=1")
        for untrusted in (
            "https://attacker.actions.githubusercontent.com/a?x=1",
            "https://token.actions.githubusercontent.com/a?x=1",
            "https://fake.pipelines.actions.githubusercontent.com/a?x=1",
        ):
            with self.subTest(untrusted=untrusted), self.assertRaises(m.Refused):
                m.validate_endpoint(untrusted, github=True)

    def test_all_claims_and_expiry_fail_closed(self):
        m.validate_claims(claims(), now=1760000020)
        for key in ("iss", "aud", "sub", "repository", "repository_id",
                    "repository_owner_id", "ref", "workflow_ref", "environment",
                    "event_name"):
            data = claims()
            data[key] = "tampered"
            with self.subTest(key=key), self.assertRaises(m.Refused):
                m.validate_claims(data, now=1760000020)
        for key, value in (("exp", 1760000000), ("exp", 1760002000), ("iat", 1760002000)):
            data = claims()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(m.Refused):
                m.validate_claims(data, now=1760000020)

    def test_compact_oidc_assertion_and_response(self):
        self.assertEqual(m.oidc_claims(jwt(claims())), claims())
        for token in ("", "untrusted", "a.b.c.d"):
            with self.subTest(token=token), self.assertRaises(m.Refused):
                m.oidc_claims(token)
        with patch.object(m, "request_json", return_value={"value": jwt(claims())}), patch.object(m, "validate_claims"):
            self.assertEqual(m.github_assertion(env()).count("."), 2)

    def test_short_lived_rpst_exchange_without_private_key_export(self):
        with patch.object(m, "request_json", return_value={"token": "r" * 128}) as spy:
            self.assertEqual(m.exchange_for_rpst(env(), "assertion", "public"), "r" * 128)
        req = spy.call_args.args[0]
        self.assertIn("res_type=githubactions", req.data.decode())
        self.assertIn("rpst_exp=20", req.data.decode())
        self.assertNotIn("private", req.data.decode())
        with patch.object(m, "request_json", return_value={"token": ""}), self.assertRaises(m.Refused):
            m.exchange_for_rpst(env(), "assertion", "public")


class OCIReadOnlySecurity(unittest.TestCase):
    def test_empty_inventory_no_cloud_writes(self):
        client = FakeOCI()
        report = m.inspect_bucket(client)
        self.assertEqual(client.calls, ["get_namespace", "get_bucket", "list_objects"])
        self.assertEqual(report["status"], "OBSERVATION_OK_CUSTOMER_RELEASE_HOLD")
        self.assertIs(report["customer_release_authorized"], False)
        self.assertIs(report["automatic_provider_mutation_enabled"], False)

    def test_one_legacy_canary_is_preserved(self):
        name = "synthetic-only/" + "a" * 24 + ".rtbk"
        client = FakeOCI(pages=[([name], None)])
        report = m.inspect_bucket(client)
        self.assertEqual(report["legacy_synthetic_orphan_count"], 1)
        self.assertNotIn(name, json.dumps(report))
        self.assertEqual(client.calls.count("list_objects"), 1)

    def test_paginate_before_success(self):
        client = FakeOCI(pages=[([], "next1"), (["synthetic-only/" + "a" * 24 + ".rtbk"], None)])
        self.assertEqual(m.inspect_bucket(client)["legacy_synthetic_orphan_count"], 1)
        self.assertEqual(client.calls.count("list_objects"), 2)

    def test_unexpected_or_stranded_objects_fail_closed(self):
        names = ("real-customer.pdf", "synthetic-only/not-verified.rtbk",
                 "synthetic-recovery/" + "b" * 32 + ".rtbk")
        for name in names:
            client = FakeOCI(pages=[([name], None)])
            with self.subTest(name=name), self.assertRaises(m.Refused):
                m.inspect_bucket(client)
            self.assertEqual(client.calls, ["get_namespace", "get_bucket", "list_objects"])

    def test_two_canaries_and_pagination_loops_refused(self):
        names = ["synthetic-only/" + letter * 24 + ".rtbk" for letter in ("a", "b")]
        with self.assertRaises(m.Refused):
            m.inspect_bucket(FakeOCI(pages=[(names, None)]))
        with self.assertRaises(m.Refused):
            m.inspect_bucket(FakeOCI(pages=[([], "same"), ([], "same")]))

    def test_config_changes_are_never_accepted(self):
        changes = (("public_access_type", "ObjectRead"), ("storage_tier", "Archive"),
                   ("versioning", "Enabled"), ("object_events_enabled", True),
                   ("replication_enabled", True), ("auto_tiering", "Enabled"),
                   ("object_lifecycle_policy_etag", "present"))
        for name, val in changes:
            with self.subTest(name=name), self.assertRaises(m.Refused):
                m.inspect_bucket(FakeOCI(changes={name: val}))

    def test_bound_inventory_prevents_unbounded_silent_scan(self):
        names = ["synthetic-only/" + f"{i:024x}" + ".rtbk" for i in range(m.MAX_OBJECTS + 1)]
        with self.assertRaises(m.Refused):
            m.inspect_bucket(FakeOCI(pages=[(names, None)]))

    def test_summary_never_contains_names_or_identity_values(self):
        report = m.inspect_bucket(FakeOCI())
        rendered = json.dumps(report)
        self.assertNotIn("testnamespace", rendered)
        self.assertNotIn(m.BUCKET, rendered)


class WorkflowCredentialExposureTests(unittest.TestCase):
    def test_oauth_client_secret_is_scoped_to_the_observer_step_only(self):
        workflow = (Path(__file__).resolve().parents[2] /
                    ".github" / "workflows" / "retally-oracle-readonly.yml").read_text()
        self.assertIn("  observe:\n", workflow)
        privileged = workflow.split("  observe:\n", 1)[1]
        anchor = "      - name: Verify GitHub OIDC and use short-lived OCI resource identity\n"
        self.assertIn(anchor, privileged)
        before, observer = privileged.split(anchor, 1)
        self.assertIn("id-token: write", before)
        self.assertIn("github.ref == 'refs/heads/main'", before)
        self.assertIn("python -m pip install", before)
        self.assertIn("        env:\n", observer)
        self.assertIn("        run: python deployment/oracle-always-free/retally_oci_readonly.py", observer)
        for name in ("RETALLY_OCI_OAUTH_CLIENT_ID", "RETALLY_OCI_OAUTH_CLIENT_SECRET"):
            expression = "secrets." + name
            self.assertNotIn(expression, before,
                             "Unrelated checkout/install steps received OAuth credentials")
            self.assertEqual(privileged.count(expression), 1)
            self.assertIn(expression, observer)
            self.assertLess(observer.index(expression),
                            observer.index("        run: python"),
                            "OAuth secret must be scoped to the observer process")
        unprivileged = workflow.split("  offline-contract:\n", 1)[1].split(
            "\n  disabled-state:\n", 1)[0]
        self.assertNotIn("id-token: write", unprivileged)
        self.assertNotIn("secrets.RETALLY_OCI_OAUTH_CLIENT_SECRET", unprivileged)


if __name__ == "__main__":
    unittest.main()
