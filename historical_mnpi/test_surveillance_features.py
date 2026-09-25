import unittest

from historical_mnpi.economic_dedup import (
    EconomicTransactionCluster,
    EconomicTransactionSignature,
)
from historical_mnpi.event_model import InformationEvent, TemporalBoundary
from historical_mnpi.surveillance_features import (
    TradeReleaseRelation,
    build_feature_set,
    build_surveillance_features,
)
from historical_mnpi.surveillance_graph import build_historical_surveillance_graph
from historical_mnpi.test_review_queue import fixture
from historical_mnpi.transaction_model import (
    InstrumentType,
    TimePrecision,
    TradeSide,
)


def sig(
    row,
    *,
    trader,
    issuer,
    event,
    timestamp=None,
    trade_date=None,
    quantity="100",
    price="10",
):
    precision = (
        TimePrecision.EXACT_TIMESTAMP
        if timestamp is not None
        else TimePrecision.DATE_ONLY
    )
    return EconomicTransactionSignature(
        normalized_row_hash=(f"{row:064x}")[-64:],
        review_item_hash=(f"{row + 1000:064x}")[-64:],
        trader_entity_id=trader,
        issuer_entity_id=issuer,
        event_id=event,
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        time_precision=precision,
        trade_timestamp=timestamp,
        trade_date=trade_date,
        currency="USD",
        quantity=quantity,
        execution_price=price,
    )


def cl(row, signature):
    return EconomicTransactionCluster(
        cluster_id=f"economic:{row:064x}",
        signatures=(signature,),
    )


class SurveillanceFeatureTests(unittest.TestCase):
    def test_exact_lead_time_and_notional(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        cluster = cl(
            1,
            sig(
                1,
                trader="trader:one",
                issuer="issuer:review:target",
                event=event.event_id,
                timestamp="2015-08-10T14:00:00-04:00",
                quantity="100",
                price="10.5",
            ),
        )
        graph = build_historical_surveillance_graph((cluster,))
        features = build_surveillance_features(
            cluster,
            graph=graph,
            events=events,
        )
        self.assertEqual(features.exact_lead_seconds, 7200)
        self.assertEqual(features.notional, "1050")
        self.assertEqual(
            features.trade_release_relation,
            TradeReleaseRelation.SAME_DAY_OR_OVERLAP,
        )
        self.assertFalse(features.live_use_allowed)

    def test_date_only_precision_does_not_invent_exact_lead_time(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        cluster = cl(
            1,
            sig(
                1,
                trader="trader:one",
                issuer="issuer:review:target",
                event=event.event_id,
                trade_date="2015-08-09",
            ),
        )
        graph = build_historical_surveillance_graph((cluster,))
        features = build_surveillance_features(
            cluster,
            graph=graph,
            events=events,
        )
        self.assertIsNone(features.exact_lead_seconds)
        self.assertEqual(features.lead_days_min, 1)
        self.assertEqual(features.lead_days_max, 1)
        self.assertEqual(
            features.trade_release_relation,
            TradeReleaseRelation.BEFORE_RELEASE,
        )

    def test_graph_counts_reflect_repeated_historical_events(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            _record,
            _candidate,
            refs,
        ) = fixture()
        second_event = InformationEvent(
            event_id="event:review:002",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=event.event_type,
            issuer_ids=event.issuer_ids,
            information_summary="Second historical public event",
            public_release=TemporalBoundary(
                ref=refs[next(
                    role for role in refs
                    if role.value == "PUBLIC_RELEASE"
                )],
                timestamp="2015-09-10T16:00:00-04:00",
            ),
        )
        events.register(
            second_event,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        first = cl(
            1,
            sig(
                1,
                trader="trader:one",
                issuer="issuer:review:target",
                event=event.event_id,
                timestamp="2015-08-10T14:00:00-04:00",
            ),
        )
        second = cl(
            2,
            sig(
                2,
                trader="trader:one",
                issuer="issuer:review:target",
                event=second_event.event_id,
                timestamp="2015-09-10T14:00:00-04:00",
            ),
        )
        graph = build_historical_surveillance_graph((first, second))
        features = build_surveillance_features(
            second,
            graph=graph,
            events=events,
        )
        self.assertEqual(features.trader_event_count, 2)
        self.assertEqual(features.issuer_trader_count, 1)
        self.assertGreaterEqual(features.connected_component_size, 6)

    def test_multi_source_cluster_records_corroboration_without_double_counting(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        first = sig(
            1,
            trader="trader:one",
            issuer="issuer:review:target",
            event=event.event_id,
            timestamp="2015-08-10T14:00:00-04:00",
        )
        second = sig(
            2,
            trader="trader:one",
            issuer="issuer:review:target",
            event=event.event_id,
            timestamp="2015-08-10T18:00:00Z",
        )
        cluster = EconomicTransactionCluster(
            cluster_id="economic:" + "c" * 64,
            signatures=(first, second),
        )
        graph = build_historical_surveillance_graph((cluster,))
        features = build_surveillance_features(
            cluster,
            graph=graph,
            events=events,
        )
        self.assertEqual(features.source_row_count, 2)
        self.assertTrue(features.multi_source_corroboration)
        self.assertEqual(features.trader_event_count, 1)

    def test_disagreement_in_economics_becomes_missing_consensus(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        first = sig(
            1,
            trader="trader:one",
            issuer="issuer:review:target",
            event=event.event_id,
            timestamp="2015-08-10T14:00:00-04:00",
            quantity="100",
        )
        second = sig(
            2,
            trader="trader:one",
            issuer="issuer:review:target",
            event=event.event_id,
            timestamp="2015-08-10T18:00:00Z",
            quantity="200",
        )
        cluster = EconomicTransactionCluster(
            cluster_id="economic:" + "d" * 64,
            signatures=(first, second),
        )
        graph = build_historical_surveillance_graph((cluster,))
        features = build_surveillance_features(
            cluster,
            graph=graph,
            events=events,
        )
        self.assertIsNone(features.quantity)
        self.assertIsNone(features.notional)

    def test_feature_body_excludes_later_legal_outcomes(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        cluster = cl(
            1,
            sig(
                1,
                trader="trader:one",
                issuer="issuer:review:target",
                event=event.event_id,
                timestamp="2015-08-10T14:00:00-04:00",
            ),
        )
        graph = build_historical_surveillance_graph((cluster,))
        body = build_surveillance_features(
            cluster,
            graph=graph,
            events=events,
        ).feature_body
        forbidden = {
            "fact_status",
            "proceeding_status",
            "convicted",
            "settled",
            "judgment",
            "documented_profit",
        }
        self.assertTrue(forbidden.isdisjoint(body))

    def test_feature_set_is_deterministically_ordered(self):
        (
            _sources,
            _manifest,
            _cases,
            events,
            _case,
            event,
            _record,
            _candidate,
            _refs,
        ) = fixture()
        first = cl(
            1,
            sig(
                1,
                trader="trader:one",
                issuer="issuer:review:target",
                event=event.event_id,
                timestamp="2015-08-10T14:00:00-04:00",
            ),
        )
        second = cl(
            2,
            sig(
                2,
                trader="trader:two",
                issuer="issuer:review:target",
                event=event.event_id,
                timestamp="2015-08-10T13:00:00-04:00",
            ),
        )
        graph = build_historical_surveillance_graph((second, first))
        result = build_feature_set(
            (second, first),
            graph=graph,
            events=events,
        )
        self.assertEqual(
            tuple(item.cluster_id for item in result),
            tuple(sorted((first.cluster_id, second.cluster_id))),
        )


if __name__ == "__main__":
    unittest.main()
