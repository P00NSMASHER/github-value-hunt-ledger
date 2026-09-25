"""Private always-on runtime adapter for the AI Business OS.

Designed for a private Railway service. It never stores Supabase database credentials. Instead it
talks to a narrowly-scoped Supabase Edge Function using a high-entropy runtime token held only in
Railway environment variables.
"""

from __future__ import annotations

import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from ai_business_os.ceo_command_center import (
    CommandCenterOperator,
)
from ai_business_os.command_center_ui import (
    APP_CSS,
    access_code_matches,
    clear_session_cookie,
    csrf_matches,
    issue_session,
    parse_session_cookie,
    render_dashboard,
    render_login,
    session_cookie,
    validate_session,
)
from ai_business_os.persistent_workers import (
    PersistentGoalWorker,
    default_worker_instance_id,
    system_health_executor,
)

STARTUP_SMOKE_OBJECTIVE = (
    "Research the current portfolio evidence gaps and identify the single highest-priority "
    "verification task. Return evidence and a recommended next step only."
)


def run_startup_smoke(operator: CommandCenterOperator) -> dict[str, Any]:
    """Run a read-only live Command Center smoke test.

    The smoke test reads the dashboard and creates a proposal object only. It never activates a
    goal, decides an approval, or invokes a write executor.
    """
    dashboard = operator.dashboard()
    businesses = dashboard.get("businesses", [])
    approvals = dashboard.get("pending_approvals", [])
    planning = dashboard.get("planning", {})
    summary = planning.get("summary", {}) if isinstance(planning, Mapping) else {}
    proposal = operator.propose_objective(
        STARTUP_SMOKE_OBJECTIVE,
        requested_by="production-smoke-test",
        priority=100,
    )
    return {
        "event": "startup_smoke_passed",
        "schema_fingerprint": dashboard.get("schema_fingerprint"),
        "business_count": len(businesses) if isinstance(businesses, list) else None,
        "businesses": [
            str(row.get("slug") or row.get("name"))
            for row in businesses
            if isinstance(row, Mapping)
        ] if isinstance(businesses, list) else [],
        "pending_approval_count": len(approvals) if isinstance(approvals, list) else None,
        "planning_summary": {
            "total_work_items": summary.get("total_work_items"),
            "agent_work_items": summary.get("agent_work_items"),
            "hunter_work_items": summary.get("hunter_work_items"),
            "research_items": summary.get("research_items"),
            "build_items": summary.get("build_items"),
            "verify_items": summary.get("verify_items"),
        },
        "objective": {
            "status": proposal.get("status"),
            "objective_hash": proposal.get("objective_hash"),
            "target_role": proposal.get("target_role"),
            "target_agent_id": proposal.get("target_agent_id"),
            "goal_type": proposal.get("goal_type"),
            "possible_action_class": proposal.get("possible_action_class"),
            "requires_human_approval_for_possible_action": proposal.get(
                "requires_human_approval_for_possible_action"
            ),
            "business_refs": proposal.get("business_refs"),
        },
    }


class RuntimeConfigError(RuntimeError):
    pass


class GatewayError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeConfigError(f"missing required environment variable: {name}")
    return value


