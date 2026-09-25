import unittest

from historical_mnpi.point_in_time import (
    CutoffPrecision,
    PointInTimeCutoff,
    PointInTimeFeatureSnapshot,
    WalkForwardWindow,
)
from historical_mnpi.retrospective_benchmark import (
    HistoricalOutcomeLabel,
    LabeledHistoricalExample,
    RetrospectiveScoringPolicy,
    evaluate_holdout,
    fit_threshold_on_train,
    run_walk_forward_benchmark,
    score_snapshot,
)
from historical_mnpi.surveillance_features import (
    HistoricalSurveillanceFeatures,
    TradeReleaseRelation,
)
from historical_mnpi.transaction_model import InstrumentType, TradeSide


def snapshot(
    row,
    *,
    cutoff_date,
    cluster_proof_hash,
    exact_lead_seconds=None,
    relation=TradeReleaseRelation.SAME_DAY_OR_OVERLAP,
    trader_event_count=1,
    issuer_trader_count=1,
    notional=None,
):
    graph_hash = (f"{row + 5000:064x}")[-64:]
    feature = HistoricalSurveillanceFeatures(
        cluster_id=f"economic:{row:064x}",
        cluster_proof_hash=cluster_proof_hash,
        trader_entity_id=f"trader:{row}",
        issuer_entity_id=f"issuer:{row}",
        event_id=f"event:{row}",
        graph_proof_hash=graph_hash,
        source_row_count=1,
        trader_event_count=trader_event_count,
        issuer_trader_count=issuer_trader_count,
        connected_component_size=4,
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        exact_trade_timestamp_utc=None,
        trade_window_start=cutoff_date,
        trade_window_end=cutoff_date,
        public_release_window_start=cutoff_date,
        public_release_window_end=cutoff_date,
        exact_lead_seconds=exact_lead_seconds,
        lead_days_min=0,
        lead_days_max=0,
        trade_release_relation=relation,
        currency="USD",
        quantity="100",
        execution_price="10",
        notional=notional,
        multi_source_corroboration=False,
        live_use_allowed=False,
    )
    cutoff = PointInTimeCutoff(
        CutoffPrecision.END_OF_DAY,
        date_value=cutoff_date,
    )
    return PointInTimeFeatureSnapshot(
        target_cluster_id=feature.cluster_id,
        cutoff=cutoff,
        feature=feature,
        eligible_cluster_hashes=(cluster_proof_hash,),
        excluded_future_cluster_hashes=(),
        graph_proof_hash=graph_hash,
        live_use_allowed=False,
    )


def example(
    row,
    *,
    cutoff_date,
    cluster_proof_hash,
    label,
    exact_lead_seconds=None,
    relation=TradeReleaseRelation.SAME_DAY_OR_OVERLAP,
    trader_event_count=1,
    issuer_trader_count=1,
    notional=None,
):
    return LabeledHistoricalExample(
        example_id=f"example:{row}",
        snapshot=snapshot(
            row,
            cutoff_date=cutoff_date,
            cluster_proof_hash=cluster_proof_hash,
            exact_lead_seconds=exact_lead_seconds,
            relation=relation,
            trader_event_count=trader_event_count,
            issuer_trader_count=issuer_trader_count,
            notional=notional,
        ),
        label=label,
    )


