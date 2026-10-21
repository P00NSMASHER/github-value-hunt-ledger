#!/usr/bin/env python3
"""RETALLY read-only OCI monitor via tightly scoped GitHub OIDC -> OCI RPST.

No OCI user API keys, no customer objects, and no write operations. Live
execution is limited to the exact main-branch GitHub workflow; OCI independently
validates the JWT signature and trust claims.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "P00NSMASHER/github-value-hunt-ledger"
REPOSITORY_ID = "1376771019"
OWNER_ID = "22281248"
WORKFLOW = ".github/workflows/retally-oci-readonly.yml"
WORKFLOW_REF = f"{REPOSITORY}/{WORKFLOW}@refs/heads/main"
SUBJECT = f"repo:{REPOSITORY}:ref:refs/heads/main"
# GitHub repos created, renamed, or opted in after July 15 2026 use an
# immutable GitHub OIDC default sub with numeric owner and repository IDs.
IMMUTABLE_SUBJECT = (
    f"repo:P00NSMASHER@{OWNER_ID}/github-value-hunt-ledger@{REPOSITORY_ID}"
    ":ref:refs/heads/main"
)
AUDIENCE = "https://cloud.oracle.com"
ISSUER = "https://token.actions.githubusercontent.com"
REGION = "us-ashburn-1"
BUCKET = "retally-synthetic-sealed-recovery"
SHAPE = "VM.Standard.E2.1.Micro"
ALLOWED_EVENTS = {"schedule", "workflow_dispatch"}
OIDC_HOST = "pipelines.actions.githubusercontent.com"
MAX_TOKEN = 32768


class Refused(RuntimeError):
    """Non-sensitive validation error; never echo network exception bodies."""


def require(ok: bool, label: str) -> None:
    if not ok:
        raise Refused(label)


def require_env(environ: dict[str, str]) -> dict[str, str]:
    context = {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
    }
    for key, expected in context.items():
        require(environ.get(key) == expected, "Untrusted GitHub execution context")
    require(environ.get("GITHUB_EVENT_NAME") in ALLOWED_EVENTS,
            "Only scheduled or manual main-branch execution is allowed")
    require(environ.get("RETALLY_OCI_MONITOR_ENABLED") == "true",
            "Monitor is not explicitly enabled")
    required = (
        "RETALLY_OCI_DOMAIN_URL", "RETALLY_OCI_CLIENT_ID", "RETALLY_OCI_CLIENT_SECRET",
        "RETALLY_OCI_NAMESPACE", "RETALLY_OCI_COMPARTMENT_OCID", "RETALLY_OCI_VM_OCID",
        "ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    )
    for key in required:
        require(bool(environ.get(key, "").strip()),
                "Missing required Oracle/GitHub monitor configuration")
    domain = urlparse(environ["RETALLY_OCI_DOMAIN_URL"])
    require(domain.scheme == "https" and bool(domain.hostname) and
            domain.hostname.endswith(".identity.oraclecloud.com") and
            not domain.username and not domain.password and not domain.port and
            domain.path in ("", "/") and not domain.query and not domain.fragment,
            "Identity-domain URL must be an OCI HTTPS identity domain origin")
    oidc = urlparse(environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    require(oidc.scheme == "https" and oidc.hostname == OIDC_HOST and
            not oidc.username and not oidc.password and not oidc.port,
            "GitHub OIDC request endpoint is not trusted")
    require(re.fullmatch(r"[a-zA-Z0-9_-]{2,80}",
                         environ["RETALLY_OCI_NAMESPACE"]) is not None,
            "Invalid OCI namespace")
    compartment = environ["RETALLY_OCI_COMPARTMENT_OCID"]
    require(re.fullmatch(r"ocid1\.(compartment|tenancy)\.oc1\.[a-z0-9.-]+", compartment)
            is not None, "Invalid OCI compartment/tenancy OCID")
    require(re.fullmatch(r"ocid1\.instance\.oc1\.[a-z0-9.-]+",
                         environ["RETALLY_OCI_VM_OCID"]) is not None,
            "Invalid expected VM OCID")
    return dict(environ)


class NoRedirect(HTTPRedirectHandler):
    """Never forward GitHub bearer or OCI OAuth credentials to a redirect."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Refused("Authentication endpoint redirect refused")


def json_response(request: Request, limit: int = MAX_TOKEN) -> dict:
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(limit + 1)
    except Exception:
        raise Refused("Authentication service request failed (details withheld)") from None
    require(len(raw) <= limit, "Authentication service response too large")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise Refused("Authentication service returned invalid JSON") from None
    require(isinstance(result, dict), "Authentication service returned unexpected JSON")
    return result


def decode_claims_for_preflight(jwt: str) -> dict:
    """Unverified payload! OCI MUST verify signature and trust independently."""
    require(isinstance(jwt, str) and jwt.count(".") == 2 and len(jwt) <= MAX_TOKEN,
            "GitHub OIDC token shape invalid")
    try:
        part = jwt.split(".")[1]
        data = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
        claims = json.loads(data)
    except (ValueError, UnicodeDecodeError, TypeError):
        raise Refused("GitHub OIDC claim parsing failed") from None
    require(isinstance(claims, dict), "GitHub OIDC claim payload invalid")
    return claims


