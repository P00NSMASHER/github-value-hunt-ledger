"""Evidence-first portfolio capital allocator for the AI Business OS.

This module is decision support, not an autonomous investment oracle. It converts evidence-backed
business metrics into a transparent ranking and bounded resource-allocation plan. Weak or missing
evidence reduces influence; forecasts never become realized cash; and any real resource allocation
must cross the Step-6 governance boundary before an external executor may act.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from ai_business_os.governance import GovernanceControlPlane
from ai_business_os.persistent_agents.runtime import AgentRuntime


RESOURCE_TYPES = {
    "AI_COST_UNITS",
    "ENGINEERING_HOURS",
    "HUMAN_HOURS",
    "CASH_CENTS",
}

MONEY_METRICS = {
    "cash_collected_30d",
    "revenue_recognized_30d",
    "cash_costs_30d",
    "ai_cost_30d",
    "contracted_pipeline_value_90d",
    "qualified_pipeline_value_90d",
}

EFFORT_METRICS = {
    "human_hours_30d",
    "remaining_effort_hours",
    "time_to_cash_days",
}

SIGNAL_METRICS = {
    "retention_signal",
    "market_evidence_signal",
    "strategic_reuse_signal",
}

ALL_METRICS = MONEY_METRICS | EFFORT_METRICS | SIGNAL_METRICS

CORE_METRICS = {
    "cash_collected_30d",
    "cash_costs_30d",
    "ai_cost_30d",
    "contracted_pipeline_value_90d",
    "remaining_effort_hours",
    "time_to_cash_days",
    "market_evidence_signal",
}

DEFAULT_POLICY = {
    "realized_net_cash_weight": 1.0,
    "recognized_revenue_weight": 0.25,
    "contracted_pipeline_weight": 0.50,
    "qualified_pipeline_weight": 0.15,
    "retention_signal_weight": 0.20,
    "market_evidence_weight": 0.15,
    "strategic_reuse_weight": 0.10,
    "human_hours_penalty": 0.10,
    "remaining_effort_penalty": 0.20,
    "time_to_cash_penalty": 0.20,
    "min_evidence_coverage": 0.60,
    "max_allocation_share": 0.50,
    "max_snapshot_skew_days": 7.0,
}

SOURCE_QUALITY = {
    "BANK": 1.00,
    "PAYMENT_PROCESSOR": 0.95,
    "GENERAL_LEDGER": 0.95,
    "SIGNED_CONTRACT": 0.90,
    "INVOICE": 0.85,
    "CRM": 0.60,
    "ANALYTICS": 0.70,
    "MANUAL_RECORD": 0.50,
    "MODEL_ESTIMATE": 0.20,
}

ALLOWED_SOURCE_TYPES = {
    "cash_collected_30d": {"BANK", "PAYMENT_PROCESSOR", "GENERAL_LEDGER"},
    "revenue_recognized_30d": {"GENERAL_LEDGER", "INVOICE"},
    "cash_costs_30d": {"BANK", "GENERAL_LEDGER", "INVOICE"},
    "ai_cost_30d": {"INVOICE", "GENERAL_LEDGER", "PAYMENT_PROCESSOR"},
    "contracted_pipeline_value_90d": {"SIGNED_CONTRACT", "CRM"},
    "qualified_pipeline_value_90d": {"CRM", "ANALYTICS", "MANUAL_RECORD"},
    "human_hours_30d": {"ANALYTICS", "MANUAL_RECORD"},
    "remaining_effort_hours": {"ANALYTICS", "MANUAL_RECORD", "MODEL_ESTIMATE"},
    "time_to_cash_days": {"ANALYTICS", "MANUAL_RECORD", "MODEL_ESTIMATE"},
    "retention_signal": {"CRM", "ANALYTICS", "MANUAL_RECORD", "MODEL_ESTIMATE"},
    "market_evidence_signal": {"CRM", "ANALYTICS", "MANUAL_RECORD", "MODEL_ESTIMATE"},
    "strategic_reuse_signal": {"ANALYTICS", "MANUAL_RECORD", "MODEL_ESTIMATE"},
}

MAX_EVIDENCE_AGE_DAYS = {
    "cash_collected_30d": 45,
    "revenue_recognized_30d": 45,
    "cash_costs_30d": 45,
    "ai_cost_30d": 45,
    "contracted_pipeline_value_90d": 100,
    "qualified_pipeline_value_90d": 100,
    "human_hours_30d": 45,
    "remaining_effort_hours": 120,
    "time_to_cash_days": 120,
    "retention_signal": 120,
    "market_evidence_signal": 120,
    "strategic_reuse_signal": 120,
}


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


class CapitalAllocatorError(ValueError):
    """Raised when allocator evidence, policy, or authority invariants are violated."""


class CapitalAllocator:
    """Transparent evidence-weighted portfolio ranking and allocation planner."""

    def __init__(
        self,
        runtime: AgentRuntime,
        governance: Optional[GovernanceControlPlane] = None,
    ):
        if governance is not None and governance.runtime is not runtime:
            raise CapitalAllocatorError(
                "allocator and governance must share the exact AgentRuntime"
            )
        self.runtime = runtime
        self.governance = governance
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio_initiatives (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                business_ref TEXT,
                product_ref TEXT,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_policies (
                id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                config_json TEXT NOT NULL,
                policy_hash TEXT NOT NULL UNIQUE,
                updated_by_principal TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id TEXT PRIMARY KEY,
                initiative_id TEXT NOT NULL REFERENCES portfolio_initiatives(id),
                as_of REAL NOT NULL,
                metrics_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL UNIQUE,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_rankings (
                id TEXT PRIMARY KEY,
                policy_id TEXT NOT NULL REFERENCES portfolio_policies(id),
                policy_hash TEXT NOT NULL,
                as_of REAL NOT NULL,
                snapshot_set_hash TEXT NOT NULL,
                ranking_json TEXT NOT NULL,
                ranking_hash TEXT NOT NULL UNIQUE,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_allocation_plans (
                id TEXT PRIMARY KEY,
                ranking_id TEXT NOT NULL REFERENCES portfolio_rankings(id),
                resource_type TEXT NOT NULL,
                total_units REAL NOT NULL,
                allocations_json TEXT NOT NULL,
                plan_hash TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                governance_request_id TEXT,
                governance_receipt_hash TEXT,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_governance_bindings (
                governance_request_id TEXT PRIMARY KEY
                    REFERENCES governance_action_requests(id),
                plan_id TEXT NOT NULL REFERENCES portfolio_allocation_plans(id),
                receipt_hash TEXT NOT NULL,
                bound_at REAL NOT NULL,
                UNIQUE(plan_id)
            );

            CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_initiative
                ON portfolio_snapshots(initiative_id, as_of);
            CREATE INDEX IF NOT EXISTS idx_portfolio_rankings_created
                ON portfolio_rankings(created_at);
            """
        )
        self.runtime.conn.commit()

    def register_initiative(
        self,
        *,
        initiative_id: str,
        name: str,
        owner_agent_id: str,
        business_ref: Optional[str] = None,
        product_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(owner_agent_id)
        initiative_id = initiative_id.strip()
        name = name.strip()
        if not initiative_id or not name:
            raise CapitalAllocatorError("initiative_id and name are required")
        if business_ref:
            self._validate_graph_ref(business_ref, "BUSINESS")
        if product_ref:
            self._validate_graph_ref(product_ref, "PRODUCT")
        ts = _now()
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO portfolio_initiatives(
                    id, name, business_ref, product_ref, owner_agent_id,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    initiative_id,
                    name,
                    business_ref.strip() if business_ref else None,
                    product_ref.strip() if product_ref else None,
                    owner_agent_id,
                    ts,
                    ts,
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise CapitalAllocatorError("initiative identity already exists") from exc
        self.runtime.conn.commit()
        return self.get_initiative(initiative_id)

    def set_policy(
        self,
        *,
        policy_id: str,
        updated_by_principal: str,
        principal_kind: str,
        evidence: Dict[str, Any],
        overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if principal_kind != "HUMAN":
            raise CapitalAllocatorError("allocator policy changes require a HUMAN principal")
        policy_id = policy_id.strip()
        if not policy_id or not updated_by_principal.strip() or not evidence:
            raise CapitalAllocatorError("policy_id, human principal, and evidence are required")
        config = dict(DEFAULT_POLICY)
        for key, raw in (overrides or {}).items():
            if key not in config:
                raise CapitalAllocatorError(f"unknown allocator policy key: {key}")
            value = float(raw)
            if not math.isfinite(value) or value < 0:
                raise CapitalAllocatorError("policy values must be finite and non-negative")
            config[key] = value
        if not 0 < config["min_evidence_coverage"] <= 1:
            raise CapitalAllocatorError("min_evidence_coverage must be within (0, 1]")
        if not 0 < config["max_allocation_share"] <= 1:
            raise CapitalAllocatorError("max_allocation_share must be within (0, 1]")
        if config["max_snapshot_skew_days"] < 0:
            raise CapitalAllocatorError("max_snapshot_skew_days cannot be negative")

        prior = self.runtime.conn.execute(
            "SELECT MAX(version) AS v FROM portfolio_policies WHERE id LIKE ?",
            (f"{policy_id}@v%",),
        ).fetchone()
        version = int(prior["v"] or 0) + 1
        # Policy IDs are immutable rows in this reference implementation. Versioned updates use
        # policy_id@vN so historical rankings always bind to an exact policy.
        stored_id = f"{policy_id}@v{version}"
        payload = {
            "policy_family": policy_id,
            "version": version,
            "config": config,
        }
        policy_hash = _sha(payload)
        evidence_hash = _sha(evidence)
        self.runtime.conn.execute(
            """
            INSERT INTO portfolio_policies(
                id, version, config_json, policy_hash, updated_by_principal,
                evidence_json, evidence_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored_id,
                version,
                _json(config),
                policy_hash,
                updated_by_principal,
                _json(evidence),
                evidence_hash,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return self.get_policy(stored_id)

    def add_snapshot(
        self,
        initiative_id: str,
        *,
        snapshot_id: str,
        as_of: float,
        metrics: Dict[str, float],
        evidence: Dict[str, Dict[str, Any]],
        created_by_agent_id: str,
    ) -> Dict[str, Any]:
        self._require_active_initiative(initiative_id)
        self.runtime._require_agent(created_by_agent_id)
        snapshot_id = snapshot_id.strip()
        if not snapshot_id:
            raise CapitalAllocatorError("snapshot_id is required")
        as_of = float(as_of)
        if not math.isfinite(as_of):
            raise CapitalAllocatorError("as_of must be finite")
        normalized_metrics = self._normalize_metrics(metrics)
        normalized_evidence = self._normalize_evidence(
            normalized_metrics,
            evidence,
            as_of=as_of,
        )
        snapshot_payload = {
            "snapshot_id": snapshot_id,
            "initiative_id": initiative_id,
            "as_of": as_of,
            "metrics": normalized_metrics,
            "evidence": normalized_evidence,
        }
        snapshot_hash = _sha(snapshot_payload)
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO portfolio_snapshots(
                    id, initiative_id, as_of, metrics_json, evidence_json,
                    snapshot_hash, created_by_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    initiative_id,
                    as_of,
                    _json(normalized_metrics),
                    _json(normalized_evidence),
                    snapshot_hash,
                    created_by_agent_id,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise CapitalAllocatorError("snapshot identity/hash already exists") from exc
        self.runtime.conn.commit()
        return self.get_snapshot(snapshot_id)

    def rank(
        self,
        snapshot_ids: Iterable[str],
        *,
        policy_id: str,
        created_by_agent_id: str,
        ranking_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        policy = self.get_policy(policy_id)
        config = policy["config"]
        snapshots = [self.get_snapshot(snapshot_id) for snapshot_id in snapshot_ids]
        if not snapshots:
            raise CapitalAllocatorError("ranking requires at least one snapshot")
        initiative_ids = [row["initiative_id"] for row in snapshots]
        if len(initiative_ids) != len(set(initiative_ids)):
            raise CapitalAllocatorError("ranking may include only one snapshot per initiative")
        as_of = max(float(row["as_of"]) for row in snapshots)
        oldest_as_of = min(float(row["as_of"]) for row in snapshots)
        max_skew_seconds = float(config["max_snapshot_skew_days"]) * 86400.0
        if as_of - oldest_as_of > max_skew_seconds + 1e-9:
            raise CapitalAllocatorError(
                "snapshot dates are too far apart for a fair portfolio comparison"
            )

        rows = []
        for snapshot in snapshots:
            row = self._score_snapshot(snapshot, config=config)
            rows.append(row)

        rows.sort(
            key=lambda row: (
                row["decision_support_score"],
                row["evidence_coverage"],
                row["realized_net_cash"],
                row["initiative_id"],
            ),
            reverse=True,
        )
        for index, row in enumerate(rows, start=1):
            row["formula_rank"] = index

        snapshot_set_hash = _sha(
            sorted((row["id"], row["snapshot_hash"]) for row in snapshots)
        )
        payload = {
            "policy_hash": policy["policy_hash"],
            "as_of": as_of,
            "snapshot_set_hash": snapshot_set_hash,
            "rows": rows,
        }
        ranking_hash = _sha(payload)
        ranking_id = ranking_id or f"ranking_{uuid.uuid4().hex}"
        self.runtime.conn.execute(
            """
            INSERT INTO portfolio_rankings(
                id, policy_id, policy_hash, as_of, snapshot_set_hash,
                ranking_json, ranking_hash, created_by_agent_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ranking_id,
                policy["id"],
                policy["policy_hash"],
                as_of,
                snapshot_set_hash,
                _json(rows),
                ranking_hash,
                created_by_agent_id,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return self.get_ranking(ranking_id)

    def build_plan(
        self,
        ranking_id: str,
        *,
        resource_type: str,
        total_units: float,
        created_by_agent_id: str,
        plan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        ranking = self.get_ranking(ranking_id)
        resource_type = resource_type.strip().upper()
        if resource_type not in RESOURCE_TYPES:
            raise CapitalAllocatorError(f"unsupported resource type: {resource_type}")
        total_units = float(total_units)
        if not math.isfinite(total_units) or total_units <= 0:
            raise CapitalAllocatorError("total_units must be finite and positive")
        if resource_type == "CASH_CENTS" and not total_units.is_integer():
            raise CapitalAllocatorError("CASH_CENTS total_units must be an integer number of cents")

        policy = self.get_policy(ranking["policy_id"])
        max_share = float(policy["config"]["max_allocation_share"])
        eligible = [
            row for row in ranking["rows"]
            if row["eligible_for_allocation"] and row["decision_support_score"] > 0
        ]
        if not eligible:
            raise CapitalAllocatorError("no initiative has enough evidence for allocation")

        weights = [row["decision_support_score"] for row in eligible]
        allocations = self._capped_proportional_allocation(
            eligible,
            weights,
            total_units=total_units,
            max_share=max_share,
        )
        if resource_type == "CASH_CENTS":
            allocations = self._integerize_cents(allocations, int(total_units))

        payload = {
            "ranking_id": ranking_id,
            "ranking_hash": ranking["ranking_hash"],
            "resource_type": resource_type,
            "total_units": total_units,
            "allocations": allocations,
        }
        plan_hash = _sha(payload)
        plan_id = plan_id or f"plan_{uuid.uuid4().hex}"
        ts = _now()
        self.runtime.conn.execute(
            """
            INSERT INTO portfolio_allocation_plans(
                id, ranking_id, resource_type, total_units, allocations_json,
                plan_hash, status, created_by_agent_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?)
            """,
            (
                plan_id,
                ranking_id,
                resource_type,
                total_units,
                _json(allocations),
                plan_hash,
                created_by_agent_id,
                ts,
                ts,
            ),
        )
        self.runtime.conn.commit()
        return self.get_plan(plan_id)

    def request_plan_authorization(
        self,
        plan_id: str,
        *,
        actor_agent_id: str,
    ) -> Dict[str, Any]:
        if self.governance is None:
            raise CapitalAllocatorError("governance is required for allocation authorization")
        plan = self.get_plan(plan_id)
        if plan["status"] != "DRAFT":
            raise CapitalAllocatorError("only DRAFT plans may request authorization")
        self._assert_ranking_current(plan["ranking_id"])
        params = self._plan_parameters(plan)
        if plan["resource_type"] == "CASH_CENTS":
            decision = self.governance.request_action(
                actor_agent_id,
                action_key="portfolio.allocate.cash",
                action_class="MONEY_MOVEMENT",
                parameters=params,
                amount_cents=int(plan["total_units"]),
            )
        else:
            decision = self.governance.request_action(
                actor_agent_id,
                action_key=f"portfolio.allocate.{plan['resource_type'].lower()}",
                action_class="INTERNAL_WRITE",
                parameters=params,
                cost_units=(
                    float(plan["total_units"])
                    if plan["resource_type"] == "AI_COST_UNITS"
                    else 0.0
                ),
            )
        self.runtime.conn.execute(
            """
            UPDATE portfolio_allocation_plans
            SET governance_request_id=?, updated_at=?
            WHERE id=?
            """,
            (decision["request_id"], _now(), plan_id),
        )
        self.runtime.conn.commit()
        return {
            "plan_id": plan_id,
            "plan_hash": plan["plan_hash"],
            "governance": decision,
        }

    def bind_authorization(
        self,
        plan_id: str,
        *,
        governance_request_id: str,
    ) -> Dict[str, Any]:
        plan = self.get_plan(plan_id)
        if plan["status"] != "DRAFT":
            raise CapitalAllocatorError("plan is not awaiting authorization")
        self._assert_ranking_current(plan["ranking_id"])
        request = self.runtime.conn.execute(
            "SELECT * FROM governance_action_requests WHERE id=?",
            (governance_request_id,),
        ).fetchone()
        if request is None or request["status"] != "AUTHORIZED":
            raise CapitalAllocatorError("governance request is not AUTHORIZED")
        expected_class = (
            "MONEY_MOVEMENT"
            if plan["resource_type"] == "CASH_CENTS"
            else "INTERNAL_WRITE"
        )
        expected_key = (
            "portfolio.allocate.cash"
            if plan["resource_type"] == "CASH_CENTS"
            else f"portfolio.allocate.{plan['resource_type'].lower()}"
        )
        if request["action_key"] != expected_key or request["action_class"] != expected_class:
            raise CapitalAllocatorError("governance action does not match this allocation plan")
        if json.loads(request["parameters_json"]) != self._plan_parameters(plan):
            raise CapitalAllocatorError(
                "governance authorization is not bound to the exact allocation plan"
            )
        if plan["resource_type"] == "CASH_CENTS":
            if int(request["amount_cents"]) != int(plan["total_units"]):
                raise CapitalAllocatorError("authorized cash amount does not match the plan")
        decision = self.runtime.conn.execute(
            """
            SELECT * FROM governance_decisions
            WHERE request_id=? AND decision='ALLOW'
            ORDER BY created_at DESC LIMIT 1
            """,
            (governance_request_id,),
        ).fetchone()
        if decision is None:
            raise CapitalAllocatorError("authorized request has no ALLOW audit receipt")

        try:
            self.runtime.conn.execute(
                """
                INSERT INTO portfolio_governance_bindings(
                    governance_request_id, plan_id, receipt_hash, bound_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    governance_request_id,
                    plan_id,
                    decision["receipt_hash"],
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise CapitalAllocatorError(
                "governance authorization or plan has already been bound"
            ) from exc
        self.runtime.conn.execute(
            """
            UPDATE portfolio_allocation_plans
            SET status='AUTHORIZED', governance_request_id=?,
                governance_receipt_hash=?, updated_at=?
            WHERE id=?
            """,
            (
                governance_request_id,
                decision["receipt_hash"],
                _now(),
                plan_id,
            ),
        )
        self.runtime.conn.commit()
        return self.get_plan(plan_id)

    def get_initiative(self, initiative_id: str) -> Dict[str, Any]:
        row = self._require_initiative(initiative_id)
        return dict(row)

    def get_policy(self, policy_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM portfolio_policies WHERE id=?",
            (policy_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown allocator policy: {policy_id}")
        return {
            "id": row["id"],
            "version": row["version"],
            "config": json.loads(row["config_json"]),
            "policy_hash": row["policy_hash"],
            "updated_by_principal": row["updated_by_principal"],
            "evidence": json.loads(row["evidence_json"]),
            "evidence_hash": row["evidence_hash"],
            "created_at": row["created_at"],
        }

    def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM portfolio_snapshots WHERE id=?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown portfolio snapshot: {snapshot_id}")
        return {
            "id": row["id"],
            "initiative_id": row["initiative_id"],
            "as_of": row["as_of"],
            "metrics": json.loads(row["metrics_json"]),
            "evidence": json.loads(row["evidence_json"]),
            "snapshot_hash": row["snapshot_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "created_at": row["created_at"],
        }

    def get_ranking(self, ranking_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM portfolio_rankings WHERE id=?",
            (ranking_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown portfolio ranking: {ranking_id}")
        return {
            "id": row["id"],
            "policy_id": row["policy_id"],
            "policy_hash": row["policy_hash"],
            "as_of": row["as_of"],
            "snapshot_set_hash": row["snapshot_set_hash"],
            "rows": json.loads(row["ranking_json"]),
            "ranking_hash": row["ranking_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "created_at": row["created_at"],
        }

    def get_plan(self, plan_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM portfolio_allocation_plans WHERE id=?",
            (plan_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown allocation plan: {plan_id}")
        return {
            "id": row["id"],
            "ranking_id": row["ranking_id"],
            "resource_type": row["resource_type"],
            "total_units": row["total_units"],
            "allocations": json.loads(row["allocations_json"]),
            "plan_hash": row["plan_hash"],
            "status": row["status"],
            "governance_request_id": row["governance_request_id"],
            "governance_receipt_hash": row["governance_receipt_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _score_snapshot(self, snapshot: Dict[str, Any], *, config: Dict[str, float]) -> Dict[str, Any]:
        m = snapshot["metrics"]
        ev = snapshot["evidence"]

        def q(metric: str) -> float:
            item = ev.get(metric)
            if not item:
                return 0.0
            return float(SOURCE_QUALITY[item["source_type"]])

        def observed(metric: str) -> float:
            return float(m.get(metric, 0.0)) if q(metric) > 0 else 0.0

        realized_net_cash = (
            observed("cash_collected_30d")
            - observed("cash_costs_30d")
            - observed("ai_cost_30d")
        )
        recognized_revenue = observed("revenue_recognized_30d")
        contracted = observed("contracted_pipeline_value_90d")
        qualified = observed("qualified_pipeline_value_90d")

        economic_value = (
            realized_net_cash * config["realized_net_cash_weight"]
            + recognized_revenue
            * q("revenue_recognized_30d")
            * config["recognized_revenue_weight"]
            + contracted
            * q("contracted_pipeline_value_90d")
            * config["contracted_pipeline_weight"]
            + qualified
            * q("qualified_pipeline_value_90d")
            * config["qualified_pipeline_weight"]
        )

        retention = observed("retention_signal")
        market = observed("market_evidence_signal")
        strategic = observed("strategic_reuse_signal")
        # Convert monetary magnitude to a dimensionless index before combining it with
        # non-monetary signals. This avoids pretending one human hour is literally one dollar.
        economic_index = math.copysign(
            math.log1p(abs(economic_value)),
            economic_value,
        ) if economic_value != 0 else 0.0

        signal_bonus = (
            retention * q("retention_signal") * config["retention_signal_weight"]
            + market * q("market_evidence_signal") * config["market_evidence_weight"]
            + strategic * q("strategic_reuse_signal") * config["strategic_reuse_weight"]
        )

        human_hours = observed("human_hours_30d")
        effort_hours = observed("remaining_effort_hours")
        time_days = observed("time_to_cash_days")
        effort_penalty = (
            math.log1p(human_hours) * config["human_hours_penalty"]
            + math.log1p(effort_hours) * config["remaining_effort_penalty"]
            + math.log1p(time_days) * config["time_to_cash_penalty"]
        )
        raw_score = economic_index + signal_bonus - effort_penalty

        # Coverage is measured against a fixed core schema plus any optional metrics the
        # initiative chose to report. Omitting weak metrics therefore cannot inflate coverage.
        coverage_denominator = CORE_METRICS | set(m)
        evidenced = {metric for metric in coverage_denominator if q(metric) > 0}
        evidence_coverage = (
            len(evidenced) / len(coverage_denominator)
            if coverage_denominator
            else 0.0
        )
        evidence_factor = evidence_coverage ** 2
        decision_support_score = raw_score * evidence_factor

        eligible = evidence_coverage >= config["min_evidence_coverage"]
        if not eligible:
            state = "OBSERVE_ONLY"
        elif realized_net_cash < 0 and economic_value <= 0:
            state = "PAUSE_REVIEW"
        elif decision_support_score > 0:
            state = "ALLOCATE_CANDIDATE"
        else:
            state = "MAINTAIN_REVIEW"

        return {
            "initiative_id": snapshot["initiative_id"],
            "snapshot_id": snapshot["id"],
            "snapshot_hash": snapshot["snapshot_hash"],
            "as_of": snapshot["as_of"],
            "realized_net_cash": realized_net_cash,
            "recognized_revenue": recognized_revenue,
            "contracted_pipeline_value": contracted,
            "qualified_pipeline_value": qualified,
            "economic_value_component": economic_value,
            "economic_index_component": economic_index,
            "signal_bonus_component": signal_bonus,
            "effort_penalty_component": effort_penalty,
            "raw_score": raw_score,
            "evidence_coverage": evidence_coverage,
            "evidence_factor": evidence_factor,
            "decision_support_score": decision_support_score,
            "eligible_for_allocation": eligible,
            "decision_state": state,
        }

    def _normalize_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        if not isinstance(metrics, dict) or not metrics:
            raise CapitalAllocatorError("metrics must be a non-empty object")
        unknown = set(metrics) - ALL_METRICS
        if unknown:
            raise CapitalAllocatorError(f"unknown portfolio metrics: {sorted(unknown)}")
        out: Dict[str, float] = {}
        for key, raw in metrics.items():
            value = float(raw)
            if not math.isfinite(value):
                raise CapitalAllocatorError("metric values must be finite")
            if key in SIGNAL_METRICS:
                if value < 0 or value > 1:
                    raise CapitalAllocatorError(f"{key} must be within [0, 1]")
            elif value < 0:
                raise CapitalAllocatorError(f"{key} cannot be negative")
            out[key] = value
        return out

    def _normalize_evidence(
        self,
        metrics: Dict[str, float],
        evidence: Dict[str, Dict[str, Any]],
        *,
        as_of: float,
    ) -> Dict[str, Dict[str, Any]]:
        if not isinstance(evidence, dict):
            raise CapitalAllocatorError("evidence must be an object")
        out: Dict[str, Dict[str, Any]] = {}
        for metric, item in evidence.items():
            if metric not in metrics:
                raise CapitalAllocatorError(
                    f"evidence supplied for absent metric: {metric}"
                )
            if not isinstance(item, dict):
                raise CapitalAllocatorError("metric evidence must be an object")
            source_type = str(item.get("source_type", "")).strip().upper()
            source_ref = str(item.get("source_ref", "")).strip()
            source_sha256 = str(item.get("source_sha256", "")).strip().lower()
            observed_at = float(item.get("observed_at"))
            if source_type not in SOURCE_QUALITY:
                raise CapitalAllocatorError(f"unsupported source_type: {source_type}")
            if source_type not in ALLOWED_SOURCE_TYPES[metric]:
                raise CapitalAllocatorError(
                    f"{source_type} is not admissible evidence for {metric}"
                )
            if not source_ref or not _valid_sha256(source_sha256):
                raise CapitalAllocatorError(
                    "metric evidence requires source_ref and SHA-256 source identity"
                )
            if not math.isfinite(observed_at) or observed_at > as_of:
                raise CapitalAllocatorError(
                    "metric evidence observed_at must be finite and not after snapshot as_of"
                )
            age_days = (as_of - observed_at) / 86400.0
            if age_days > MAX_EVIDENCE_AGE_DAYS[metric] + 1e-9:
                raise CapitalAllocatorError(
                    f"evidence for {metric} is too stale for allocation"
                )
            out[metric] = {
                "source_type": source_type,
                "source_ref": source_ref,
                "source_sha256": source_sha256,
                "observed_at": observed_at,
            }
        return out

    def _capped_proportional_allocation(
        self,
        rows: List[Dict[str, Any]],
        weights: List[float],
        *,
        total_units: float,
        max_share: float,
    ) -> List[Dict[str, Any]]:
        n = len(rows)
        if max_share * n < 1.0 - 1e-12:
            raise CapitalAllocatorError(
                "max_allocation_share is too low to allocate the full resource pool"
            )
        remaining = total_units
        active = set(range(n))
        allocations = [0.0] * n
        cap = total_units * max_share
        remaining_weights = [max(0.0, float(w)) for w in weights]

        while active and remaining > 1e-9:
            weight_sum = sum(remaining_weights[i] for i in active)
            if weight_sum <= 0:
                equal = remaining / len(active)
                for i in list(active):
                    give = min(equal, cap - allocations[i])
                    allocations[i] += give
                    remaining -= give
                break
            capped_any = False
            for i in list(active):
                share = remaining * remaining_weights[i] / weight_sum
                room = cap - allocations[i]
                if share >= room - 1e-12:
                    give = max(0.0, room)
                    allocations[i] += give
                    remaining -= give
                    active.remove(i)
                    capped_any = True
            if capped_any:
                continue
            for i in list(active):
                give = remaining * remaining_weights[i] / weight_sum
                allocations[i] += give
            remaining = 0.0

        return [
            {
                "initiative_id": rows[i]["initiative_id"],
                "formula_rank": rows[i]["formula_rank"],
                "decision_support_score": rows[i]["decision_support_score"],
                "units": allocations[i],
                "share": allocations[i] / total_units,
            }
            for i in range(n)
        ]

    def _integerize_cents(
        self,
        allocations: List[Dict[str, Any]],
        total_cents: int,
    ) -> List[Dict[str, Any]]:
        floors = [int(row["units"]) for row in allocations]
        remaining = total_cents - sum(floors)
        fractions = sorted(
            [
                (allocations[i]["units"] - floors[i], i)
                for i in range(len(allocations))
            ],
            reverse=True,
        )
        for _, idx in fractions[:remaining]:
            floors[idx] += 1
        out = []
        for idx, row in enumerate(allocations):
            item = dict(row)
            item["units"] = floors[idx]
            item["share"] = floors[idx] / total_cents
            out.append(item)
        return out

    def _assert_ranking_current(self, ranking_id: str) -> None:
        ranking = self.get_ranking(ranking_id)
        policy = self.get_policy(ranking["policy_id"])
        family = ranking["policy_id"].rsplit("@v", 1)[0]
        latest = self.runtime.conn.execute(
            """
            SELECT id, version FROM portfolio_policies
            WHERE id LIKE ?
            ORDER BY version DESC LIMIT 1
            """,
            (f"{family}@v%",),
        ).fetchone()
        if latest is None or latest["id"] != policy["id"]:
            raise CapitalAllocatorError(
                "allocator policy changed after ranking; rebuild the ranking"
            )

        for row in ranking["rows"]:
            snapshot = self.get_snapshot(row["snapshot_id"])
            newer = self.runtime.conn.execute(
                """
                SELECT id FROM portfolio_snapshots
                WHERE initiative_id=? AND as_of > ?
                ORDER BY as_of DESC LIMIT 1
                """,
                (snapshot["initiative_id"], snapshot["as_of"]),
            ).fetchone()
            if newer is not None:
                raise CapitalAllocatorError(
                    "newer initiative data exists; rebuild ranking before authorization"
                )

    def _plan_parameters(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        ranking = self.get_ranking(plan["ranking_id"])
        return {
            "plan_id": plan["id"],
            "plan_hash": plan["plan_hash"],
            "ranking_id": plan["ranking_id"],
            "ranking_hash": ranking["ranking_hash"],
            "resource_type": plan["resource_type"],
            "total_units": plan["total_units"],
            "allocations": plan["allocations"],
        }

    def _validate_graph_ref(self, node_id: str, expected_type: str) -> None:
        try:
            row = self.runtime.conn.execute(
                """
                SELECT node_type, status FROM graph_nodes
                WHERE id=?
                """,
                (node_id,),
            ).fetchone()
        except Exception as exc:
            raise CapitalAllocatorError(
                "knowledge graph must be initialized before graph references are used"
            ) from exc
        if row is None:
            raise CapitalAllocatorError(f"unknown knowledge-graph node: {node_id}")
        if row["node_type"] != expected_type or row["status"] != "ACTIVE":
            raise CapitalAllocatorError(
                f"graph reference must be an ACTIVE {expected_type} node"
            )

    def _require_initiative(self, initiative_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM portfolio_initiatives WHERE id=?",
            (initiative_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown portfolio initiative: {initiative_id}")
        return row

    def _require_active_initiative(self, initiative_id: str):
        row = self._require_initiative(initiative_id)
        if row["status"] != "ACTIVE":
            raise CapitalAllocatorError("initiative is not ACTIVE")
        return row
