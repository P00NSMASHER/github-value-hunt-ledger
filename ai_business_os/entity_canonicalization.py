"""Reversible, provenance-preserving entity canonicalization for the AI Business OS.

The canonicalizer resolves duplicate identity records without deleting source nodes. Strong matches
can merge automatically; ambiguous matches fail into REVIEW until a human approves them. Hard
identifier conflicts always keep records separate. Canonical field values use explicit source
weights, while disagreements and losing values remain recorded in the canonicalization ledger.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import time
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from ai_business_os.knowledge_graph import KnowledgeGraph, KnowledgeGraphError
from ai_business_os.persistent_agents.runtime import AgentRuntime


IDENTITY_NODE_TYPES = {
    "REPO",
    "DATA",
    "TECHNOLOGY",
    "PRODUCT",
    "BUSINESS",
    "CUSTOMER",
}

CORPORATE_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company",
    "llc", "ltd", "limited", "plc", "lp", "llp",
}

HARD_IDENTIFIER_FIELDS = {
    "ein",
    "tax_id",
    "duns",
    "sam_uei",
    "github_repo_id",
    "repository_id",
    "stripe_customer_id",
}


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _alias_key(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _normalize_name(value: str) -> str:
    return " ".join(
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in CORPORATE_SUFFIXES
    )


def _tokens(value: str) -> Set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1
    }


def _jaccard(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


class CanonicalizationError(ValueError):
    """Raised when entity-resolution invariants are violated."""


@dataclasses.dataclass(frozen=True)
class MatchEvidence:
    left_id: str
    right_id: str
    left_provenance_hash: str
    right_provenance_hash: str
    node_type: str
    normalized_name_equal: bool
    alias_overlap: float
    description_overlap: float
    neighbor_overlap: float
    hard_identifier_matches: Tuple[str, ...]
    hard_identifier_conflicts: Tuple[str, ...]
    score: float
    decision: str
    reasons: Tuple[str, ...]

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


class EntityCanonicalizer:
    """Deterministic entity resolver with reversible canonical decisions."""

    VERSION = "ai-business-os-entity-canonicalizer-v1"

    def __init__(
        self,
        runtime: AgentRuntime,
        graph: KnowledgeGraph,
        *,
        auto_merge_threshold: float = 0.80,
        review_threshold: float = 0.55,
    ):
        if graph.runtime is not runtime:
            raise CanonicalizationError(
                "canonicalizer and knowledge graph must share the exact AgentRuntime"
            )
        if not 0 <= review_threshold <= auto_merge_threshold <= 1:
            raise CanonicalizationError(
                "thresholds must satisfy 0 <= review <= auto <= 1"
            )
        self.runtime = runtime
        self.graph = graph
        self.auto_merge_threshold = float(auto_merge_threshold)
        self.review_threshold = float(review_threshold)
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS entity_canonicalizations (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                canonical_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                status TEXT NOT NULL,
                match_evidence_json TEXT NOT NULL,
                match_evidence_hash TEXT NOT NULL,
                source_weights_json TEXT NOT NULL,
                survivorship_json TEXT NOT NULL,
                conflicts_json TEXT NOT NULL,
                reviewer_principal TEXT,
                reviewer_kind TEXT,
                review_evidence_hash TEXT,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL,
                reversed_at REAL,
                reversed_by_agent_id TEXT REFERENCES agents(id),
                reversal_evidence_hash TEXT
            );

            CREATE TABLE IF NOT EXISTS entity_canonical_members (
                canonicalization_id TEXT NOT NULL
                    REFERENCES entity_canonicalizations(id),
                source_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                previous_status TEXT NOT NULL,
                source_weight REAL NOT NULL,
                PRIMARY KEY(canonicalization_id, source_node_id)
            );

            CREATE TABLE IF NOT EXISTS entity_canonical_alias_snapshots (
                canonicalization_id TEXT NOT NULL
                    REFERENCES entity_canonicalizations(id),
                node_type TEXT NOT NULL,
                alias_norm TEXT NOT NULL,
                alias_display TEXT NOT NULL,
                node_id TEXT NOT NULL REFERENCES graph_nodes(id),
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL,
                PRIMARY KEY(canonicalization_id, node_type, alias_norm)
            );

            CREATE TABLE IF NOT EXISTS entity_canonical_created_aliases (
                canonicalization_id TEXT NOT NULL
                    REFERENCES entity_canonicalizations(id),
                node_type TEXT NOT NULL,
                alias_norm TEXT NOT NULL,
                alias_display TEXT NOT NULL,
                PRIMARY KEY(canonicalization_id, node_type, alias_norm)
            );

            CREATE INDEX IF NOT EXISTS idx_entity_canonical_member
                ON entity_canonical_members(source_node_id);
            CREATE INDEX IF NOT EXISTS idx_entity_canonical_active
                ON entity_canonicalizations(node_type, status);
            """
        )
        self.runtime.conn.commit()

    def compare(self, left_node_id: str, right_node_id: str) -> MatchEvidence:
        left = self.graph.get_node(left_node_id)
        right = self.graph.get_node(right_node_id)
        if left_node_id == right_node_id:
            raise CanonicalizationError("cannot compare a node with itself")
        if left["node_type"] != right["node_type"]:
            return MatchEvidence(
                left_id=left_node_id,
                right_id=right_node_id,
                left_provenance_hash=left["provenance_hash"],
                right_provenance_hash=right["provenance_hash"],
                node_type=f"{left['node_type']}!={right['node_type']}",
                normalized_name_equal=False,
                alias_overlap=0.0,
                description_overlap=0.0,
                neighbor_overlap=0.0,
                hard_identifier_matches=(),
                hard_identifier_conflicts=(),
                score=0.0,
                decision="KEEP_SEPARATE",
                reasons=("node types differ",),
            )
        node_type = left["node_type"]
        if node_type not in IDENTITY_NODE_TYPES:
            return MatchEvidence(
                left_id=left_node_id,
                right_id=right_node_id,
                left_provenance_hash=left["provenance_hash"],
                right_provenance_hash=right["provenance_hash"],
                node_type=node_type,
                normalized_name_equal=False,
                alias_overlap=0.0,
                description_overlap=0.0,
                neighbor_overlap=0.0,
                hard_identifier_matches=(),
                hard_identifier_conflicts=(),
                score=0.0,
                decision="KEEP_SEPARATE",
                reasons=("node type is not identity-canonicalizable",),
            )

        left_name = _normalize_name(left["label"])
        right_name = _normalize_name(right["label"])
        normalized_equal = bool(left_name) and left_name == right_name

        left_aliases = self._alias_signature(left_node_id) | {left_name}
        right_aliases = self._alias_signature(right_node_id) | {right_name}
        left_aliases.discard("")
        right_aliases.discard("")
        alias_overlap = _jaccard(left_aliases, right_aliases)

        left_desc = _tokens(str(left["attributes"].get("description", "")))
        right_desc = _tokens(str(right["attributes"].get("description", "")))
        description_overlap = _jaccard(left_desc, right_desc)

        neighbor_overlap = _jaccard(
            self._neighbor_signature(left_node_id),
            self._neighbor_signature(right_node_id),
        )

        hard_matches, hard_conflicts = self._hard_identifier_comparison(left, right)
        reasons: List[str] = []
        if hard_conflicts:
            reasons.append(
                "conflicting hard identifier(s): " + ", ".join(hard_conflicts)
            )
            score = 0.0
            decision = "KEEP_SEPARATE"
        else:
            score = (
                (0.82 if hard_matches else 0.0)
                + (0.45 if normalized_equal else 0.0)
                + 0.30 * alias_overlap
                + 0.10 * description_overlap
                + 0.15 * neighbor_overlap
            )
            score = min(1.0, score)
            if hard_matches:
                reasons.append("matching hard identifier(s): " + ", ".join(hard_matches))
            if normalized_equal:
                reasons.append("normalized names match")
            if alias_overlap:
                reasons.append(f"alias overlap={alias_overlap:.3f}")
            if description_overlap:
                reasons.append(f"description overlap={description_overlap:.3f}")
            if neighbor_overlap:
                reasons.append(f"neighbor overlap={neighbor_overlap:.3f}")

            if score >= self.auto_merge_threshold:
                decision = "AUTO_MERGE"
            elif score >= self.review_threshold:
                decision = "REVIEW"
            else:
                decision = "KEEP_SEPARATE"
            if not reasons:
                reasons.append("insufficient positive identity evidence")

        return MatchEvidence(
            left_id=left_node_id,
            right_id=right_node_id,
            left_provenance_hash=left["provenance_hash"],
            right_provenance_hash=right["provenance_hash"],
            node_type=node_type,
            normalized_name_equal=normalized_equal,
            alias_overlap=alias_overlap,
            description_overlap=description_overlap,
            neighbor_overlap=neighbor_overlap,
            hard_identifier_matches=tuple(sorted(hard_matches)),
            hard_identifier_conflicts=tuple(sorted(hard_conflicts)),
            score=score,
            decision=decision,
            reasons=tuple(reasons),
        )

    def candidates(
        self,
        *,
        node_type: str,
        minimum_decision: str = "REVIEW",
    ) -> List[MatchEvidence]:
        node_type = node_type.strip().upper()
        if node_type not in IDENTITY_NODE_TYPES:
            raise CanonicalizationError("unsupported canonicalizable node type")
        order = {"KEEP_SEPARATE": 0, "REVIEW": 1, "AUTO_MERGE": 2}
        if minimum_decision not in order:
            raise CanonicalizationError(
                "minimum_decision must be KEEP_SEPARATE, REVIEW, or AUTO_MERGE"
            )
        rows = self.runtime.conn.execute(
            """
            SELECT id FROM graph_nodes
            WHERE node_type=? AND status='ACTIVE'
            ORDER BY id
            """,
            (node_type,),
        ).fetchall()
        out: List[MatchEvidence] = []
        ids = [str(row["id"]) for row in rows]
        for idx, left in enumerate(ids):
            for right in ids[idx + 1:]:
                evidence = self.compare(left, right)
                if order[evidence.decision] >= order[minimum_decision]:
                    out.append(evidence)
        return sorted(
            out,
            key=lambda item: (item.score, item.left_id, item.right_id),
            reverse=True,
        )

    def merge(
        self,
        left_node_id: str,
        right_node_id: str,
        *,
        created_by_agent_id: str,
        match_evidence: Optional[MatchEvidence] = None,
        source_weights: Optional[Mapping[str, float]] = None,
        reviewer_principal: Optional[str] = None,
        reviewer_kind: Optional[str] = None,
        review_evidence: Optional[Dict[str, Any]] = None,
        canonical_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        evidence = match_evidence or self.compare(left_node_id, right_node_id)
        if {evidence.left_id, evidence.right_id} != {left_node_id, right_node_id}:
            raise CanonicalizationError("match evidence does not bind to supplied nodes")
        left = self.graph.get_node(left_node_id)
        right = self.graph.get_node(right_node_id)
        if (
            evidence.left_provenance_hash != left["provenance_hash"]
            or evidence.right_provenance_hash != right["provenance_hash"]
        ):
            raise CanonicalizationError(
                "source provenance changed after match evaluation; compare again"
            )
        if left["status"] != "ACTIVE" or right["status"] != "ACTIVE":
            raise CanonicalizationError("only ACTIVE source nodes may be canonicalized")
        if evidence.decision == "KEEP_SEPARATE":
            raise CanonicalizationError("match evidence does not permit a merge")
        if evidence.hard_identifier_conflicts:
            raise CanonicalizationError("hard identifier conflict forbids canonicalization")
        if evidence.decision == "REVIEW":
            if reviewer_kind != "HUMAN":
                raise CanonicalizationError(
                    "ambiguous canonicalization requires a HUMAN reviewer"
                )
            if not (reviewer_principal or "").strip() or not review_evidence:
                raise CanonicalizationError(
                    "ambiguous canonicalization requires reviewer identity and evidence"
                )

        weights = self._normalize_weights(
            [left_node_id, right_node_id],
            source_weights,
        )
        survivorship, conflicts = self._survivorship(
            [left, right],
            weights,
            canonical_label=canonical_label,
        )
        merge_id = f"canonmerge_{uuid.uuid4().hex}"
        canonical_seed = {
            "version": self.VERSION,
            "merge_id": merge_id,
            "members": sorted([left_node_id, right_node_id]),
            "match_evidence_hash": evidence.sha256,
            "source_weights": weights,
            "survivorship": survivorship,
        }
        seed_hash = _sha(canonical_seed)
        node_type = left["node_type"]
        canonical_node_id = f"canonical_{node_type.lower()}_{seed_hash[:20]}"
        canonical_key = f"canonical:{node_type.lower()}:{seed_hash[:24]}"

        proposed_aliases = self._proposed_aliases(
            [left, right],
            canonical_label=survivorship["label"],
        )
        self._ensure_aliases_available(
            node_type,
            proposed_aliases,
            member_ids={left_node_id, right_node_id},
        )

        provenance_refs = sorted(
            {
                ref
                for node in (left, right)
                for ref in node["provenance"].get("evidence_refs", [])
            }
        )
        provenance_refs.append(f"canonicalization:{merge_id}")
        canonical_provenance = {
            "evidence_refs": provenance_refs,
            "derived": True,
            "canonicalization_id": merge_id,
            "source_node_ids": sorted([left_node_id, right_node_id]),
            "match_evidence_hash": evidence.sha256,
        }
        canonical_attributes = dict(survivorship["attributes"])
        canonical_attributes["_canonicalization"] = {
            "id": merge_id,
            "version": self.VERSION,
            "source_node_ids": sorted([left_node_id, right_node_id]),
            "source_weights": weights,
            "conflicts_hash": _sha(conflicts),
        }
        provenance_hash = _sha(canonical_provenance)
        ts = _now()
        review_evidence_hash = _sha(review_evidence) if review_evidence else None

        conn = self.runtime.conn
        try:
            conn.execute("BEGIN IMMEDIATE")
            alias_rows = conn.execute(
                """
                SELECT * FROM graph_aliases
                WHERE node_id IN (?, ?)
                ORDER BY node_type, alias_norm
                """,
                (left_node_id, right_node_id),
            ).fetchall()

            conn.execute(
                """
                INSERT INTO graph_nodes(
                    id, node_type, canonical_key, label, attributes_json,
                    provenance_json, provenance_hash, created_by_agent_id,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    canonical_node_id,
                    node_type,
                    canonical_key,
                    survivorship["label"],
                    _json(canonical_attributes),
                    _json(canonical_provenance),
                    provenance_hash,
                    created_by_agent_id,
                    ts,
                    ts,
                ),
            )
            conn.execute(
                """
                INSERT INTO entity_canonicalizations(
                    id, node_type, canonical_node_id, status,
                    match_evidence_json, match_evidence_hash,
                    source_weights_json, survivorship_json, conflicts_json,
                    reviewer_principal, reviewer_kind, review_evidence_hash,
                    created_by_agent_id, created_at
                ) VALUES (?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    merge_id,
                    node_type,
                    canonical_node_id,
                    _json(dataclasses.asdict(evidence)),
                    evidence.sha256,
                    _json(weights),
                    _json(survivorship),
                    _json(conflicts),
                    reviewer_principal,
                    reviewer_kind,
                    review_evidence_hash,
                    created_by_agent_id,
                    ts,
                ),
            )
            for node in (left, right):
                conn.execute(
                    """
                    INSERT INTO entity_canonical_members(
                        canonicalization_id, source_node_id,
                        previous_status, source_weight
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        merge_id,
                        node["id"],
                        node["status"],
                        weights[node["id"]],
                    ),
                )

            for row in alias_rows:
                conn.execute(
                    """
                    INSERT INTO entity_canonical_alias_snapshots(
                        canonicalization_id, node_type, alias_norm, alias_display,
                        node_id, evidence_json, evidence_hash,
                        created_by_agent_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        merge_id,
                        row["node_type"],
                        row["alias_norm"],
                        row["alias_display"],
                        row["node_id"],
                        row["evidence_json"],
                        row["evidence_hash"],
                        row["created_by_agent_id"],
                        row["created_at"],
                    ),
                )

            conn.execute(
                "DELETE FROM graph_aliases WHERE node_id IN (?, ?)",
                (left_node_id, right_node_id),
            )
            conn.execute(
                """
                UPDATE graph_nodes
                SET status='CANONICALIZED', updated_at=?
                WHERE id IN (?, ?)
                """,
                (ts, left_node_id, right_node_id),
            )

            for alias_norm, alias_display in sorted(proposed_aliases.items()):
                alias_evidence = {
                    "canonicalization_id": merge_id,
                    "match_evidence_hash": evidence.sha256,
                    "source_node_ids": sorted([left_node_id, right_node_id]),
                    "alias": alias_display,
                }
                alias_evidence_hash = _sha(alias_evidence)
                conn.execute(
                    """
                    INSERT INTO graph_aliases(
                        node_type, alias_norm, alias_display, node_id,
                        evidence_json, evidence_hash, created_by_agent_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node_type,
                        alias_norm,
                        alias_display,
                        canonical_node_id,
                        _json(alias_evidence),
                        alias_evidence_hash,
                        created_by_agent_id,
                        ts,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO entity_canonical_created_aliases(
                        canonicalization_id, node_type, alias_norm, alias_display
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (merge_id, node_type, alias_norm, alias_display),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        self.runtime.append_event(
            created_by_agent_id,
            "ENTITY_CANONICALIZED",
            {
                "canonicalization_id": merge_id,
                "canonical_node_id": canonical_node_id,
                "source_node_ids": sorted([left_node_id, right_node_id]),
                "match_evidence_hash": evidence.sha256,
                "conflicts_hash": _sha(conflicts),
                "reviewer_principal": reviewer_principal,
            },
        )
        return self.get_canonicalization(merge_id)

    def reverse(
        self,
        canonicalization_id: str,
        *,
        reversed_by_agent_id: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.runtime._require_agent(reversed_by_agent_id)
        row = self._require_canonicalization(canonicalization_id)
        if row["status"] != "ACTIVE":
            raise CanonicalizationError("canonicalization is not ACTIVE")
        if not reason.strip() or not evidence:
            raise CanonicalizationError("reversal requires reason and evidence")
        canonical_node_id = row["canonical_node_id"]

        active_edges = self.runtime.conn.execute(
            """
            SELECT COUNT(*) AS n FROM graph_edges
            WHERE status='ACTIVE'
              AND (source_node_id=? OR target_node_id=?)
            """,
            (canonical_node_id, canonical_node_id),
        ).fetchone()
        if int(active_edges["n"]) > 0:
            raise CanonicalizationError(
                "canonical entity has active relationships; close/supersede them before reversal"
            )

        created_aliases = self.runtime.conn.execute(
            """
            SELECT * FROM entity_canonical_created_aliases
            WHERE canonicalization_id=?
            ORDER BY alias_norm
            """,
            (canonicalization_id,),
        ).fetchall()
        current_aliases = self.runtime.conn.execute(
            """
            SELECT alias_norm, node_id FROM graph_aliases
            WHERE node_type=? AND node_id=?
            """,
            (row["node_type"], canonical_node_id),
        ).fetchall()
        expected_alias_norms = {item["alias_norm"] for item in created_aliases}
        current_alias_norms = {item["alias_norm"] for item in current_aliases}
        if current_alias_norms != expected_alias_norms:
            raise CanonicalizationError(
                "canonical aliases changed after merge; reconcile them before reversal"
            )

        snapshots = self.runtime.conn.execute(
            """
            SELECT * FROM entity_canonical_alias_snapshots
            WHERE canonicalization_id=?
            ORDER BY alias_norm
            """,
            (canonicalization_id,),
        ).fetchall()
        members = self.runtime.conn.execute(
            """
            SELECT * FROM entity_canonical_members
            WHERE canonicalization_id=?
            ORDER BY source_node_id
            """,
            (canonicalization_id,),
        ).fetchall()

        reversal_evidence_hash = _sha(
            {
                "canonicalization_id": canonicalization_id,
                "reason": reason,
                "evidence": evidence,
            }
        )
        ts = _now()
        conn = self.runtime.conn
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "DELETE FROM graph_aliases WHERE node_id=?",
                (canonical_node_id,),
            )
            for snap in snapshots:
                collision = conn.execute(
                    """
                    SELECT node_id FROM graph_aliases
                    WHERE node_type=? AND alias_norm=?
                    """,
                    (snap["node_type"], snap["alias_norm"]),
                ).fetchone()
                if collision is not None:
                    raise CanonicalizationError(
                        f"cannot restore alias {snap['alias_display']}: it is now occupied"
                    )
                conn.execute(
                    """
                    INSERT INTO graph_aliases(
                        node_type, alias_norm, alias_display, node_id,
                        evidence_json, evidence_hash, created_by_agent_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snap["node_type"],
                        snap["alias_norm"],
                        snap["alias_display"],
                        snap["node_id"],
                        snap["evidence_json"],
                        snap["evidence_hash"],
                        snap["created_by_agent_id"],
                        snap["created_at"],
                    ),
                )
            for member in members:
                conn.execute(
                    """
                    UPDATE graph_nodes SET status=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        member["previous_status"],
                        ts,
                        member["source_node_id"],
                    ),
                )
            conn.execute(
                """
                UPDATE graph_nodes
                SET status='REVERSED', updated_at=?
                WHERE id=?
                """,
                (ts, canonical_node_id),
            )
            conn.execute(
                """
                UPDATE entity_canonicalizations
                SET status='REVERSED', reversed_at=?,
                    reversed_by_agent_id=?, reversal_evidence_hash=?
                WHERE id=?
                """,
                (
                    ts,
                    reversed_by_agent_id,
                    reversal_evidence_hash,
                    canonicalization_id,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        self.runtime.append_event(
            reversed_by_agent_id,
            "ENTITY_CANONICALIZATION_REVERSED",
            {
                "canonicalization_id": canonicalization_id,
                "canonical_node_id": canonical_node_id,
                "reason": reason,
                "reversal_evidence_hash": reversal_evidence_hash,
            },
        )
        return self.get_canonicalization(canonicalization_id)

    def canonical_node_id(self, node_id: str) -> str:
        row = self.runtime.conn.execute(
            """
            SELECT c.canonical_node_id
            FROM entity_canonical_members m
            JOIN entity_canonicalizations c
              ON c.id=m.canonicalization_id
            WHERE m.source_node_id=? AND c.status='ACTIVE'
            """,
            (node_id,),
        ).fetchone()
        return str(row["canonical_node_id"]) if row else node_id

    def canonical_view(self, node_id: str) -> Dict[str, Any]:
        canonical_id = self.canonical_node_id(node_id)
        canonical = self.graph.get_node(canonical_id)
        row = self.runtime.conn.execute(
            """
            SELECT * FROM entity_canonicalizations
            WHERE canonical_node_id=? AND status='ACTIVE'
            """,
            (canonical_id,),
        ).fetchone()
        if row is None:
            return {
                "canonical_node": canonical,
                "source_nodes": [canonical],
                "canonicalization": None,
                "neighbors": self._canonical_neighbors([canonical_id]),
            }
        members = self.runtime.conn.execute(
            """
            SELECT source_node_id FROM entity_canonical_members
            WHERE canonicalization_id=?
            ORDER BY source_node_id
            """,
            (row["id"],),
        ).fetchall()
        source_ids = [str(item["source_node_id"]) for item in members]
        return {
            "canonical_node": canonical,
            "source_nodes": [self.graph.get_node(item) for item in source_ids],
            "canonicalization": self.get_canonicalization(str(row["id"])),
            "neighbors": self._canonical_neighbors([canonical_id, *source_ids]),
        }

    def get_canonicalization(self, canonicalization_id: str) -> Dict[str, Any]:
        row = self._require_canonicalization(canonicalization_id)
        members = self.runtime.conn.execute(
            """
            SELECT * FROM entity_canonical_members
            WHERE canonicalization_id=?
            ORDER BY source_node_id
            """,
            (canonicalization_id,),
        ).fetchall()
        return {
            "id": row["id"],
            "node_type": row["node_type"],
            "canonical_node_id": row["canonical_node_id"],
            "status": row["status"],
            "match_evidence": json.loads(row["match_evidence_json"]),
            "match_evidence_hash": row["match_evidence_hash"],
            "source_weights": json.loads(row["source_weights_json"]),
            "survivorship": json.loads(row["survivorship_json"]),
            "conflicts": json.loads(row["conflicts_json"]),
            "reviewer_principal": row["reviewer_principal"],
            "reviewer_kind": row["reviewer_kind"],
            "review_evidence_hash": row["review_evidence_hash"],
            "members": [
                {
                    "source_node_id": item["source_node_id"],
                    "previous_status": item["previous_status"],
                    "source_weight": item["source_weight"],
                }
                for item in members
            ],
            "created_by_agent_id": row["created_by_agent_id"],
            "created_at": row["created_at"],
            "reversed_at": row["reversed_at"],
            "reversed_by_agent_id": row["reversed_by_agent_id"],
            "reversal_evidence_hash": row["reversal_evidence_hash"],
        }

    def _survivorship(
        self,
        nodes: Sequence[Dict[str, Any]],
        weights: Mapping[str, float],
        *,
        canonical_label: Optional[str],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        if canonical_label is not None and not canonical_label.strip():
            raise CanonicalizationError("canonical_label cannot be blank")
        conflicts: List[Dict[str, Any]] = []

        if canonical_label is None:
            label_candidates = [
                (weights[node["id"]], node["label"], node["id"]) for node in nodes
            ]
            label_candidates.sort(
                key=lambda item: (item[0], len(_tokens(item[1])), len(item[1]), item[1], item[2]),
                reverse=True,
            )
            chosen_label = label_candidates[0][1]
        else:
            chosen_label = canonical_label.strip()

        fields = sorted(
            {
                key
                for node in nodes
                for key in node["attributes"].keys()
                if key != "_canonicalization"
            }
        )
        chosen_attributes: Dict[str, Any] = {}
        winners: Dict[str, Dict[str, Any]] = {}
        for field in fields:
            candidates = []
            for node in nodes:
                if field not in node["attributes"]:
                    continue
                value = node["attributes"][field]
                candidates.append(
                    {
                        "node_id": node["id"],
                        "value": value,
                        "weight": weights[node["id"]],
                        "canonical_value": _json(value),
                    }
                )
            if not candidates:
                continue
            distinct = {item["canonical_value"] for item in candidates}
            ranked = sorted(
                candidates,
                key=lambda item: (
                    item["weight"],
                    item["canonical_value"],
                    item["node_id"],
                ),
                reverse=True,
            )
            winner = ranked[0]
            chosen_attributes[field] = winner["value"]
            winners[field] = {
                "source_node_id": winner["node_id"],
                "source_weight": winner["weight"],
            }
            if len(distinct) > 1:
                conflicts.append(
                    {
                        "field": field,
                        "winner_source_node_id": winner["node_id"],
                        "winner_value": winner["value"],
                        "candidates": [
                            {
                                "source_node_id": item["node_id"],
                                "value": item["value"],
                                "source_weight": item["weight"],
                            }
                            for item in ranked
                        ],
                    }
                )

        return (
            {
                "label": chosen_label,
                "attributes": chosen_attributes,
                "field_winners": winners,
            },
            conflicts,
        )

    def _normalize_weights(
        self,
        node_ids: Sequence[str],
        source_weights: Optional[Mapping[str, float]],
    ) -> Dict[str, float]:
        if source_weights is None:
            return {node_id: 1.0 for node_id in node_ids}
        if set(source_weights) != set(node_ids):
            raise CanonicalizationError(
                "source_weights must specify exactly the merged source nodes"
            )
        out: Dict[str, float] = {}
        for node_id in node_ids:
            value = float(source_weights[node_id])
            if not math.isfinite(value) or value <= 0:
                raise CanonicalizationError(
                    "source weights must be finite and greater than zero"
                )
            out[node_id] = value
        return out

    def _proposed_aliases(
        self,
        nodes: Sequence[Dict[str, Any]],
        *,
        canonical_label: str,
    ) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        for node in nodes:
            for display in (
                node["label"],
                node["canonical_key"],
                *self._alias_displays(node["id"]),
            ):
                display = str(display).strip()
                norm = _alias_key(display)
                if not norm:
                    continue
                current = aliases.get(norm)
                if current is None or (len(display), display) > (len(current), current):
                    aliases[norm] = display
        canonical_norm = _alias_key(canonical_label)
        if canonical_norm:
            aliases.setdefault(canonical_norm, canonical_label)
        return aliases

    def _ensure_aliases_available(
        self,
        node_type: str,
        proposed_aliases: Mapping[str, str],
        *,
        member_ids: Set[str],
    ) -> None:
        for alias_norm, alias_display in proposed_aliases.items():
            row = self.runtime.conn.execute(
                """
                SELECT a.node_id, n.status
                FROM graph_aliases a
                JOIN graph_nodes n ON n.id=a.node_id
                WHERE a.node_type=? AND a.alias_norm=?
                """,
                (node_type, alias_norm),
            ).fetchone()
            if row is not None and row["node_id"] not in member_ids:
                raise CanonicalizationError(
                    f"alias {alias_display!r} belongs to another entity"
                )
            canonical_rows = self.runtime.conn.execute(
                """
                SELECT id, canonical_key FROM graph_nodes
                WHERE node_type=? AND status='ACTIVE'
                """,
                (node_type,),
            ).fetchall()
            for candidate in canonical_rows:
                if candidate["id"] in member_ids:
                    continue
                if _alias_key(candidate["canonical_key"]) == alias_norm:
                    raise CanonicalizationError(
                        f"alias {alias_display!r} collides with another canonical key"
                    )

    def _alias_signature(self, node_id: str) -> Set[str]:
        return {
            _normalize_name(item)
            for item in self._alias_displays(node_id)
            if _normalize_name(item)
        }

    def _alias_displays(self, node_id: str) -> List[str]:
        rows = self.runtime.conn.execute(
            """
            SELECT alias_display FROM graph_aliases
            WHERE node_id=?
            ORDER BY alias_norm
            """,
            (node_id,),
        ).fetchall()
        return [str(row["alias_display"]) for row in rows]

    def _neighbor_signature(self, node_id: str) -> Set[str]:
        signature: Set[str] = set()
        for edge in self.graph.neighbors(node_id, direction="both"):
            if edge["source_node_id"] == node_id:
                other_id = edge["target_node_id"]
                direction = "out"
            else:
                other_id = edge["source_node_id"]
                direction = "in"
            other = self.graph.get_node(other_id)
            signature.add(
                f"{direction}:{edge['edge_type']}:{other['node_type']}:{_normalize_name(other['label'])}"
            )
        return signature

    def _hard_identifier_comparison(
        self,
        left: Dict[str, Any],
        right: Dict[str, Any],
    ) -> Tuple[Set[str], Set[str]]:
        matches: Set[str] = set()
        conflicts: Set[str] = set()
        for field in HARD_IDENTIFIER_FIELDS:
            if field not in left["attributes"] or field not in right["attributes"]:
                continue
            left_raw = left["attributes"][field]
            right_raw = right["attributes"][field]
            if left_raw is None or right_raw is None:
                continue
            if isinstance(left_raw, (dict, list)) or isinstance(right_raw, (dict, list)):
                continue
            left_value = str(left_raw).strip().casefold()
            right_value = str(right_raw).strip().casefold()
            if not left_value or not right_value:
                continue
            if left_value == right_value:
                matches.add(field)
            else:
                conflicts.add(field)
        return matches, conflicts

    def _canonical_neighbors(self, node_ids: Sequence[str]) -> List[Dict[str, Any]]:
        grouped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for node_id in node_ids:
            for edge in self.graph.neighbors(node_id, direction="both"):
                canonical_source = self.canonical_node_id(edge["source_node_id"])
                canonical_target = self.canonical_node_id(edge["target_node_id"])
                if canonical_source == canonical_target:
                    continue
                key = (
                    canonical_source,
                    edge["edge_type"],
                    canonical_target,
                )
                bucket = grouped.setdefault(
                    key,
                    {
                        "canonical_source_node_id": canonical_source,
                        "edge_type": edge["edge_type"],
                        "canonical_target_node_id": canonical_target,
                        "evidence_edges": [],
                    },
                )
                bucket["evidence_edges"].append(
                    {
                        "via_node_id": node_id,
                        "edge": edge,
                    }
                )
        return [
            grouped[key]
            for key in sorted(grouped)
        ]

    def _require_canonicalization(self, canonicalization_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM entity_canonicalizations WHERE id=?",
            (canonicalization_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown canonicalization: {canonicalization_id}")
        return row
