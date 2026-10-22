"""Offline no-network regression tests for the separate OCI remote canary identity."""
from __future__ import annotations

import base64
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("oci_runcommand_canary", HERE / "oci_runcommand_canary.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def fixture():
    return {
        **m.EXPECTED_KEYS,
        "RETALLY_OCI_RUN_COMMAND_ENABLED": "true",
        "RETALLY_OCI_RUN_DOMAIN_URL": "https://idcs-example.identity.oraclecloud.com",
        "RETALLY_OCI_RUN_CLIENT_ID": "remote-only-client",
        "RETALLY_OCI_RUN_CLIENT_SECRET": "dummy-never-live",
        "RETALLY_OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..testcompartment",
        "RETALLY_OCI_VM_OCID": "ocid1.instance.oc1.iad.testinstance",
        "ACTIONS_ID_TOKEN_REQUEST_URL": "https://pipelines.actions.githubusercontent.com/oidc/token?a=b",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "dummy-gh-job-token",
        "RETALLY_OCI_RUN_APPROVED_SHA": "a" * 40,
        "GITHUB_SHA": "a" * 40,
        "GITHUB_RUN_ID": "1234567890",
        "GITHUB_RUN_ATTEMPT": "1",
    }


def claims():
    now = int(time.time())
    return {
        "iss": m.ISSUER, "aud": m.AUDIENCE, "sub": m.auth.SUBJECT,
        "repository": m.REPOSITORY, "repository_id": m.REPOSITORY_ID,
        "repository_owner_id": m.OWNER_ID, "workflow_ref": m.WORKFLOW_REF,
        "ref": "refs/heads/main", "event_name": "workflow_dispatch",
        "exp": now + 200, "iat": now - 2,
    }


class ContextTests(unittest.TestCase):
    def test_approved_manual_main_exact_sha_only(self):
        m.check_context(fixture())
        for key, value in [
            ("GITHUB_REF", "refs/heads/pr"), ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_EVENT_NAME", "schedule"), ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REPOSITORY_ID", "4"), ("GITHUB_REPOSITORY_OWNER_ID", "3"),
            ("GITHUB_WORKFLOW_REF", m.auth.WORKFLOW_REF),
            ("RETALLY_OCI_RUN_COMMAND_ENABLED", "false"),
            ("RETALLY_OCI_RUN_APPROVED_SHA", "b" * 40),
            ("GITHUB_SHA", "bad"), ("GITHUB_RUN_ID", "bad"), ("GITHUB_RUN_ATTEMPT", "0"),
            ("RETALLY_OCI_RUN_DOMAIN_URL", "http://idcs-abc.identity.oraclecloud.com"),
            ("RETALLY_OCI_RUN_DOMAIN_URL", "https://idcs-abc.identity.oraclecloud.com@evil.net"),
            ("ACTIONS_ID_TOKEN_REQUEST_URL", "https://evil.example/token"),
            ("ACTIONS_ID_TOKEN_REQUEST_URL", "https://bad.actions.githubusercontent.com/token"),
            ("RETALLY_OCI_VM_OCID", "bad"), ("RETALLY_OCI_COMPARTMENT_OCID", "bad"),
            ("RETALLY_OCI_RUN_CLIENT_SECRET", ""),
        ]:
            with self.subTest(key=key):
                env = fixture()
                env[key] = value
                with self.assertRaises(m.auth.Refused):
                    m.check_context(env)

    def test_shared_monitor_client_and_workflow_ref_are_rejected(self):
        env = fixture()
        env["RETALLY_OCI_CLIENT_ID"] = env["RETALLY_OCI_RUN_CLIENT_ID"]
        with self.assertRaisesRegex(m.auth.Refused, "SHARED_MONITOR_CREDENTIAL_REFUSED"):
            m.check_context(env)
        self.assertNotEqual(m.WORKFLOW_REF, m.auth.WORKFLOW_REF)

    def test_fail_closed_before_network_or_sdk_import(self):
        env = fixture()
        env["RETALLY_OCI_RUN_APPROVED_SHA"] = "0" * 40
        with patch.object(m, "get_github_jwt", side_effect=AssertionError("network called")):
            with self.assertRaises(m.auth.Refused):
                m.execute_canary(env)

    def test_sanitized_failure_does_not_print_secrets(self):
        env = fixture()
        env["RETALLY_OCI_RUN_CLIENT_SECRET"] = "SYNTHETIC_SECRET_NEVER_PRINT"
        env["GITHUB_REF"] = "refs/heads/bad"
        stream = io.StringIO()
        with patch.dict(m.os.environ, env, clear=True), patch("sys.stdout", stream):
            self.assertEqual(m.main(), 1)
        self.assertIn("INVALID_GITHUB_CONTEXT", stream.getvalue())
        self.assertNotIn("SYNTHETIC_SECRET_NEVER_PRINT", stream.getvalue())


