"""Historical graph layer for retrospective MNPI surveillance research.

Step 12 builds a deterministic relationship graph from already-approved,
deduplicated historical economic transactions. It is strictly retrospective and
public-record scoped: no live feeds, alerts, order generation, or private data.

Nodes represent durable traders, durable issuers, information events, and
economic transaction clusters. Source-backed normalized rows remain members of
clusters; the graph never replaces their provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .economic_dedup import EconomicTransactionCluster
from .source_registry import USAGE_SCOPE, canonical_hash


class SurveillanceNodeKind(str, Enum):
    TRADER = "TRADER"
    ISSUER = "ISSUER"
    EVENT = "EVENT"
    ECONOMIC_TRANSACTION = "ECONOMIC_TRANSACTION"


class SurveillanceEdgeKind(str, Enum):
    TRADER_EXECUTED = "TRADER_EXECUTED"
    ISSUER_SUBJECT = "ISSUER_SUBJECT"
    EVENT_CONTEXT = "EVENT_CONTEXT"


@dataclass(frozen=True)
class SurveillanceNode:
    node_id: str
    kind: SurveillanceNodeKind
    stable_ref: str

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if not self.stable_ref.strip():
            raise ValueError("stable_ref is required")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "node_id": self.node_id,
            "kind": self.kind.value,
            "stable_ref": self.stable_ref,
        })


@dataclass(frozen=True)
class SurveillanceEdge:
    edge_id: str
    kind: SurveillanceEdgeKind
    source_node_id: str
    target_node_id: str
    cluster_id: str

    def __post_init__(self) -> None:
        if not self.edge_id.startswith("surveillance-edge:"):
            raise ValueError("edge_id must use surveillance-edge: prefix")
        if not self.source_node_id or not self.target_node_id:
            raise ValueError("edge endpoints are required")
        if not self.cluster_id.startswith("economic:"):
            raise ValueError("cluster_id must use economic: prefix")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "edge_id": self.edge_id,
            "kind": self.kind.value,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "cluster_id": self.cluster_id,
        })


def _node_id(kind: SurveillanceNodeKind, stable_ref: str) -> str:
    return "surveillance:" + kind.value.lower() + ":" + canonical_hash({
        "schema": 1,
        "kind": kind.value,
        "stable_ref": stable_ref,
    })


def _edge(
    kind: SurveillanceEdgeKind,
    source_node_id: str,
    target_node_id: str,
    cluster_id: str,
) -> SurveillanceEdge:
    body = {
        "schema": 1,
        "kind": kind.value,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "cluster_id": cluster_id,
    }
    return SurveillanceEdge(
        edge_id="surveillance-edge:" + canonical_hash(body),
        kind=kind,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        cluster_id=cluster_id,
    )


@dataclass(frozen=True)
class HistoricalSurveillanceGraph:
    nodes: tuple[SurveillanceNode, ...]
    edges: tuple[SurveillanceEdge, ...]
    cluster_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        node_ids = [item.node_id for item in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("duplicate surveillance node")
        edge_ids = [item.edge_id for item in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("duplicate surveillance edge")
        node_set = set(node_ids)
        for edge in self.edges:
            if edge.source_node_id not in node_set:
                raise ValueError("edge source node missing from graph")
            if edge.target_node_id not in node_set:
                raise ValueError("edge target node missing from graph")
        if tuple(sorted(set(self.cluster_hashes))) != self.cluster_hashes:
            raise ValueError("cluster_hashes must be unique and sorted")

    def node(self, node_id: str) -> SurveillanceNode:
        try:
            return next(item for item in self.nodes if item.node_id == node_id)
        except StopIteration as exc:
            raise KeyError("unknown surveillance node: " + node_id) from exc

    def nodes_of_kind(
        self,
        kind: SurveillanceNodeKind,
    ) -> tuple[SurveillanceNode, ...]:
        return tuple(item for item in self.nodes if item.kind is kind)

    def neighbors(self, node_id: str) -> tuple[str, ...]:
        self.node(node_id)
        out = set()
        for edge in self.edges:
            if edge.source_node_id == node_id:
                out.add(edge.target_node_id)
            if edge.target_node_id == node_id:
                out.add(edge.source_node_id)
        return tuple(sorted(out))

    def degree(self, node_id: str) -> int:
        return len(self.neighbors(node_id))

    def connected_component(self, node_id: str) -> tuple[str, ...]:
        self.node(node_id)
        seen = {node_id}
        frontier = [node_id]
        while frontier:
            current = frontier.pop()
            for neighbor in self.neighbors(current):
                if neighbor not in seen:
                    seen.add(neighbor)
                    frontier.append(neighbor)
        return tuple(sorted(seen))

    def cluster_node_id(self, cluster_id: str) -> str:
        target = _node_id(
            SurveillanceNodeKind.ECONOMIC_TRANSACTION,
            cluster_id,
        )
        self.node(target)
        return target

    def trader_node_id(self, trader_entity_id: str) -> str:
        target = _node_id(SurveillanceNodeKind.TRADER, trader_entity_id)
        self.node(target)
        return target

    def issuer_node_id(self, issuer_entity_id: str) -> str:
        target = _node_id(SurveillanceNodeKind.ISSUER, issuer_entity_id)
        self.node(target)
        return target

    def event_node_id(self, event_id: str) -> str:
        target = _node_id(SurveillanceNodeKind.EVENT, event_id)
        self.node(target)
        return target

    def trader_event_count(self, trader_entity_id: str) -> int:
        trader_id = self.trader_node_id(trader_entity_id)
        event_ids = set()
        for cluster_id in self.neighbors(trader_id):
            cluster = self.node(cluster_id)
            if cluster.kind is not SurveillanceNodeKind.ECONOMIC_TRANSACTION:
                continue
            for neighbor in self.neighbors(cluster.node_id):
                if self.node(neighbor).kind is SurveillanceNodeKind.EVENT:
                    event_ids.add(neighbor)
        return len(event_ids)

    def issuer_trader_count(self, issuer_entity_id: str) -> int:
        issuer_id = self.issuer_node_id(issuer_entity_id)
        trader_ids = set()
        for cluster_id in self.neighbors(issuer_id):
            cluster = self.node(cluster_id)
            if cluster.kind is not SurveillanceNodeKind.ECONOMIC_TRANSACTION:
                continue
            for neighbor in self.neighbors(cluster.node_id):
                if self.node(neighbor).kind is SurveillanceNodeKind.TRADER:
                    trader_ids.add(neighbor)
        return len(trader_ids)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "node_hashes": sorted(item.proof_hash for item in self.nodes),
            "edge_hashes": sorted(item.proof_hash for item in self.edges),
            "cluster_hashes": list(self.cluster_hashes),
        })


def build_historical_surveillance_graph(
    clusters: Iterable[EconomicTransactionCluster],
) -> HistoricalSurveillanceGraph:
    cluster_tuple = tuple(sorted(
        clusters,
        key=lambda item: item.cluster_id,
    ))
    nodes: dict[str, SurveillanceNode] = {}
    edges: dict[str, SurveillanceEdge] = {}

    def add_node(kind: SurveillanceNodeKind, stable_ref: str) -> str:
        node_id = _node_id(kind, stable_ref)
        node = SurveillanceNode(
            node_id=node_id,
            kind=kind,
            stable_ref=stable_ref,
        )
        existing = nodes.get(node_id)
        if existing is not None and existing.proof_hash != node.proof_hash:
            raise ValueError("surveillance node id collision")
        nodes[node_id] = node
        return node_id

    for cluster in cluster_tuple:
        first = cluster.signatures[0]
        trader_ids = {item.trader_entity_id for item in cluster.signatures}
        issuer_ids = {item.issuer_entity_id for item in cluster.signatures}
        event_ids = {item.event_id for item in cluster.signatures}
        if len(trader_ids) != 1:
            raise ValueError("economic cluster spans multiple durable traders")
        if len(issuer_ids) != 1:
            raise ValueError("economic cluster spans multiple durable issuers")
        if len(event_ids) != 1:
            raise ValueError("economic cluster spans multiple information events")

        cluster_node = add_node(
            SurveillanceNodeKind.ECONOMIC_TRANSACTION,
            cluster.cluster_id,
        )
        trader_node = add_node(
            SurveillanceNodeKind.TRADER,
            first.trader_entity_id,
        )
        issuer_node = add_node(
            SurveillanceNodeKind.ISSUER,
            first.issuer_entity_id,
        )
        event_node = add_node(
            SurveillanceNodeKind.EVENT,
            first.event_id,
        )

        for edge in (
            _edge(
                SurveillanceEdgeKind.TRADER_EXECUTED,
                trader_node,
                cluster_node,
                cluster.cluster_id,
            ),
            _edge(
                SurveillanceEdgeKind.ISSUER_SUBJECT,
                issuer_node,
                cluster_node,
                cluster.cluster_id,
            ),
            _edge(
                SurveillanceEdgeKind.EVENT_CONTEXT,
                event_node,
                cluster_node,
                cluster.cluster_id,
            ),
        ):
            edges[edge.edge_id] = edge

    return HistoricalSurveillanceGraph(
        nodes=tuple(sorted(nodes.values(), key=lambda item: item.node_id)),
        edges=tuple(sorted(edges.values(), key=lambda item: item.edge_id)),
        cluster_hashes=tuple(sorted(
            item.proof_hash for item in cluster_tuple
        )),
    )


__all__ = [
    "HistoricalSurveillanceGraph",
    "SurveillanceEdge",
    "SurveillanceEdgeKind",
    "SurveillanceNode",
    "SurveillanceNodeKind",
    "build_historical_surveillance_graph",
]
