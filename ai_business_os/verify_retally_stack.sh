#!/usr/bin/env bash
# Fresh, sequential acceptance against private prepared pins. Usage in VERIFY_RETALLY_STACK.md.
set -euo pipefail
umask 077
repo=$(cd "$(dirname "$0")/.." && pwd)
work=$(realpath -m "${1:?Supply a NEW private directory outside the RETALLY checkout}")
case "$work/" in "$repo/"*) echo "Choose a private directory outside the checkout" >&2; exit 2;; esac
cache=$(realpath "${RETALLY_PILOT_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/retally-pilot}")
sources=$(realpath "${RETALLY_UPSTREAM_ROOT:?Set RETALLY_UPSTREAM_ROOT to the directory containing postmill/ and prime/}")
python="$cache/venv/bin/python"
pg_bin=${RETALLY_POSTGRES_BIN:-/usr/lib/postgresql/17/bin}
pg_share=${RETALLY_POSTGRES_SHARE:-/usr/share/postgresql/17}
redis=${RETALLY_REDIS_SERVER:-/usr/bin/redis-server}
go_bin=${RETALLY_GO_BIN:-go}
model=${RETALLY_PRIME_GGUF:-}
app="$repo/ai_business_os"
for bin in "$python" "$cache/gopher-server" "$cache/create-admin" "$pg_bin/initdb" "$redis"; do
    [[ -x "$bin" ]] || { echo "Missing prepared executable: $bin" >&2; exit 2; }
done
for bin in "$cache/gopher-server" "$cache/create-admin"; do
    info=$("$go_bin" version -m "$bin")
    [[ "$info" == *'vcs.revision=ae53d6dbb251e33484207756cc9699bd316834a7'* && "$info" == *'vcs.modified=false'* ]] ||
        { echo "Unexpected GopherCRM binary provenance: $bin" >&2; exit 2; }
done
[[ -f "$app/prime_pilot/node_modules/@electric-sql/pglite/package.json" ]] ||
    { echo "Install prime_pilot's locked dependencies before running acceptance." >&2; exit 2; }
if [[ -n "$model" ]]; then
    model=$(realpath "$model")
fi
mkdir -p "$(dirname "$work")"
mkdir -m 700 "$work"  # fail if a prior run or symlink already occupies this path
cd "$repo"
echo "Running pinned Postmill draft write, revision and restart proof"
"$python" "$app/postmill-local-proof.py" --upstream "$sources/postmill" --state "$work/postmill" \
    --pg-bin "$pg_bin" --pg-share "$pg_share" --redis "$redis" > "$work/postmill-run.log"
options=()
[[ -z "${RETALLY_SOURCE_PDF:-}" ]] || options+=(--source-pdf "$RETALLY_SOURCE_PDF")
echo "Running intake, CRM outage and restore, freight and CaptureBrief"
"$python" -m ai_business_os.retally_pilot --workspace "$work/desk" --gopher "$cache/gopher-server" \
    --admin "$cache/create-admin" --capturebrief "$cache/capturebrief" \
    --postmill-receipt "$work/postmill/receipt.json" "${options[@]}" > "$work/desk-run.log"
echo "Running Prime Agent lease and independent patch verification with the replay fixture"
node "$app/prime_pilot/pilot.mjs" "$sources/prime" > "$work/prime-replay.json"
if [[ -n "$model" ]]; then
    echo "Running Prime Agent with the local CPU model and independent verifier"
    "$python" "$app/prime_pilot/cpu/run.py" "$sources/prime" "$model" "$work/prime-cpu"
fi
"$python" - "$work" <<'PY'
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

work = Path(sys.argv[1])
def load(name):
    return json.loads((work/name).read_bytes())

post, desk, prime = (load(path) for path in ("postmill/receipt.json", "desk/acceptance.json", "prime-replay.json"))
for path in ("desk/desk.sqlite", "desk/restore/desk.sqlite"):
    with sqlite3.connect(f"file:{work/path}?mode=ro", uri=True) as db:
        ids = dict(db.execute("SELECT slug,remote_id FROM social_calendar"))
        if ids != post["draft_ids_after_restart"]:
            raise ValueError(f"Draft IDs in {path} differ from this Postmill run")
if not (desk["restore_readback"] and desk["restored_key_rotated"] and len(desk["crm_readback"]) == 2 and
        prime["real_model_job"] is False and prime["current_lease_required"] and
        prime["patched_counts"] == {"fixture-A": 1, "fixture-B": 1}):
    raise ValueError("A required component receipt failed validation")
receipts = ["postmill/receipt.json", "desk/acceptance.json", "prime-replay.json"]
cpu_status = "not requested"
if (work/"prime-cpu").exists():
    attempts = sorted((work/"prime-cpu").glob("attempt-*.json"))
    if not attempts or not any(json.loads(p.read_bytes())["status"] == "verified" for p in attempts):
        raise ValueError("CPU inference did not yield an independently verified patch")
    for attempt in attempts:
        result = json.loads(attempt.read_bytes())
        patch = attempt.with_suffix(".patch")
        if result["status"] == "verified" and result["verifier"]["diff_sha256"] != hashlib.sha256(patch.read_bytes()).hexdigest():
            raise ValueError("CPU patch differs from independently verified content")
        receipts.extend([str(attempt.relative_to(work)), str(patch.relative_to(work))])
    cpu_status = "verified"
result = {"environment": "local synthetic", "same_drafts_in_fresh_and_restored_desk": True,
          "cpu_model": cpu_status, "receipts": {name: hashlib.sha256((work/name).read_bytes()).hexdigest() for name in receipts}}
(work/"stack-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, sort_keys=True))
PY