class TokenTests(unittest.TestCase):
    def test_claims_exact_workflow_repository_and_expiry(self):
        m.check_claims(claims())
        c = claims()
        c["sub"] = m.auth.IMMUTABLE_SUBJECT
        m.check_claims(c)
        for key, value in [
            ("iss", "bad"), ("aud", "bad"), ("sub", "repo:attacker/repo"),
            ("repository_id", "123"), ("repository_owner_id", "123"),
            ("workflow_ref", m.auth.WORKFLOW_REF),
            ("ref", "refs/heads/dev"), ("event_name", "schedule"),
            ("exp", int(time.time()) - 1), ("exp", int(time.time()) + 1200),
            ("iat", int(time.time()) - 900),
        ]:
            with self.subTest(key=key):
                c = claims()
                c[key] = value
                with self.assertRaises(m.auth.Refused):
                    m.check_claims(c)

    def test_token_request_is_bounded_and_exact(self):
        c = claims()
        part = base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip("=")
        jwt = "header." + part + ".signature"
        with patch.object(m.auth, "json_response", return_value={"value": jwt}) as mock:
            self.assertEqual(m.get_github_jwt(fixture()), jwt)
            req = mock.call_args.args[0]
            self.assertEqual(req.get_header("Authorization"), "Bearer dummy-gh-job-token")
            self.assertIn("audience=https%3A%2F%2Fcloud.oracle.com", req.full_url)
        c["workflow_ref"] = "bad"
        part = base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip("=")
        with patch.object(m.auth, "json_response", return_value={"value": "h."+part+".s"}):
            with self.assertRaises(m.auth.Refused):
                m.get_github_jwt(fixture())


