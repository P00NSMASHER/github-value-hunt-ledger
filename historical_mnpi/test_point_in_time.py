import unittest

from historical_mnpi.economic_dedup import (
    EconomicTransactionCluster,
    EconomicTransactionSignature,
)
from historical_mnpi.point_in_time import (
    CutoffPrecision,
    PointInTimeControlPlan,
    PointInTimeCutoff,
    build_point_in_time_snapshot,
    build_walk_forward_window,
    cluster_available_by,
    signature_available_by,
)
from historical_mnpi.test_review_queue import fixture
from historical_mnpi.transaction_model import (
    InstrumentType,
    TimePrecision,
    TradeSide,
)


def signature(
    row,
    *,
    event,
    timestamp=None,
    trade_date=None,
    range_start=None,
    range_end=None,
):
    precision = (
        TimePrecision.EXACT_TIMESTAMP
        if timestamp is not None
        else TimePrecision.DATE_ONLY
        if trade_date is not None
        else TimePrecision.DATE_RANGE
    )
    return EconomicTransactionSignature(
        normalized_row_hash=(f"{row:064x}")[-64:],
        review_item_hash=(f"{row + 1000:064x}")[-64:],
        trader_entity_id=f"trader:{row}",
        issuer_entity_id="issuer:review:target",
        event_id=event,
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        time_precision=precision,
        trade_timestamp=timestamp,
        trade_date=trade_date,
        trade_date_range_start=range_start,
        trade_date_range_end=range_end,
        currency="USD",
        quantity="100",
        execution_price="10",
    )


def cluster(row, signature):
    return EconomicTransactionCluster(
        cluster_id=f"economic:{row:064x}",
        signatures=(signature,),
    )


class PointInTimeTests(unittest.TestCase):
    def test_intraday_cutoff_includes_prior_exact_timestamp(self):
        sig = signature(
            1,
            event="event:one",
            timestamp="2015-08-10T13:00:00-04:00",
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T14:00:00-04:00",
        )
        self.assertTrue(signature_available_by(sig, cutoff))

    def test_intraday_cutoff_excludes_same_day_date_only_record(self):
        sig = signature(
            1,
            event="event:one",
            trade_date="2015-08-10",
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T14:00:00-04:00",
        )
        self.assertFalse(signature_available_by(sig, cutoff))

    def test_end_of_day_cutoff_includes_same_day_date_only_record(self):
        sig = signature(
            1,
            event="event:one",
            trade_date="2015-08-10",
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.END_OF_DAY,
            date_value="2015-08-10",
        )
        self.assertTrue(signature_available_by(sig, cutoff))

    def test_intraday_cutoff_excludes_range_ending_same_day(self):
        sig = signature(
            1,
            event="event:one",
            range_start="2015-08-08",
            range_end="2015-08-10",
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T23:00:00-04:00",
        )
        self.assertFalse(signature_available_by(sig, cutoff))

    def test_cluster_requires_all_source_signatures_available(self):
        exact = signature(
            1,
            event="event:one",
            timestamp="2015-08-10T13:00:00-04:00",
        )
        coarse = signature(
            2,
            event="event:one",
            trade_date="2015-08-10",
        )
        combined = EconomicTransactionCluster(
            cluster_id="economic:" + "a" * 64,
            signatures=(exact, coarse),
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T14:00:00-04:00",
        )
        self.assertFalse(cluster_available_by(combined, cutoff))

    def test_snapshot_excludes_future_cluster_from_graph_features(self):
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
        target = cluster(
            1,
            signature(
                1,
                event=event.event_id,
                timestamp="2015-08-10T14:00:00-04:00",
            ),
        )
        future = cluster(
            2,
            signature(
                2,
                event=event.event_id,
                timestamp="2015-08-11T14:00:00-04:00",
            ),
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T15:00:00-04:00",
        )
        snapshot = build_point_in_time_snapshot(
            target,
            clusters=(target, future),
            events=events,
            cutoff=cutoff,
        )
        self.assertIn(target.proof_hash, snapshot.eligible_cluster_hashes)
        self.assertIn(
            future.proof_hash,
            snapshot.excluded_future_cluster_hashes,
        )
        self.assertEqual(snapshot.feature.trader_event_count, 1)
        self.assertFalse(snapshot.live_use_allowed)

    def test_target_not_available_by_cutoff_fails_closed(self):
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
        target = cluster(
            1,
            signature(
                1,
                event=event.event_id,
                timestamp="2015-08-10T16:00:00-04:00",
            ),
        )
        cutoff = PointInTimeCutoff(
            CutoffPrecision.EXACT_TIMESTAMP,
            timestamp="2015-08-10T15:00:00-04:00",
        )
        with self.assertRaisesRegex(ValueError, "not available"):
            build_point_in_time_snapshot(
                target,
                clusters=(target,),
                events=events,
                cutoff=cutoff,
            )

    def test_walk_forward_window_has_no_train_evaluation_overlap(self):
        first = cluster(
            1,
            signature(
                1,
                event="event:one",
                trade_date="2015-08-01",
            ),
        )
        second = cluster(
            2,
            signature(
                2,
                event="event:one",
                trade_date="2015-08-10",
            ),
        )
        third = cluster(
            3,
            signature(
                3,
                event="event:one",
                trade_date="2015-08-20",
            ),
        )
        window = build_walk_forward_window(
            (first, second, third),
            train_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-05",
            ),
            evaluation_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-15",
            ),
        )
        self.assertEqual(window.train_cluster_hashes, (first.proof_hash,))
        self.assertEqual(
            window.evaluation_cluster_hashes,
            (second.proof_hash,),
        )
        self.assertNotIn(third.proof_hash, window.train_cluster_hashes)
        self.assertNotIn(third.proof_hash, window.evaluation_cluster_hashes)

    def test_control_plan_requires_chronological_unique_cutoffs(self):
        first = PointInTimeCutoff(
            CutoffPrecision.END_OF_DAY,
            date_value="2015-08-01",
        )
        second = PointInTimeCutoff(
            CutoffPrecision.END_OF_DAY,
            date_value="2015-08-02",
        )
        plan = PointInTimeControlPlan((first, second))
        self.assertEqual(len(plan.proof_hash), 64)

        with self.assertRaisesRegex(ValueError, "chronological"):
            PointInTimeControlPlan((second, first))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            PointInTimeControlPlan((first, first))


if __name__ == "__main__":
    unittest.main()