def validate_claims(claims: dict, event_name: str, now: int | None = None) -> None:
    """Defense in depth, not an authentication or JWT signature check."""
    # Exact legacy and immutable GitHub subjects; no patterns or wildcards.
    require(claims.get("sub") in (SUBJECT, IMMUTABLE_SUBJECT),
            "GitHub OIDC subject does not match the approved repository")
    for key, expected in {
        "iss": ISSUER, "aud": AUDIENCE,
        "repository": REPOSITORY, "repository_id": REPOSITORY_ID,
        "repository_owner_id": OWNER_ID, "workflow_ref": WORKFLOW_REF,
        "ref": "refs/heads/main", "event_name": event_name,
    }.items():
        require(claims.get(key) == expected,
                "GitHub OIDC claims did not match approved workload")
    now = int(time.time()) if now is None else now
    require(type(claims.get("exp")) is int and now < claims["exp"] <= now + 600,
            "GitHub OIDC JWT expired or unexpectedly long-lived")
    require(type(claims.get("iat")) is int and now - 600 <= claims["iat"] <= now + 60,
            "GitHub OIDC JWT issued outside permitted window")


def github_oidc_token(settings: dict[str, str]) -> str:
    endpoint = settings["ACTIONS_ID_TOKEN_REQUEST_URL"]
    separator = "&" if "?" in endpoint else "?"
    endpoint = endpoint + separator + urlencode({"audience": AUDIENCE})
    request = Request(endpoint, headers={
        "Authorization": "Bearer " + settings["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
        "Accept": "application/json",
    })
    result = json_response(request)
    jwt = result.get("value")
    validate_claims(decode_claims_for_preflight(jwt), settings["GITHUB_EVENT_NAME"])
    return jwt


def exchange_for_rpst(settings: dict[str, str], github_jwt: str, public_pem: str) -> str:
    # A dedicated, NON-ADMIN identity-domain OAuth client may invoke token
    # exchange only. It is not itself a blanket OCI API authorization.
    credentials = (settings["RETALLY_OCI_CLIENT_ID"] + ":" +
                   settings["RETALLY_OCI_CLIENT_SECRET"]).encode()
    basic = base64.b64encode(credentials).decode("ascii")
    url = settings["RETALLY_OCI_DOMAIN_URL"].rstrip("/") + "/oauth2/v1/token"
    payload = urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "requested_token_type": "urn:oci:token-type:oci-rpst",
        "public_key": public_pem, "subject_token": github_jwt,
        "subject_token_type": "jwt", "res_type": "ref_github", "rpst_exp": "20",
    }).encode("utf-8")
    request = Request(url, data=payload, method="POST", headers={
        "Authorization": "Basic " + basic,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    token = json_response(request).get("token")
    require(isinstance(token, str) and token.count(".") == 2 and len(token) <= MAX_TOKEN,
            "OCI did not issue a valid-shaped RPST")
    return token


def check_bucket(bucket: object, expected_compartment: str) -> None:
    def value(name):
        return getattr(bucket, name, None)
    require(value("name") == BUCKET and value("public_access_type") == "NoPublicAccess",
            "Private bucket identity/access check failed")
    require(value("compartment_id") == expected_compartment,
            "Private bucket is not in the expected OCI compartment")
    require(value("storage_tier") == "Standard" and value("versioning") == "Disabled",
            "Private bucket storage-tier/versioning check failed")
    require(value("object_events_enabled") is False and
            value("replication_enabled") is False,
            "Private bucket events/replication check failed")
    require(value("auto_tiering") in (None, "Disabled"),
            "Unexpected automatic storage-tier change")


def check_instance(instance: object, expected_id: str,
                   expected_compartment: str) -> None:
    require(getattr(instance, "id", None) == expected_id,
            "OCI VM identity check failed")
    require(getattr(instance, "compartment_id", None) == expected_compartment,
            "OCI VM is not in the expected OCI compartment")
    require(getattr(instance, "shape", None) == SHAPE, "OCI VM shape changed")
    require(getattr(instance, "lifecycle_state", None) == "RUNNING",
            "OCI VM is not RUNNING")


def do_live_check(settings: dict[str, str]) -> None:
    # Imports only inside authorized live job; unit tests use stdlib only.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import oci

    jwt = github_oidc_token(settings)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()
    rpst = exchange_for_rpst(settings, jwt, public_pem)
    # In-memory ephemeral key and RPST only. No OCI writes, object-list or GET.
    signer = oci.auth.signers.EphemeralResourcePrincipalSigner(
        session_token=rpst, private_key=private_pem, region=REGION)
    cfg = {"region": REGION, "additional_user_agent": "retally-oci-readonly-health/1"}
    no_retry = oci.retry.NoneRetryStrategy()
    storage = oci.object_storage.ObjectStorageClient(cfg, signer=signer,
                                                     retry_strategy=no_retry)
    compute = oci.core.ComputeClient(cfg, signer=signer, retry_strategy=no_retry)
    bucket = storage.get_bucket(settings["RETALLY_OCI_NAMESPACE"], BUCKET).data
    check_bucket(bucket, settings["RETALLY_OCI_COMPARTMENT_OCID"])
    vm = compute.get_instance(settings["RETALLY_OCI_VM_OCID"]).data
    check_instance(vm, settings["RETALLY_OCI_VM_OCID"],
                   settings["RETALLY_OCI_COMPARTMENT_OCID"])


def report(ok: bool) -> None:
    print("RETALLY OCI HEALTH: PASS (private bucket and expected VM)" if ok else
          "RETALLY OCI HEALTH: FAIL (no changes attempted; customer release HOLD)")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as stream:
                stream.write("### RETALLY OCI read-only health\n\n")
                stream.write("- Result: **PASS**\n" if ok else "- Result: **FAIL / HOLD**\n")
                stream.write("- Scope: private synthetic bucket metadata and VM state only\n")
                stream.write("- Recovery exercise: **NOT executed**\n")
                stream.write("- Customer release: **HOLD**\n")
        except OSError:
            pass


def main() -> int:
    try:
        settings = require_env(os.environ)
        do_live_check(settings)
    except Exception:
        # No exception body, OCI identifier, JWT, key, secret or HTTP response in logs.
        report(False)
        return 1
    report(True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
