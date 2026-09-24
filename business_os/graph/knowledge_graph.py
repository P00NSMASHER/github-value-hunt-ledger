"""Provenance-preserving business knowledge graph for AI Business OS.

The graph connects repositories, capabilities, products, customers,
experiments and outcomes. Nodes and edges retain source references and hashes
so relationship claims remain auditable rather than becoming opaque memory.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any


ALLOWED_NODE_TYPES = {
    "REPO",
    "CAPABILITY",
    "TECHNOLOGY",
    "BUSINESS",
    "PRODUCT",
    "CUSTOMER",
    "PROSPECT",
    "OPPORTUNITY",
    "EXPERIMENT",
    "OUTCOME",
    "TOOL",
    "DOCUMENT",
    "DECISION",
    "METRIC",
}


@dataclasses.dataclass(frozen=True)
class Node:
    id: str
    type: str
    name: str
    properties: dict[str, Any]
    source_ref: str
    source_sha256: str
    created_at: float
    updated_at: float


@dataclasses.dataclass(frozen=True)
class Edge:
    id: str
    src: str
    relation: str
    dst: str
    properties: dict[str, Any]
    source_ref: str
    source_sha256: str
    created_at: float


class KnowledgeGraph:
    def __init__(self, db_path: str | Path = "ai_business_os.sqlite3") -> None:
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _initialize(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_node_versions (
                    version_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                    properties_json TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    observed_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    id TEXT PRIMARY KEY,
                    src TEXT NOT NULL REFERENCES graph_nodes(id),
                    relation TEXT NOT NULL,
                    dst TEXT NOT NULL REFERENCES graph_nodes(id),
                    properties_json TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(src, relation, dst, source_sha256)
                );

                CREATE INDEX IF NOT EXISTS idx_graph_nodes_type
                    ON graph_nodes(type, name);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_src
                    ON graph_edges(src, relation);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_dst
                    ON graph_edges(dst, relation);
                """
            )

    def add_node(
        self,
        node_type: str,
        name: str,
        *,
        properties: dict[str, Any] | None = None,
        source_ref: str,
        source_sha256: str,
        node_id: str | None = None,
        now: float | None = None,
    ) -> Node:
        if node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(f"unsupported node type: {node_type}")
        if not name.strip():
            raise ValueError("node name cannot be empty")
        _check_digest(source_sha256)
        ts = time.time() if now is None else float(now)
        node_id = node_id or f"{node_type.lower()}_{uuid.uuid4().hex}"
        props = properties or {}

        with self._connect() as con:
            existing = con.execute(
                "SELECT * FROM graph_nodes WHERE id=?", (node_id,)
            ).fetchone()
            if existing is None:
                con.execute(
                    """
                    INSERT INTO graph_nodes(
                        id, type, name, properties_json, source_ref,
                        source_sha256, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node_id,
                        node_type,
                        name.strip(),
                        _canonical(props),
                        source_ref,
                        source_sha256,
                        ts,
                        ts,
                    ),
                )
            else:
                if existing["type"] != node_type:
                    raise ValueError("node type is immutable")
                con.execute(
                    """
                    UPDATE graph_nodes
                    SET name=?, properties_json=?, source_ref=?,
                        source_sha256=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        name.strip(),
                        _canonical(props),
                        source_ref,
                        source_sha256,
                        ts,
                        node_id,
                    ),
                )

            version_payload = {
                "node_id": node_id,
                "name": name.strip(),
                "properties": props,
                "source_ref": source_ref,
                "source_sha256": source_sha256,
                "observed_at": ts,
            }
            version_id = "nodever_" + _sha(version_payload)
            con.execute(
                """
                INSERT OR IGNORE INTO graph_node_versions(
                    version_id, node_id, properties_json, source_ref,
                    source_sha256, observed_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    node_id,
                    _canonical({"name": name.strip(), **props}),
                    source_ref,
                    source_sha256,
                    ts,
                ),
            )

        return self.get_node(node_id)

    def add_edge(
        self,
        src: str,
        relation: str,
        dst: str,
        *,
        properties: dict[str, Any] | None = None,
        source_ref: str,
        source_sha256: str,
        edge_id: str | None = None,
        now: float | None = None,
    ) -> Edge:
        if not relation.strip():
            raise ValueError("relation cannot be empty")
        _check_digest(source_sha256)
        ts = time.time() if now is None else float(now)
        props = properties or {}

        with self._connect() as con:
            for node_id in (src, dst):
                if (
                    con.execute(
                        "SELECT 1 FROM graph_nodes WHERE id=?", (node_id,)
                    ).fetchone()
                    is None
                ):
                    raise KeyError(f"unknown graph node: {node_id}")

            if edge_id is None:
                identity = {
                    "src": src,
                    "relation": relation,
                    "dst": dst,
                    "source_sha256": source_sha256,
                }
                edge_id = "edge_" + _sha(identity)

            con.execute(
                """
                INSERT OR IGNORE INTO graph_edges(
                    id, src, relation, dst, properties_json,
                    source_ref, source_sha256, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge_id,
                    src,
                    relation.strip(),
                    dst,
                    _canonical(props),
                    source_ref,
                    source_sha256,
                    ts,
                ),
            )
        return self.get_edge(edge_id)

    def get_node(self, node_id: str) -> Node:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM graph_nodes WHERE id=?", (node_id,)
            ).fetchone()
        if row is None:
            raise KeyError(node_id)
        return _node(row)

    def get_edge(self, edge_id: str) -> Edge:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM graph_edges WHERE id=?", (edge_id,)
            ).fetchone()
        if row is None:
            raise KeyError(edge_id)
        return _edge(row)

    def neighbors(
        self,
        node_id: str,
        *,
        relation: str | None = None,
        direction: str = "out",
    ) -> list[tuple[Edge, Node]]:
        if direction not in {"out", "in", "both"}:
            raise ValueError("direction must be out, in or both")
        self.get_node(node_id)

        clauses = []
        params: list[Any] = []
        if direction in {"out", "both"}:
            clauses.append("src=?")
            params.append(node_id)
        if direction in {"in", "both"}:
            clauses.append("dst=?")
            params.append(node_id)

        sql = "SELECT * FROM graph_edges WHERE (" + " OR ".join(clauses) + ")"
        if relation is not None:
            sql += " AND relation=?"
            params.append(relation)

        result: list[tuple[Edge, Node]] = []
        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()
            for row in rows:
                edge = _edge(row)
                other_id = edge.dst if edge.src == node_id else edge.src
                nrow = con.execute(
                    "SELECT * FROM graph_nodes WHERE id=?", (other_id,)
                ).fetchone()
                result.append((edge, _node(nrow)))
        return result

    def shortest_path(
        self,
        src: str,
        dst: str,
        *,
        max_depth: int = 8,
    ) -> list[str] | None:
        if max_depth < 1:
            return None
        self.get_node(src)
        self.get_node(dst)
        if src == dst:
            return [src]

        queue = deque([(src, [src])])
        visited = {src}
        while queue:
            current, path = queue.popleft()
            if len(path) - 1 >= max_depth:
                continue
            for _, neighbor in self.neighbors(current, direction="out"):
                if neighbor.id in visited:
                    continue
                next_path = path + [neighbor.id]
                if neighbor.id == dst:
                    return next_path
                visited.add(neighbor.id)
                queue.append((neighbor.id, next_path))
        return None

    def find_nodes(
        self,
        *,
        node_type: str | None = None,
        name_contains: str | None = None,
    ) -> list[Node]:
        sql = "SELECT * FROM graph_nodes WHERE 1=1"
        params: list[Any] = []
        if node_type is not None:
            sql += " AND type=?"
            params.append(node_type)
        if name_contains is not None:
            sql += " AND lower(name) LIKE ?"
            params.append(f"%{name_contains.lower()}%")
        sql += " ORDER BY type, name, id"

        with self._connect() as con:
            return [_node(row) for row in con.execute(sql, params).fetchall()]

    def export(self) -> dict[str, Any]:
        with self._connect() as con:
            nodes = [
                dataclasses.asdict(_node(row))
                for row in con.execute(
                    "SELECT * FROM graph_nodes ORDER BY type, name, id"
                )
            ]
            edges = [
                dataclasses.asdict(_edge(row))
                for row in con.execute(
                    "SELECT * FROM graph_edges ORDER BY src, relation, dst, id"
                )
            ]
        return {"nodes": nodes, "edges": edges}


def _node(row: sqlite3.Row) -> Node:
    return Node(
        id=row["id"],
        type=row["type"],
        name=row["name"],
        properties=json.loads(row["properties_json"]),
        source_ref=row["source_ref"],
        source_sha256=row["source_sha256"],
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
    )


def _edge(row: sqlite3.Row) -> Edge:
    return Edge(
        id=row["id"],
        src=row["src"],
        relation=row["relation"],
        dst=row["dst"],
        properties=json.loads(row["properties_json"]),
        source_ref=row["source_ref"],
        source_sha256=row["source_sha256"],
        created_at=float(row["created_at"]),
    )


def _check_digest(value: str) -> None:
    if len(value) != 64:
        raise ValueError("source_sha256 must be a 64-character digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("source_sha256 must be hexadecimal") from exc


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
