"""Exercise all seven synthetic branches inside an isolated 768 MiB container.

This is NOT performance acceptance for actual customers on a 1 GiB E2 Micro VM.
OCI capacity, device security, encrypted offsite recovery and independent approval
must be validated separately. No network access or real customer data is used.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time


def run(args: list[str], *, timeout: int) -> dict:
    response = subprocess.run(args, check=False, capture_output=True,
                              text=True, timeout=timeout)
    if response.returncode:
        print("ERROR: synthetic acceptance process failed, exit=",
              response.returncode, file=sys.stderr)
        # Synthetic-only stderr; not a place to dump real records.
        print(response.stderr[-1500:], file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(response.stdout)
    except (ValueError, TypeError):
        raise SystemExit("ERROR: synthetic test produced unexpected non-JSON output")


def smoke_http(workspace: Path) -> None:
    cmd = [sys.executable, "-m", "recoveryworks.workbench_server",
           "--workspace", str(workspace), "--port", "18765"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 18
        while True:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", 18765, timeout=3)
                connection.request("GET", "/")
                page = connection.getresponse()
                page.read()
                connection.close()
                if page.status == 200:
                    break
                raise AssertionError("static synthetic page inaccessible")
            except (ConnectionError, OSError):
                if time.monotonic() >= deadline:
                    raise AssertionError("synthetic service failed to start")
                time.sleep(0.2)

        for path, expected in (("/api/state", 403), ("/credentials.json", 404)):
            connection = http.client.HTTPConnection("127.0.0.1", 18765, timeout=3)
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            connection.close()
            assert response.status == expected, (path, response.status)

        connection = http.client.HTTPConnection("127.0.0.1", 18765, timeout=3)
        connection.request("GET", "/", headers={"Host": "attacker.invalid"})
        response = connection.getresponse()
        response.read()
        connection.close()
        assert response.status == 403
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=7)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    assert sys.platform == "linux", "this benchmark is Linux-only"
    assert os.environ.get("RETALLY_SYNTHETIC_ONLY") == "1"
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="retally-micro-synthetic-") as directory:
        workspace = Path(directory) / "workspace"
        report = run([sys.executable, "-m", "recoveryworks.seven_branch_simulation",
                      "--workspace", str(workspace), "--exercise"], timeout=660)
        assert report["simulation"] is True
        assert set(report["branches"]) == {
            "freight", "ap", "warranty_credit", "procurement",
            "rebate", "parcel", "utility"}
        assert all(v.get("journey") == "PASS" for v in report["branches"].values())
        assert report["real_customers"] == report["real_recovered_cents"] == 0
        assert report["external_actions_sent"] == 0
        assert report["commercially_validated"] is False
        assert report["production_certified"] is False
        assert report["restore_verified"] is True
        health = run([sys.executable, "-m", "recoveryworks.workbench_health",
                      "--workspace", str(workspace)], timeout=90)
        assert health["healthy"] is True
        assert health["simulation"] is True
        assert health["production_certified"] is False
        smoke_http(workspace)
        elapsed = time.monotonic() - started
        # Unix ru_maxrss is kilobytes on Linux; children were run sequentially.
        maximum_child_kib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        summary = {
            "schema": 1, "kind": "OCI E2 Micro resource-budget rehearsal",
            "simulation": True, "branch_journeys": 7, "health": "PASS",
            "backup_restore": "PASS", "http_isolation": "PASS",
            "memory_limit_mib": 768, "cpu_quota": 0.125,
            "measured_peak_child_rss_mib": round(maximum_child_kib / 1024, 1),
            "elapsed_seconds": round(elapsed, 1),
            "real_customers": 0, "external_actions": 0,
            "production_certified": False, "off_device_backup_verified": False,
        }
        print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
