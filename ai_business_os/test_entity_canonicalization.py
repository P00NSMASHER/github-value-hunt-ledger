import tempfile
import unittest
from pathlib import Path

from ai_business_os.entity_canonicalization import (
    CanonicalizationError,
    EntityCanonicalizer,
)
from ai_business_os.knowledge_graph import KnowledgeGraph, KnowledgeGraphError
from ai_business_os.persistent_agents.runtime import AgentRuntime


class EntityCanonicalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.graph = KnowledgeGraph(self.runtime)
        self.agent = self.runtime.register_agent("entity-curator")
        self.reviewer = self.runtime.register_agent("entity-reviewer")
        self.canonicalizer = EntityCanonicalizer(self.runtime, self.graph)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def node(
        self,
        node_id,
        label,
        *,
        node_type="CUSTOMER",
        attributes=None,
        aliases=(),
    ):
        node = self.graph.register_node(
            node_type=node_type,
            canonical_key=node_id,
            label=label,
            attributes=attributes or {},
            provenance={"evidence_refs": [f"source:{node_id}"]},
            created_by_agent_id=self.agent,
            node_id=node_id,
        )
        for alias in aliases:
            self.graph.add_alias(
                node_id,
                alias=alias,
                evidence={"source": node_id, "alias": alias},
                created_by_agent_id=self.agent,
            )
        return node

    def shared_business_neighbor(self, *customer_ids):
        business = self.node(
            f"business-{len(customer_ids)}-{customer_ids[0]}",
            "Freight Recovery",
            node_type="BUSINESS",
        )
        for idx, customer_id in enumerate(customer_ids):
            self.graph.add_edge(
                source_node_id=business["id"],
                edge_type="SERVES",
                target_node_id=customer_id,
                evidence={"source": f"crm-{idx}"},
                created_by_agent_id=self.agent,
            )
        return business

    def test_type_mismatch_never_merges(self):
        customer = self.node("customer:a", "Alpha")
        product = self.node("product:a", "Alpha", node_type="PRODUCT")
        evidence = self.canonicalizer.compare(customer["id"], product["id"])
        self.assertEqual("KEEP_SEPARATE", evidence.decision)
        self.assertEqual(0.0, evidence.score)

    def test_same_name_but_conflicting_hard_identifier_stays_separate(self):
        a = self.node("customer:a", "Acme Incorporated", attributes={"ein": "11-1111111"})
        b = self.node("customer:b", "Acme Inc", attributes={"ein": "22-2222222"})
        evidence = self.canonicalizer.compare(a["id"], b["id"])
        self.assertEqual("KEEP_SEPARATE", evidence.decision)
        self.assertIn("ein", evidence.hard_identifier_conflicts)
        with self.assertRaises(CanonicalizationError):
            self.canonicalizer.merge(
                a["id"],
                b["id"],
                created_by_agent_id=self.agent,
                match_evidence=evidence,
            )

    def test_matching_hard_identifier_is_strong_identity_evidence(self):
        a = self.node(
            "customer:a",
            "Acme Holdings",
            attributes={"ein": "11-1111111"},
        )
        b = self.node(
            "customer:b",
            "Acme Northeast Division",
            attributes={"ein": "11-1111111"},
        )
        evidence = self.canonicalizer.compare(a["id"], b["id"])
        self.assertEqual("AUTO_MERGE", evidence.decision)
        self.assertIn("ein", evidence.hard_identifier_matches)

    def test_context_can_auto_merge_normalized_name_variants(self):
        a = self.node(
            "customer:a",
            "Federal Express Corporation",
            attributes={"description": "parcel logistics carrier"},
            aliases=["FedEx"],
        )
        b = self.node(
            "customer:b",
            "Federal Express Corp",
            attributes={"description": "parcel logistics carrier"},
        )
        self.shared_business_neighbor(a["id"], b["id"])
        evidence = self.canonicalizer.compare(a["id"], b["id"])
        self.assertTrue(evidence.normalized_name_equal)
        self.assertGreaterEqual(evidence.score, self.canonicalizer.auto_merge_threshold)
        self.assertEqual("AUTO_MERGE", evidence.decision)

    def test_ambiguous_pair_requires_human_review(self):
        a = self.node(
            "customer:a",
            "Acme Freight",
            attributes={"description": "regional freight logistics carrier"},
            aliases=["Acme Logistics"],
        )
        b = self.node(
            "customer:b",
            "Acme Logistics",
            attributes={"description": "regional freight logistics carrier"},
            aliases=["Acme Freight"],
        )
        self.shared_business_neighbor(a["id"], b["id"])
        evidence = self.canonicalizer.compare(a["id"], b["id"])
        self.assertEqual("REVIEW", evidence.decision)

        with self.assertRaises(CanonicalizationError):
            self.canonicalizer.merge(
                a["id"],
                b["id"],
                created_by_agent_id=self.agent,
                match_evidence=evidence,
            )

        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
            match_evidence=evidence,
            reviewer_principal="owner",
            reviewer_kind="HUMAN",
            review_evidence={"review": "same customer after source comparison"},
        )
        self.assertEqual("ACTIVE", merged["status"])
        self.assertEqual("HUMAN", merged["reviewer_kind"])
        self.assertTrue(merged["review_evidence_hash"])

    def test_source_weighted_survivorship_records_conflicts(self):
        a = self.node(
            "customer:a",
            "Acme Legacy",
            attributes={
                "ein": "11-1111111",
                "status": "legacy",
                "phone": "111",
            },
        )
        b = self.node(
            "customer:b",
            "Acme Current",
            attributes={
                "ein": "11-1111111",
                "status": "current",
                "phone": "222",
            },
        )
        evidence = self.canonicalizer.compare(a["id"], b["id"])
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
            match_evidence=evidence,
            source_weights={a["id"]: 1.0, b["id"]: 5.0},
        )
        canonical = self.graph.get_node(merged["canonical_node_id"])
        self.assertEqual("Acme Current", canonical["label"])
        self.assertEqual("current", canonical["attributes"]["status"])
        self.assertEqual("222", canonical["attributes"]["phone"])
        conflict_fields = {item["field"] for item in merged["conflicts"]}
        self.assertTrue({"status", "phone"} <= conflict_fields)
        self.assertEqual(
            b["id"],
            merged["survivorship"]["field_winners"]["status"]["source_node_id"],
        )

    def test_merge_hides_duplicates_from_normal_resolution_but_preserves_sources(self):
        a = self.node(
            "customer:a",
            "Acme Incorporated",
            attributes={"ein": "11-1111111"},
            aliases=["Acme Parent"],
        )
        b = self.node(
            "customer:b",
            "Acme Inc",
            attributes={"ein": "11-1111111"},
        )
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        canonical_id = merged["canonical_node_id"]

        self.assertEqual("CANONICALIZED", self.graph.get_node(a["id"])["status"])
        self.assertEqual("CANONICALIZED", self.graph.get_node(b["id"])["status"])
        self.assertEqual("ACTIVE", self.graph.get_node(canonical_id)["status"])
        self.assertEqual(
            canonical_id,
            self.graph.resolve("customer:a", node_type="CUSTOMER")["id"],
        )
        self.assertEqual(
            canonical_id,
            self.graph.resolve("Acme Parent", node_type="CUSTOMER")["id"],
        )
        self.assertEqual(a["id"], merged["members"][0]["source_node_id"])
        self.assertEqual(b["id"], merged["members"][1]["source_node_id"])

    def test_new_graph_writes_must_target_canonical_entity(self):
        a = self.node("customer:a", "Acme A", attributes={"ein": "11"})
        b = self.node("customer:b", "Acme B", attributes={"ein": "11"})
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        business = self.node("business:x", "Business X", node_type="BUSINESS")

        with self.assertRaises(KnowledgeGraphError):
            self.graph.add_alias(
                a["id"],
                alias="New Duplicate Alias",
                evidence={"source": "bad"},
                created_by_agent_id=self.agent,
            )
        with self.assertRaises(KnowledgeGraphError):
            self.graph.add_edge(
                source_node_id=business["id"],
                edge_type="SERVES",
                target_node_id=a["id"],
                evidence={"source": "bad"},
                created_by_agent_id=self.agent,
            )

        edge = self.graph.add_edge(
            source_node_id=business["id"],
            edge_type="SERVES",
            target_node_id=merged["canonical_node_id"],
            evidence={"source": "good"},
            created_by_agent_id=self.agent,
        )
        self.assertEqual(merged["canonical_node_id"], edge["target_node_id"])

    def test_canonical_view_deduplicates_relationships_and_keeps_all_evidence(self):
        a = self.node("customer:a", "Acme A", attributes={"ein": "11"})
        b = self.node("customer:b", "Acme B", attributes={"ein": "11"})
        business = self.shared_business_neighbor(a["id"], b["id"])
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        view = self.canonicalizer.canonical_view(a["id"])
        matches = [
            item for item in view["neighbors"]
            if item["edge_type"] == "SERVES"
            and item["canonical_source_node_id"] == business["id"]
            and item["canonical_target_node_id"] == merged["canonical_node_id"]
        ]
        self.assertEqual(1, len(matches))
        self.assertEqual(2, len(matches[0]["evidence_edges"]))

    def test_reversal_restores_source_identity_and_aliases(self):
        a = self.node(
            "customer:a",
            "Acme A",
            attributes={"ein": "11"},
            aliases=["Acme First"],
        )
        b = self.node(
            "customer:b",
            "Acme B",
            attributes={"ein": "11"},
            aliases=["Acme Second"],
        )
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        canonical_id = merged["canonical_node_id"]
        self.assertEqual(
            canonical_id,
            self.graph.resolve("Acme First", node_type="CUSTOMER")["id"],
        )

        reversed_merge = self.canonicalizer.reverse(
            merged["id"],
            reversed_by_agent_id=self.reviewer,
            reason="later evidence showed records must remain independent",
            evidence={"case": "REV-1"},
        )
        self.assertEqual("REVERSED", reversed_merge["status"])
        self.assertEqual("ACTIVE", self.graph.get_node(a["id"])["status"])
        self.assertEqual("ACTIVE", self.graph.get_node(b["id"])["status"])
        self.assertEqual("REVERSED", self.graph.get_node(canonical_id)["status"])
        self.assertEqual(
            a["id"],
            self.graph.resolve("Acme First", node_type="CUSTOMER")["id"],
        )
        self.assertEqual(a["id"], self.canonicalizer.canonical_node_id(a["id"]))

    def test_reversal_blocks_when_canonical_entity_has_live_relationships(self):
        a = self.node("customer:a", "Acme A", attributes={"ein": "11"})
        b = self.node("customer:b", "Acme B", attributes={"ein": "11"})
        merged = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        business = self.node("business:x", "Business X", node_type="BUSINESS")
        self.graph.add_edge(
            source_node_id=business["id"],
            edge_type="SERVES",
            target_node_id=merged["canonical_node_id"],
            evidence={"source": "live"},
            created_by_agent_id=self.agent,
        )
        with self.assertRaises(CanonicalizationError):
            self.canonicalizer.reverse(
                merged["id"],
                reversed_by_agent_id=self.reviewer,
                reason="attempt reversal",
                evidence={"case": "REV-2"},
            )

    def test_transitive_canonicalization_resolves_to_latest_entity_and_leaf_sources(self):
        a = self.node("customer:a", "Acme A", attributes={"ein": "11"})
        b = self.node("customer:b", "Acme B", attributes={"ein": "11"})
        first = self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        c = self.node("customer:c", "Acme C", attributes={"ein": "11"})
        evidence = self.canonicalizer.compare(first["canonical_node_id"], c["id"])
        second = self.canonicalizer.merge(
            first["canonical_node_id"],
            c["id"],
            created_by_agent_id=self.agent,
            match_evidence=evidence,
        )
        latest = second["canonical_node_id"]

        self.assertEqual(latest, self.canonicalizer.canonical_node_id(a["id"]))
        self.assertEqual(latest, self.canonicalizer.canonical_node_id(b["id"]))
        self.assertEqual(latest, self.canonicalizer.canonical_node_id(c["id"]))
        view = self.canonicalizer.canonical_view(a["id"])
        self.assertEqual(
            {a["id"], b["id"], c["id"]},
            {node["id"] for node in view["source_nodes"]},
        )

        with self.assertRaises(CanonicalizationError):
            self.canonicalizer.reverse(
                first["id"],
                reversed_by_agent_id=self.reviewer,
                reason="wrong reversal order",
                evidence={"case": "REV-ORDER"},
            )

    def test_candidate_scan_excludes_canonicalized_sources(self):
        a = self.node("customer:a", "Acme A", attributes={"ein": "11"})
        b = self.node("customer:b", "Acme B", attributes={"ein": "11"})
        self.canonicalizer.merge(
            a["id"],
            b["id"],
            created_by_agent_id=self.agent,
        )
        c = self.node("customer:c", "Different", attributes={"ein": "22"})
        candidates = self.canonicalizer.candidates(node_type="CUSTOMER")
        compared_ids = {
            node_id
            for item in candidates
            for node_id in (item.left_id, item.right_id)
        }
        self.assertNotIn(a["id"], compared_ids)
        self.assertNotIn(b["id"], compared_ids)
        self.assertIn(c["id"], {
            row["id"]
            for row in self.runtime.conn.execute(
                "SELECT id FROM graph_nodes WHERE status='ACTIVE'"
            ).fetchall()
        })


if __name__ == "__main__":
    unittest.main()