class GatewayClient:
    def __init__(self, url: str, token: str, *, timeout_seconds: float = 15.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def call(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(
            {"action": action, "payload": dict(payload or {})},
            separators=(",", ":"),
        ).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-AIBOS-Runtime-Token": self.token,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise GatewayError(f"gateway HTTP {exc.code}: {detail[:500]}") from exc
        except OSError as exc:
            raise GatewayError(f"gateway connection failed: {exc}") from exc
        if status != HTTPStatus.OK:
            raise GatewayError(f"gateway returned unexpected HTTP {status}")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GatewayError("gateway returned invalid JSON") from exc
        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            raise GatewayError(f"gateway rejected request: {decoded}")
        data = decoded.get("data")
        if not isinstance(data, dict):
            raise GatewayError("gateway response data must be an object")
        return data


class GatewayProductionBridge:
    """Duck-typed production bridge backed by named gateway operations, not SQL."""

    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway
        self._portfolio_cache: dict[str, Any] | None = None

    def schema_fingerprint(self) -> str:
        return str(self.gateway.call("health")["schema_fingerprint"])

    def assert_schema_current(self, expected_fingerprint: str) -> str:
        live = self.schema_fingerprint()
        if not hmac.compare_digest(live, expected_fingerprint):
            raise GatewayError(
                f"production schema drift: expected {expected_fingerprint}, got {live}"
            )
        return live

    def portfolio_view(self, *, expected_schema_fingerprint: str | None = None) -> dict[str, Any]:
        data = self.gateway.call("portfolio_view")
        if expected_schema_fingerprint:
            live = str(data.get("schema_fingerprint", ""))
            if not hmac.compare_digest(live, expected_schema_fingerprint):
                raise GatewayError(
                    f"production schema drift: expected {expected_schema_fingerprint}, got {live}"
                )
        self._portfolio_cache = data
        return data

    def planning_inputs(self) -> dict[str, Any]:
        return self.gateway.call("planning_inputs")

    def businesses(self) -> list[dict[str, Any]]:
        if self._portfolio_cache is None:
            self._portfolio_cache = self.gateway.call("portfolio_view")
        businesses = self._portfolio_cache.get("businesses", [])
        if not isinstance(businesses, list):
            raise GatewayError("businesses payload is not a list")
        return [dict(row) for row in businesses]


class GatewayReadExecutor:
    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway

    def __call__(self, sql: str, params: tuple[Any, ...]):
        normalized = " ".join(sql.split()).lower()
        if "from ai_business_os_prod.approval_inbox" not in normalized:
            raise GatewayError("runtime read executor refuses unrecognized SQL contract")
        if len(params) != 1:
            raise GatewayError("approval lookup requires exactly one request key")
        data = self.gateway.call("approval_lookup", {"request_key": params[0]})
        row = data.get("approval")
        return [] if row is None else [row]


class GatewayWriteExecutor:
    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway

    def __call__(self, sql: str, params: tuple[Any, ...]):
        normalized = " ".join(sql.split()).lower()
        if "insert into ai_business_os_prod.agent_goals" in normalized:
            if len(params) != 6:
                raise GatewayError("goal activation requires six bound parameters")
            data = self.gateway.call(
                "activate_goal",
                {
                    "target_agent_id": params[0],
                    "goal_type": params[1],
                    "objective": params[2],
                    "priority": params[3],
                    "constraints": json.loads(params[4]),
                    "evidence_requirements": json.loads(params[5]),
                },
            )
            return [data["goal"]]
        if "ai_business_os_prod.approval_decide" in normalized:
            if len(params) != 4:
                raise GatewayError("approval decision requires four bound parameters")
            data = self.gateway.call(
                "decide_approval",
                {
                    "request_key": params[0],
                    "decision": params[1],
                    "human_principal": params[2],
                    "reason": params[3],
                },
            )
            return [data["receipt"]]
        raise GatewayError("runtime write executor refuses unrecognized SQL contract")


class RuntimeState:
    def __init__(self, gateway: GatewayClient, expected_fingerprint: str):
        self.gateway = gateway
        self.expected_fingerprint = expected_fingerprint
        self._lock = threading.Lock()
        self.last_gateway_ok_at: float | None = None
        self.last_error: str | None = None
        self.live_fingerprint: str | None = None

    def probe(self) -> None:
        try:
            fingerprint = str(self.gateway.call("health")["schema_fingerprint"])
            if not hmac.compare_digest(fingerprint, self.expected_fingerprint):
                raise GatewayError(
                    f"production schema drift: expected {self.expected_fingerprint}, got {fingerprint}"
                )
            with self._lock:
                self.last_gateway_ok_at = time.time()
                self.last_error = None
                self.live_fingerprint = fingerprint
        except Exception as exc:
            with self._lock:
                self.last_error = str(exc)
                self.live_fingerprint = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            age = (
                None
                if self.last_gateway_ok_at is None
                else max(0.0, time.time() - self.last_gateway_ok_at)
            )
            healthy = age is not None and age <= 90.0 and self.last_error is None
            return {
                "ok": healthy,
                "gateway_age_seconds": age,
                "schema_fingerprint": self.live_fingerprint,
                "error": self.last_error,
            }


def activate_bootstrap_objective(
    operator: CommandCenterOperator,
    bridge: GatewayProductionBridge,
    write_execute: GatewayWriteExecutor,
    *,
    objective: str,
    human_principal: str,
    priority: int = 100,
) -> dict[str, Any]:
    """Activate one exact Command Center objective idempotently as a PENDING goal."""
    proposal = operator.propose_objective(
        objective,
        requested_by=human_principal,
        priority=priority,
    )
    objective_hash = str(proposal["objective_hash"])
    planning_inputs = bridge.planning_inputs()
    for goal in planning_inputs.get("open_goals", []):
        if not isinstance(goal, Mapping):
            continue
        constraints = goal.get("constraints")
        if isinstance(constraints, str):
            try:
                constraints = json.loads(constraints)
            except json.JSONDecodeError:
                constraints = {}
        if isinstance(constraints, Mapping) and constraints.get("objective_hash") == objective_hash:
            return {
                "event": "bootstrap_objective_already_present",
                "objective_hash": objective_hash,
                "goal_id": goal.get("id"),
                "status": goal.get("status"),
                "target_agent_id": goal.get("agent_id"),
            }

    activated = operator.activate_objective(
        proposal,
        human_principal=human_principal,
        write_execute=write_execute,
    )
    goal = activated["goal"]
    return {
        "event": "bootstrap_objective_activated",
        "objective_hash": objective_hash,
        "goal_id": goal.get("id"),
        "status": goal.get("status"),
        "target_agent_id": goal.get("agent_id"),
        "goal_type": goal.get("goal_type"),
        "possible_action_class": proposal.get("possible_action_class"),
    }


def _probe_loop(state: RuntimeState) -> None:
    while True:
        state.probe()
        time.sleep(30)


def build_server() -> ThreadingHTTPServer:
    gateway = GatewayClient(
        _required_env("AIBOS_GATEWAY_URL"),
        _required_env("AIBOS_RUNTIME_TOKEN"),
    )
    operator_token = _required_env("AIBOS_OPERATOR_TOKEN")
    expected_fingerprint = _required_env("AIBOS_SCHEMA_FINGERPRINT")
    ui_enabled = os.environ.get("AIBOS_UI_ENABLED", "0") == "1"
    ui_access_sha256 = _required_env("AIBOS_UI_ACCESS_SHA256") if ui_enabled else ""
    ui_session_secret = _required_env("AIBOS_UI_SESSION_SECRET") if ui_enabled else ""
    ui_principal = _required_env("AIBOS_UI_PRINCIPAL") if ui_enabled else ""
    port = int(os.environ.get("PORT", "8080"))

    bridge = GatewayProductionBridge(gateway)
    operator = CommandCenterOperator(
        bridge,
        expected_schema_fingerprint=expected_fingerprint,
    )
    read_execute = GatewayReadExecutor(gateway)
    write_execute = GatewayWriteExecutor(gateway)
    state = RuntimeState(gateway, expected_fingerprint)
    state.probe()
    worker = PersistentGoalWorker(
        gateway,
        worker_instance_id=default_worker_instance_id(),
        executors={"SYSTEM_HEALTH_CHECK": system_health_executor(gateway)},
        lease_seconds=int(os.environ.get("AIBOS_WORKER_LEASE_SECONDS", "180")),
        heartbeat_seconds=int(os.environ.get("AIBOS_WORKER_HEARTBEAT_SECONDS", "45")),
        poll_seconds=float(os.environ.get("AIBOS_WORKER_POLL_SECONDS", "15")),
    )

    class Handler(BaseHTTPRequestHandler):
        server_version = "AIBusinessOSRuntime/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            print(json.dumps({"event": "http", "message": fmt % args}), flush=True)

        def _json(self, status: int, payload: Mapping[str, Any]) -> None:
            raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                return

        def _authorized(self) -> bool:
            supplied = self.headers.get("X-AIBOS-Operator-Token", "")
            return hmac.compare_digest(supplied, operator_token)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("invalid request body length")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        def do_GET(self) -> None:
            if self.path == "/health":
                snapshot = state.snapshot()
                snapshot["worker"] = worker.snapshot()
                self._json(200 if snapshot["ok"] else 503, snapshot)
                return
            if not self._authorized():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            if self.path == "/dashboard":
                try:
                    self._json(200, {"ok": True, "data": operator.dashboard()})
                except Exception as exc:
                    self._json(503, {"ok": False, "error": str(exc)})
                return
            self._json(404, {"ok": False, "error": "not_found"})

        def do_POST(self) -> None:
            if not self._authorized():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            try:
                body = self._body()
                if self.path == "/objective/propose":
                    data = operator.propose_objective(
                        str(body.get("objective", "")),
                        requested_by=str(body.get("requested_by", "")),
                        priority=int(body.get("priority", 80)),
                    )
                elif self.path == "/objective/activate":
                    proposal = body.get("proposal")
                    if not isinstance(proposal, dict):
                        raise ValueError("proposal must be an object")
                    data = operator.activate_objective(
                        proposal,
                        human_principal=str(body.get("human_principal", "")),
                        write_execute=write_execute,
                    )
                elif self.path == "/approval/decide":
                    data = operator.decide_approval(
                        request_key=str(body.get("request_key", "")),
                        intent_hash=str(body.get("intent_hash", "")),
                        decision=str(body.get("decision", "")),
                        human_principal=str(body.get("human_principal", "")),
                        reason=str(body.get("reason", "")),
                        read_execute=read_execute,
                        write_execute=write_execute,
                    )
                else:
                    self._json(404, {"ok": False, "error": "not_found"})
                    return
                self._json(200, {"ok": True, "data": data})
            except Exception as exc:
                self._json(400, {"ok": False, "error": str(exc)})

    threading.Thread(target=_probe_loop, args=(state,), daemon=True).start()
    if os.environ.get("AIBOS_WORKER_ENABLED", "1") == "1":
        threading.Thread(target=worker.run_forever, daemon=True, name="aibos-worker").start()
    else:
        worker.stop()
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main() -> None:
    server = build_server()
    print(
        json.dumps(
            {
                "event": "runtime_started",
                "port": server.server_address[1],
                "public_domain_required": False,
            }
        ),
        flush=True,
    )
    if os.environ.get("AIBOS_STARTUP_SMOKE", "1") == "1":
        try:
            smoke_gateway = GatewayClient(
                _required_env("AIBOS_GATEWAY_URL"),
                _required_env("AIBOS_RUNTIME_TOKEN"),
            )
            smoke_bridge = GatewayProductionBridge(smoke_gateway)
            smoke_operator = CommandCenterOperator(
                smoke_bridge,
                expected_schema_fingerprint=_required_env("AIBOS_SCHEMA_FINGERPRINT"),
            )
            print(json.dumps(run_startup_smoke(smoke_operator), separators=(",", ":")), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {"event": "startup_smoke_failed", "error": str(exc)},
                    separators=(",", ":"),
                ),
                flush=True,
            )
            raise

    if os.environ.get("AIBOS_BOOTSTRAP_OBJECTIVE_ENABLED", "0") == "1":
        bootstrap_gateway = GatewayClient(
            _required_env("AIBOS_GATEWAY_URL"),
            _required_env("AIBOS_RUNTIME_TOKEN"),
        )
        bootstrap_bridge = GatewayProductionBridge(bootstrap_gateway)
        bootstrap_operator = CommandCenterOperator(
            bootstrap_bridge,
            expected_schema_fingerprint=_required_env("AIBOS_SCHEMA_FINGERPRINT"),
        )
        bootstrap_write = GatewayWriteExecutor(bootstrap_gateway)
        result = activate_bootstrap_objective(
            bootstrap_operator,
            bootstrap_bridge,
            bootstrap_write,
            objective=_required_env("AIBOS_BOOTSTRAP_OBJECTIVE"),
            human_principal=_required_env("AIBOS_BOOTSTRAP_PRINCIPAL"),
            priority=int(os.environ.get("AIBOS_BOOTSTRAP_PRIORITY", "100")),
        )
        print(json.dumps(result, separators=(",", ":")), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
