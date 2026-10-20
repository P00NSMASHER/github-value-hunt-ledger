#!/usr/bin/env python3
"""GitHub OIDC to OCI RPST: narrowly scoped read-only synthetic Object Storage observation.

This is NOT a general CLI runner. No download, object mutation, VM or release action.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPOSITORY = "P00NSMASHER/github-value-hunt-ledger"
REPOSITORY_ID = "1376771019"
OWNER_ID = "22281248"
WORKFLOW_PATH = ".github/workflows/retally-oracle-readonly.yml"
ENVIRONMENT = "retally-oci-readonly"
AUDIENCE = "retally-oci-readonly-v1"
ISSUER = "https://token.actions.githubusercontent.com"
REGION = "us-ashburn-1"
BUCKET = "retally-synthetic-sealed-recovery"
EXPECTED_WORKFLOW_REF = f"{REPOSITORY}/{WORKFLOW_PATH}@refs/heads/main"
EXPECTED_SUB = f"repo:{REPOSITORY}:environment:{ENVIRONMENT}"
MAX_OBJECTS = 128
ALLOWED_EVENTS = frozenset(("schedule", "workflow_dispatch"))
LEGACY_RE = re.compile(r"synthetic-only/[a-f0-9]{24}\.rtbk\Z")
RECOVERY_RE = re.compile(r"synthetic-recovery/[a-f0-9]{32}\.rtbk\Z")


class Refused(RuntimeError):
    """Fixed-message failure; no provider response body is printed."""


def ensure(ok, reason="Read-only OCI observer refused unverified state."):
    if not ok:
        raise Refused(reason)


def require_runtime(env):
    required = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": EXPECTED_WORKFLOW_REF,
    }
    ensure(all(env.get(k) == v for k, v in required.items()),
           "GitHub repository, workflow or main-branch identity differs from pinned target.")
    ensure(env.get("GITHUB_EVENT_NAME") in ALLOWED_EVENTS,
           "Only scheduled and manual main-branch runs may use OCI identity.")
    ensure(all(env.get(k) for k in (
        "ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "RETALLY_OCI_IDENTITY_DOMAIN_URL", "RETALLY_OCI_OAUTH_CLIENT_ID",
        "RETALLY_OCI_OAUTH_CLIENT_SECRET")),
        "OCI federation configuration incomplete; no Oracle requests were sent.")


def validate_endpoint(url, *, github=False):
    try:
        p = urlsplit(url)
        host, port = (p.hostname or "").lower(), p.port
    except (ValueError, TypeError) as exc:
        raise Refused("Invalid identity endpoint URL.") from exc
    ensure(p.scheme == "https" and p.username is None and p.password is None
           and port in (None, 443), "Only HTTPS identity endpoints with default TLS port allowed.")
    ensure(host and not host.startswith(".") and ".." not in host and not p.fragment,
           "Invalid identity endpoint host.")
    if github:
        ensure(host == "token.actions.githubusercontent.com"
               or host.endswith(".actions.githubusercontent.com"),
               "GitHub OIDC endpoint host is unexpected.")
        ensure(p.path.startswith("/"), "GitHub OIDC path invalid.")
        return url
    ensure(host.endswith(".identity.oraclecloud.com")
           or host.endswith(".identity.oci.oraclecloud.com"),
           "Oracle identity domain must be a verified OCI domain.")
    ensure(p.path in ("", "/") and not p.query,
           "Oracle identity-domain URL cannot contain a path or query.")
    return f"https://{host}/oauth2/v1/token"


def safe_json(raw, *, max_bytes=20000):
    ensure(isinstance(raw, bytes) and 0 < len(raw) <= max_bytes,
           "Unexpected identity response size.")
    try:
        obj = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise Refused("Identity provider returned malformed JSON.") from exc
    ensure(isinstance(obj, dict), "Identity response root must be JSON object.")
    return obj


def request_json(request):
    class RejectRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise Refused("Identity endpoint redirected; refusing credential forwarding.")
    try:
        with build_opener(RejectRedirect).open(request, timeout=20) as response:
            ensure(response.status == 200, "Identity endpoint did not acknowledge request.")
            data = response.read(20001)
    except Refused:
        raise
    except Exception as exc:
        raise Refused("Identity endpoint request failed; no response contents logged.") from exc
    return safe_json(data)


def oidc_claims(token):
    ensure(isinstance(token, str) and 64 < len(token) <= 20000,
           "OIDC assertion missing or oversized.")
    parts = token.split(".")
    ensure(len(parts) == 3, "OIDC assertion is not a compact JWT.")
    try:
        payload = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        claims = safe_json(payload, max_bytes=12000)
    except Exception as exc:
        raise Refused("Malformed OIDC claims.") from exc
    return claims


def validate_claims(claims, *, now=None):
    expected = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": EXPECTED_SUB,
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "repository_owner_id": OWNER_ID,
        "ref": "refs/heads/main",
        "workflow_ref": EXPECTED_WORKFLOW_REF,
        "environment": ENVIRONMENT,
    }
    ensure(all(claims.get(k) == v for k, v in expected.items()),
           "OIDC claim binding does not match approved repository/workflow/environment.")
    ensure(claims.get("event_name") in ALLOWED_EVENTS,
           "OIDC event claim is not an approved trigger.")
    clock = int(time.time()) if now is None else now
    ensure(type(claims.get("exp")) is int and clock < claims["exp"] <= clock + 600,
           "OIDC expiry outside short validity window.")
    ensure(type(claims.get("iat")) is int and clock - 600 <= claims["iat"] <= clock + 60,
           "OIDC issuance time untrusted.")


def github_assertion(env):
    base = validate_endpoint(env["ACTIONS_ID_TOKEN_REQUEST_URL"], github=True)
    sep = "&" if urlsplit(base).query else "?"
    req = Request(base + sep + urlencode({"audience": AUDIENCE}),
                  headers={"Authorization": "bearer " + env["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
                           "Accept": "application/json"})
    token = request_json(req).get("value")
    validate_claims(oidc_claims(token))
    return token


def create_ephemeral_key(directory):
    private = directory / "rpst-key.pem"
    public = directory / "rpst-public.pem"
    commands = [
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
         "-out", str(private)],
        ["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)],
    ]
    old_umask = os.umask(0o077)
    try:
        for command in commands:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=20, check=False)
            ensure(result.returncode == 0, "Ephemeral key setup failed.")
        ensure(private.is_file() and public.is_file()
               and not (private.stat().st_mode & 0o077),
               "Ephemeral private key is not owner-only.")
        return private.read_text(encoding="ascii"), public.read_text(encoding="ascii")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("Ephemeral signing-key setup failed.") from exc
    finally:
        os.umask(old_umask)


def exchange_for_rpst(env, assertion, public_key):
    endpoint = validate_endpoint(env["RETALLY_OCI_IDENTITY_DOMAIN_URL"])
    client_id = env["RETALLY_OCI_OAUTH_CLIENT_ID"]
    client_secret = env["RETALLY_OCI_OAUTH_CLIENT_SECRET"]
    ensure(0 < len(client_id) <= 2000 and 0 < len(client_secret) <= 5000,
           "OCI confidential-client values invalid.")
    basic = base64.b64encode((client_id + ":" + client_secret).encode()).decode()
    form = urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "requested_token_type": "urn:oci:token-type:oci-rpst",
        "subject_token_type": "jwt",
        "subject_token": assertion,
        "public_key": public_key,
        "res_type": "githubactions",
        "rpst_exp": "20",
    }).encode("ascii")
    req = Request(endpoint, data=form, method="POST", headers={
        "Authorization": "Basic " + basic,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    token = request_json(req).get("token")
    ensure(isinstance(token, str) and 100 <= len(token) <= 20000,
           "OCI did not issue valid-looking RPST.")
    return token


def inspect_bucket(client):
    """Only GetNamespace, GetBucket and paginated ListObjects; never downloads bytes."""
    namespace = client.get_namespace().data
    ensure(isinstance(namespace, str)
           and re.fullmatch(r"[a-zA-Z0-9_-]{2,80}", namespace) is not None,
           "OCI namespace unavailable or invalid.")
    bucket = client.get_bucket(namespace, BUCKET).data
    fields = {
        "name": BUCKET,
        "public_access_type": "NoPublicAccess",
        "storage_tier": "Standard",
        "versioning": "Disabled",
        "object_events_enabled": False,
        "replication_enabled": False,
        "object_lifecycle_policy_etag": None,
    }
    ensure(all(hasattr(bucket, k) and type(getattr(bucket, k)) == type(v)
               and getattr(bucket, k) == v for k, v in fields.items()),
           "Synthetic bucket properties differ from accepted security baseline.")
    ensure(hasattr(bucket, "auto_tiering") and bucket.auto_tiering in (None, "Disabled"),
           "Bucket auto-tiering state unapproved.")
    legacy = recovery = total = 0
    marker = None
    seen = set()
    while True:
        kwargs = {"limit": 100, "start": marker} if marker else {"limit": 100}
        page = client.list_objects(namespace, BUCKET, **kwargs).data
        objects = getattr(page, "objects", None)
        ensure(isinstance(objects, list), "OCI listing lacks an explicit object list.")
        for item in objects:
            total += 1
            ensure(total <= MAX_OBJECTS, "Inventory exceeds conservative synthetic-only cap.")
            name = getattr(item, "name", None)
            ensure(isinstance(name, str), "OCI listed an invalid object name.")
            if LEGACY_RE.fullmatch(name):
                legacy += 1
            elif RECOVERY_RE.fullmatch(name):
                recovery += 1
            else:
                raise Refused("Synthetic-only bucket contains unexpected object; no bytes retrieved.")
        next_marker = getattr(page, "next_start_with", None)
        if next_marker is None or next_marker == "":
            break
        ensure(isinstance(next_marker, str) and next_marker not in seen,
               "OCI object pagination incomplete or cyclic.")
        seen.add(next_marker)
        marker = next_marker
    ensure(legacy <= 1, "More than one legacy canary; manual review required.")
    ensure(recovery == 0, "Stranded synthetic recovery ciphertext; manual review required.")
    return {
        "status": "OBSERVATION_OK_CUSTOMER_RELEASE_HOLD",
        "private_bucket": True,
        "legacy_synthetic_orphan_count": legacy,
        "recovery_test_object_count": recovery,
        "real_backup_restore_verified": False,
        "customer_release_authorized": False,
        "automatic_provider_mutation_enabled": False,
    }


def write_summary(report):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [
        "## RETALLY OCI observation (read-only)",
        "",
        "**LIVE OCI INVENTORY** completed; **NOT** recovery acceptance.",
        "",
        f"- Bucket private: **{report['private_bucket']}**",
        f"- Historical orphan: **{report['legacy_synthetic_orphan_count']}** (preserved)",
        f"- Stranded recovery objects: **{report['recovery_test_object_count']}**",
        "- Off-device restore: **NOT VERIFIED**",
        "- Customer release: **HOLD**",
        "- No upload, download, deletion, SSH, service install or VM operation.",
        "",
    ]
    try:
        with Path(path).open("a", encoding="utf-8") as output:
            output.write("\n".join(lines))
    except OSError as exc:
        raise Refused("GitHub run summary could not be written.") from exc


def main():
    try:
        env = dict(os.environ)
        require_runtime(env)
        import oci  # late import: offline tests make no provider calls
        assertion = github_assertion(env)
        with tempfile.TemporaryDirectory(prefix="retally-rpst-") as tmp:
            private, public = create_ephemeral_key(Path(tmp))
            token = exchange_for_rpst(env, assertion, public)
            signer = oci.auth.signers.EphemeralResourcePrincipalSigner(
                session_token=token, private_key=private, region=REGION)
            client = oci.object_storage.ObjectStorageClient(
                {"region": REGION}, signer=signer,
                retry_strategy=oci.retry.NoneRetryStrategy())
            report = inspect_bucket(client)
        write_summary(report)
        print("OCI read-only observation successful; customer release remains HOLD.")
        if report["legacy_synthetic_orphan_count"]:
            print("::warning::Historical synthetic canary remains unresolved and preserved.")
        return 0
    except Refused as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    except Exception:
        print("::error::OCI read-only observation failed closed; inspect private OCI audit. No mutation performed.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
