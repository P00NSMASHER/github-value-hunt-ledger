import hashlib
import tempfile
import unittest
from pathlib import Path

from business_os.graph.canonicalize import EntityCanonicalizer
from business_os.graph.knowledge_graph import KnowledgeGraph


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class EntityCanonicalizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "graph.sqlite3"
        self.g = KnowledgeGraph(self.db)
        self.c = EntityCanonicalizer(
            self.g,
            auto_merge_threshold=0.70,
            review_threshold=0.45,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def add_company(self, node_id, name, aliases=None, description=""):
        return self.g.add_node(
            "CUSTOMER",
            name,
            node_id=node_id,
            properties={"aliases": aliases or [], "description": description},
            source_ref=f"source/{node_id}",
            source_sha256=digest(node_id),
        )

    def test_type_mismatch_never_merges(self):
        a = self.add_company("a", "FedEx")
        b = self.g.add_node(
            "PRODUCT",
            "FedEx",
            node_id="b",
            source_ref="b",
            source_sha256=digest("b"),
        )
        ev = self.c.compare(a, b)
        self.assertEqual("KEEP_SEPARATE", ev.decision)
        self.assertEqual(0.0, ev.score)

    def test_normalization_and_aliases_detect_duplicate(self):
        a = self.add_company(
            "a",
            "Federal Express Corporation",
            aliases=["FedEx"],
            description="parcel logistics carrier",
        )
        b = self.add_company(
            "b",
            "Federal Express Corp",
            aliases=["FedEx", "Federal Express"],
            description="parcel logistics carrier",
        )
        ev = self.c.compare(a, b)
        self.assertTrue(ev.normalized_name_equal)
        self.assertGreaterEqual(ev.score, 0.70)
        self.assertEqual("AUTO_MERGE", ev.decision)

    def test_shared_neighbors_add_positive_identity_evidence(self):
        account = self.g.add_node(
            "BUSINESS",
            "Freight Recovery",
            node_id="business",
            source_ref="business",
            source_sha256=digest("business"),
        )
        a = self.add_company("a", "Acme Shipping", aliases=["Acme Logistics"])
        b = self.add_company("b", "Acme Logistics", aliases=["Acme Shipping"])
        for node_id, label in [("a", "ea"), ("b", "eb")]:
            self.g.add_edge(
                node_id,
                "CUSTOMER_OF",
                account.id,
                source_ref=label,
                source_sha256=digest(label),
            )
        ev = self.c.compare(a, b)
        self.assertGreater(ev.neighbor_overlap, 0)

    def test_absent_neighbors_are_not_negative_evidence(self):
        a = self.add_company("a", "Acme Logistics", aliases=["Acme Shipping"])
        b = self.add_company("b", "Acme Shipping", aliases=["Acme Logistics"])
        ev = self.c.compare(a, b)
        self.assertEqual(0.0, ev.neighbor_overlap)
        self.assertGreater(ev.score, 0)

    def test_review_pair_requires_explicit_approval(self):
        account = self.g.add_node(
            "BUSINESS",
            "Freight Recovery",
            node_id="review-business",
            source_ref="review-business",
            source_sha256=digest("review-business"),
        )
        a = self.add_company(
            "a",
            "Acme Freight",
            aliases=["Acme", "Acme Logistics"],
            description="regional freight logistics carrier",
        )
        b = self.add_company(
            "b",
            "Acme Logistics",
            aliases=["Acme", "Acme Freight"],
            description="regional freight logistics carrier",
        )
        for node_id, label in [("a", "review-a"), ("b", "review-b")]:
            self.g.add_edge(
                node_id,
                "CUSTOMER_OF",
                account.id,
                source_ref=label,
                source_sha256=digest(label),
            )

        ev = self.c.compare(a, b)
        self.assertEqual("REVIEW", ev.decision)
        self.assertGreater(ev.neighbor_overlap, 0)
        with self.assertRaises(PermissionError):
            self.c.merge(a, b, evidence=ev)

        canonical = self.c.merge(a, b, evidence=ev, reviewer_approved=True)
        self.assertIn("a", canonical.properties["_merged_from"])
        self.assertIn("b", canonical.properties["_merged_from"])

    def test_merge_preserves_source_nodes_and_explicit_edges(self):
        a = self.add_company(
            "a", "Federal Express Corporation", aliases=["FedEx"]
        )
        b = self.add_company(
            "b", "Federal Express Corp", aliases=["FedEx"]
        )
        ev = self.c.compare(a, b)
        canonical = self.c.merge(a, b, evidence=ev)
        self.assertEqual("a", self.g.get_node("a").id)
        self.assertEqual("b", self.g.get_node("b").id)

        incoming = self.g.neighbors(canonical.id, relation="MERGED_INTO", direction="in")
        self.assertEqual({"a", "b"}, {node.id for _, node in incoming})
        self.assertEqual(ev.sha256, canonical.properties["_merge_evidence_sha256"])

    def test_unrelated_entities_stay_separate(self):
        a = self.add_company("a", "FedEx")
        b = self.add_company("b", "United Parcel Service")
        ev = self.c.compare(a, b)
        self.assertEqual("KEEP_SEPARATE", ev.decision)
        with self.assertRaises(ValueError):
            self.c.merge(a, b, evidence=ev)

    def test_candidate_scan_only_returns_review_or_better(self):
        self.add_company("a", "Federal Express Corporation", aliases=["FedEx"])
        self.add_company("b", "Federal Express Corp", aliases=["FedEx"])
        self.add_company("c", "Totally Different Company")
        rows = self.c.candidates(node_type="CUSTOMER")
        self.assertEqual(1, len(rows))
        self.assertEqual({"a", "b"}, {rows[0].left_id, rows[0].right_id})


if __name__ == "__main__":
    unittest.main()
