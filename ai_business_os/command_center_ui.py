"""Server-rendered CEO Command Center UI helpers.

No production credential is sent to the browser. The UI uses a separate access-code hash to mint
short-lived signed HttpOnly sessions. All production reads/writes are executed by the runtime on the
server through the existing bounded gateway.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import time
from collections.abc import Mapping, Sequence
from typing import Any

SESSION_COOKIE = "__Host-aibos_ceo"
SESSION_TTL_SECONDS = 12 * 60 * 60


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def access_code_matches(access_code: str, expected_sha256: str) -> bool:
    supplied = hashlib.sha256(str(access_code).encode("utf-8")).hexdigest()
    expected = str(expected_sha256).strip().lower()
    return len(expected) == 64 and hmac.compare_digest(supplied, expected)


def issue_session(
    session_secret: str,
    principal: str,
    *,
    now: int | None = None,
    ttl_seconds: int = SESSION_TTL_SECONDS,
) -> str:
    if not session_secret or not principal:
        raise ValueError("session secret and principal are required")
    current = int(time.time() if now is None else now)
    payload = {
        "v": 1,
        "principal": principal,
        "iat": current,
        "exp": current + int(ttl_seconds),
        "nonce": secrets.token_urlsafe(16),
    }
    encoded = _b64e(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        session_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def validate_session(
    token: str,
    session_secret: str,
    expected_principal: str,
    *,
    now: int | None = None,
) -> dict[str, Any] | None:
    try:
        encoded, supplied_sig = str(token).rsplit(".", 1)
    except ValueError:
        return None
    expected_sig = hmac.new(
        session_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied_sig, expected_sig):
        return None
    try:
        payload = json.loads(_b64d(encoded).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("v") != 1:
        return None
    if payload.get("principal") != expected_principal:
        return None
    current = int(time.time() if now is None else now)
    try:
        issued = int(payload["iat"])
        expires = int(payload["exp"])
    except (KeyError, TypeError, ValueError):
        return None
    if issued > current + 60 or expires <= current or expires - issued > SESSION_TTL_SECONDS:
        return None
    return payload


def csrf_token(session_token: str, session_secret: str) -> str:
    return hmac.new(
        session_secret.encode("utf-8"),
        ("csrf:" + session_token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def csrf_matches(session_token: str, session_secret: str, supplied: str) -> bool:
    expected = csrf_token(session_token, session_secret)
    return hmac.compare_digest(str(supplied), expected)


def session_cookie(token: str) -> str:
    return (
        f"{SESSION_COOKIE}={token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; "
        "HttpOnly; Secure; SameSite=Strict"
    )


def clear_session_cookie() -> str:
    return f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict"


def parse_session_cookie(cookie_header: str) -> str:
    for part in str(cookie_header or "").split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key == SESSION_COOKIE:
            return value
    return ""


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _short(value: Any, length: int = 14) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return text[:length] + "…"


def _status_class(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    safe = "".join(ch for ch in normalized if ch.isalnum() or ch == "-")
    return safe or "unknown"


def _json_for_hidden(value: Mapping[str, Any]) -> str:
    return _e(json.dumps(dict(value), sort_keys=True, separators=(",", ":")))


def render_login(*, error: str | None = None) -> str:
    error_html = (
        f'<div class="notice error">{_e(error)}</div>' if error else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>AI Business OS · CEO Command Center</title>
  <link rel="stylesheet" href="/ui/assets/app.css">
</head>
<body class="login-body">
  <main class="login-wrap">
    <section class="login-card">
      <div class="eyebrow">AI BUSINESS OS</div>
      <h1>CEO Command Center</h1>
      <p class="muted">Private production control surface. Access is session-bound and no database credential is sent to this browser.</p>
      {error_html}
      <form method="post" action="/ui/login" autocomplete="off">
        <label for="access_code">Access code</label>
        <input id="access_code" name="access_code" type="password" required autofocus autocomplete="current-password">
        <button class="primary" type="submit">Enter Command Center</button>
      </form>
    </section>
  </main>
</body>
</html>"""


