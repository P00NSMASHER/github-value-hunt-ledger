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
        "RETALLY_OCI_VM_COMPARTMENT_OCID": "ocid1.compartment.oc1..aaaavmexample",
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
            ("RETALLY_OCI_VM_OCID", "junk"),
            ("RETALLY_OCI_VM_COMPARTMENT_OCID", "junk"),
            ("RETALLY_OCI_NAMESPACE", "a/../x"),
        ]:
            with self.subTest(key=key):
                s = fixture()
                s[key] = value
                with self.assertRaises(m.Refused):
                    m.require_env(s)

    def test_accepts_documented_github_oidc_hosted_runner_origins(self):
        # GitHub documents *.actions.githubusercontent.com for OIDC retrieval.
        # Real GitHub-hosted runners may use regional pipelinesghub* origins.
        for hostname in (
            "pipelines.actions.githubusercontent.com",
            "pipelinesghubeus13.actions.githubusercontent.com",
            "pipelinesghubwus24.actions.githubusercontent.com",
            "run-actions-1-azure-eastus.actions.githubusercontent.com",
            "run-actions-24-azure-westus2.actions.githubusercontent.com",
        ):
            with self.subTest(hostname=hostname):
                s = fixture()
                s["ACTIONS_ID_TOKEN_REQUEST_URL"] = (
                    f"https://{hostname}/oidc/token?x=1")
                self.assertEqual(m.require_env(s), s)
        for url in (
            "https://evil.actions.githubusercontent.com/oidc/token?x=1",
            "https://run-actions-x-azure-eastus.actions.githubusercontent.com/oidc/token",
            "https://run-actions-1-azure-eastus.actions.githubusercontent.com.evil.net/oidc/token",
            "https://run-actions-1-azure-eastus.actions.githubusercontent.com:444/oidc/token",
            "http://run-actions-1-azure-eastus.actions.githubusercontent.com/oidc/token",
            "https://pipelinesghub.actions.githubusercontent.com/oidc/token",
            "https://pipelinesghub-.actions.githubusercontent.com/oidc/token",
            "https://pipelinesghubeus13.actions.githubusercontent.com.evil.net/oidc/token",
            "https://pipelinesghubeus13.actions.githubusercontent.com@evil.net/oidc/token",
            "http://pipelinesghubeus13.actions.githubusercontent.com/oidc/token",
            "https://pipelinesghubeus13.actions.githubusercontent.com:443/oidc/token",
        ):
            with self.subTest(url=url):
                s = fixture()
                s["ACTIONS_ID_TOKEN_REQUEST_URL"] = url
                with self.assertRaises(m.Refused):
                    m.require_env(s)

    def test_rejected_oidc_url_reports_safe_host_only(self):
        for url, allowed_label in (
            ("https://pipelinesghubeus13.actions.githubusercontent.com:444/idtoken?SECRET_QUERY",
             "pipelinesghubeus13"),
            ("https://untrusted.example/idtoken?SECRET_QUERY", "OTHER"),
        ):
            with self.subTest(url=url):
                s = fixture()
                s["ACTIONS_ID_TOKEN_REQUEST_URL"] = url
                output = io.StringIO()
                with patch("sys.stdout", output):
                    with self.assertRaises(m.Refused):
                        m.require_env(s)
                self.assertIn("RETALLY OCI OIDC ORIGIN: ", output.getvalue())
                self.assertIn("label=" + allowed_label, output.getvalue())
                self.assertNotIn("SECRET_QUERY", output.getvalue())
                self.assertNotIn("idtoken", output.getvalue())
                self.assertNotIn("untrusted.example", output.getvalue())

    def test_sanitized_context_failure_names_key_not_value(self):
        bad = fixture()
        bad["GITHUB_REPOSITORY_ID"] = "TOP_SECRET_FOR_TEST"
        stream = io.StringIO()
        with patch.dict(m.os.environ, bad, clear=True), patch("sys.stdout", stream):
            self.assertEqual(m.main(), 1)
        self.assertIn("RETALLY OCI DIAG: Untrusted GitHub execution context: GITHUB_REPOSITORY_ID", stream.getvalue())
        self.assertNotIn("TOP_SECRET_FOR_TEST", stream.getvalue())
        self.assertIn("FAIL", stream.getvalue())

    def test_diagnostics_never_include_unexpected_exception_messages(self):
        self.assertEqual(m.safe_failure_code(ValueError("TOP_SECRET_FOR_TEST")),
                         "UNCLASSIFIED_FAILURE")
        self.assertEqual(m.safe_failure_code(m.Refused("TOP_SECRET_FOR_TEST")),
                         "UNCLASSIFIED_FAILURE")
        self.assertEqual(m.safe_failure_code(m.Refused("OCI_TOKEN_EXCHANGE")),
                         "OCI_TOKEN_EXCHANGE")

    def test_fixed_preflight_reasons_report_safe_codes(self):
        allowed = (
            "Only scheduled or manual main-branch execution is allowed",
            "Monitor is not explicitly enabled",
            "Identity-domain URL must be an OCI HTTPS identity domain origin",
            "GitHub OIDC request endpoint is not trusted",
            "Invalid OCI namespace",
            "Invalid OCI compartment/tenancy OCID",
            "Invalid OCI VM compartment OCID",
            "Invalid expected VM OCID",
        )
        for reason in allowed:
            with self.subTest(reason=reason):
                self.assertEqual(m.safe_failure_code(m.Refused(reason)), reason)
        self.assertEqual(m.safe_failure_code(m.Refused("SECRET_EXAMPLE_VALUE")),
                         "UNCLASSIFIED_FAILURE")

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


