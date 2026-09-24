"""Evidence-preserving entity canonicalization for AI Business OS.

This layer finds likely duplicate graph entities using deterministic lexical,
alias, type and graph-neighbor evidence. Merges never delete source nodes.
Instead, a canonical node is created and explicit MERGED_INTO edges preserve
the original identities and the evidence used.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import uuid
from typing import Any, Iterable

from business_os.graph.knowledge_graph import KnowledgeGraph, Node


CORPORATE_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company",
    "llc", "ltd", "limited", "plc", "lp", "llp"
}


@dataclasses.dataclass(frozen=True)
class MatchEvidence:
    left_id: str
    right_id: str
    type_compatible: bool
    normalized_name_equal: bool
    alias_overlap: float
    description_overlap: float
    neighbor_overlap: float
    score: float
    decision: str
    reasons: tuple[str, ...]

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


class EntityCanonicalizer:
    """Deterministic duplicate resolver.

    The normal path never invokes an LLM. Ambiguous pairs are returned as
    REVIEW rather than guessed.
    """

    VERSION = "entity-canonicalizer-v1"

    def __init__(
        self,
        graph: KnowledgeGraph,
        *,
        auto_merge_threshold: float = 0.82,
        review_threshold: float = 0.58,
    ) -> None:
        if not 0 <= review_threshold <= auto_merge_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 <= review <= auto <= 1")
        self.graph = graph
        self.auto_merge_threshold = auto_merge_threshold
        self.review_threshold = review_threshold

    def compare(self, left: Node | str, right: Node | str) -> MatchEvidence:
        l = self.graph.get_node(left) if isinstance(left, str) else left
        r = self.graph.get_node(right) if isinstance(right, str) else right
        if l.id == r.id:
            raise ValueError("cannot compare a node with itself")

        compatible = l.type == r.type
        lname = _normalize_name(l.name)
        rname = _normalize_name(r.name)
        normalized_equal = lname == rname and bool(lname)

        l_aliases = {_normalize_name(x) for x in _aliases(l)} | {lname}
        r_aliases = {_normalize_name(x) for x in _aliases(r)} | {rname}
        l_aliases.discard("")
        r_aliases.discard("")
        alias_overlap = _jaccard(l_aliases, r_aliases)

        ldesc = _tokens(str(l.properties.get("description", "")))
        rdesc = _tokens(str(r.properties.get("description", "")))
        description_overlap = _jaccard(ldesc, rdesc)

        lneighbors = self._neighbor_signature(l.id)
        rneighbors = self._neighbor_signature(r.id)
        neighbor_overlap = _jaccard(lneighbors, rneighbors)

        reasons: list[str] = []
        if not compatible:
            score = 0.0
            decision = "KEEP_SEPARATE"
            reasons.append("node types differ")
        else:
            # Absent neighbor context is not negative evidence; only positive
            # overlap contributes. This mirrors the strongest Hunter finding.
            score = (
                (0.45 if normalized_equal else 0.0)
                + 0.30 * alias_overlap
                + 0.10 * description_overlap
                + 0.15 * neighbor_overlap
            )
            score = min(1.0, score)

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
            left_id=l.id,
            right_id=r.id,
            type_compatible=compatible,
            normalized_name_equal=normalized_equal,
            alias_overlap=alias_overlap,
            description_overlap=description_overlap,
            neighbor_overlap=neighbor_overlap,
            score=score,
            decision=decision,
            reasons=tuple(reasons),
        )

    def merge(
        self,
        left: Node | str,
        right: Node | str,
        *,
        evidence: MatchEvidence | None = None,
        reviewer_approved: bool = False,
        canonical_name: str | None = None,
    ) -> Node:
        l = self.graph.get_node(left) if isinstance(left, str) else left
        r = self.graph.get_node(right) if isinstance(right, str) else right
        evidence = evidence or self.compare(l, r)

        if {evidence.left_id, evidence.right_id} != {l.id, r.id}:
            raise ValueError("match evidence does not bind to supplied nodes")
        if evidence.decision == "KEEP_SEPARATE":
            raise ValueError("insufficient evidence to merge")
        if evidence.decision == "REVIEW" and not reviewer_approved:
            raise PermissionError("ambiguous merge requires reviewer approval")
        if l.type != r.type:
            raise ValueError("cannot merge nodes of different types")

        aliases = sorted(
            {
                l.name,
                r.name,
                *_aliases(l),
                *_aliases(r),
            }
        )
        canonical_name = canonical_name or _choose_name(l.name, r.name)
        merge_payload = {
            "version": self.VERSION,
            "left": l.id,
            "right": r.id,
            "evidence": dataclasses.asdict(evidence),
            "reviewer_approved": reviewer_approved,
            "canonical_name": canonical_name,
        }
        source_sha = _sha(merge_payload)
        canonical_id = f"canonical_{l.type.lower()}_{source_sha[:24]}"

        canonical = self.graph.add_node(
            l.type,
            canonical_name,
            node_id=canonical_id,
            properties={
                "aliases": aliases,
                "_merged_from": sorted([l.id, r.id]),
                "_merge_evidence_sha256": evidence.sha256,
                "_merge_strategy": self.VERSION,
            },
            source_ref=f"derived:{self.VERSION}",
            source_sha256=source_sha,
        )

        for source in (l, r):
            self.graph.add_edge(
                source.id,
                "MERGED_INTO",
                canonical.id,
                properties={
                    "score": evidence.score,
                    "decision": evidence.decision,
                    "evidence_sha256": evidence.sha256,
                },
                source_ref=f"derived:{self.VERSION}",
                source_sha256=source_sha,
            )
        return canonical

    def candidates(
        self,
        *,
        node_type: str,
        minimum_decision: str = "REVIEW",
    ) -> list[MatchEvidence]:
        order = {"KEEP_SEPARATE": 0, "REVIEW": 1, "AUTO_MERGE": 2}
        if minimum_decision not in order:
            raise ValueError("minimum_decision must be KEEP_SEPARATE, REVIEW or AUTO_MERGE")
        nodes = self.graph.find_nodes(node_type=node_type)
        out: list[MatchEvidence] = []
        for i, left in enumerate(nodes):
            for right in nodes[i + 1 :]:
                ev = self.compare(left, right)
                if order[ev.decision] >= order[minimum_decision]:
                    out.append(ev)
        return sorted(out, key=lambda x: x.score, reverse=True)

    def _neighbor_signature(self, node_id: str) -> set[str]:
        sig: set[str] = set()
        for edge, node in self.graph.neighbors(node_id, direction="both"):
            # Preserve relation direction in signature so shared graph context
            # is stronger than generic co-occurrence.
            direction = "out" if edge.src == node_id else "in"
            sig.add(f"{direction}:{edge.relation}:{node.type}:{_normalize_name(node.name)}")
        return sig


def _aliases(node: Node) -> list[str]:
    raw = node.properties.get("aliases", [])
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _choose_name(a: str, b: str) -> str:
    # Prefer the more informative display name, not the normalized string.
    return max((a.strip(), b.strip()), key=lambda x: (len(_tokens(x)), len(x)))


def _normalize_name(value: str) -> str:
    parts = [
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in CORPORATE_SUFFIXES
    ]
    return " ".join(parts)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _sha(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
