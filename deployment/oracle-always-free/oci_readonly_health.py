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
from urllib.error import HTTPError
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
# GitHub documents *.actions.githubusercontent.com for the token-request
# endpoint. Its hosted runners also use regional pipelinesghub* subdomains.
# Restrict to those exact GitHub-operated pipeline host shapes.
OIDC_REGIONAL_HOST = re.compile(
    r"pipelinesghub[a-z0-9]{1,24}\.actions\.githubusercontent\.com"
)
# Confirmed in authenticated GitHub-hosted run 39606539848. GitHub also
# serves job-scoped OIDC requests from regional run-actions-N-azure-REGION
# endpoints. Never accept an arbitrary domain or user-configured suffix.
OIDC_AZURE_RUNNER_HOST = re.compile(
    r"run-actions-[0-9]{1,3}-azure-[a-z0-9]{2,24}\.actions\.githubusercontent\.com"
)
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
        require(environ.get(key) == expected, "Untrusted GitHub execution context: " + key)
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
                "Missing required Oracle/GitHub monitor configuration: " + key)
    domain = urlparse(environ["RETALLY_OCI_DOMAIN_URL"])
    require(domain.scheme == "https" and bool(domain.hostname) and
            domain.hostname.endswith(".identity.oraclecloud.com") and
            not domain.username and not domain.password and not domain.port and
            domain.path in ("", "/") and not domain.query and not domain.fragment,
            "Identity-domain URL must be an OCI HTTPS identity domain origin")
    oidc = urlparse(environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    approved_oidc_host = (
        oidc.hostname == OIDC_HOST or
        OIDC_REGIONAL_HOST.fullmatch(oidc.hostname or "") is not None or
        OIDC_AZURE_RUNNER_HOST.fullmatch(oidc.hostname or "") is not None
    )
    approved_oidc_origin = (
        oidc.scheme == "https" and approved_oidc_host and
        not oidc.username and not oidc.password and not oidc.port and
        bool(oidc.path) and not oidc.fragment
    )
    if not approved_oidc_origin:
        # The request URL can contain a job-specific token path/query. Never
        # log those fields. Print only validated GitHub subdomain metadata.
        hostname = oidc.hostname or ""
        is_github_host = re.fullmatch(
            r"[a-z0-9][a-z0-9-]{1,62}\.actions\.githubusercontent\.com",
            hostname,
        ) is not None
        label = hostname.split(".", 1)[0] if is_github_host else "OTHER"
        print(
            "RETALLY OCI OIDC ORIGIN: label=" + label +
            " github_suffix=" + str(is_github_host) +
            " https=" + str(oidc.scheme == "https") +
            " port_explicit=" + str(oidc.port is not None) +
            " path_present=" + str(bool(oidc.path)) +
            " userinfo_present=" + str(bool(oidc.username or oidc.password)) +
            " fragment_present=" + str(bool(oidc.fragment))
        )
    require(approved_oidc_origin, "GitHub OIDC request endpoint is not trusted")
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


# Fixed allowlists only; provider messages, token URLs, JWTs and credentials
# must never appear in diagnostics or exception strings.
AUTH_HTTP_STATUSES = {400, 401, 403, 404, 405, 409, 422, 429, 500, 502, 503}
AUTH_OAUTH_ERRORS = {
    "invalid_client", "unauthorized_client", "invalid_grant",
    "invalid_request", "unsupported_grant_type", "access_denied",
}


def classify_auth_http_error(error: HTTPError) -> str:
    status = str(error.code) if type(error.code) is int and error.code in AUTH_HTTP_STATUSES else "other"
    category = "other"
    try:
        # Read a bounded response privately. Only the exact approved 'error'
        # category can escape; descriptions and unknown keys are discarded.
        raw = error.read(4097)
        if len(raw) <= 4096:
            doc = json.loads(raw)
            if isinstance(doc, dict) and doc.get("error") in AUTH_OAUTH_ERRORS:
                category = doc["error"]
    except Exception:
        pass
    return "AUTH_HTTP_" + status + "_" + category


def json_response(request: Request, limit: int = MAX_TOKEN) -> dict:
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(limit + 1)
    except HTTPError as exc:
        raise Refused(classify_auth_http_error(exc)) from None
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
    try:
        token = json_response(request).get("token")
    except Refused as exc:
        error_code = str(exc)
        if re.fullmatch(
            r"AUTH_HTTP_(?:400|401|403|404|405|409|422|429|500|502|503|other)_"
            r"(?:invalid_client|unauthorized_client|invalid_grant|invalid_request|"
            r"unsupported_grant_type|access_denied|other)",
            error_code,
        ):
            raise Refused("OCI_TOKEN_EXCHANGE_" + error_code) from None
        raise Refused("OCI_TOKEN_EXCHANGE") from None
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

    try:
        jwt = github_oidc_token(settings)
    except Exception:
        raise Refused("OIDC_TOKEN_OR_CLAIMS") from None
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()
    try:
        rpst = exchange_for_rpst(settings, jwt, public_pem)
    except Refused as exc:
        # The category was already reduced to a fixed non-secret allowlist.
        label = str(exc)
        if re.fullmatch(
            r"OCI_TOKEN_EXCHANGE_AUTH_HTTP_(?:400|401|403|404|405|409|422|429|500|502|503|other)_"
            r"(?:invalid_client|unauthorized_client|invalid_grant|invalid_request|"
            r"unsupported_grant_type|access_denied|other)",
            label,
        ):
            raise Refused(label) from None
        raise Refused("OCI_TOKEN_EXCHANGE") from None
    except Exception:
        raise Refused("OCI_TOKEN_EXCHANGE") from None
    # In-memory ephemeral key and RPST only. No OCI writes, object-list or GET.
    try:
        signer = oci.auth.signers.EphemeralResourcePrincipalSigner(
            session_token=rpst, private_key=private_pem, region=REGION)
    except Exception:
        raise Refused("OCI_SIGNER_INITIALIZATION") from None
    cfg = {"region": REGION, "additional_user_agent": "retally-oci-readonly-health/1"}
    no_retry = oci.retry.NoneRetryStrategy()
    try:
        storage = oci.object_storage.ObjectStorageClient(cfg, signer=signer,
                                                         retry_strategy=no_retry)
        compute = oci.core.ComputeClient(cfg, signer=signer, retry_strategy=no_retry)
    except Exception:
        raise Refused("OCI_CLIENT_INITIALIZATION") from None
    try:
        bucket = storage.get_bucket(settings["RETALLY_OCI_NAMESPACE"], BUCKET).data
        check_bucket(bucket, settings["RETALLY_OCI_COMPARTMENT_OCID"])
    except Exception:
        raise Refused("OCI_BUCKET_READ_OR_VALIDATION") from None
    try:
        vm = compute.get_instance(settings["RETALLY_OCI_VM_OCID"]).data
        check_instance(vm, settings["RETALLY_OCI_VM_OCID"],
                       settings["RETALLY_OCI_COMPARTMENT_OCID"])
    except Exception:
        raise Refused("OCI_INSTANCE_READ_OR_VALIDATION") from None


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


def safe_failure_code(exc: Exception) -> str:
    """Expose only fixed labels or configuration KEY NAMES, never values."""
    if isinstance(exc, Refused):
        label = str(exc)
        if re.fullmatch(
            r"(Untrusted GitHub execution context|Missing required Oracle/GitHub monitor configuration): [A-Z_]{2,64}",
            label,
        ):
            return label
        if re.fullmatch(
            r"OCI_TOKEN_EXCHANGE_AUTH_HTTP_(?:400|401|403|404|405|409|422|429|500|502|503|other)_"
            r"(?:invalid_client|unauthorized_client|invalid_grant|invalid_request|"
            r"unsupported_grant_type|access_denied|other)",
            label,
        ):
            return label
        if label in {
            "Only scheduled or manual main-branch execution is allowed",
            "Monitor is not explicitly enabled",
            "Identity-domain URL must be an OCI HTTPS identity domain origin",
            "GitHub OIDC request endpoint is not trusted",
            "Invalid OCI namespace",
            "Invalid OCI compartment/tenancy OCID",
            "Invalid expected VM OCID",
            "OIDC_TOKEN_OR_CLAIMS", "OCI_TOKEN_EXCHANGE",
            "OCI_SIGNER_INITIALIZATION", "OCI_CLIENT_INITIALIZATION",
            "OCI_BUCKET_READ_OR_VALIDATION", "OCI_INSTANCE_READ_OR_VALIDATION",
        }:
            return label
    return "UNCLASSIFIED_FAILURE"


def main() -> int:
    try:
        settings = require_env(os.environ)
        do_live_check(settings)
    except Exception as exc:
        # A bounded status label only. Never emit exception bodies or credentials.
        print("RETALLY OCI DIAG: " + safe_failure_code(exc))
        report(False)
        return 1
    report(True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
