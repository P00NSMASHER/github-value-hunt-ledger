"""Negative HTTP acceptance against the ACTUAL unpublished M8 Floot endpoints.

No user credentials, API keys, real payment references, or provider operations.
The only allowed target is the existing independently isolated M8 sandbox.
"""
import hashlib
import json
import os
import sys
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

HOST = "https://41bb5a26-a38a-4a93-ae8d-a07f9e11f77b.sandbox.floot.app"
assert HOST.endswith(".sandbox.floot.app") and "freight-recoveryos" not in HOST

scenarios = [
    ("GET", "/_api/recovery/payments", None),
    ("POST", "/_api/recovery/payment_prepare", {
        "payerId": "SIM-UNAUTHENTICATED-ONLY",
        "payeeId": "SIM-UNAUTHENTICATED-ONLY",
        "currency": "USD",
        "amountCents": 1000,
        "purpose": "Negative staging authentication regression",
        "findingIds": ["m9-missing-synthetic-reference"],
        "idempotencyKey": "m9-unauthenticated-http-0001",
    }),
    ("POST", "/_api/recovery/payment_authorize", {
        "instructionId": "m9-missing-synthetic-reference",
        "reason": "Negative staging authentication regression",
    }),
    ("POST", "/_api/recovery/payment_event", {
        "instructionId": "m9-missing-synthetic-reference",
        "state": "SUBMITTED",
        "provider": "SIMULATED_ONLY",
        "providerReference": "NOT_REAL",
        "amountCents": 1000,
        "sourceHash": "a" * 64,
        "occurredAt": "2026-10-08T12:00:00Z",
    }),
]

def exercise(method, path, body):
    data = json.dumps({"json": body}).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Origin": HOST}
    req = Request(HOST + path, data=data, headers=headers, method=method)
    # Sandbox builds can briefly return a non-API response while warming.
    # Retry only unparseable responses. Never count them as passing, and never
    # treat an incorrect authenticated/authorization status as success.
    payload = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as resp:
                status = resp.status
                raw = resp.read(4096)
        except HTTPError as err:
            status = err.code
            raw = err.read(4096)
        try:
            payload = json.loads(raw)["json"]
            break
        except (ValueError, KeyError, TypeError):
            if attempt == 2:
                snippet = raw[:100].decode("utf-8", "replace")
                raise AssertionError(
                    f"{path}: non-JSON Floot response after 3 attempts "
                    f"(HTTP {status}, starts {snippet!r})"
                ) from None
            time.sleep(0.6)
    assert status == 401, f"{path}: expected 401, received {status}"
    assert payload.get("error") == "Not authenticated", (
        f"{path}: incorrect rejection payload {payload!r}"
    )
    return {"method": method, "path": path, "status": status, "result": "PASS"}

start = time.monotonic()
blocked_reason = None
try:
    tests = [exercise(*s) for s in scenarios]
    verdict = "PASS"
except Exception as exc:
    blocked_reason = str(exc)[:420]
    verdict = "BLOCKED" if "sandbox access denied" in blocked_reason.lower() else "FAIL"
    tests = []
files = {
    name: Path(f"freight/mission8/floot/endpoints/recovery/{name}").read_bytes()
    for name in ["payment_prepare_POST.ts","payment_authorize_POST.ts",
                 "payment_event_POST.ts","payments_GET.ts"]
}
receipt = {
    "schema_version": 1,
    "scope": "REAL_UNPUBLISHED_FLOOT_M8_STAGING_NEGATIVE_HTTP_NO_AUTH",
    "staging_project_id": "41bb5a26-a38a-4a93-ae8d-a07f9e11f77b",
    "tested_head_sha": os.environ.get("RETALLY_TESTED_HEAD_SHA"),
    "app_endpoint_snapshot_hashes": {
        k: hashlib.sha256(v).hexdigest() for k,v in files.items()
    },
    "tests": tests,
    "verdict": verdict,
    "blocker": blocked_reason,
    "duration_seconds": round(time.monotonic()-start,3),
    "credentials_sent": False,
    "production_touched": False,
    "authenticated_positive_flow_verified": False,
    "settlement_cash_verified": False,
    "historical_findings_closed": 0,
}
assert receipt["tested_head_sha"], "Missing pinned source identity"
Path("freight/mission8/ci_negative_http_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print("M9_STAGING_HTTP_NEGATIVE="+json.dumps(receipt,sort_keys=True))
if verdict != "PASS":
    sys.exit(1)
