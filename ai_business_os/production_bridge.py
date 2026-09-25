"""Read-only bridge from the canonical AI Business OS to production state.

This module deliberately does not own credentials or a database driver. A private runtime injects
an executor that can issue parameterized SELECT statements against the authoritative
`ai_business_os_prod` schema. Keeping the bridge read-only makes production observation a
separate capability from governed mutation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any


class ProductionBridgeError(RuntimeError):
    """Raised when production state cannot be read safely or validated."""


Row = Mapping[str, Any]
QueryExecutor = Callable[[str, tuple[Any, ...]], Sequence[Row]]

SCHEMA_FINGERPRINT_SQL = """
select ai_business_os_prod.schema_fingerprint_v1() as schema_fingerprint
"""

BUSINESSES_SQL = """
select id, slug, name
from ai_business_os_prod.businesses
order by slug
"""

LATEST_COMMAND_CENTER_SQL = """
select snapshot_key, snapshot_hash, payload, generated_at
from ai_business_os_prod.command_center_snapshots
order by generated_at desc
limit 1
"""

PENDING_APPROVALS_SQL = """
select
    id,
    request_key,
    agent_id,
    action_key,
    action_class,
    title,
    intent_hash,
    predicted_risk,
    expected_money_cents,
    status,
    created_at,
    expires_at
from ai_business_os_prod.approval_inbox
where status = %s
order by created_at
"""

_MUTATING_WORD = re.compile(
    r"\b(insert|update|delete|alter|drop|create|grant|revoke|truncate|copy|call|execute|set)\b",
    re.IGNORECASE,
)
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _assert_read_only_sql(sql: str) -> None:
    normalized = " ".join(sql.strip().split())
    if not normalized.lower().startswith("select "):
        raise ProductionBridgeError("production bridge permits SELECT statements only")
    if ";" in normalized:
        raise ProductionBridgeError("production bridge permits one SELECT statement at a time")
    if _MUTATING_WORD.search(normalized):
        raise ProductionBridgeError("mutating SQL is forbidden in the production read bridge")


class ProductionReadBridge:
    """Fail-closed read model over the private production Business Brain."""

    def __init__(self, execute: QueryExecutor):
        self._execute = execute

    def _run(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        _assert_read_only_sql(sql)
        rows = self._execute(sql, params)
        return [dict(row) for row in rows]

    def schema_fingerprint(self) -> str:
        rows = self._run(SCHEMA_FINGERPRINT_SQL)
        if len(rows) != 1:
            raise ProductionBridgeError("expected exactly one production schema fingerprint row")
        value = str(rows[0].get("schema_fingerprint", ""))
        if not _SHA256.fullmatch(value):
            raise ProductionBridgeError("production schema fingerprint is not a SHA-256 digest")
        return value.lower()

    def assert_schema_current(self, expected_fingerprint: str) -> str:
        if not _SHA256.fullmatch(expected_fingerprint):
            raise ProductionBridgeError("expected schema fingerprint is not a SHA-256 digest")
        live = self.schema_fingerprint()
        if live != expected_fingerprint.lower():
            raise ProductionBridgeError(
                f"production schema drift: expected {expected_fingerprint.lower()}, got {live}"
            )
        return live

    def businesses(self) -> list[dict[str, Any]]:
        return self._run(BUSINESSES_SQL)

    def latest_command_center_snapshot(self) -> dict[str, Any] | None:
        rows = self._run(LATEST_COMMAND_CENTER_SQL)
        if not rows:
            return None
        if len(rows) != 1:
            raise ProductionBridgeError("latest command-center query returned multiple rows")
        snapshot = rows[0]
        payload = snapshot.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ProductionBridgeError("command-center payload is invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ProductionBridgeError("command-center payload must be a JSON object")
        snapshot["payload"] = dict(payload)
        return snapshot

    def pending_approvals(self) -> list[dict[str, Any]]:
        rows = self._run(PENDING_APPROVALS_SQL, ("PENDING",))
        for row in rows:
            if row.get("status") != "PENDING":
                raise ProductionBridgeError("pending-approval query returned a non-pending row")
            if not row.get("request_key") or not row.get("intent_hash"):
                raise ProductionBridgeError("pending approval is missing immutable request identity")
        return rows

    def portfolio_view(self, *, expected_schema_fingerprint: str | None = None) -> dict[str, Any]:
        fingerprint = (
            self.assert_schema_current(expected_schema_fingerprint)
            if expected_schema_fingerprint
            else self.schema_fingerprint()
        )
        return {
            "schema_fingerprint": fingerprint,
            "businesses": self.businesses(),
            "command_center": self.latest_command_center_snapshot(),
            "pending_approvals": self.pending_approvals(),
        }
