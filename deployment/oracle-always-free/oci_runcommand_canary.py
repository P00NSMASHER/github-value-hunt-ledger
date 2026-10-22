#!/usr/bin/env python3
"""RETALLY one-shot non-mutating Oracle Run Command proof from separate OIDC trust.

This is not a generic shell/deployment interface. The existing metadata-only
OCI monitor and its OAuth client must never be granted Run Command rights.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import sys
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request

import oci_readonly_health as auth

REPOSITORY = auth.REPOSITORY
OWNER_ID = auth.OWNER_ID
REPOSITORY_ID = auth.REPOSITORY_ID
WORKFLOW_REF = REPOSITORY + "/.github/workflows/retally-oci-runcommand-canary.yml@refs/heads/main"
ISSUER = auth.ISSUER
AUDIENCE = auth.AUDIENCE
REGION = auth.REGION
VM_SHAPE = auth.SHAPE
MARKER = "RETALLY_OCI_SYNTHETIC_CANARY_V1_OK"
CANARY = """#!/bin/bash
set -eu
# No input, no packages, no credentials, no network calls, no disk writes.
test "$(id -u)" -ne 0
test -r /proc/uptime
test -r /proc/meminfo
printf 'RETALLY_OCI_SYNTHETIC_CANARY_V1_OK\\n'
"""
EXPECTED_KEYS = {
    "GITHUB_REPOSITORY": REPOSITORY,
    "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
    "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
    "GITHUB_EVENT_NAME": "workflow_dispatch",
}
REQUIRED = (
    "RETALLY_OCI_RUN_DOMAIN_URL", "RETALLY_OCI_RUN_CLIENT_ID",
    "RETALLY_OCI_RUN_CLIENT_SECRET", "RETALLY_OCI_VM_COMPARTMENT_OCID",
    "RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID",
    "RETALLY_OCI_VM_OCID", "ACTIONS_ID_TOKEN_REQUEST_URL",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "RETALLY_OCI_RUN_APPROVED_SHA",
    "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
)


def check_context(env: dict[str, str]) -> None:
    for key, expected in EXPECTED_KEYS.items():
        auth.require(env.get(key) == expected, "INVALID_GITHUB_CONTEXT")
    auth.require(env.get("RETALLY_OCI_RUN_COMMAND_ENABLED") == "true", "RUN_COMMAND_DISABLED")
    for key in REQUIRED:
        auth.require(bool(env.get(key, "").strip()), "MISSING_CONFIGURATION")
    auth.require(re.fullmatch(r"[0-9a-f]{40}", env["GITHUB_SHA"]) is not None,
                 "SOURCE_SHA_INVALID")
    auth.require(env["GITHUB_SHA"] == env["RETALLY_OCI_RUN_APPROVED_SHA"],
                 "SOURCE_SHA_NOT_APPROVED")
    auth.require(re.fullmatch(r"[1-9][0-9]{0,19}", env["GITHUB_RUN_ID"]) is not None and
                 re.fullmatch(r"[1-9][0-9]{0,3}", env["GITHUB_RUN_ATTEMPT"]) is not None,
                 "INVALID_GITHUB_CONTEXT")
    domain = urlparse(env["RETALLY_OCI_RUN_DOMAIN_URL"])
    auth.require(domain.scheme == "https" and domain.hostname is not None and
                 domain.hostname.endswith(".identity.oraclecloud.com") and
                 domain.port is None and not domain.username and not domain.password and
                 domain.path in ("", "/") and not domain.query and not domain.fragment,
                 "UNTRUSTED_IDENTITY_DOMAIN")
    oidc = urlparse(env["ACTIONS_ID_TOKEN_REQUEST_URL"])
    host = oidc.hostname or ""
    allowed = (host == auth.OIDC_HOST or
               auth.OIDC_REGIONAL_HOST.fullmatch(host) is not None or
               auth.OIDC_AZURE_RUNNER_HOST.fullmatch(host) is not None)
    auth.require(oidc.scheme == "https" and allowed and bool(oidc.path) and
                 oidc.port is None and not oidc.username and not oidc.password and
                 not oidc.fragment, "UNTRUSTED_GITHUB_OIDC_ENDPOINT")
    auth.require(re.fullmatch(r"ocid1\.(compartment|tenancy)\.oc1\.[a-z0-9.-]+",
                                  env["RETALLY_OCI_VM_COMPARTMENT_OCID"]) is not None,
                 "COMPARTMENT_INVALID")
    auth.require(re.fullmatch(r"ocid1\.compartment\.oc1\.[a-z0-9.-]+",
                                  env["RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID"]) is not None,
                 "COMPARTMENT_INVALID")
    auth.require(env["RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID"] ==
                 env["RETALLY_OCI_VM_COMPARTMENT_OCID"], "COMPARTMENT_INVALID")
    auth.require(re.fullmatch(r"ocid1\.instance\.oc1\.[a-z0-9.-]+",
                                  env["RETALLY_OCI_VM_OCID"]) is not None,
                 "INSTANCE_INVALID")
    existing = env.get("GITHUB_INPUT_EXISTING_COMMAND_ID", "").strip()
    auth.require(not existing or re.fullmatch(
        r"ocid1\.instanceagentcommand\.oc1\.[a-z0-9.-]+", existing) is not None,
        "COMMAND_ID_INVALID")
    auth.require(env["RETALLY_OCI_RUN_CLIENT_ID"] != env.get("RETALLY_OCI_CLIENT_ID"),
                 "SHARED_MONITOR_CREDENTIAL_REFUSED")


def check_claims(claims: dict[str, object], now: int | None = None) -> None:
    accepted_subjects = {auth.SUBJECT, auth.IMMUTABLE_SUBJECT}
    auth.require(claims.get("sub") in accepted_subjects, "OIDC_CLAIMS_REJECTED")
    expected = {
        "iss": ISSUER, "aud": AUDIENCE, "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID, "repository_owner_id": OWNER_ID,
        "workflow_ref": WORKFLOW_REF, "ref": "refs/heads/main",
        "event_name": "workflow_dispatch",
    }
    auth.require(all(claims.get(k) == v for k, v in expected.items()),
                 "OIDC_CLAIMS_REJECTED")
    now = int(time.time()) if now is None else now
    auth.require(type(claims.get("exp")) is int and now < claims["exp"] <= now + 600 and
                 type(claims.get("iat")) is int and now - 600 <= claims["iat"] <= now + 60,
                 "OIDC_TOKEN_EXPIRED")


def get_github_jwt(env: dict[str, str]) -> str:
    url = env["ACTIONS_ID_TOKEN_REQUEST_URL"]
    url += ("&" if "?" in url else "?") + urlencode({"audience": AUDIENCE})
    req = Request(url, headers={
        "Authorization": "Bearer " + env["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
        "Accept": "application/json",
    })
    jwt = auth.json_response(req).get("value")
    claims = auth.decode_claims_for_preflight(jwt)
    check_claims(claims)
    return jwt


def check_vm(vm: object, env: dict[str, str]) -> None:
    auth.require(getattr(vm, "id", None) == env["RETALLY_OCI_VM_OCID"] and
                 getattr(vm, "compartment_id", None) == env["RETALLY_OCI_VM_COMPARTMENT_OCID"] and
                 getattr(vm, "shape", None) == VM_SHAPE and
                 getattr(vm, "lifecycle_state", None) == "RUNNING", "INSTANCE_NOT_APPROVED")
    agent = getattr(vm, "agent_config", None)
    auth.require(agent is not None and getattr(agent, "are_all_plugins_disabled", None) is False,
                 "AGENT_CONFIGURATION_UNVERIFIED")
    plugin_cfg = getattr(agent, "plugins_config", None)
    # Oracle omits overrides when the platform default is in effect. This
    # is not runtime proof: execute_canary still requires check_plugin(RUNNING).
    auth.require(plugin_cfg is None or isinstance(plugin_cfg, list),
                 "AGENT_CONFIGURATION_UNVERIFIED")
    matches = [p for p in (plugin_cfg or [])
               if getattr(p, "name", None) == "Compute Instance Run Command"]
    auth.require(not matches or (len(matches) == 1 and
                 getattr(matches[0], "desired_state", None) == "ENABLED"),
                 "RUN_PLUGIN_NOT_ENABLED")


def check_plugin(plugins: list[object]) -> None:
    matches = [p for p in plugins if getattr(p, "name", None) == "Compute Instance Run Command"]
    auth.require(len(matches) == 1 and getattr(matches[0], "status", None) == "RUNNING",
                 "RUN_PLUGIN_NOT_RUNNING")


def make_command_details(oci, env: dict[str, str]):
    m = oci.compute_instance_agent.models
    return m.CreateInstanceAgentCommandDetails(
        compartment_id=env["RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID"],
        execution_time_out_in_seconds=45,
        display_name="RETALLY synthetic no-write canary",
        target=m.InstanceAgentCommandTarget(instance_id=env["RETALLY_OCI_VM_OCID"]),
        content=m.InstanceAgentCommandContent(
            source=m.InstanceAgentCommandSourceViaTextDetails(text=CANARY),
            output=m.InstanceAgentCommandOutputViaTextDetails(),
        ),
    )


def check_execution(run: object, command_id: str, vm_id: str) -> bool:
    auth.require(getattr(run, "instance_agent_command_id", None) == command_id and
                 getattr(run, "instance_id", None) == vm_id,
                 "EXECUTION_IDENTITY_MISMATCH")
    status = getattr(run, "lifecycle_state", None)
    auth.require(status in ("ACCEPTED", "IN_PROGRESS", "SUCCEEDED"),
                 "EXECUTION_FAILED_OR_UNKNOWN")
    if status != "SUCCEEDED":
        return False
    output = getattr(run, "content", None)
    auth.require(output is not None and getattr(output, "output_type", None) == "TEXT" and
                 type(getattr(output, "exit_code", None)) is int and
                 output.exit_code == 0 and getattr(output, "text", None) == MARKER + "\n",
                 "EXECUTION_OUTPUT_REJECTED")
    return True


def list_exact_execution(command, compartment_id: str, command_id: str,
                         instance_id: str):
    response = command.list_instance_agent_command_executions(
        compartment_id, instance_id, limit=100)
    headers = getattr(response, "headers", {})
    auth.require(isinstance(headers, dict) and not headers.get("opc-next-page"),
                 "EXECUTION_LOOKUP_UNVERIFIED")
    items = getattr(response, "data", None)
    auth.require(isinstance(items, list), "EXECUTION_LOOKUP_UNVERIFIED")
    matches = [item for item in items
               if getattr(item, "instance_agent_command_id", None) == command_id]
    auth.require(len(matches) <= 1, "EXECUTION_IDENTITY_MISMATCH")
    return matches[0] if matches else None


def poll_existing_command(command, compartment_id: str, command_id: str, instance_id: str,
                          max_attempts: int = 45, delay_seconds: int = 4) -> None:
    """Poll the *same* accepted command. Never resubmit on lookup errors.

    OCI can return 404 for the per-command execution endpoint even after the
    record exists. On that exact error, use the documented compartment- and
    instance-bounded execution list, select the exact command ID, and retain
    the same strict identity/output validation. Neither path creates a command.
    """
    auth.require(max_attempts >= 1 and delay_seconds >= 0, "EXECUTION_LOOKUP_UNVERIFIED")
    for attempt in range(max_attempts):
        try:
            result = command.get_instance_agent_command_execution(
                command_id, instance_id).data
        except Exception as exc:
            if (getattr(exc, "status", None) == 404 and
                    getattr(exc, "code", None) in ("NotAuthorizedOrNotFound", "NotFound")):
                try:
                    result = list_exact_execution(
                        command, compartment_id, command_id, instance_id)
                except auth.Refused:
                    raise
                except Exception:
                    result = None
                if result is None:
                    if attempt + 1 < max_attempts:
                        time.sleep(delay_seconds)
                        continue
                    raise auth.Refused("EXECUTION_LOOKUP_UNVERIFIED") from None
            else:
                raise auth.Refused("EXECUTION_LOOKUP_UNVERIFIED") from None
        if check_execution(result, command_id, instance_id):
            return
        if attempt + 1 < max_attempts:
            time.sleep(delay_seconds)
    raise auth.Refused("EXECUTION_UNCONFIRMED_NO_RETRY")


def submit_or_reconcile(oci, command, env: dict[str, str]) -> bool:
    """Return True only when this invocation creates a command."""
    existing = env.get("GITHUB_INPUT_EXISTING_COMMAND_ID", "").strip()
    if existing:
        # Read once only. This mode exists to reconcile a known accepted
        # command without any chance of resubmission.
        poll_existing_command(command, env["RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID"],
                              existing, env["RETALLY_OCI_VM_OCID"],
                              max_attempts=1, delay_seconds=0)
        return False
    details = make_command_details(oci, env)
    request_key = hashlib.sha256((
        "retally-synthetic:" + env["GITHUB_RUN_ID"] + ":" + env["GITHUB_RUN_ATTEMPT"]
    ).encode()).hexdigest()
    try:
        created = command.create_instance_agent_command(
            details, opc_retry_token=request_key).data
    except Exception:
        raise auth.Refused("COMMAND_ACCEPTANCE_UNKNOWN_NO_RETRY") from None
    command_id = getattr(created, "id", None)
    auth.require(isinstance(command_id, str) and
                 command_id.startswith("ocid1.instanceagentcommand."),
                 "COMMAND_ACKNOWLEDGEMENT_INVALID")
    poll_existing_command(command, env["RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID"],
                          command_id, env["RETALLY_OCI_VM_OCID"])
    return True


def execute_canary(env: dict[str, str]) -> bool:
    check_context(env)  # Before importing OCI or doing any network I/O.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import oci
    try:
        jwt = get_github_jwt(env)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        der = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        exchange_env = {
            "RETALLY_OCI_CLIENT_ID": env["RETALLY_OCI_RUN_CLIENT_ID"],
            "RETALLY_OCI_CLIENT_SECRET": env["RETALLY_OCI_RUN_CLIENT_SECRET"],
            "RETALLY_OCI_DOMAIN_URL": env["RETALLY_OCI_RUN_DOMAIN_URL"],
        }
        rpst = auth.exchange_for_rpst(exchange_env, jwt, auth.encode_rpst_public_key(der))
        signer = oci.auth.signers.EphemeralResourcePrincipalSigner(
            session_token=rpst, private_key=pem, region=REGION)
    except Exception:
        raise auth.Refused("FEDERATED_AUTH_FAILED") from None

    try:
        cfg = {"region": REGION, "additional_user_agent": "retally-runcommand-canary/1"}
        noretry = oci.retry.NoneRetryStrategy()
        compute = oci.core.ComputeClient(cfg, signer=signer, retry_strategy=noretry)
        plugin = oci.compute_instance_agent.PluginClient(cfg, signer=signer,
                                                        retry_strategy=noretry)
        command = oci.compute_instance_agent.ComputeInstanceAgentClient(
            cfg, signer=signer, retry_strategy=noretry)
        check_vm(compute.get_instance(env["RETALLY_OCI_VM_OCID"]).data, env)
        check_plugin(plugin.list_instance_agent_plugins(
            env["RETALLY_OCI_VM_COMPARTMENT_OCID"], env["RETALLY_OCI_VM_OCID"],
            name="Compute Instance Run Command").data)
    except auth.Refused:
        raise
    except Exception:
        raise auth.Refused("PROVIDER_PREFLIGHT_FAILED") from None

    return submit_or_reconcile(oci, command, env)


PUBLIC_CODES = {
    "INVALID_GITHUB_CONTEXT", "RUN_COMMAND_DISABLED", "MISSING_CONFIGURATION",
    "SOURCE_SHA_INVALID", "SOURCE_SHA_NOT_APPROVED", "UNTRUSTED_IDENTITY_DOMAIN",
    "UNTRUSTED_GITHUB_OIDC_ENDPOINT", "COMPARTMENT_INVALID", "INSTANCE_INVALID",
    "COMMAND_ID_INVALID",
    "SHARED_MONITOR_CREDENTIAL_REFUSED", "OIDC_CLAIMS_REJECTED", "OIDC_TOKEN_EXPIRED",
    "INSTANCE_NOT_APPROVED", "AGENT_CONFIGURATION_UNVERIFIED", "RUN_PLUGIN_NOT_ENABLED",
    "RUN_PLUGIN_NOT_RUNNING", "EXECUTION_IDENTITY_MISMATCH",
    "EXECUTION_FAILED_OR_UNKNOWN", "EXECUTION_OUTPUT_REJECTED", "FEDERATED_AUTH_FAILED",
    "PROVIDER_PREFLIGHT_FAILED", "COMMAND_ACCEPTANCE_UNKNOWN_NO_RETRY",
    "COMMAND_ACKNOWLEDGEMENT_INVALID", "EXECUTION_LOOKUP_UNVERIFIED",
    "EXECUTION_UNCONFIRMED_NO_RETRY",
}


def main() -> int:
    try:
        created = execute_canary(dict(os.environ))
    except Exception as exc:
        print("RETALLY OCI REMOTE: HOLD " + (
            str(exc) if isinstance(exc, auth.Refused) and str(exc) in PUBLIC_CODES
            else "UNCLASSIFIED_FAILURE"))
        return 1
    print("RETALLY OCI REMOTE: PASS (" + (
        "one synthetic, no-write command on verified VM" if created else
        "existing accepted command reconciled; no command created") + ")")
    print("RETALLY CUSTOMER RELEASE: HOLD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
