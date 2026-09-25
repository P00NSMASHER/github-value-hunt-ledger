import unittest

from historical_mnpi.economic_dedup import (
    EconomicTransactionCluster,
    EconomicTransactionSignature,
)
from historical_mnpi.surveillance_graph import (
    SurveillanceNodeKind,
    build_historical_surveillance_graph,
)
from historical_mnpi.transaction_model import (
    InstrumentType,
    TimePrecision,
    TradeSide,
)


def signature(
    row: int,
    *,
    trader: str,
    issuer: str,
    event: str,
    timestamp: str,
) -> EconomicTransactionSignature:
    return EconomicTransactionSignature(
        normalized_row_hash=(f"{row:064x}")[-64:],
        review_item_hash=(f"{row + 1000:064x}")[-64:],
        trader_entity_id=trader,
        issuer_entity_id=issuer,
        event_id=event,
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        time_precision=TimePrecision.EXACT_TIMESTAMP,
        trade_timestamp=timestamp,
        currency="USD",
        quantity="100",
        execution_price="10",
    )


def cluster(
    row: int,
    *,
    trader: str,
    issuer: str,
    event: str,
    timestamp: str,
) -> EconomicTransactionCluster:
    item = signature(
        row,
        trader=trader,
        issuer=issuer,
        event=event,
        timestamp=timestamp,
    )
    return EconomicTransactionCluster(
        cluster_id=f"economic:{row:064x}",
        signatures=(item,),
    )


class SurveillanceGraphTests(unittest.TestCase):
    def test_single_cluster_creates_four_nodes_and_three_edges(self):
        item = cluster(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        graph = build_historical_surveillance_graph((item,))
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 3)
        self.assertEqual(
            len(graph.nodes_of_kind(SurveillanceNodeKind.TRADER)),
            1,
        )
        self.assertEqual(len(graph.proof_hash), 64)

    def test_shared_trader_connects_multiple_events(self):
        first = cluster(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = cluster(
            2,
            trader="trader:one",
            issuer="issuer:two",
            event="event:two",
            timestamp="2015-09-10T14:00:00-04:00",
        )
        graph = build_historical_surveillance_graph((first, second))
        self.assertEqual(graph.trader_event_count("trader:one"), 2)
        trader_node = graph.trader_node_id("trader:one")
        self.assertEqual(graph.degree(trader_node), 2)

    def test_issuer_trader_count_uses_durable_identities(self):
        first = cluster(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = cluster(
            2,
            trader="trader:two",
            issuer="issuer:one",
            event="event:two",
            timestamp="2015-09-10T14:00:00-04:00",
        )
        graph = build_historical_surveillance_graph((first, second))
        self.assertEqual(graph.issuer_trader_count("issuer:one"), 2)

    def test_disconnected_cases_form_separate_components(self):
        first = cluster(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = cluster(
            2,
            trader="trader:two",
            issuer="issuer:two",
            event="event:two",
            timestamp="2015-09-10T14:00:00-04:00",
        )
        graph = build_historical_surveillance_graph((first, second))
        first_component = graph.connected_component(
            graph.cluster_node_id(first.cluster_id)
        )
        second_component = graph.connected_component(
            graph.cluster_node_id(second.cluster_id)
        )
        self.assertTrue(set(first_component).isdisjoint(second_component))

    def test_graph_hash_is_independent_of_cluster_input_order(self):
        first = cluster(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = cluster(
            2,
            trader="trader:one",
            issuer="issuer:two",
            event="event:two",
            timestamp="2015-09-10T14:00:00-04:00",
        )
        left = build_historical_surveillance_graph((first, second))
        right = build_historical_surveillance_graph((second, first))
        self.assertEqual(left.proof_hash, right.proof_hash)

    def test_multi_source_economic_cluster_remains_one_transaction_node(self):
        first = signature(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = signature(
            2,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T18:00:00Z",
        )
        combined = EconomicTransactionCluster(
            cluster_id="economic:" + "a" * 64,
            signatures=(first, second),
        )
        graph = build_historical_surveillance_graph((combined,))
        self.assertEqual(
            len(graph.nodes_of_kind(
                SurveillanceNodeKind.ECONOMIC_TRANSACTION
            )),
            1,
        )
        self.assertEqual(len(graph.cluster_hashes), 1)

    def test_cluster_spanning_multiple_traders_fails_closed(self):
        first = signature(
            1,
            trader="trader:one",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = signature(
            2,
            trader="trader:two",
            issuer="issuer:one",
            event="event:one",
            timestamp="2015-08-10T18:00:00Z",
        )
        malformed = EconomicTransactionCluster(
            cluster_id="economic:" + "b" * 64,
            signatures=(first, second),
        )
        with self.assertRaisesRegex(ValueError, "multiple durable traders"):
            build_historical_surveillance_graph((malformed,))

    def test_unknown_node_lookup_fails_closed(self):
        graph = build_historical_surveillance_graph(())
        with self.assertRaisesRegex(KeyError, "unknown surveillance node"):
            graph.node("missing")


if __name__ == "__main__":
    unittest.main()