def render_dashboard(
    data: Mapping[str, Any],
    *,
    principal: str,
    session_token: str,
    session_secret: str,
    proposal: Mapping[str, Any] | None = None,
    notice: str | None = None,
    error: str | None = None,
) -> str:
    runtime = data.get("runtime") if isinstance(data.get("runtime"), Mapping) else {}
    command = (
        data.get("command_center")
        if isinstance(data.get("command_center"), Mapping)
        else {}
    )
    planning_inputs = (
        data.get("planning_inputs")
        if isinstance(data.get("planning_inputs"), Mapping)
        else {}
    )
    worker_status = (
        data.get("worker_status")
        if isinstance(data.get("worker_status"), Mapping)
        else {}
    )

    businesses = command.get("businesses", [])
    approvals = command.get("pending_approvals", [])
    planning = command.get("planning", {})
    summary = planning.get("summary", {}) if isinstance(planning, Mapping) else {}
    agents = planning_inputs.get("agents", [])
    initiatives = planning_inputs.get("initiatives", [])
    gaps = planning_inputs.get("data_gaps", [])
    goals = planning_inputs.get("open_goals", [])
    heartbeats = worker_status.get("heartbeats", [])
    leases = worker_status.get("leases", [])
    recent_runs = worker_status.get("recent_runs", [])

    if not isinstance(businesses, Sequence) or isinstance(businesses, (str, bytes)):
        businesses = []
    if not isinstance(approvals, Sequence) or isinstance(approvals, (str, bytes)):
        approvals = []
    if not isinstance(agents, Sequence) or isinstance(agents, (str, bytes)):
        agents = []
    if not isinstance(initiatives, Sequence) or isinstance(initiatives, (str, bytes)):
        initiatives = []
    if not isinstance(gaps, Sequence) or isinstance(gaps, (str, bytes)):
        gaps = []
    if not isinstance(goals, Sequence) or isinstance(goals, (str, bytes)):
        goals = []
    if not isinstance(heartbeats, Sequence) or isinstance(heartbeats, (str, bytes)):
        heartbeats = []
    if not isinstance(leases, Sequence) or isinstance(leases, (str, bytes)):
        leases = []
    if not isinstance(recent_runs, Sequence) or isinstance(recent_runs, (str, bytes)):
        recent_runs = []

    heartbeats_by_agent = {
        str(row.get("agent_id")): row
        for row in heartbeats
        if isinstance(row, Mapping) and row.get("agent_id")
    }

    csrf = csrf_token(session_token, session_secret)

    business_cards = "".join(
        f"""<article class="mini-card">
  <div class="mini-title">{_e(row.get("name") or row.get("slug"))}</div>
  <div class="mini-sub">{_e(row.get("slug"))}</div>
</article>"""
        for row in businesses
        if isinstance(row, Mapping)
    ) or '<div class="empty">No businesses returned.</div>'

    agent_rows = "".join(
        f"""<tr>
  <td><strong>{_e(row.get("display_name") or row.get("agent_id"))}</strong><div class="mono subtle">{_e(row.get("role_key"))}</div></td>
  <td><span class="pill {_status_class(row.get("status"))}">{_e(row.get("status"))}</span></td>
  <td>{_e((heartbeats_by_agent.get(str(row.get("agent_id"))) or {}).get("state", {}).get("phase") if isinstance((heartbeats_by_agent.get(str(row.get("agent_id"))) or {}).get("state"), Mapping) else "—")}</td>
  <td class="mono">{_short((heartbeats_by_agent.get(str(row.get("agent_id"))) or {}).get("last_heartbeat_at"), 22)}</td>
</tr>"""
        for row in agents
        if isinstance(row, Mapping)
    ) or '<tr><td colspan="4" class="empty">No active agents returned.</td></tr>'

    goal_rows = "".join(
        f"""<tr>
  <td><strong>{_e(row.get("title"))}</strong><div class="mono subtle">{_short(row.get("id"), 20)}</div></td>
  <td>{_e(row.get("agent_id"))}</td>
  <td>{_e(row.get("goal_type"))}</td>
  <td><span class="pill {_status_class(row.get("status"))}">{_e(row.get("status"))}</span></td>
  <td>{_e(row.get("priority"))}</td>
</tr>"""
        for row in list(goals)[:14]
        if isinstance(row, Mapping)
    ) or '<tr><td colspan="5" class="empty">No pending or active goals.</td></tr>'

    gap_rows = "".join(
        f"""<tr>
  <td><strong>{_e(row.get("metric_key"))}</strong><div class="subtle">{_e(row.get("rationale"))}</div></td>
  <td>{_e(row.get("gap_type"))}</td>
  <td>{_e(row.get("recommended_source_type"))}</td>
  <td>{_e(row.get("priority"))}</td>
</tr>"""
        for row in list(gaps)[:12]
        if isinstance(row, Mapping)
    ) or '<tr><td colspan="4" class="empty">No unresolved evidence gaps.</td></tr>'

    approval_rows = "".join(
        f"""<tr>
  <td><strong>{_e(row.get("title"))}</strong><div class="mono subtle">{_e(row.get("request_key"))}</div></td>
  <td>{_e(row.get("action_key"))}</td>
  <td><span class="pill {_status_class(row.get("predicted_risk"))}">{_e(row.get("predicted_risk"))}</span></td>
  <td>{_e(row.get("expected_money_cents")) if row.get("expected_money_cents") is not None else "—"}</td>
  <td>{_short(row.get("expires_at"), 22)}</td>
</tr>"""
        for row in list(approvals)[:12]
        if isinstance(row, Mapping)
    ) or '<tr><td colspan="5" class="empty">No pending approvals.</td></tr>'

    run_rows = "".join(
        f"""<tr>
  <td>{_e(row.get("agent_id"))}</td>
  <td>{_e(row.get("status"))}</td>
  <td>{_e(row.get("outcome") or "—")}</td>
  <td class="mono">{_short(row.get("goal_id"), 18)}</td>
  <td class="mono">{_short(row.get("started_at"), 22)}</td>
</tr>"""
        for row in list(recent_runs)[:12]
        if isinstance(row, Mapping)
    ) or '<tr><td colspan="5" class="empty">No recent worker runs.</td></tr>'

    proposal_html = ""
    if proposal:
        activation = "Human approval remains required for the possible consequential action." if proposal.get(
            "requires_human_approval_for_possible_action"
        ) else "No consequential external action is authorized by activation."
        proposal_html = f"""<section class="proposal">
  <div class="section-kicker">PROPOSAL READY</div>
  <h3>{_e(proposal.get("objective"))}</h3>
  <div class="proposal-grid">
    <div><span>Route</span><strong>{_e(proposal.get("target_role"))}</strong></div>
    <div><span>Agent</span><strong>{_e(proposal.get("target_agent_id"))}</strong></div>
    <div><span>Goal type</span><strong>{_e(proposal.get("goal_type"))}</strong></div>
    <div><span>Action class</span><strong>{_e(proposal.get("possible_action_class"))}</strong></div>
  </div>
  <p class="muted">{_e(activation)}</p>
  <form method="post" action="/ui/objective/activate">
    <input type="hidden" name="csrf" value="{_e(csrf)}">
    <input type="hidden" name="proposal_json" value="{_json_for_hidden(proposal)}">
    <button class="primary" type="submit">Activate as governed PENDING goal</button>
  </form>
</section>"""

    notice_html = f'<div class="notice success">{_e(notice)}</div>' if notice else ""
    error_html = f'<div class="notice error">{_e(error)}</div>' if error else ""

    schema = command.get("schema_fingerprint") or runtime.get("schema_fingerprint")
    worker = runtime.get("worker") if isinstance(runtime.get("worker"), Mapping) else {}
    active_leases = len(leases)
    open_goals = len(goals)
    gap_count = len(gaps)
    approval_count = len(approvals)
    health_status = "HEALTHY" if runtime.get("ok") else "DEGRADED"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>AI Business OS · CEO Command Center</title>
  <link rel="stylesheet" href="/ui/assets/app.css">
