"""Conservative GitHub issue notifications for RETALLY live-site audit.

Only a completed, trusted main-branch independent live audit can create or
close an incident. Raw Cloudflare edge 504 logs never trigger an issue.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

REPO = "P00NSMASHER/github-value-hunt-ledger"
WORKFLOW = "retally-live-publication-audit.yml"
LABEL = "retally-live-audit-incident"
TITLE = "RETALLY: independent live publication audit requires investigation"
ALLOWED_TRIGGER_EVENTS = frozenset({"schedule", "push", "workflow_dispatch"})
ALERT_CONCLUSIONS = frozenset({"failure", "timed_out"})
RECOVERY_CONCLUSIONS = frozenset({"success"})


def event_details(payload: dict) -> dict | None:
    """Reject untrusted scope before any write operation."""
    repo = payload.get("repository") or {}
    run = payload.get("workflow_run") or {}
    if repo.get("full_name") != REPO or run.get("head_branch") != "main":
        return None
    if run.get("event") not in ALLOWED_TRIGGER_EVENTS:
        return None
    status = run.get("conclusion")
    if status not in ALERT_CONCLUSIONS | RECOVERY_CONCLUSIONS:
        return None
    run_id = run.get("id")
    if not isinstance(run_id, int) or run_id <= 0:
        return None
    return {"id": run_id, "conclusion": status, "event": run["event"]}


def is_latest_trusted_run(run_id: int, results: list[dict]) -> bool:
    """Use the newest completed, actionable audit, not cancelled/running jobs.

    A cancelled or skipped newer run is not recovery evidence and must not
    suppress an older genuine failure. A newer running audit has no result yet.
    """
    candidates = [
        x for x in results
        if x.get("head_branch") == "main"
        and x.get("event") in ALLOWED_TRIGGER_EVENTS
        and x.get("status") == "completed"
        and x.get("conclusion") in ALERT_CONCLUSIONS | RECOVERY_CONCLUSIONS
        and isinstance(x.get("id"), int)
    ]
    return any(x["id"] == run_id for x in candidates) and run_id == max(
        (x["id"] for x in candidates), default=-1
    )


class GithubAPI:
    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub Actions incident token not configured")
        self.token = token
        self.base = "https://api.github.com/repos/" + REPO

    def call(self, method: str, path: str, data: dict | None = None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        request = Request(
            self.base + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "RETALLY-Live-Audit-Incident/1.0",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                contents = response.read(1_000_000)
                return json.loads(contents) if contents else {}
        except HTTPError as e:
            # Never echo the bearer token, raw body, or untrusted event text.
            if e.code == 404:
                return None
            raise RuntimeError(f"GitHub incident API {method} failed HTTP {e.code}") from None


def ensure_label(api: GithubAPI) -> None:
    label_url = "/labels/" + quote(LABEL, safe="")
    if api.call("GET", label_url) is not None:
        return
    api.call("POST", "/labels", {
        "name": LABEL,
        "color": "b60205",
        "description": "GitHub live-site audit failed; NOT raw Cloudflare cache misses",
    })


def open_incidents(api: GithubAPI) -> list[dict]:
    path = "/issues?" + urlencode({"state": "open", "labels": LABEL, "per_page": 100})
    items = api.call("GET", path)
    if not isinstance(items, list):
        raise RuntimeError("GitHub live-site incident listing was incomplete")
    return [x for x in items if x.get("title") == TITLE and "pull_request" not in x]


def run_url(run_id: int) -> str:
    return f"https://github.com/{REPO}/actions/runs/{run_id}"


def process(api: GithubAPI, details: dict) -> str:
    runs = api.call(
        "GET", "/actions/workflows/" + WORKFLOW + "/runs?branch=main&per_page=20"
    )
    if not isinstance(runs, dict) or not isinstance(runs.get("workflow_runs"), list):
        raise RuntimeError("Could not independently establish current live-audit run")
    matches = [x for x in runs["workflow_runs"] if x.get("id") == details["id"]]
    if len(matches) != 1 or any(
        x.get("status") != "completed" or
        x.get("head_branch") != "main" or
        x.get("event") != details["event"] or
        x.get("conclusion") != details["conclusion"]
        for x in matches
    ):
        raise RuntimeError("The triggering audit completion could not be verified")
    if not is_latest_trusted_run(details["id"], runs["workflow_runs"]):
        return "STALE_RUN_IGNORED"

    existing = open_incidents(api)
    link = run_url(details["id"])
    if details["conclusion"] in ALERT_CONCLUSIONS:
        message = (
            f"@P00NSMASHER — **Read-only live publication audit "
            f"{details['conclusion']}**: {link}\n\n"
            "An independent public GET/content/security check or the audit "
            "runner itself failed. Investigate the exact workflow job logs. "
            "**This does not prove customer-visible downtime.** Cloudflare "
            "Early Hints/Cache API internal 504 entries are not used as an "
            "alert trigger. The monitor must remain fail-closed for repeat "
            "504s, missing content, identity/security failures, and transport errors.\n\n"
            "Do not submit or transfer customer freight records during triage."
        )
        if existing:
            api.call("POST", f"/issues/{existing[0]['number']}/comments", {"body": message})
            return "ACTIVE_INCIDENT_UPDATED"
        ensure_label(api)
        api.call("POST", "/issues", {
            "title": TITLE, "body": message, "labels": [LABEL],
        })
        return "LIVE_AUDIT_INCIDENT_OPENED"

    if not existing:
        return "LIVE_AUDIT_PASSED_NO_OPEN_INCIDENT"
    message = (
        f"**Recovery evidence:** {link} completed successfully on main.\n\n"
        "The independent read-only public-site audit passed. This closes the "
        "GitHub audit-failure incident; it does not establish a historical "
        "zero-outage SLA or exclude unrelated customer reports."
    )
    for issue in existing:
        api.call("POST", f"/issues/{issue['number']}/comments", {"body": message})
        api.call("PATCH", f"/issues/{issue['number']}", {"state": "closed"})
    return "RECOVERY_EVIDENCED_AND_INCIDENT_CLOSED"


def main() -> None:
    payload = json.loads(
        Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")
    )
    details = event_details(payload)
    if details is None:
        print("IGNORED_UNTRUSTED_OR_NON_ACTIONABLE_WORKFLOW_EVENT")
        return
    api = GithubAPI(os.environ.get("GH_TOKEN", ""))
    print(process(api, details))


if __name__ == "__main__":
    main()