class ProviderTests(unittest.TestCase):
    def vm(self):
        return SimpleNamespace(
            id=fixture()["RETALLY_OCI_VM_OCID"],
            compartment_id=fixture()["RETALLY_OCI_COMPARTMENT_OCID"],
            shape=m.VM_SHAPE, lifecycle_state="RUNNING",
            agent_config=SimpleNamespace(are_all_plugins_disabled=False, plugins_config=[
                SimpleNamespace(name="Compute Instance Run Command", desired_state="ENABLED")]))

    def test_instance_identity_state_and_agent_config_fail_closed(self):
        m.check_vm(self.vm(), fixture())
        for key, value in [
            ("id", "other"), ("compartment_id", "other"),
            ("shape", "VM.Standard.A1.Flex"), ("lifecycle_state", "STOPPED"),
            ("agent_config", None),
        ]:
            with self.subTest(key=key):
                altered = SimpleNamespace(**{**vars(self.vm()), key:value})
                with self.assertRaises(m.auth.Refused):
                    m.check_vm(altered, fixture())
        altered = self.vm()
        altered.agent_config = SimpleNamespace(
            are_all_plugins_disabled=False, plugins_config=[
                SimpleNamespace(name="Compute Instance Run Command", desired_state="DISABLED")])
        with self.assertRaises(m.auth.Refused):
            m.check_vm(altered, fixture())

    def test_default_plugin_configuration_accepts_confirmed_running_plugin(self):
        for config in (None, [], [SimpleNamespace(name="Compute Instance Monitoring", desired_state="ENABLED")]):
            with self.subTest(config=config):
                vm = self.vm()
                vm.agent_config.plugins_config = config
                try:
                    m.check_vm(vm, fixture())
                except m.auth.Refused as exc:
                    self.fail("Valid OCI default plugin configuration rejected: " + str(exc))
                m.check_plugin([SimpleNamespace(name="Compute Instance Run Command", status="RUNNING")])
                with self.assertRaises(m.auth.Refused):
                    m.check_plugin([SimpleNamespace(name="Compute Instance Run Command", status="STOPPED")])

    def test_defaults_do_not_override_disabled_or_malformed_configuration(self):
        for disabled, config in (
            (True, None), (None, None), (False, {}), (False, "ENABLED"),
            (False, [SimpleNamespace(name="Compute Instance Run Command", desired_state="ENABLED")] * 2),
            (False, [SimpleNamespace(name="Compute Instance Run Command", desired_state="DISABLED")]),
        ):
            with self.subTest(disabled=disabled, config=config):
                vm = self.vm()
                vm.agent_config.are_all_plugins_disabled = disabled
                vm.agent_config.plugins_config = config
                with self.assertRaises(m.auth.Refused):
                    m.check_vm(vm, fixture())

    def test_plugin_must_be_running(self):
        m.check_plugin([SimpleNamespace(name="Compute Instance Run Command", status="RUNNING")])
        for state in ("STOPPED", "NOT_SUPPORTED", "INVALID", "UNKNOWN_ENUM_VALUE"):
            with self.subTest(state=state):
                with self.assertRaises(m.auth.Refused):
                    m.check_plugin([SimpleNamespace(
                        name="Compute Instance Run Command",status=state)])
        with self.assertRaises(m.auth.Refused):
            m.check_plugin([])

    def test_existing_command_poll_recovers_after_transient_404_without_recreate(self):
        command_id = "ocid1.instanceagentcommand.oc1.dummy"
        vm_id = fixture()["RETALLY_OCI_VM_OCID"]
        class NotVisible(Exception):
            status = 404
            code = "NotAuthorizedOrNotFound"
        terminal = SimpleNamespace(instance_agent_command_id=command_id,
            instance_id=vm_id, lifecycle_state="SUCCEEDED",
            content=SimpleNamespace(output_type="TEXT", exit_code=0,
                                    text=m.MARKER + "\\n"))
        command = Mock()
        command.get_instance_agent_command_execution.side_effect = [
            NotVisible(), NotVisible(), SimpleNamespace(data=terminal)]
        with patch.object(m.time, "sleep") as sleeper:
            m.poll_existing_command(command, command_id, vm_id, max_attempts=4,
                                    delay_seconds=1)
        self.assertEqual(command.get_instance_agent_command_execution.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)
        command.create_instance_agent_command.assert_not_called()

    def test_existing_command_poll_exhausts_404_without_recreate(self):
        command_id = "ocid1.instanceagentcommand.oc1.dummy"
        vm_id = fixture()["RETALLY_OCI_VM_OCID"]
        class NotVisible(Exception):
            status = 404
            code = "NotAuthorizedOrNotFound"
        command = Mock()
        command.get_instance_agent_command_execution.side_effect = NotVisible()
        with patch.object(m.time, "sleep") as sleeper:
            with self.assertRaisesRegex(m.auth.Refused, "EXECUTION_LOOKUP_UNVERIFIED"):
                m.poll_existing_command(command, command_id, vm_id,
                                        max_attempts=3, delay_seconds=1)
        self.assertEqual(command.get_instance_agent_command_execution.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)
        command.create_instance_agent_command.assert_not_called()

    def test_existing_command_poll_rejects_other_provider_errors_immediately(self):
        command_id = "ocid1.instanceagentcommand.oc1.dummy"
        vm_id = fixture()["RETALLY_OCI_VM_OCID"]
        for status, code in ((401, "NotAuthenticated"), (403, "Forbidden"),
                             (404, "InvalidParameter"), (429, "TooManyRequests"),
                             (500, "InternalError")):
            with self.subTest(status=status, code=code):
                exc = type("RemoteReadError", (Exception,),
                           {"status": status, "code": code})()
                command = Mock()
                command.get_instance_agent_command_execution.side_effect = exc
                with patch.object(m.time, "sleep") as sleeper:
                    with self.assertRaisesRegex(m.auth.Refused,
                                                "EXECUTION_LOOKUP_UNVERIFIED"):
                        m.poll_existing_command(command, command_id, vm_id,
                                                max_attempts=4, delay_seconds=1)
                command.get_instance_agent_command_execution.assert_called_once_with(
                    command_id, vm_id)
                sleeper.assert_not_called()
                command.create_instance_agent_command.assert_not_called()

    def test_existing_command_poll_rejects_mismatched_or_failed_execution(self):
        command_id = "ocid1.instanceagentcommand.oc1.dummy"
        vm_id = fixture()["RETALLY_OCI_VM_OCID"]
        for wrong_command, state in (("other", "SUCCEEDED"),
                                     (command_id, "FAILED")):
            with self.subTest(wrong_command=wrong_command, state=state):
                record = SimpleNamespace(instance_agent_command_id=wrong_command,
                    instance_id=vm_id, lifecycle_state=state,
                    content=SimpleNamespace(output_type="TEXT", exit_code=0,
                                            text=m.MARKER + "\\n"))
                command = Mock()
                command.get_instance_agent_command_execution.return_value = SimpleNamespace(
                    data=record)
                with patch.object(m.time, "sleep") as sleeper:
                    with self.assertRaises(m.auth.Refused):
                        m.poll_existing_command(command, command_id, vm_id,
                                                max_attempts=4, delay_seconds=1)
                sleeper.assert_not_called()
                command.create_instance_agent_command.assert_not_called()

    def test_poll_in_progress_then_success_bounded(self):
        command_id = "ocid1.instanceagentcommand.oc1.dummy"
        vm_id = fixture()["RETALLY_OCI_VM_OCID"]
        result = SimpleNamespace(instance_agent_command_id=command_id,
            instance_id=vm_id, lifecycle_state="IN_PROGRESS", content=None)
        success = SimpleNamespace(instance_agent_command_id=command_id,
            instance_id=vm_id, lifecycle_state="SUCCEEDED",
            content=SimpleNamespace(output_type="TEXT", exit_code=0,
                                    text=m.MARKER + "\\n"))
        command = Mock()
        command.get_instance_agent_command_execution.side_effect = [
            SimpleNamespace(data=result), SimpleNamespace(data=success)]
        with patch.object(m.time, "sleep") as sleeper:
            m.poll_existing_command(command, command_id, vm_id,
                                    max_attempts=2, delay_seconds=1)
        self.assertEqual(command.get_instance_agent_command_execution.call_count, 2)
        sleeper.assert_called_once_with(1)
        command.create_instance_agent_command.assert_not_called()

    def test_script_is_fixed_short_nonroot_and_no_write(self):
        self.assertLess(len(m.CANARY.encode()), 4096)
        self.assertIn('test "$(id -u)" -ne 0', m.CANARY)
        self.assertEqual(m.CANARY.count(m.MARKER), 1)
        for token in ("sudo", "rm ", "curl", "wget", "ssh", "git ", "oci ",
                      "apt ", "systemctl", "export ", "eval ", "base64"):
            self.assertNotIn(token, m.CANARY)

    def test_execution_requires_matching_target_terminal_success_exact_output(self):
        cmd = "ocid1.instanceagentcommand.oc1.dummy"
        vm = fixture()["RETALLY_OCI_VM_OCID"]
        payload = SimpleNamespace(output_type="TEXT", exit_code=0, text=m.MARKER+"\n")
        good = dict(instance_agent_command_id=cmd, instance_id=vm,
                    lifecycle_state="SUCCEEDED",content=payload)
        self.assertTrue(m.check_execution(SimpleNamespace(**good),cmd,vm))
        x = dict(good,lifecycle_state="IN_PROGRESS")
        self.assertFalse(m.check_execution(SimpleNamespace(**x),cmd,vm))
        for key,value in [
            ("instance_id","other"),("instance_agent_command_id","other"),
            ("lifecycle_state","FAILED"),("lifecycle_state","TIMED_OUT"),
            ("content",SimpleNamespace(output_type="TEXT",exit_code=1,text=m.MARKER+"\n")),
            ("content",SimpleNamespace(output_type="TEXT",exit_code=0,text="WRONG")),
        ]:
            with self.subTest(key=key):
                x=dict(good)
                x[key]=value
                with self.assertRaises(m.auth.Refused):
                    m.check_execution(SimpleNamespace(**x),cmd,vm)

    def test_command_payload_has_no_arbitrary_parameters_or_bucket_access(self):
        class Model:
            def __init__(self,**kw):
                self.__dict__.update(kw)
        types = SimpleNamespace(**{k:Model for k in (
            "CreateInstanceAgentCommandDetails","InstanceAgentCommandTarget",
            "InstanceAgentCommandContent","InstanceAgentCommandSourceViaTextDetails",
            "InstanceAgentCommandOutputViaTextDetails")})
        fake = SimpleNamespace(compute_instance_agent=SimpleNamespace(models=types))
        data = m.make_command_details(fake,fixture())
        self.assertEqual(data.execution_time_out_in_seconds,45)
        self.assertEqual(data.target.instance_id,fixture()["RETALLY_OCI_VM_OCID"])
        self.assertEqual(data.content.source.text,m.CANARY)
        self.assertFalse(hasattr(data.content,"command_string"))
        self.assertFalse(hasattr(data.content.source,"bucket_name"))


if __name__ == "__main__":
    unittest.main()