</head>
<body>
  <header class="topbar">
    <div>
      <div class="eyebrow">AI BUSINESS OS · PRODUCTION</div>
      <h1>CEO Command Center</h1>
    </div>
    <div class="top-actions">
      <div class="identity"><span class="dot"></span>{_e(principal)}</div>
      <form method="post" action="/ui/logout">
        <input type="hidden" name="csrf" value="{_e(csrf)}">
        <button class="ghost" type="submit">Sign out</button>
      </form>
    </div>
  </header>

  <main class="page">
    {notice_html}
    {error_html}

    <section class="hero-grid">
      <article class="metric-card primary-card">
        <div class="metric-label">Runtime</div>
        <div class="metric-value">{_e(health_status)}</div>
        <div class="metric-meta">Schema {_e(_short(schema, 18))}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">Active agents</div>
        <div class="metric-value">{len(agents)}</div>
        <div class="metric-meta">Persistent worker {_e("running" if worker.get("running") else "stopped")}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">Open goals</div>
        <div class="metric-value">{open_goals}</div>
        <div class="metric-meta">{active_leases} live worker lease{"s" if active_leases != 1 else ""}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">Evidence gaps</div>
        <div class="metric-value">{gap_count}</div>
        <div class="metric-meta">{_e(summary.get("verify_items", 0))} verification work items</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">Approvals</div>
        <div class="metric-value">{approval_count}</div>
        <div class="metric-meta">Read-only in Step 4</div>
      </article>
    </section>

    <section class="panel command-panel">
      <div class="section-heading">
        <div>
          <div class="section-kicker">COMMAND</div>
          <h2>Set an objective</h2>
        </div>
        <span class="badge">Governed activation</span>
      </div>
      <form class="objective-form" method="post" action="/ui/objective/propose">
        <input type="hidden" name="csrf" value="{_e(csrf)}">
        <textarea name="objective" rows="3" maxlength="2000" required placeholder="Example: Research the highest-value evidence gap in FreightRecovery and return a verified recommendation."></textarea>
        <div class="form-row">
          <label>Priority <input name="priority" type="number" min="0" max="100" value="80"></label>
          <button class="primary" type="submit">Create proposal</button>
        </div>
      </form>
      {proposal_html}
    </section>

    <section class="two-col">
      <article class="panel">
        <div class="section-heading"><div><div class="section-kicker">PORTFOLIO</div><h2>Businesses</h2></div><span class="badge">{len(initiatives)} active initiatives</span></div>
        <div class="mini-grid">{business_cards}</div>
      </article>
      <article class="panel">
        <div class="section-heading"><div><div class="section-kicker">WORKER</div><h2>Persistent runtime</h2></div><span class="badge">{_e(worker.get("worker_instance_id") or "runtime")}</span></div>
        <dl class="facts">
          <div><dt>Polls</dt><dd>{_e(worker.get("ticks", 0))}</dd></div>
          <div><dt>Claims</dt><dd>{_e(worker.get("claims", 0))}</dd></div>
          <div><dt>Submitted</dt><dd>{_e(worker.get("submitted", 0))}</dd></div>
          <div><dt>Failed</dt><dd>{_e(worker.get("failed", 0))}</dd></div>
        </dl>
      </article>
    </section>

    <section class="panel">
      <div class="section-heading"><div><div class="section-kicker">AGENTS</div><h2>Agent fleet</h2></div><span class="badge">{len(agents)} active</span></div>
      <div class="table-wrap"><table><thead><tr><th>Agent</th><th>Status</th><th>Worker phase</th><th>Heartbeat</th></tr></thead><tbody>{agent_rows}</tbody></table></div>
    </section>

    <section class="panel">
      <div class="section-heading"><div><div class="section-kicker">GOALS</div><h2>Open goal queue</h2></div><span class="badge">{open_goals} open</span></div>
      <div class="table-wrap"><table><thead><tr><th>Goal</th><th>Agent</th><th>Type</th><th>Status</th><th>Priority</th></tr></thead><tbody>{goal_rows}</tbody></table></div>
    </section>

    <section class="two-col wide-left">
      <article class="panel">
        <div class="section-heading"><div><div class="section-kicker">EVIDENCE</div><h2>Unresolved gaps</h2></div><span class="badge">{gap_count} gaps</span></div>
        <div class="table-wrap"><table><thead><tr><th>Metric</th><th>Type</th><th>Source</th><th>Priority</th></tr></thead><tbody>{gap_rows}</tbody></table></div>
      </article>

      <article class="panel">
        <div class="section-heading"><div><div class="section-kicker">APPROVALS</div><h2>Human approval queue</h2></div><span class="badge">View only</span></div>
        <div class="table-wrap"><table><thead><tr><th>Request</th><th>Action</th><th>Risk</th><th>¢</th><th>Expires</th></tr></thead><tbody>{approval_rows}</tbody></table></div>
      </article>
    </section>

    <section class="panel">
      <div class="section-heading"><div><div class="section-kicker">EXECUTION</div><h2>Recent worker runs</h2></div><span class="badge">{len(recent_runs)} loaded</span></div>
      <div class="table-wrap"><table><thead><tr><th>Agent</th><th>Status</th><th>Outcome</th><th>Goal</th><th>Started</th></tr></thead><tbody>{run_rows}</tbody></table></div>
    </section>
  </main>
