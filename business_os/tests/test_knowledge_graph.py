import hashlib
import tempfile
import unittest
from pathlib import Path

from business_os.graph.knowledge_graph import KnowledgeGraph


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "graph.sqlite3"
        self.g = KnowledgeGraph(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def add_chain(self):
        self.g.add_node(
            "REPO",
            "RecoveryOS",
            node_id="repo",
            source_ref="github/recoveryos",
            source_sha256=digest("repo"),
        )
        self.g.add_node(
            "CAPABILITY",
            "Freight recovery",
            node_id="cap",
            source_ref="hunter/CAPABILITIES.md",
            source_sha256=digest("cap"),
        )
        self.g.add_node(
            "PRODUCT",
            "Freight Recovery",
            node_id="product",
            source_ref="business/product",
            source_sha256=digest("product"),
        )
        self.g.add_node(
            "OUTCOME",
            "Recovered customer funds",
            node_id="outcome",
            source_ref="business/outcome",
            source_sha256=digest("outcome"),
        )
        self.g.add_edge(
            "repo",
            "IMPLEMENTS",
            "cap",
            source_ref="evidence/1",
            source_sha256=digest("edge1"),
        )
        self.g.add_edge(
            "cap",
            "ENABLES",
            "product",
            source_ref="evidence/2",
            source_sha256=digest("edge2"),
        )
        self.g.add_edge(
            "product",
            "PRODUCES",
            "outcome",
            source_ref="evidence/3",
            source_sha256=digest("edge3"),
        )

    def test_builds_repo_to_outcome_path(self):
        self.add_chain()
        self.assertEqual(
            ["repo", "cap", "product", "outcome"],
            self.g.shortest_path("repo", "outcome"),
        )

    def test_edges_require_existing_nodes(self):
        self.g.add_node(
            "REPO",
            "A",
            node_id="a",
            source_ref="x",
            source_sha256=digest("a"),
        )
        with self.assertRaises(KeyError):
            self.g.add_edge(
                "a",
                "REL",
                "missing",
                source_ref="x",
                source_sha256=digest("edge"),
            )

    def test_node_type_is_immutable(self):
        self.g.add_node(
            "REPO",
            "A",
            node_id="same",
            source_ref="x",
            source_sha256=digest("a"),
        )
        with self.assertRaises(ValueError):
            self.g.add_node(
                "PRODUCT",
                "A",
                node_id="same",
                source_ref="y",
                source_sha256=digest("b"),
            )

    def test_neighbor_query_preserves_provenance(self):
        self.add_chain()
        rows = self.g.neighbors("repo", relation="IMPLEMENTS")
        self.assertEqual(1, len(rows))
        edge, node = rows[0]
        self.assertEqual("cap", node.id)
        self.assertEqual("evidence/1", edge.source_ref)
        self.assertEqual(digest("edge1"), edge.source_sha256)

    def test_cycle_safe_shortest_path(self):
        self.add_chain()
        self.g.add_edge(
            "outcome",
            "INFORMS",
            "repo",
            source_ref="cycle",
            source_sha256=digest("cycle"),
        )
        self.assertEqual(
            ["repo", "cap", "product", "outcome"],
            self.g.shortest_path("repo", "outcome"),
        )

    def test_find_nodes_by_type_and_name(self):
        self.add_chain()
        self.g.add_node(
            "PRODUCT",
            "CaptureBrief",
            node_id="capture",
            source_ref="product",
            source_sha256=digest("capture"),
        )
        products = self.g.find_nodes(node_type="PRODUCT")
        self.assertEqual({"product", "capture"}, {x.id for x in products})
        capture = self.g.find_nodes(name_contains="capture")
        self.assertEqual(["capture"], [x.id for x in capture])

    def test_export_is_machine_readable_and_complete(self):
        self.add_chain()
        exported = self.g.export()
        self.assertEqual(4, len(exported["nodes"]))
        self.assertEqual(3, len(exported["edges"]))
        self.assertTrue(all("source_sha256" in x for x in exported["edges"]))

    def test_updates_preserve_new_node_version(self):
        self.g.add_node(
            "PRODUCT",
            "X",
            node_id="x",
            properties={"price": 100},
            source_ref="v1",
            source_sha256=digest("v1"),
            now=100,
        )
        updated = self.g.add_node(
            "PRODUCT",
            "X",
            node_id="x",
            properties={"price": 120},
            source_ref="v2",
            source_sha256=digest("v2"),
            now=200,
        )
        self.assertEqual(120, updated.properties["price"])
        with self.g._connect() as con:
            count = con.execute(
                "SELECT COUNT(*) FROM graph_node_versions WHERE node_id='x'"
            ).fetchone()[0]
        self.assertEqual(2, count)


if __name__ == "__main__":
    unittest.main()
