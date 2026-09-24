import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_business_os.capital_allocator import CapitalAllocator, CapitalAllocatorError
from ai_business_os.governance import GovernanceControlPlane
from ai_business_os.knowledge_graph import KnowledgeGraph
from ai_business_os.persistent_agents.runtime import AgentRuntime


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class CapitalAllocatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.gov = GovernanceControlPlane(self.runtime)
        self.graph = KnowledgeGraph(self.runtime)
        self.alloc = CapitalAllocator(self.runtime, self.gov)

        self.owner = self.runtime.register_agent("portfolio-owner")
        self.analyst = self.runtime.register_agent("portfolio-analyst")
        self.executor = self.runtime.register_agent("portfolio-executor")

        self.business = self.graph.register_node(
            node_type="BUSINESS",
            canonical_key="business:alpha",
            label="Alpha Business",
            attributes={},
            provenance={"evidence_refs": ["registry:alpha"]},
            created_by_agent_id=self.owner,
        )
        self.product = self.graph.register_node(
            node_type="PRODUCT",
            canonical_key="product:alpha",
            label="Alpha Product",
            attributes={},
            provenance={"evidence_refs": ["catalog:alpha"]},
            created_by_agent_id=self.owner,
        )

        self.alloc.register_initiative(
            initiative_id="alpha",
            name="Alpha",
            owner_agent_id=self.owner,
            business_ref=self.business["id"],
            product_ref=self.product["id"],
        )
        self.alloc.register_initiative(
            initiative_id="beta",
            name="Beta",
            owner_agent_id=self.owner,
        )
        self.policy = self.alloc.set_policy(
            policy_id="money-first",
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"decision": "initial portfolio policy"},
            overrides={"max_allocation_share": 0.60},
        )

        self.gov.set_agent_policy(
            self.executor,
            allowed_classes=["INTERNAL_WRITE", "MONEY_MOVEMENT"],
            allowed_action_keys=[
                "portfolio.allocate.ai_cost_units",
                "portfolio.allocate.engineering_hours",
                "portfolio.allocate.human_hours",
                "portfolio.allocate.cash",
            ],
            human_approval_classes=["MONEY_MOVEMENT"],
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"policy": "portfolio executor"},
            max_cost_units_per_window=1000.0,
            max_money_cents_per_window=1000000,
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def evidence(self, metric, source_type, *, observed_at=1000.0, label=None):
        return {
            "source_type": source_type,
            "source_ref": f"source/{label or metric}",
            "source_sha256": digest(label or metric),
            "observed_at": observed_at,
        }

    def core_snapshot(
        self,
        initiative_id,
        snapshot_id,
        *,
        as_of=1000.0,
        cash=0.0,
        costs=0.0,
        ai_cost=0.0,
        contracted=0.0,
        effort=20.0,
        time_days=30.0,
        market=0.5,
        qualified=0.0,
        revenue=0.0,
        human_hours=10.0,
        retention=0.5,
        strategic=0.5,
    ):
        metrics = {
            "cash_collected_30d": cash,
            "cash_costs_30d": costs,
            "ai_cost_30d": ai_cost,
            "contracted_pipeline_value_90d": contracted,
            "remaining_effort_hours": effort,
            "time_to_cash_days": time_days,
            "market_evidence_signal": market,
            "qualified_pipeline_value_90d": qualified,
            "revenue_recognized_30d": revenue,
            "human_hours_30d": human_hours,
            "retention_signal": retention,
            "strategic_reuse_signal": strategic,
        }
        evidence = {
            "cash_collected_30d": self.evidence("cash", "BANK", observed_at=as_of),
            "cash_costs_30d": self.evidence("costs", "GENERAL_LEDGER", observed_at=as_of),
            "ai_cost_30d": self.evidence("ai", "INVOICE", observed_at=as_of),
            "contracted_pipeline_value_90d": self.evidence(
                "contracted", "SIGNED_CONTRACT", observed_at=as_of
            ),
            "remaining_effort_hours": self.evidence(
                "effort", "ANALYTICS", observed_at=as_of
            ),
            "time_to_cash_days": self.evidence(
                "time", "ANALYTICS", observed_at=as_of
            ),
            "market_evidence_signal": self.evidence(
                "market", "ANALYTICS", observed_at=as_of
            ),
            "qualified_pipeline_value_90d": self.evidence(
                "qualified", "CRM", observed_at=as_of
            ),
            "revenue_recognized_30d": self.evidence(
                "revenue", "GENERAL_LEDGER", observed_at=as_of
            ),
            "human_hours_30d": self.evidence(
                "human", "ANALYTICS", observed_at=as_of
            ),
            "retention_signal": self.evidence(
                "retention", "CRM", observed_at=as_of
            ),
            "strategic_reuse_signal": self.evidence(
                "strategic", "ANALYTICS", observed_at=as_of
            ),
        }
        return self.alloc.add_snapshot(
            initiative_id,
            snapshot_id=snapshot_id,
            as_of=as_of,
            metrics=metrics,
            evidence=evidence,
            created_by_agent_id=self.analyst,
        )

    def ranking(self):
        a = self.core_snapshot(
            "alpha",
            "snap-alpha",
            cash=10000,
            costs=2000,
            ai_cost=500,
            contracted=30000,
            effort=15,
            time_days=14,
            market=0.8,
            qualified=10000,
            revenue=9000,
        )
        b = self.core_snapshot(
            "beta",
            "snap-beta",
            cash=2000,
            costs=1500,
            ai_cost=500,
            contracted=5000,
            effort=60,
            time_days=60,
            market=0.4,
            qualified=25000,
            revenue=2500,
        )
        return self.alloc.rank(
            [a["id"], b["id"]],
            policy_id=self.policy["id"],
            created_by_agent_id=self.analyst,
            ranking_id="ranking-1",
        )

    def test_initiative_graph_refs_must_be_typed_and_active(self):
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.register_initiative(
                initiative_id="bad-ref",
                name="Bad Ref",
                owner_agent_id=self.owner,
                business_ref=self.product["id"],
            )

    def test_policy_changes_require_human_principal(self):
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.set_policy(
                policy_id="unsafe",
                updated_by_principal="agent",
                principal_kind="AGENT",
                evidence={"attempt": "self tune"},
            )

    def test_policy_versions_are_immutable_and_hashed(self):
        p2 = self.alloc.set_policy(
            policy_id="money-first",
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"decision": "second policy"},
            overrides={"max_allocation_share": 0.70},
        )
        self.assertEqual(1, self.policy["version"])
        self.assertEqual(2, p2["version"])
        self.assertNotEqual(self.policy["id"], p2["id"])
        self.assertNotEqual(self.policy["policy_hash"], p2["policy_hash"])

    def test_model_estimate_cannot_masquerade_as_realized_cash(self):
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.add_snapshot(
                "alpha",
                snapshot_id="bad-cash",
                as_of=1000,
                metrics={"cash_collected_30d": 50000},
                evidence={
                    "cash_collected_30d": self.evidence(
                        "cash", "MODEL_ESTIMATE", observed_at=1000
                    )
                },
                created_by_agent_id=self.analyst,
            )

    def test_future_and_stale_evidence_fail_closed(self):
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.add_snapshot(
                "alpha",
                snapshot_id="future",
                as_of=1000,
                metrics={"cash_collected_30d": 100},
                evidence={
                    "cash_collected_30d": self.evidence(
                        "cash", "BANK", observed_at=1001
                    )
                },
                created_by_agent_id=self.analyst,
            )
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.add_snapshot(
                "alpha",
                snapshot_id="stale",
                as_of=1000 + 50 * 86400,
                metrics={"cash_collected_30d": 100},
                evidence={
                    "cash_collected_30d": self.evidence(
                        "cash", "BANK", observed_at=1000
                    )
                },
                created_by_agent_id=self.analyst,
            )

    def test_cherry_picked_single_metric_does_not_get_full_coverage(self):
        snap = self.alloc.add_snapshot(
            "alpha",
            snapshot_id="thin",
            as_of=1000,
            metrics={"cash_collected_30d": 10000},
            evidence={
                "cash_collected_30d": self.evidence(
                    "cash", "BANK", observed_at=1000
                )
            },
            created_by_agent_id=self.analyst,
        )
        ranking = self.alloc.rank(
            [snap["id"]],
            policy_id=self.policy["id"],
            created_by_agent_id=self.analyst,
        )
        row = ranking["rows"][0]
        self.assertLess(row["evidence_coverage"], 0.60)
        self.assertFalse(row["eligible_for_allocation"])
        self.assertEqual("OBSERVE_ONLY", row["decision_state"])

    def test_realized_economics_and_stronger_pipeline_outrank_weak_speculation(self):
        ranking = self.ranking()
        self.assertEqual(["alpha", "beta"], [r["initiative_id"] for r in ranking["rows"]])
        self.assertGreater(
            ranking["rows"][0]["decision_support_score"],
            ranking["rows"][1]["decision_support_score"],
        )
        self.assertGreater(ranking["rows"][0]["realized_net_cash"], 0)

    def test_score_components_are_transparent_and_dimensionless_at_final_stage(self):
        ranking = self.ranking()
        row = ranking["rows"][0]
        expected_raw = (
            row["economic_index_component"]
            + row["signal_bonus_component"]
            - row["effort_penalty_component"]
        )
        self.assertAlmostEqual(expected_raw, row["raw_score"], places=8)
        self.assertAlmostEqual(
            row["raw_score"] * row["evidence_factor"],
            row["decision_support_score"],
            places=8,
        )

    def test_snapshots_too_far_apart_cannot_be_compared(self):
        a = self.core_snapshot("alpha", "skew-a", as_of=1000)
        b = self.core_snapshot("beta", "skew-b", as_of=1000 + 8 * 86400)
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.rank(
                [a["id"], b["id"]],
                policy_id=self.policy["id"],
                created_by_agent_id=self.analyst,
            )

    def test_allocation_plan_respects_concentration_cap(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        self.assertAlmostEqual(
            100.0,
            sum(row["units"] for row in plan["allocations"]),
            places=6,
        )
        self.assertTrue(all(row["share"] <= 0.60 + 1e-9 for row in plan["allocations"]))

    def test_cash_plan_is_integer_exact(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="CASH_CENTS",
            total_units=10001,
            created_by_agent_id=self.analyst,
        )
        self.assertEqual(10001, sum(row["units"] for row in plan["allocations"]))
        self.assertTrue(all(isinstance(row["units"], int) for row in plan["allocations"]))

    def test_no_evidence_eligible_initiative_means_no_plan(self):
        snap = self.alloc.add_snapshot(
            "alpha",
            snapshot_id="thin2",
            as_of=1000,
            metrics={"market_evidence_signal": 1.0},
            evidence={
                "market_evidence_signal": self.evidence(
                    "market", "MODEL_ESTIMATE", observed_at=1000
                )
            },
            created_by_agent_id=self.analyst,
        )
        ranking = self.alloc.rank(
            [snap["id"]],
            policy_id=self.policy["id"],
            created_by_agent_id=self.analyst,
        )
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.build_plan(
                ranking["id"],
                resource_type="AI_COST_UNITS",
                total_units=10,
                created_by_agent_id=self.analyst,
            )

    def test_newer_snapshot_invalidates_authorization(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        self.core_snapshot("alpha", "snap-alpha-new", as_of=1001, cash=11000)
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.request_plan_authorization(
                plan["id"],
                actor_agent_id=self.executor,
            )

    def test_new_policy_invalidates_old_ranking_authorization(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        self.alloc.set_policy(
            policy_id="money-first",
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"decision": "updated policy"},
            overrides={"max_allocation_share": 0.70},
        )
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.request_plan_authorization(
                plan["id"],
                actor_agent_id=self.executor,
            )

    def test_internal_resource_plan_can_be_governance_authorized(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        request = self.alloc.request_plan_authorization(
            plan["id"],
            actor_agent_id=self.executor,
        )
        self.assertEqual("ALLOW", request["governance"]["decision"])
        authorized = self.alloc.bind_authorization(
            plan["id"],
            governance_request_id=request["governance"]["request_id"],
        )
        self.assertEqual("AUTHORIZED", authorized["status"])
        self.assertEqual(64, len(authorized["governance_receipt_hash"]))

    def test_cash_allocation_requires_human_approval(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="CASH_CENTS",
            total_units=10000,
            created_by_agent_id=self.analyst,
        )
        request = self.alloc.request_plan_authorization(
            plan["id"],
            actor_agent_id=self.executor,
        )
        self.assertEqual("REQUIRE_APPROVAL", request["governance"]["decision"])
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.bind_authorization(
                plan["id"],
                governance_request_id=request["governance"]["request_id"],
            )

        approval = self.gov.approve_request(
            request["governance"]["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": "cash allocation"},
        )
        allowed = self.gov.evaluate_request(
            request["governance"]["request_id"],
            approval_id=approval["id"],
        )
        self.assertEqual("ALLOW", allowed["decision"])
        authorized = self.alloc.bind_authorization(
            plan["id"],
            governance_request_id=allowed["request_id"],
        )
        self.assertEqual("AUTHORIZED", authorized["status"])

    def test_kill_switch_blocks_allocation_authorization(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        self.gov.set_global_kill_switch(
            enabled=True,
            principal="owner",
            principal_kind="HUMAN",
            reason="portfolio freeze",
            evidence={"incident": "INC-9"},
        )
        request = self.alloc.request_plan_authorization(
            plan["id"],
            actor_agent_id=self.executor,
        )
        self.assertEqual("DENY", request["governance"]["decision"])

    def test_governance_authorization_is_exact_plan_bound_and_single_use(self):
        ranking = self.ranking()
        plan = self.alloc.build_plan(
            ranking["id"],
            resource_type="ENGINEERING_HOURS",
            total_units=100,
            created_by_agent_id=self.analyst,
        )
        request = self.alloc.request_plan_authorization(
            plan["id"],
            actor_agent_id=self.executor,
        )
        self.alloc.bind_authorization(
            plan["id"],
            governance_request_id=request["governance"]["request_id"],
        )
        with self.assertRaises(CapitalAllocatorError):
            self.alloc.bind_authorization(
                plan["id"],
                governance_request_id=request["governance"]["request_id"],
            )


if __name__ == "__main__":
    unittest.main()
