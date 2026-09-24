"""Typed, provenance-preserving knowledge graph for the AI Business OS.

The graph connects technical evidence to business consequences without turning associations into
authority. Nodes and edges are durable SQLite records with content-addressed provenance. Aliases
resolve identities without destructive merging, and relationship supersession preserves history.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ai_business_os.persistent_agents.runtime import AgentRuntime


NODE_TYPES = {
    "REPO",
    "DATA",
    "CAPABILITY",
    "TECHNOLOGY",
    "PRODUCT",
    "BUSINESS",
    "CUSTOMER",
    "EXPERIMENT",
    "OUTCOME",
    "MEMORY",
}

# Relationship contracts intentionally stay explicit. DEPENDS_ON and COMBINES_WITH are the two
# broad composition relations; money/result lineage uses PRODUCED and ATTRIBUTED_TO.
EDGE_CONTRACTS: Dict[str, Set[Tuple[str, str]]] = {
    "IMPLEMENTS": {
        ("REPO", "CAPABILITY"),
        ("DATA", "CAPABILITY"),
        ("TECHNOLOGY", "CAPABILITY"),
    },
    "STRENGTHENS": {
        ("REPO", "CAPABILITY"),
        ("DATA", "CAPABILITY"),
        ("TECHNOLOGY", "CAPABILITY"),
        ("EXPERIMENT", "CAPABILITY"),
        ("EXPERIMENT", "PRODUCT"),
        ("EXPERIMENT", "BUSINESS"),
    },
    "CHALLENGES": {
        ("REPO", "CAPABILITY"),
        ("DATA", "CAPABILITY"),
        ("TECHNOLOGY", "CAPABILITY"),
        ("EXPERIMENT", "CAPABILITY"),
        ("EXPERIMENT", "PRODUCT"),
        ("EXPERIMENT", "BUSINESS"),
    },
    "ENABLES": {
        ("CAPABILITY", "PRODUCT"),
        ("CAPABILITY", "BUSINESS"),
        ("TECHNOLOGY", "PRODUCT"),
        ("TECHNOLOGY", "BUSINESS"),
    },
    "USES": {
        ("PRODUCT", "CAPABILITY"),
        ("PRODUCT", "TECHNOLOGY"),
        ("PRODUCT", "DATA"),
        ("BUSINESS", "CAPABILITY"),
        ("BUSINESS", "TECHNOLOGY"),
        ("BUSINESS", "DATA"),
    },
    "OWNS": {
        ("BUSINESS", "PRODUCT"),
    },
    "SERVES": {
        ("PRODUCT", "CUSTOMER"),
        ("BUSINESS", "CUSTOMER"),
    },
    "TESTED_BY": {
        ("CAPABILITY", "EXPERIMENT"),
        ("PRODUCT", "EXPERIMENT"),
        ("BUSINESS", "EXPERIMENT"),
    },
    "PRODUCED": {
        ("EXPERIMENT", "OUTCOME"),
        ("PRODUCT", "OUTCOME"),
        ("BUSINESS", "OUTCOME"),
    },
    "ATTRIBUTED_TO": {
        ("OUTCOME", "EXPERIMENT"),
        ("OUTCOME", "PRODUCT"),
        ("OUTCOME", "BUSINESS"),
        ("OUTCOME", "CAPABILITY"),
    },
    "INFORMED_BY": {
        ("PRODUCT", "MEMORY"),
        ("BUSINESS", "MEMORY"),
        ("EXPERIMENT", "MEMORY"),
        ("OUTCOME", "MEMORY"),
    },
}

BROAD_EDGE_TYPES = {"DEPENDS_ON", "COMBINES_WITH"}


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _norm(value: str) -> str:
    return " ".join(value.casefold().strip().split())


class KnowledgeGraphError(ValueError):
    """Raised when graph truth/provenance invariants are violated."""


class KnowledgeGraph:
    """SQLite-backed typed property graph with provenance and temporal relationships."""

    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL,
                label TEXT NOT NULL,
                attributes_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                provenance_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(node_type, canonical_key)
            );

            CREATE TABLE IF NOT EXISTS graph_aliases (
                node_type TEXT NOT NULL,
                alias_norm TEXT NOT NULL,
                alias_display TEXT NOT NULL,
                node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL,
                PRIMARY KEY(node_type, alias_norm)
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                id TEXT PRIMARY KEY,
                source_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                edge_type TEXT NOT NULL,
                target_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                attributes_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                valid_from REAL NOT NULL,
                valid_to REAL,
                supersedes_edge_id TEXT REFERENCES graph_edges(id),
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_graph_nodes_type_key
                ON graph_nodes(node_type, canonical_key, status);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_source
                ON graph_edges(source_node_id, edge_type, status);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_target
                ON graph_edges(target_node_id, edge_type, status);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_validity
                ON graph_edges(status, valid_from, valid_to);
            """
        )
        self.runtime.conn.commit()

    def register_node(
        self,
        *,
        node_type: str,
        canonical_key: str,
        label: str,
        attributes: Dict[str, Any],
        provenance: Dict[str, Any],
        created_by_agent_id: str,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        node_type = node_type.strip().upper()
        canonical_key = canonical_key.strip()
        label = label.strip()
        self.runtime._require_agent(created_by_agent_id)
        if node_type not in NODE_TYPES:
            raise KnowledgeGraphError(f"unsupported node type: {node_type}")
        if not canonical_key or not label:
            raise KnowledgeGraphError("canonical_key and label must be non-empty")
        if not isinstance(attributes, dict):
            raise KnowledgeGraphError("attributes must be an object")
        self._validate_provenance(node_type, provenance)

        node_id = node_id or f"node_{uuid.uuid4().hex}"
        provenance_hash = _sha(provenance)
        ts = _now()
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO graph_nodes(
                    id, node_type, canonical_key, label, attributes_json, provenance_json,
                    provenance_hash, created_by_agent_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    node_id,
                    node_type,
                    canonical_key,
                    label,
                    _json(attributes),
                    _json(provenance),
                    provenance_hash,
                    created_by_agent_id,
                    ts,
                    ts,
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise KnowledgeGraphError(
                f"node identity already exists: {node_type}:{canonical_key}"
            ) from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "KNOWLEDGE_GRAPH_NODE_REGISTERED",
            {
                "node_id": node_id,
                "node_type": node_type,
                "canonical_key": canonical_key,
                "provenance_hash": provenance_hash,
            },
        )
        return self.get_node(node_id)

    def add_alias(
        self,
        node_id: str,
        *,
        alias: str,
        evidence: Dict[str, Any],
        created_by_agent_id: str,
    ) -> Dict[str, Any]:
        node = self._require_node(node_id)
        self.runtime._require_agent(created_by_agent_id)
        if node["status"] != "ACTIVE":
            raise KnowledgeGraphError("new aliases may only target ACTIVE nodes")
        alias_display = alias.strip()
        alias_norm = _norm(alias)
        if not alias_norm:
            raise KnowledgeGraphError("alias must be non-empty")
        if not isinstance(evidence, dict) or not evidence:
            raise KnowledgeGraphError("alias requires evidence")

        # An alias cannot shadow another canonical identity of the same type.
        canonical_collision = self.runtime.conn.execute(
            """
            SELECT id FROM graph_nodes
            WHERE node_type = ? AND lower(canonical_key) = lower(?) AND status = 'ACTIVE'
            """,
            (node["node_type"], alias_display),
        ).fetchone()
        if canonical_collision is not None and canonical_collision["id"] != node_id:
            raise KnowledgeGraphError("alias collides with another canonical node")

        evidence_hash = _sha(evidence)
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO graph_aliases(
                    node_type, alias_norm, alias_display, node_id, evidence_json,
                    evidence_hash, created_by_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node["node_type"],
                    alias_norm,
                    alias_display,
                    node_id,
                    _json(evidence),
                    evidence_hash,
                    created_by_agent_id,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise KnowledgeGraphError(
                "alias is already bound within this node type"
            ) from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "KNOWLEDGE_GRAPH_ALIAS_ADDED",
            {
                "node_id": node_id,
                "node_type": node["node_type"],
                "alias": alias_display,
                "evidence_hash": evidence_hash,
            },
        )
        return self.resolve(alias_display, node_type=node["node_type"])

    def resolve(self, identity: str, *, node_type: Optional[str] = None) -> Dict[str, Any]:
        identity = identity.strip()
        if not identity:
            raise KnowledgeGraphError("identity must be non-empty")
        normalized_type = node_type.strip().upper() if node_type else None
        if normalized_type and normalized_type not in NODE_TYPES:
            raise KnowledgeGraphError(f"unsupported node type: {normalized_type}")

        params: List[Any] = [identity]
        type_clause = ""
        if normalized_type:
            type_clause = " AND node_type = ?"
            params.append(normalized_type)
        canonical = self.runtime.conn.execute(
            f"""
            SELECT * FROM graph_nodes
            WHERE lower(canonical_key) = lower(?) AND status = 'ACTIVE'{type_clause}
            """,
            params,
        ).fetchall()
        alias_params: List[Any] = [_norm(identity)]
        alias_type_clause = ""
        if normalized_type:
            alias_type_clause = " AND a.node_type = ?"
            alias_params.append(normalized_type)
        aliases = self.runtime.conn.execute(
            f"""
            SELECT n.* FROM graph_aliases a
            JOIN graph_nodes n ON n.id = a.node_id
            WHERE a.alias_norm = ? AND n.status = 'ACTIVE'{alias_type_clause}
            """,
            alias_params,
        ).fetchall()

        by_id = {row["id"]: row for row in [*canonical, *aliases]}
        if not by_id:
            raise KeyError(f"unresolved graph identity: {identity}")
        if len(by_id) > 1:
            raise KnowledgeGraphError(
                "identity is ambiguous across node types; provide node_type"
            )
        return self.get_node(next(iter(by_id)))

    def add_edge(
        self,
        *,
        source_node_id: str,
        edge_type: str,
        target_node_id: str,
        evidence: Dict[str, Any],
        created_by_agent_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        valid_from: Optional[float] = None,
        supersedes_edge_id: Optional[str] = None,
        edge_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        source = self._require_node(source_node_id)
        target = self._require_node(target_node_id)
        self.runtime._require_agent(created_by_agent_id)
        if (
            (source["status"] != "ACTIVE" or target["status"] != "ACTIVE")
            and supersedes_edge_id is None
        ):
            raise KnowledgeGraphError(
                "new edges may only connect ACTIVE nodes; historical edges may only be superseded"
            )
        edge_type = edge_type.strip().upper()
        if source_node_id == target_node_id:
            raise KnowledgeGraphError("self edges are not allowed")
        self._validate_edge_contract(source["node_type"], edge_type, target["node_type"])
        if not isinstance(evidence, dict) or not evidence:
            raise KnowledgeGraphError("edge requires non-empty evidence")
        attributes = attributes or {}
        if not isinstance(attributes, dict):
            raise KnowledgeGraphError("edge attributes must be an object")
        valid_from = _now() if valid_from is None else float(valid_from)
        if not isinstance(valid_from, float) or valid_from != valid_from:
            raise KnowledgeGraphError("valid_from must be finite")
        if supersedes_edge_id is not None:
            old = self._require_edge(supersedes_edge_id)
            if old["status"] != "ACTIVE":
                raise KnowledgeGraphError("only an ACTIVE edge may be superseded")
            if (
                old["source_node_id"] != source_node_id
                or old["edge_type"] != edge_type
                or old["target_node_id"] != target_node_id
            ):
                raise KnowledgeGraphError(
                    "superseding edge must preserve source/type/target identity"
                )

        duplicate = self.runtime.conn.execute(
            """
            SELECT id FROM graph_edges
            WHERE source_node_id = ? AND edge_type = ? AND target_node_id = ?
              AND status = 'ACTIVE'
            """,
            (source_node_id, edge_type, target_node_id),
        ).fetchone()
        if duplicate is not None and supersedes_edge_id != duplicate["id"]:
            raise KnowledgeGraphError(
                "an ACTIVE edge with the same source/type/target already exists"
            )

        evidence_hash = _sha(evidence)
        edge_id = edge_id or f"edge_{uuid.uuid4().hex}"
        ts = _now()
        if supersedes_edge_id is not None:
            self.runtime.conn.execute(
                """
                UPDATE graph_edges
                SET status = 'SUPERSEDED', valid_to = ?
                WHERE id = ?
                """,
                (valid_from, supersedes_edge_id),
            )
        self.runtime.conn.execute(
            """
            INSERT INTO graph_edges(
                id, source_node_id, edge_type, target_node_id, attributes_json,
                evidence_json, evidence_hash, created_by_agent_id, status,
                valid_from, valid_to, supersedes_edge_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, NULL, ?, ?)
            """,
            (
                edge_id,
                source_node_id,
                edge_type,
                target_node_id,
                _json(attributes),
                _json(evidence),
                evidence_hash,
                created_by_agent_id,
                valid_from,
                supersedes_edge_id,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "KNOWLEDGE_GRAPH_EDGE_ADDED",
            {
                "edge_id": edge_id,
                "source_node_id": source_node_id,
                "edge_type": edge_type,
                "target_node_id": target_node_id,
                "evidence_hash": evidence_hash,
                "supersedes_edge_id": supersedes_edge_id,
            },
        )
        return self.get_edge(edge_id)

    def supersede_edge(
        self,
        edge_id: str,
        *,
        evidence: Dict[str, Any],
        created_by_agent_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        valid_from: Optional[float] = None,
    ) -> Dict[str, Any]:
        old = self._require_edge(edge_id)
        return self.add_edge(
            source_node_id=old["source_node_id"],
            edge_type=old["edge_type"],
            target_node_id=old["target_node_id"],
            evidence=evidence,
            created_by_agent_id=created_by_agent_id,
            attributes=attributes if attributes is not None else json.loads(old["attributes_json"]),
            valid_from=valid_from,
            supersedes_edge_id=edge_id,
        )

    def neighbors(
        self,
        node_id: str,
        *,
        direction: str = "out",
        edge_types: Optional[Iterable[str]] = None,
        as_of: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        self._require_node(node_id)
        direction = direction.lower().strip()
        if direction not in {"out", "in", "both"}:
            raise KnowledgeGraphError("direction must be out, in, or both")
        allowed = {edge.strip().upper() for edge in edge_types} if edge_types else None
        as_of = _now() if as_of is None else float(as_of)

        rows = self.runtime.conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)
              AND (source_node_id = ? OR target_node_id = ?)
            ORDER BY created_at, id
            """,
            (as_of, as_of, node_id, node_id),
        ).fetchall()
        result = []
        for row in rows:
            if allowed and row["edge_type"] not in allowed:
                continue
            if direction == "out" and row["source_node_id"] != node_id:
                continue
            if direction == "in" and row["target_node_id"] != node_id:
                continue
            result.append(self.get_edge(str(row["id"])))
        return result

    def find_paths(
        self,
        start_node_id: str,
        end_node_id: str,
        *,
        max_depth: int = 5,
        edge_types: Optional[Iterable[str]] = None,
        as_of: Optional[float] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return directed evidence-bearing paths from start to end."""
        self._require_node(start_node_id)
        self._require_node(end_node_id)
        if max_depth <= 0 or max_depth > 8:
            raise KnowledgeGraphError("max_depth must be between 1 and 8")
        if limit <= 0:
            raise KnowledgeGraphError("limit must be positive")
        allowed = {edge.strip().upper() for edge in edge_types} if edge_types else None
        as_of = _now() if as_of is None else float(as_of)

        queue = deque([(start_node_id, [start_node_id], [])])
        paths: List[Dict[str, Any]] = []
        while queue and len(paths) < limit:
            current, node_path, edge_path = queue.popleft()
            if len(edge_path) >= max_depth:
                continue
            for edge in self.neighbors(
                current,
                direction="out",
                edge_types=allowed,
                as_of=as_of,
            ):
                nxt = edge["target_node_id"]
                if nxt in node_path:
                    continue
                next_nodes = [*node_path, nxt]
                next_edges = [*edge_path, edge["id"]]
                if nxt == end_node_id:
                    paths.append(self._materialize_path(next_nodes, next_edges))
                    if len(paths) >= limit:
                        break
                else:
                    queue.append((nxt, next_nodes, next_edges))
        return paths

    def outcome_lineage(
        self,
        outcome_node_id: str,
        *,
        max_depth: int = 6,
        as_of: Optional[float] = None,
    ) -> Dict[str, Any]:
        outcome = self._require_node(outcome_node_id)
        if outcome["node_type"] != "OUTCOME":
            raise KnowledgeGraphError("outcome_lineage requires an OUTCOME node")
        as_of = _now() if as_of is None else float(as_of)

        visited = {outcome_node_id}
        queue = deque([(outcome_node_id, 0)])
        nodes = {outcome_node_id: self.get_node(outcome_node_id)}
        edges: Dict[str, Dict[str, Any]] = {}
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.neighbors(current, direction="in", as_of=as_of):
                source_id = edge["source_node_id"]
                edges[edge["id"]] = edge
                nodes[source_id] = self.get_node(source_id)
                if source_id not in visited:
                    visited.add(source_id)
                    queue.append((source_id, depth + 1))
            # ATTRIBUTED_TO edges point out of outcomes and are part of attribution lineage.
            if current == outcome_node_id:
                for edge in self.neighbors(
                    current,
                    direction="out",
                    edge_types={"ATTRIBUTED_TO"},
                    as_of=as_of,
                ):
                    target_id = edge["target_node_id"]
                    edges[edge["id"]] = edge
                    nodes[target_id] = self.get_node(target_id)
        return {
            "outcome": self.get_node(outcome_node_id),
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "provenance_hash": _sha(
                {
                    "outcome_node_id": outcome_node_id,
                    "node_provenance": sorted(
                        node["provenance_hash"] for node in nodes.values()
                    ),
                    "edge_evidence": sorted(
                        edge["evidence_hash"] for edge in edges.values()
                    ),
                }
            ),
        }

    def retire_node(
        self,
        node_id: str,
        *,
        created_by_agent_id: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        node = self._require_node(node_id)
        self.runtime._require_agent(created_by_agent_id)
        if node["status"] != "ACTIVE":
            raise KnowledgeGraphError("node is already retired")
        if not reason.strip() or not evidence:
            raise KnowledgeGraphError("retirement requires reason and evidence")
        active_edges = self.runtime.conn.execute(
            """
            SELECT COUNT(*) AS n FROM graph_edges
            WHERE status = 'ACTIVE'
              AND (source_node_id = ? OR target_node_id = ?)
            """,
            (node_id, node_id),
        ).fetchone()
        if int(active_edges["n"]) > 0:
            raise KnowledgeGraphError(
                "node with active relationships cannot be retired; supersede/close edges first"
            )
        evidence_hash = _sha({"node_id": node_id, "reason": reason, "evidence": evidence})
        self.runtime.conn.execute(
            "UPDATE graph_nodes SET status = 'RETIRED', updated_at = ? WHERE id = ?",
            (_now(), node_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "KNOWLEDGE_GRAPH_NODE_RETIRED",
            {
                "node_id": node_id,
                "reason": reason,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_node(node_id)

    def get_node(self, node_id: str) -> Dict[str, Any]:
        row = self._require_node(node_id)
        return {
            "id": row["id"],
            "node_type": row["node_type"],
            "canonical_key": row["canonical_key"],
            "label": row["label"],
            "attributes": json.loads(row["attributes_json"]),
            "provenance": json.loads(row["provenance_json"]),
            "provenance_hash": row["provenance_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_edge(self, edge_id: str) -> Dict[str, Any]:
        row = self._require_edge(edge_id)
        return {
            "id": row["id"],
            "source_node_id": row["source_node_id"],
            "edge_type": row["edge_type"],
            "target_node_id": row["target_node_id"],
            "attributes": json.loads(row["attributes_json"]),
            "evidence": json.loads(row["evidence_json"]),
            "evidence_hash": row["evidence_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "status": row["status"],
            "valid_from": row["valid_from"],
            "valid_to": row["valid_to"],
            "supersedes_edge_id": row["supersedes_edge_id"],
            "created_at": row["created_at"],
        }

    def _materialize_path(
        self, node_ids: Sequence[str], edge_ids: Sequence[str]
    ) -> Dict[str, Any]:
        nodes = [self.get_node(node_id) for node_id in node_ids]
        edges = [self.get_edge(edge_id) for edge_id in edge_ids]
        return {
            "node_ids": list(node_ids),
            "edge_ids": list(edge_ids),
            "nodes": nodes,
            "edges": edges,
            "evidence_chain_hash": _sha(
                {
                    "nodes": [node["provenance_hash"] for node in nodes],
                    "edges": [edge["evidence_hash"] for edge in edges],
                }
            ),
        }

    def _validate_provenance(self, node_type: str, provenance: Dict[str, Any]) -> None:
        if not isinstance(provenance, dict) or not provenance:
            raise KnowledgeGraphError("node requires non-empty provenance")
        refs = provenance.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            raise KnowledgeGraphError("provenance requires at least one evidence_ref")
        if node_type == "OUTCOME":
            if provenance.get("verified") is not True:
                raise KnowledgeGraphError(
                    "OUTCOME nodes require provenance.verified == true"
                )
            if not str(provenance.get("event_id", "")).strip():
                raise KnowledgeGraphError(
                    "OUTCOME nodes require a stable provenance.event_id"
                )

    def _validate_edge_contract(
        self, source_type: str, edge_type: str, target_type: str
    ) -> None:
        if edge_type in BROAD_EDGE_TYPES:
            return
        allowed = EDGE_CONTRACTS.get(edge_type)
        if allowed is None:
            raise KnowledgeGraphError(f"unsupported edge type: {edge_type}")
        if (source_type, target_type) not in allowed:
            raise KnowledgeGraphError(
                f"invalid relationship contract: {source_type} -{edge_type}-> {target_type}"
            )

    def _require_node(self, node_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM graph_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown graph node: {node_id}")
        return row

    def _require_edge(self, edge_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM graph_edges WHERE id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown graph edge: {edge_id}")
        return row
