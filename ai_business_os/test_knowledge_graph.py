import tempfile
import unittest
from pathlib import Path

from ai_business_os.knowledge_graph import KnowledgeGraph, KnowledgeGraphError
from ai_business_os.persistent_agents.runtime import AgentRuntime


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.graph = KnowledgeGraph(self.runtime)
        self.agent = self.runtime.register_agent("graph-curator")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def node(self, node_type, key, label=None, provenance=None, attributes=None):
        return self.graph.register_node(
            node_type=node_type,
            canonical_key=key,
            label=label or key,
            attributes=attributes or {},
            provenance=provenance
            or {"evidence_refs": [f"evidence:{node_type}:{key}"]},
            created_by_agent_id=self.agent,
        )

    def build_lineage(self):
        repo = self.node("REPO", "repo:research-engine")
        capability = self.node("CAPABILITY", "cap:lead-research")
        product = self.node("PRODUCT", "product:business-os")
        experiment = self.node("EXPERIMENT", "exp:lead-test")
        outcome = self.node(
            "OUTCOME",
            "out:customer-win",
            provenance={
                "evidence_refs": ["invoice:1", "crm:deal-1"],
                "verified": True,
                "event_id": "revenue-event-1",
            },
            attributes={"metric": "revenue", "amount": 1000},
        )
        customer = self.node("CUSTOMER", "customer:acme")

        self.graph.add_edge(
            source_node_id=repo["id"],
            edge_type="IMPLEMENTS",
            target_node_id=capability["id"],
            evidence={"source": "code inspection"},
            created_by_agent_id=self.agent,
        )
        self.graph.add_edge(
            source_node_id=capability["id"],
            edge_type="ENABLES",
            target_node_id=product["id"],
            evidence={"source": "architecture acceptance"},
            created_by_agent_id=self.agent,
        )
        self.graph.add_edge(
            source_node_id=product["id"],
            edge_type="TESTED_BY",
            target_node_id=experiment["id"],
            evidence={"source": "experiment plan"},
            created_by_agent_id=self.agent,
        )
        self.graph.add_edge(
            source_node_id=experiment["id"],
            edge_type="PRODUCED",
            target_node_id=outcome["id"],
            evidence={"source": "verified outcome record"},
            created_by_agent_id=self.agent,
        )
        self.graph.add_edge(
            source_node_id=product["id"],
            edge_type="SERVES",
            target_node_id=customer["id"],
            evidence={"source": "customer record"},
            created_by_agent_id=self.agent,
        )
        return repo, capability, product, experiment, outcome, customer

    def test_typed_lineage_path_connects_repo_to_verified_outcome(self):
        repo, _, _, _, outcome, _ = self.build_lineage()
        paths = self.graph.find_paths(repo["id"], outcome["id"])
        self.assertEqual(len(paths), 1)
        self.assertEqual(
            [node["node_type"] for node in paths[0]["nodes"]],
            ["REPO", "CAPABILITY", "PRODUCT", "EXPERIMENT", "OUTCOME"],
        )
        self.assertEqual(len(paths[0]["evidence_chain_hash"]), 64)

    def test_invalid_edge_contract_fails_closed(self):
        repo = self.node("REPO", "repo:x")
        customer = self.node("CUSTOMER", "customer:x")
        with self.assertRaises(KnowledgeGraphError):
            self.graph.add_edge(
                source_node_id=repo["id"],
                edge_type="SERVES",
                target_node_id=customer["id"],
                evidence={"source": "invalid"},
                created_by_agent_id=self.agent,
            )

    def test_outcome_requires_verified_stable_provenance(self):
        with self.assertRaises(KnowledgeGraphError):
            self.node(
                "OUTCOME",
                "out:projection",
                provenance={
                    "evidence_refs": ["forecast:1"],
                    "verified": False,
                    "event_id": "forecast-only",
                },
            )
        with self.assertRaises(KnowledgeGraphError):
            self.node(
                "OUTCOME",
                "out:no-event",
                provenance={
                    "evidence_refs": ["receipt:1"],
                    "verified": True,
                },
            )

    def test_alias_resolves_without_destructive_merge(self):
        fedex = self.node("CUSTOMER", "customer:fedex", label="Federal Express Corporation")
        resolved = self.graph.add_alias(
            fedex["id"],
            alias="FedEx",
            evidence={"source": "customer master"},
            created_by_agent_id=self.agent,
        )
        self.assertEqual(resolved["id"], fedex["id"])
        self.assertEqual(
            self.graph.resolve("fedex", node_type="CUSTOMER")["canonical_key"],
            "customer:fedex",
        )

    def test_alias_ambiguity_across_types_requires_type(self):
        customer = self.node("CUSTOMER", "customer:alpha")
        product = self.node("PRODUCT", "product:alpha")
        self.graph.add_alias(
            customer["id"],
            alias="Alpha",
            evidence={"source": "crm"},
            created_by_agent_id=self.agent,
        )
        self.graph.add_alias(
            product["id"],
            alias="Alpha",
            evidence={"source": "catalog"},
            created_by_agent_id=self.agent,
        )
        with self.assertRaises(KnowledgeGraphError):
            self.graph.resolve("Alpha")
        self.assertEqual(
            self.graph.resolve("Alpha", node_type="PRODUCT")["id"],
            product["id"],
        )

    def test_duplicate_active_edge_is_rejected(self):
        repo = self.node("REPO", "repo:duplicate")
        capability = self.node("CAPABILITY", "cap:duplicate")
        self.graph.add_edge(
            source_node_id=repo["id"],
            edge_type="IMPLEMENTS",
            target_node_id=capability["id"],
            evidence={"source": "first"},
            created_by_agent_id=self.agent,
        )
        with self.assertRaises(KnowledgeGraphError):
            self.graph.add_edge(
                source_node_id=repo["id"],
                edge_type="IMPLEMENTS",
                target_node_id=capability["id"],
                evidence={"source": "duplicate"},
                created_by_agent_id=self.agent,
            )

    def test_supersession_preserves_temporal_history(self):
        repo = self.node("REPO", "repo:temporal")
        capability = self.node("CAPABILITY", "cap:temporal")
        old = self.graph.add_edge(
            source_node_id=repo["id"],
            edge_type="IMPLEMENTS",
            target_node_id=capability["id"],
            evidence={"revision": "old"},
            created_by_agent_id=self.agent,
            attributes={"revision": 1},
            valid_from=100.0,
        )
        new = self.graph.supersede_edge(
            old["id"],
            evidence={"revision": "new"},
            created_by_agent_id=self.agent,
            attributes={"revision": 2},
            valid_from=200.0,
        )
        historical = self.graph.neighbors(repo["id"], as_of=150.0)
        current = self.graph.neighbors(repo["id"], as_of=250.0)
        self.assertEqual([edge["id"] for edge in historical], [old["id"]])
        self.assertEqual([edge["id"] for edge in current], [new["id"]])
        self.assertEqual(self.graph.get_edge(old["id"])["status"], "SUPERSEDED")
        self.assertEqual(new["supersedes_edge_id"], old["id"])

    def test_outcome_lineage_recovers_upstream_evidence_chain(self):
        repo, capability, product, experiment, outcome, _ = self.build_lineage()
        lineage = self.graph.outcome_lineage(outcome["id"])
        lineage_ids = {node["id"] for node in lineage["nodes"]}
        self.assertTrue(
            {repo["id"], capability["id"], product["id"], experiment["id"], outcome["id"]}
            <= lineage_ids
        )
        self.assertEqual(len(lineage["provenance_hash"]), 64)

    def test_node_with_active_relationship_cannot_be_retired(self):
        repo = self.node("REPO", "repo:active")
        capability = self.node("CAPABILITY", "cap:active")
        self.graph.add_edge(
            source_node_id=repo["id"],
            edge_type="IMPLEMENTS",
            target_node_id=capability["id"],
            evidence={"source": "active"},
            created_by_agent_id=self.agent,
        )
        with self.assertRaises(KnowledgeGraphError):
            self.graph.retire_node(
                repo["id"],
                created_by_agent_id=self.agent,
                reason="cleanup",
                evidence={"ticket": "1"},
            )

    def test_missing_edge_evidence_fails_closed(self):
        repo = self.node("REPO", "repo:no-evidence")
        capability = self.node("CAPABILITY", "cap:no-evidence")
        with self.assertRaises(KnowledgeGraphError):
            self.graph.add_edge(
                source_node_id=repo["id"],
                edge_type="IMPLEMENTS",
                target_node_id=capability["id"],
                evidence={},
                created_by_agent_id=self.agent,
            )

    def test_broad_dependency_relationship_still_preserves_evidence(self):
        business = self.node("BUSINESS", "business:a")
        data = self.node("DATA", "data:a")
        edge = self.graph.add_edge(
            source_node_id=business["id"],
            edge_type="DEPENDS_ON",
            target_node_id=data["id"],
            evidence={"source": "business requirement"},
            created_by_agent_id=self.agent,
        )
        self.assertEqual(edge["edge_type"], "DEPENDS_ON")
        self.assertEqual(len(edge["evidence_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
