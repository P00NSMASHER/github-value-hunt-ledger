"""Run the pinned CPU model in Prime, retain its unmodified output and verify a scoped proposal."""
import argparse
import difflib
import json
import os
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1]
BASE = ("Fix this SQLite insert in create_lead.sql. The table leads(external_id TEXT NOT NULL) has no "
        "unique index. Retrying the same reference must produce one row; different references must be "
        "preserved. ")
HINT = ("Use INSERT ... SELECT with a NOT EXISTS predicate. Do not use ON CONFLICT or change the schema. "
        "Use SQLite set subtraction (EXCEPT) between a singleton candidate and stored external IDs. ")
MODEL = "qwen2.5-coder-0.5b"


def generate(prime, weights, work, prompt):
    ack = False
    model = None
    started = time.monotonic()
    proc = subprocess.Popen(["bash", str(PILOT/"sandbox.sh"), prime, work, "cpu", weights],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for command in [{"id":"model", "type":"get_state"},
                        {"id":"local-001", "type":"prompt", "message":prompt}]:
            proc.stdin.write(json.dumps(command).encode() + b"\n")
        proc.stdin.flush()
        data = b""
        received = 0
        while time.monotonic() - started < 25:
            if not select.select([proc.stdout], [], [], 1)[0]:
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Prime exited before the model finished")
            received += len(chunk)
            if received > 1024 * 1024:
                raise RuntimeError("RPC output budget exceeded")
            data += chunk
            while b"\n" in data:
                line, data = data.split(b"\n", 1)
                event = json.loads(line)
                if event.get("id") == "model":
                    model = event["data"]["model"]["id"]
                if event.get("id") == "local-001":
                    ack = event.get("success") is True
                if event["type"] == "agent_end":
                    msg = next(m for m in reversed(event["messages"]) if m["role"] == "assistant")
                    if not ack or model != MODEL or msg["stopReason"] != "stop" or msg["usage"]["output"] <= 0:
                        raise RuntimeError("Unverified RPC result: " + str(msg.get("errorMessage", "")))
                    return {"id":"local-001", "model":model, "ack":ack, "prompt":prompt, "usage":msg["usage"],
                            "answer":msg["content"][0]["text"], "elapsed_seconds":round(time.monotonic()-started,2)}
        raise TimeoutError("Prime CPU job exceeded its wall budget")
    finally:
        proc.kill()
        proc.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prime", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)/"work"
        validator = [sys.executable, str(PILOT/"verify.py")]
        subprocess.run([*validator, "--init-fixture", str(work)], check=True, stdout=subprocess.DEVNULL)
        source = (work/"create_lead.sql").read_text()
        for attempt, hint in enumerate(["Do not change the schema. ", HINT], start=1):
            prompt = BASE + hint + "Return exactly the proposed SQL, no prose. Current file:\n" + source
            job = generate(args.prime.resolve(), args.weights.resolve(), work, prompt)
            answer = job["answer"].strip()
            if answer.startswith("```") and answer.endswith("```"):
                answer = "\n".join(answer.splitlines()[1:-1])
            diff = "".join(difflib.unified_diff(source.splitlines(True), (answer.strip()+"\n").splitlines(True),
                                                "a/create_lead.sql", "b/create_lead.sql"))
            (args.output/f"attempt-{attempt}.patch").write_text(diff)
            checked = subprocess.run(validator, input=diff, text=True, capture_output=True, timeout=5)
            job["status"] = "verified" if checked.returncode == 0 else "rejected"
            job["verifier"] = json.loads(checked.stdout) if checked.returncode == 0 else checked.stderr.splitlines()[-1]
            job["environment"] = "synthetic Prime CPU worker | no network | local weights"
            (args.output/f"attempt-{attempt}.json").write_text(json.dumps(job, indent=2)+"\n")
            print(job["status"], "attempt", attempt, flush=True)
            if checked.returncode == 0:
                return
        raise SystemExit("Neither model proposal passed the independent verifier")


if __name__ == "__main__":
    main()
