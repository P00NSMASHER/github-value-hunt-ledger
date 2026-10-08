"""Exercise the ACTUAL checked-in RecoveryOS M8 PL/pgSQL function on ephemeral Postgres.

This does not invoke Floot's authenticated HTTP payment endpoint and does not
attest to real buyer, carrier, bank, or recovered cash.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

CONTAINER = os.environ.get("M8_POSTGRES_CONTAINER_ID")
if not CONTAINER:
    sys.exit("M8_POSTGRES_CONTAINER_ID missing; cannot pretend PostgreSQL was tested")

PAYLOAD = {
    "schema": 1, "tenant_id": "exact_t",
    "payer_id": "TEST_PAYER", "payee_id": "TEST_PAYEE",
    "currency": "USD", "amount_cents": 10_000,
    "purpose": "Synthetic exact retry concurrency test",
    "finding_ids": ["exact_finding"],
    "idempotency_key": "m8-ci-exact-replay-0001",
}
BODY = json.dumps(PAYLOAD, sort_keys=True, separators=(",", ":"))
FIXED_HASH = "a" * 64


def psql(sql):
    cp = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-d",
         "recoveryos_m8", "-A", "-t", "-F", "|", "-v", "ON_ERROR_STOP=1",
         "-c", sql],
        capture_output=True, text=True, timeout=45,
    )
    if cp.returncode:
        raise RuntimeError(cp.stderr.strip()[:400])
    return cp.stdout.strip()


def statement(body=BODY, digest=FIXED_HASH):
    escaped = body.replace("'", "''")
    return (
        "SELECT instruction_id,instruction_hash,replayed "
        "FROM recovery_prepare_financial_instruction("
        "'exact_t',(SELECT id FROM users WHERE email='exact.owner@example.invalid'),"
        f"'{escaped}'::jsonb,'{digest}')"
    )


expected_head = os.environ.get("RETALLY_TESTED_HEAD_SHA")
actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert expected_head and actual_head == expected_head, (
    f"CI tested unexpected commit {actual_head}, expected {expected_head}"
)

start = time.monotonic()
with ThreadPoolExecutor(max_workers=32) as executor:
    submitted = list(executor.map(lambda _: psql(statement()), range(100)))
elapsed = round(time.monotonic() - start, 3)

parts = [row.split("|") for row in submitted]
assert len(parts) == 100, "100 attempts were not completed"
assert all(len(p) == 3 for p in parts), "Malformed function response"
ids = [p[0] for p in parts]
assert len(set(ids)) == 1, f"Replay IDs not stable: {len(set(ids))}"
assert all(p[1] == FIXED_HASH for p in parts), "Instruction digest inconsistent"
insert_count = sum(p[2] == "f" for p in parts)
replay_count = sum(p[2] == "t" for p in parts)
assert (insert_count, replay_count) == (1, 99), (
    f"Duplicate preparation acceptance: {insert_count} inserts, {replay_count} replays"
)

quantities = psql(
    "SELECT (SELECT count(*) FROM recovery_payment_instructions "
    "WHERE tenant_id='exact_t'),"
    "(SELECT count(*) FROM recovery_value_allocations WHERE tenant_id='exact_t'),"
    "(SELECT coalesce(sum(amount_cents),0) FROM recovery_value_allocations "
    "WHERE tenant_id='exact_t')"
)
assert quantities == "1|1|10000", f"Allocation conservation failed: {quantities}"

altered = dict(PAYLOAD, amount_cents=9_000)
altered_text = json.dumps(altered, sort_keys=True, separators=(",", ":"))
proc = subprocess.run(
    ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-d",
     "recoveryos_m8", "-v", "ON_ERROR_STOP=1", "-c",
     statement(altered_text, "b" * 64)],
    capture_output=True, text=True, timeout=45,
)
assert proc.returncode != 0, "Conflicting financial terms unexpectedly accepted"
assert "idempotency" in proc.stderr.lower(), "Conflicting retry failed for unrelated reason"
assert psql("SELECT count(*) FROM recovery_payment_instructions WHERE tenant_id='exact_t'") == "1"

receipt = {
    "schema_version": 1,
    "scope": "ACTUAL_M8_POSTGRES_FUNCTION_EPHEMERAL_SYNTHETIC_NOT_HTTP",
    "tested_head_sha": actual_head,
    "workflow_event_sha": os.environ.get("GITHUB_SHA"),
    "fixture_sha256": hashlib.sha256(Path("freight/mission8/ci_same_key_setup.sql").read_bytes()).hexdigest(),
    "payload_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
    "attempts": 100, "max_parallel_workers": 32,
    "insert_count": insert_count, "replay_count": replay_count,
    "distinct_instruction_ids": len(set(ids)),
    "persisted_instruction_rows": 1, "persisted_allocation_rows": 1,
    "allocated_cents": 10_000, "conflicting_financial_retry_rejected": True,
    "measured_seconds": elapsed,
    "hosted_floot_endpoint_tested": False,
    "buyer_bank_carrier_authority_verified": False,
    "production_changed": False,
    "historical_defects_closed": 0,
}
out = Path("freight/mission8/ci_same_key_receipt.json")
out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print("M8_ACTUAL_PG_FUNCTION_" + json.dumps(receipt, sort_keys=True))
