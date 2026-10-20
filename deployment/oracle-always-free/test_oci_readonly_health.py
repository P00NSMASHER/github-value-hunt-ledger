"""Offline, no-network security and behavior tests for the GitHub -> OCI observer."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

MODULE = Path(__file__).with_name("oci_readonly_health.py")
spec = importlib.util.spec_from_file_location("oci_readonly_health", MODULE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def fixture():
    return {
        "GITHUB_REPOSITORY": m.REPOSITORY,
        "GITHUB_REPOSITORY_ID": m.REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER_ID": m.OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": m.WORKFLOW_REF,
        "GITHUB_EVENT_NAME": "schedule",
        "RETALLY_OCI_MONITOR_ENABLED": "true",
        "RETALLY_OCI_DOMAIN_URL": "https://idcs-example.identity.oraclecloud.com",
        "RETALLY_OCI_CLIENT_ID": "narrow-client",
        "RETALLY_OCI_CLIENT_SECRET": "confidential-client-secret",
        "RETALLY_OCI_NAMESPACE": "exampletenant",
        "RETALLY_OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..aaaaexample",
        "RETALLY_OCI_VM_OCID": "ocid1.instance.oc1.iad.aaaaexample",
        "ACTIONS_ID_TOKEN_REQUEST_URL": "https://pipelines.actions.githubusercontent.com/oidc/token?x=1",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "opaque-gh-request-token",
    }


def claims():
    now = int(time.time())
    return {
        "iss": m.ISSUER, "aud": m.AUDIENCE, "sub": m.SUBJECT,
        "repository": m.REPOSITORY, "repository_id": m.REPOSITORY_ID,
        "repository_owner_id": m.OWNER_ID,
        "workflow_ref": m.WORKFLOW_REF,
        "ref": "refs/heads/main", "event_name": "schedule", "iat": now - 4,
        "exp": now + 180,
    }


def jwt(c):
    body = base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip("=")
    return "eyJhbGciOiJSUzI1NiJ9." + body + ".dummy_signature"


class ContextTests(unittest.TestCase):
    def test_accepts_only_exact_main_scheduled_or_manual(self):
        s = fixture()
        self.assertEqual(m.require_env(s), s)
        s["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        self.assertEqual(m.require_env(s), s)

    def test_denies_pr_fork_untrusted_ref_renamed_repo_and_owner(self):
        for key, value in [
            ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_REF", "refs/heads/test"),
            ("GITHUB_WORKFLOW_REF", m.WORKFLOW_REF.replace("main", "test")),
            ("GITHUB_REPOSITORY", "attacker/github-value-hunt-ledger"),
            ("GITHUB_REPOSITORY_ID", "not-expected"),
            ("GITHUB_REPOSITORY_OWNER_ID", "not-expected"),
            ("RETALLY_OCI_MONITOR_ENABLED", "false"),
        ]:
            with self.subTest(key=key):
                s = fixture()
                s[key] = value
                with self.assertRaises(m.Refused):
                    m.require_env(s)

    def test_denies_missing_and_malformed_configuration(self):
        for key, value in [
            ("RETALLY_OCI_CLIENT_SECRET", ""),
            ("RETALLY_OCI_DOMAIN_URL", "http://evil.identity.oraclecloud.com"),
            ("RETALLY_OCI_DOMAIN_URL", "https://evil.identity.oraclecloud.com@evil.net"),
            ("RETALLY_OCI_DOMAIN_URL", "https://idcs-example.identity.oraclecloud.com/evil"),
            ("ACTIONS_ID_TOKEN_REQUEST_URL", "http://pipelines.actions.githubusercontent.com/oidc/token"),
            ("ACTIONS_ID_TOKEN_REQUEST_URL", "https://evil.net/oidc/token"),
            ("RETALLY_OCI_VM_OCID", "junk"), ("RETALLY_OCI_NAMESPACE", "a/../x"),
        ]:
            with self.subTest(key=key):
                s = fixture()
                s[key] = value
                with self.assertRaises(m.Refused):
                    m.require_env(s)

    def test_github_claim_exactness_and_expiry(self):
        good = claims()
        m.validate_claims(good, "schedule")
        immutable = dict(good)
        immutable["sub"] = m.IMMUTABLE_SUBJECT
        m.validate_claims(immutable, "schedule")
        self.assertIn("@22281248/", immutable["sub"])
        self.assertIn("@1376771019:", immutable["sub"])
        for key, value in [
            ("iss", "https://evil.example"), ("aud", "evil"),
            ("sub", "repo:bad/other:ref:refs/heads/main"),
            ("repository_id", "other-id"), ("repository_owner_id", "wrong"),
            ("workflow_ref", "bad"), ("ref", "refs/heads/test"),
            ("event_name", "pull_request"), ("exp", int(time.time()) - 1),
            ("iat", int(time.time()) - 700),
        ]:
            with self.subTest(key=key):
                c = dict(good)
                c[key] = value
                with self.assertRaises(m.Refused):
                    m.validate_claims(c, "schedule")

    def test_preflight_claims_decode_does_not_imply_signature_verified(self):
        self.assertEqual(m.decode_claims_for_preflight(jwt(claims()))["repository_id"],
                         m.REPOSITORY_ID)
        for token in ("", "broken", "a.b", "a.b.c.d"):
            with self.assertRaises(m.Refused):
                m.decode_claims_for_preflight(token)


class AccessTests(unittest.TestCase):
    def test_bucket_expected_private_no_events_no_replication(self):
        good = dict(name=m.BUCKET, compartment_id=fixture()["RETALLY_OCI_COMPARTMENT_OCID"],
                    public_access_type="NoPublicAccess",
                    storage_tier="Standard", versioning="Disabled",
                    object_events_enabled=False, replication_enabled=False,
                    auto_tiering="Disabled")
        m.check_bucket(SimpleNamespace(**good), fixture()["RETALLY_OCI_COMPARTMENT_OCID"])
        for field, bad in [
            ("name", "another"), ("compartment_id", "wrong"),
            ("public_access_type", "ObjectRead"),
            ("storage_tier", "Archive"), ("versioning", "Enabled"),
            ("object_events_enabled", True), ("replication_enabled", True),
            ("replication_enabled", None), ("auto_tiering", "InfrequentAccess"),
        ]:
            with self.subTest(field=field, bad=bad):
                x = dict(good)
                x[field] = bad
                with self.assertRaises(m.Refused):
                    m.check_bucket(SimpleNamespace(**x), fixture()["RETALLY_OCI_COMPARTMENT_OCID"])

    def test_vm_expected_running_shape(self):
        vm = dict(id=fixture()["RETALLY_OCI_VM_OCID"],
                  compartment_id=fixture()["RETALLY_OCI_COMPARTMENT_OCID"], shape=m.SHAPE,
                  lifecycle_state="RUNNING")
        m.check_instance(SimpleNamespace(**vm), vm["id"], vm["compartment_id"])
        for field, value in [
            ("id", "wrong"), ("compartment_id", "wrong"),
            ("shape", "VM.Standard.A1.Flex"),
            ("lifecycle_state", "STOPPED"),
        ]:
            x = dict(vm)
            x[field] = value
            with self.assertRaises(m.Refused):
                m.check_instance(SimpleNamespace(**x), vm["id"], vm["compartment_id"])

    def test_rpst_exchange_uses_strict_token_type_and_no_write_scope(self):
        s = fixture()
        token = jwt(claims())
        requests = []

        def fake_json(request):
            requests.append(request)
            return {"token": token}

        with patch.object(m, "json_response", fake_json):
            self.assertEqual(m.exchange_for_rpst(s, token, "PUBLIC KEY"), token)
        data = requests[0].data.decode()
        self.assertIn("oci-rpst", data)
        self.assertIn("res_type=ref_github", data)
        self.assertIn("rpst_exp=20", data)
        self.assertEqual(requests[0].get_method(), "POST")
        self.assertTrue(requests[0].full_url.endswith("/oauth2/v1/token"))

    def test_failure_never_emits_exception_or_secret(self):
        s = fixture()
        s["RETALLY_OCI_CLIENT_SECRET"] = "TOP_SECRET_FOR_TEST"
        stream = io.StringIO()
        with patch.dict(m.os.environ, s, clear=True):
            with patch.object(m, "do_live_check",
                              side_effect=Exception("TOP_SECRET_FOR_TEST")):
                with patch("sys.stdout", stream):
                    self.assertEqual(m.main(), 1)
        self.assertNotIn("TOP_SECRET_FOR_TEST", stream.getvalue())
        self.assertIn("FAIL", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