class AuthErrorTests(unittest.TestCase):
    def test_http_error_classification_is_bounded_and_never_leaks_provider_body(self):
        from urllib.error import HTTPError
        secret = "SHOULD_NOT_LEAK_PRIVATE_PROVIDER_RESPONSE"
        req = m.Request("https://idcs-example.identity.oraclecloud.com/oauth2/v1/token",
                        data=b"synthetic")
        for status, provider_error, expected in (
            (400, "invalid_request", "AUTH_HTTP_400_invalid_request"),
            (401, "invalid_client", "AUTH_HTTP_401_invalid_client"),
            (403, "access_denied", "AUTH_HTTP_403_access_denied"),
            (500, "arbitrary_" + secret, "AUTH_HTTP_500_other"),
        ):
            with self.subTest(status=status):
                body = json.dumps({"error": provider_error,
                                   "error_description": secret}).encode()
                err = HTTPError(req.full_url, status, secret, {},
                                io.BytesIO(body))
                class FakeOpener:
                    def open(self, *a, **kw):
                        raise err
                with patch.object(m, "build_opener", return_value=FakeOpener()):
                    with self.assertRaises(m.Refused) as caught:
                        m.json_response(req)
                self.assertEqual(str(caught.exception), expected)
                self.assertNotIn(secret, str(caught.exception))

    def test_exchange_reports_only_fixed_http_and_oauth_category(self):
        settings = fixture()
        for label, diagnostic in (
            ("AUTH_HTTP_401_invalid_client",
             "OCI_TOKEN_EXCHANGE_AUTH_HTTP_401_invalid_client"),
            ("AUTH_HTTP_400_invalid_grant",
             "OCI_TOKEN_EXCHANGE_AUTH_HTTP_400_invalid_grant"),
            ("Authentication secret leak", "OCI_TOKEN_EXCHANGE"),
        ):
            with self.subTest(label=label):
                with patch.object(m, "json_response", side_effect=m.Refused(label)):
                    with self.assertRaises(m.Refused) as caught:
                        m.exchange_for_rpst(settings, "synthetic.jwt.token", "PUBLIC")
                self.assertEqual(str(caught.exception), diagnostic)
                self.assertEqual(m.safe_failure_code(caught.exception), diagnostic)


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
                  compartment_id=fixture()["RETALLY_OCI_VM_COMPARTMENT_OCID"], shape=m.SHAPE,
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

    def test_rpst_public_key_uses_single_line_der_base64_not_pem(self):
        # Oracle's RPST GitHub token-exchange implementations use base64 DER
        # SubjectPublicKeyInfo as one form field, without PEM delimiters.
        der = bytes.fromhex("300d06092a864886f70d0101010500")
        encoded = m.encode_rpst_public_key(der)
        self.assertEqual(encoded, base64.b64encode(der).decode("ascii"))
        self.assertEqual(base64.b64decode(encoded, validate=True), der)
        self.assertNotIn("BEGIN PUBLIC KEY", encoded)
        self.assertNotIn("\\n", encoded)
        for invalid in ("PUBLIC KEY", b"", b"not-der"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(m.Refused):
                    m.encode_rpst_public_key(invalid)

    def test_rpst_key_serializer_is_used_by_live_path(self):
        import inspect
        live = inspect.getsource(m.do_live_check)
        self.assertIn("serialization.Encoding.DER", live)
        self.assertIn("encode_rpst_public_key(", live)

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


class WorkflowSecretIsolationTests(unittest.TestCase):
    def test_oauth_credentials_reach_only_the_final_readonly_step(self):
        workflow = (Path(__file__).resolve().parents[2] /
                    ".github" / "workflows" / "retally-oci-readonly.yml").read_text()
        self.assertIn("  oracle-readonly:\n", workflow)
        privileged = workflow.split("  oracle-readonly:\n", 1)[1]
        anchor = "      - name: Verify private Oracle bucket and VM (read-only)\n"
        self.assertIn(anchor, privileged)
        before_final, final = privileged.split(anchor, 1)
        self.assertIn("id-token: write", before_final)
        self.assertIn("vars.RETALLY_OCI_MONITOR_ENABLED", before_final)
        self.assertIn("python -m pip install", before_final)
        self.assertIn("        env:\n", final)
        self.assertIn("        run: python deployment/oracle-always-free/oci_readonly_health.py", final)
        for key in ("RETALLY_OCI_CLIENT_ID", "RETALLY_OCI_CLIENT_SECRET"):
            expression = "secrets." + key
            self.assertNotIn(expression, before_final,
                             "OAuth credentials leaked to setup or pip steps")
            self.assertEqual(privileged.count(expression), 1,
                             "OAuth secret must be scoped to one step only")
            self.assertIn(expression, final)
            self.assertLess(final.index(expression),
                            final.index("        run: python"),
                            "Secret must be scoped to the verification step")
        # Fork/PR test jobs must not request OIDC or receive OCI secrets.
        offline = workflow.split("  validate-offline:\n", 1)[1].split(
            "\n  disabled-state:\n", 1)[0]
        self.assertNotIn("id-token: write", offline)
        self.assertNotIn("secrets.RETALLY_OCI_CLIENT_SECRET", offline)
        self.assertIn("github.event_name == 'schedule'", before_final)
        self.assertIn("github.ref == 'refs/heads/main'", before_final)


if __name__ == "__main__":
    unittest.main()
