"""Test original-vs-repaired RecoveryOS authorization atomicity on real PostgreSQL.

Uses actual RecoveryOS Phase 1-3 schema + M8 preparation function in ephemeral CI.
The SQL functions are faithful transaction-pattern reproductions of the old and
new TypeScript authorization handler, NOT calls into hosted Floot HTTP.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

CONTAINER = os.environ["M8_POSTGRES_CONTAINER_ID"]
HEAD = os.environ["RETALLY_TESTED_HEAD_SHA"]
assert HEAD == subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
SOURCE = Path("freight/mission8/floot/endpoints/recovery/payment_authorize_POST.ts").read_text()
assert 'db.transaction().execute(async trx =>' in SOURCE
assert '.forUpdate()' in SOURCE
assert 'trx.selectFrom("recoveryPaymentInstructions")' in SOURCE
assert 'trx.selectFrom("recoveryPaymentAuthorizations")' in SOURCE
assert 'trx.insertInto("recoveryPaymentAuthorizations")' in SOURCE

def statement(function, label, reference):
    return f"SELECT {function}('{label}','{reference}')"

def query(sql):
    r = subprocess.run(
        ["docker","exec",CONTAINER,"psql","-U","postgres","-d","recoveryos_m8",
         "-A","-t","-v","ON_ERROR_STOP=1","-c",sql],
        capture_output=True,text=True,timeout=50,
    )
    if r.returncode:
        return {"ok":False,"error":r.stderr.strip()}
    return {"ok":True,"result":r.stdout.strip()}

start = time.monotonic()
with ThreadPoolExecutor(max_workers=2) as executor:
    original = list(executor.map(
        lambda ref:query(statement("m10_unsafe_authorize","unsafe",ref)),
        ("first", "second"),
    ))
original_inserts = [x["result"] for x in original if x["ok"]]
original_rejections = [x["error"] for x in original if not x["ok"]]
assert len(original_inserts) == 1, f"Original race was not independently reproduced: {original}"
assert len(original_rejections) == 1
assert "duplicate key" in original_rejections[0].lower(), original_rejections[0]
assert "recovery_payment_authorizations_tenant_id_instruction_id_key" in original_rejections[0], original_rejections[0]
assert original_inserts[0].startswith("INSERT:")
assert query("SELECT count(*) FROM recovery_payment_authorizations WHERE instruction_id="
             "(SELECT instruction_id FROM m10_authorization_targets WHERE label='unsafe')")["result"] == "1"

with ThreadPoolExecutor(max_workers=32) as executor:
    repaired = list(executor.map(
        lambda i:query(statement("m10_locked_authorize","locked",f"ref-{i:03d}")),
        range(100),
    ))
assert all(x["ok"] for x in repaired), f"Fixed authorization generated failures: {[x for x in repaired if not x['ok']][:3]}"
inserted = [x["result"] for x in repaired if x["result"].startswith("INSERT:")]
replayed = [x["result"] for x in repaired if x["result"].startswith("REPLAY:")]
all_ids = [x["result"].split(":",1)[1] for x in repaired]
assert len(inserted) == 1 and len(replayed) == 99, (
    f"Expected 1 insert, 99 replays. Got {len(inserted)}, {len(replayed)}"
)
assert len(set(all_ids)) == 1, "Concurrent retries returned inconsistent authorization identities"
sql = """SELECT count(*)::text || '|' || min(authorized_cents)::text
FROM recovery_payment_authorizations WHERE instruction_id =
(SELECT instruction_id FROM m10_authorization_targets WHERE label='locked')"""
persisted = query(sql)
assert persisted == {"ok":True,"result":"1|2000"}, persisted

receipt = {
 "schema_version":1,
 "scope":"ACTUAL_RECOVERYOS_SCHEMA_POSTGRES_EQUIVALENT_AUTHORIZATION_NOT_HOSTED_HTTP",
 "tested_head_sha":HEAD,
 "staging_source_sha256":hashlib.sha256(SOURCE.encode()).hexdigest(),
 "postgres_18_or_16_ephemeral_ci":True,
 "original_concurrent_attempts":2,
 "original_one_insert_one_duplicate_constraint_rejection":True,
 "fixed_parallel_requests":100,
 "fixed_max_workers":32,
 "fixed_successful_original_inserts":len(inserted),
 "fixed_idempotent_replays":len(replayed),
 "fixed_distinct_authorization_ids":len(set(all_ids)),
 "fixed_persisted_authorization_rows":1,
 "fixed_authorized_cents":2000,
 "production_modified":False,
 "hosted_authenticated_authorization_verified":False,
 "historical_findings_closed":0,
 "duration_seconds":round(time.monotonic()-start,3),
}
Path("freight/mission8/ci_authorization_atomicity_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("M10_POSTGRES_AUTHORIZATION="+json.dumps(receipt,sort_keys=True))