</body>
</html>"""


APP_CSS = r"""
:root {
  color-scheme: dark;
  --bg: #071018;
  --panel: rgba(14, 27, 39, .92);
  --panel-2: rgba(18, 35, 50, .92);
  --line: rgba(167, 220, 255, .14);
  --text: #edf8ff;
  --muted: #8eabba;
  --cyan: #67e8f9;
  --blue: #60a5fa;
  --green: #5ee6a8;
  --amber: #f4c96b;
  --red: #ff7f93;
  --shadow: 0 18px 60px rgba(0,0,0,.34);
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at 10% 0%, rgba(36, 159, 255, .18), transparent 30rem),
    radial-gradient(circle at 90% 5%, rgba(33, 240, 196, .11), transparent 28rem),
    linear-gradient(180deg, #08131d 0%, #050b11 100%);
}
button, input, textarea { font: inherit; }
.topbar {
  position: sticky; top: 0; z-index: 10;
  display: flex; justify-content: space-between; align-items: center; gap: 20px;
  padding: 20px clamp(18px, 4vw, 54px);
  border-bottom: 1px solid var(--line);
  background: rgba(5, 12, 18, .82);
  backdrop-filter: blur(18px);
}
h1, h2, h3, p { margin-top: 0; }
h1 { margin-bottom: 0; font-size: clamp(1.45rem, 3vw, 2.15rem); letter-spacing: -.035em; }
h2 { margin-bottom: 0; font-size: 1.08rem; letter-spacing: -.02em; }
h3 { margin-bottom: 10px; }
.eyebrow, .section-kicker {
  color: var(--cyan); font-size: .69rem; font-weight: 800; letter-spacing: .16em;
}
.section-kicker { margin-bottom: 4px; }
.page { width: min(1500px, calc(100% - 28px)); margin: 26px auto 70px; }
.hero-grid {
  display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 14px; margin-bottom: 16px;
}
.metric-card, .panel, .login-card {
  border: 1px solid var(--line);
  background: linear-gradient(145deg, rgba(18, 37, 53, .94), rgba(9, 21, 31, .94));
  box-shadow: var(--shadow);
  border-radius: 20px;
}
.metric-card { padding: 19px; min-height: 126px; }
.primary-card {
  background: linear-gradient(145deg, rgba(17, 77, 100, .95), rgba(9, 31, 45, .95));
  border-color: rgba(103,232,249,.32);
}
.metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.metric-value { margin: 10px 0 5px; font-size: clamp(1.55rem, 3vw, 2.3rem); font-weight: 850; letter-spacing: -.04em; }
.metric-meta { color: var(--muted); font-size: .78rem; }
.panel { padding: 20px; margin-bottom: 16px; overflow: hidden; }
.section-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:18px; }
.badge, .pill {
  display:inline-flex; align-items:center; border:1px solid var(--line); border-radius:999px;
  padding:5px 9px; font-size:.72rem; color:#ccecff; background:rgba(255,255,255,.035);
}
.pill.active, .pill.healthy, .pill.approved, .pill.verifying { color: var(--green); border-color: rgba(94,230,168,.26); }
.pill.pending, .pill.medium, .pill.running { color: var(--amber); border-color: rgba(244,201,107,.26); }
.pill.blocked, .pill.failed, .pill.high, .pill.degraded { color: var(--red); border-color: rgba(255,127,147,.26); }
.two-col { display:grid; grid-template-columns: 1fr 1fr; gap:16px; }
.wide-left { grid-template-columns: 1.15fr .85fr; }
.mini-grid { display:grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap:10px; }
.mini-card { padding:14px; border:1px solid var(--line); border-radius:14px; background:rgba(255,255,255,.025); }
.mini-title { font-weight:800; }
.mini-sub, .subtle, .muted { color:var(--muted); font-size:.82rem; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.facts { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:0; }
.facts div { border:1px solid var(--line); border-radius:14px; padding:13px; background:rgba(255,255,255,.025); }
.facts dt { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }
.facts dd { margin:6px 0 0; font-size:1.35rem; font-weight:800; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:14px; }
table { width:100%; border-collapse:collapse; min-width:680px; }
th, td { padding:12px 13px; text-align:left; border-bottom:1px solid rgba(167,220,255,.08); vertical-align:top; }
th { color:#a8c8d9; font-size:.69rem; text-transform:uppercase; letter-spacing:.08em; background:rgba(255,255,255,.022); }
td { font-size:.84rem; }
tr:last-child td { border-bottom:0; }
.empty { color:var(--muted); padding:18px; }
.command-panel {
  background: linear-gradient(145deg, rgba(13, 49, 67, .95), rgba(10, 25, 36, .96));
  border-color: rgba(103,232,249,.22);
}
.objective-form textarea, .login-card input, .objective-form input[type="number"] {
  width:100%; border:1px solid rgba(167,220,255,.18); border-radius:13px; color:var(--text);
  background:rgba(0,0,0,.24); outline:none; padding:13px 14px;
}
.objective-form textarea:focus, .login-card input:focus, .objective-form input:focus {
  border-color:rgba(103,232,249,.68); box-shadow:0 0 0 3px rgba(103,232,249,.08);
}
.form-row { display:flex; justify-content:space-between; align-items:end; gap:14px; margin-top:12px; }
.form-row label { display:grid; gap:6px; width:130px; color:var(--muted); font-size:.76rem; }
button { border:0; cursor:pointer; }
.primary {
  padding:11px 16px; border-radius:12px; font-weight:800; color:#041018;
  background:linear-gradient(135deg,var(--cyan),#7dd3fc); box-shadow:0 10px 28px rgba(70,207,238,.16);
}
.primary:hover { filter:brightness(1.06); }
.ghost { padding:9px 12px; border-radius:10px; color:#d7edf8; background:rgba(255,255,255,.055); border:1px solid var(--line); }
.proposal { margin-top:16px; border:1px solid rgba(94,230,168,.22); background:rgba(16,70,56,.17); border-radius:16px; padding:16px; }
.proposal-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:14px 0; }
.proposal-grid div { border:1px solid var(--line); border-radius:12px; padding:11px; }
.proposal-grid span { display:block; color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.07em; margin-bottom:5px; }
.notice { padding:12px 14px; border-radius:13px; margin-bottom:14px; border:1px solid var(--line); }
.notice.success { color:#bff8da; border-color:rgba(94,230,168,.25); background:rgba(16,91,63,.22); }
.notice.error { color:#ffd1d8; border-color:rgba(255,127,147,.25); background:rgba(96,25,39,.24); }
.top-actions { display:flex; align-items:center; gap:10px; }
.identity { display:flex; align-items:center; gap:8px; color:#cce3ee; font-size:.8rem; }
.dot { width:8px; height:8px; border-radius:50%; background:var(--green); box-shadow:0 0 18px var(--green); }
.login-body { display:grid; place-items:center; }
.login-wrap { width:min(460px,calc(100% - 28px)); padding:60px 0; }
.login-card { padding:30px; }
.login-card h1 { margin:6px 0 12px; }
.login-card label { display:block; color:#b6cfdb; font-size:.8rem; margin:22px 0 7px; }
.login-card .primary { width:100%; margin-top:12px; }
@media (max-width: 1050px) {
  .hero-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .two-col, .wide-left { grid-template-columns:1fr; }
}
@media (max-width: 700px) {
  .topbar { align-items:flex-start; }
  .top-actions { flex-direction:column; align-items:flex-end; }
  .hero-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .proposal-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .page { width:min(100% - 18px,1500px); margin-top:14px; }
  .panel { padding:15px; border-radius:16px; }
}
@media (max-width: 470px) {
  .hero-grid { grid-template-columns:1fr 1fr; gap:9px; }
  .metric-card { min-height:108px; padding:14px; border-radius:15px; }
  .metric-value { font-size:1.55rem; }
  .proposal-grid, .mini-grid { grid-template-columns:1fr; }
  .form-row { align-items:stretch; flex-direction:column; }
  .form-row label { width:100%; }
  .form-row .primary { width:100%; }
}
"""