class RetrospectiveBenchmarkTests(unittest.TestCase):
    def test_score_is_transparent_and_historical_only(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        snap = snapshot(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            exact_lead_seconds=3600,
            trader_event_count=3,
            issuer_trader_count=2,
            notional="150000",
        )
        score = score_snapshot(snap, policy)
        self.assertEqual(score.score, 10)
        self.assertEqual(
            dict(score.signal_breakdown),
            {
                "ISSUER_NETWORK_BREADTH": 1,
                "LARGE_NOTIONAL": 1,
                "PRE_RELEASE_EXACT": 4,
                "REPEATED_TRADER_EVENTS": 4,
            },
        )
        self.assertFalse(score.live_use_allowed)

    def test_coarse_pre_release_signal_never_invents_exact_timing(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        snap = snapshot(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            relation=TradeReleaseRelation.BEFORE_RELEASE,
        )
        score = score_snapshot(snap, policy)
        self.assertEqual(
            dict(score.signal_breakdown),
            {"PRE_RELEASE_COARSE": 2},
        )

    def test_threshold_fit_uses_training_examples_and_is_order_independent(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        positive = example(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
            trader_event_count=2,
        )
        negative = example(
            2,
            cutoff_date="2015-08-02",
            cluster_proof_hash="b" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        left = fit_threshold_on_train(
            (positive, negative),
            policy=policy,
        )
        right = fit_threshold_on_train(
            (negative, positive),
            policy=policy,
        )
        self.assertEqual(left.proof_hash, right.proof_hash)
        self.assertEqual(left.threshold, 6)
        self.assertEqual(left.balanced_accuracy, "1.000000")

    def test_training_requires_both_outcome_classes(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        positive = example(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
        )
        with self.assertRaisesRegex(ValueError, "both outcome classes"):
            fit_threshold_on_train((positive,), policy=policy)

    def test_holdout_overlap_with_training_is_rejected(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        positive = example(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
        )
        negative = example(
            2,
            cutoff_date="2015-08-02",
            cluster_proof_hash="b" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        fit = fit_threshold_on_train(
            (positive, negative),
            policy=policy,
        )
        with self.assertRaisesRegex(ValueError, "overlap"):
            evaluate_holdout(
                (positive,),
                policy=policy,
                threshold_fit=fit,
            )

    def test_holdout_metrics_are_bound_to_frozen_threshold(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        train_positive = example(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
            trader_event_count=2,
        )
        train_negative = example(
            2,
            cutoff_date="2015-08-02",
            cluster_proof_hash="b" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        fit = fit_threshold_on_train(
            (train_positive, train_negative),
            policy=policy,
        )
        holdout_positive = example(
            3,
            cutoff_date="2015-08-10",
            cluster_proof_hash="c" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=1800,
            trader_event_count=2,
        )
        holdout_negative = example(
            4,
            cutoff_date="2015-08-11",
            cluster_proof_hash="d" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        receipt = evaluate_holdout(
            (holdout_positive, holdout_negative),
            policy=policy,
            threshold_fit=fit,
        )
        self.assertEqual(receipt.true_positive, 1)
        self.assertEqual(receipt.true_negative, 1)
        self.assertEqual(receipt.false_positive, 0)
        self.assertEqual(receipt.false_negative, 0)
        self.assertEqual(receipt.balanced_accuracy, "1.000000")
        self.assertFalse(receipt.live_use_allowed)

    def test_walk_forward_benchmark_enforces_partition_membership(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        train_positive = example(
            1,
            cutoff_date="2015-08-01",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
            trader_event_count=2,
        )
        train_negative = example(
            2,
            cutoff_date="2015-08-02",
            cluster_proof_hash="b" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        eval_positive = example(
            3,
            cutoff_date="2015-08-10",
            cluster_proof_hash="c" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
            trader_event_count=2,
        )
        eval_negative = example(
            4,
            cutoff_date="2015-08-11",
            cluster_proof_hash="d" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        window = WalkForwardWindow(
            train_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-05",
            ),
            evaluation_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-15",
            ),
            train_cluster_hashes=("a" * 64, "b" * 64),
            evaluation_cluster_hashes=("c" * 64, "d" * 64),
        )
        fit, evaluation, receipt = run_walk_forward_benchmark(
            window=window,
            train_examples=(train_positive, train_negative),
            evaluation_examples=(eval_positive, eval_negative),
            policy=policy,
        )
        self.assertEqual(fit.threshold, 6)
        self.assertEqual(evaluation.balanced_accuracy, "1.000000")
        self.assertEqual(receipt.window_hash, window.proof_hash)
        self.assertFalse(receipt.live_use_allowed)

    def test_future_training_snapshot_is_rejected(self):
        policy = RetrospectiveScoringPolicy("policy:v1")
        future = example(
            1,
            cutoff_date="2015-08-10",
            cluster_proof_hash="a" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
            exact_lead_seconds=3600,
        )
        negative = example(
            2,
            cutoff_date="2015-08-02",
            cluster_proof_hash="b" * 64,
            label=HistoricalOutcomeLabel.NEGATIVE_CONTROL,
        )
        eval_positive = example(
            3,
            cutoff_date="2015-08-11",
            cluster_proof_hash="c" * 64,
            label=HistoricalOutcomeLabel.POSITIVE_CASE,
        )
        window = WalkForwardWindow(
            train_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-05",
            ),
            evaluation_cutoff=PointInTimeCutoff(
                CutoffPrecision.END_OF_DAY,
                date_value="2015-08-15",
            ),
            train_cluster_hashes=("a" * 64, "b" * 64),
            evaluation_cluster_hashes=("c" * 64,),
        )
        with self.assertRaisesRegex(ValueError, "beyond train cutoff"):
            run_walk_forward_benchmark(
                window=window,
                train_examples=(future, negative),
                evaluation_examples=(eval_positive,),
                policy=policy,
            )

    def test_policy_cannot_enable_live_use(self):
        with self.assertRaisesRegex(ValueError, "live use"):
            RetrospectiveScoringPolicy(
                "policy:bad",
                live_use_allowed=True,
            )


if __name__ == "__main__":
    unittest.main()
