import json
import unittest
from datetime import date, timedelta

from historical_mnpi.coverage_planner import (
    BASELINE_SESSIONS,
    CoverageEvidence,
    CoverageGate,
    HistoricalFirstTradeEvent,
    MarketSourceFamily,
    XNYSSession,
    build_coverage_plan,
)


def sessions(count=120):
    result = []
    day = date(2015, 1, 2)
    while len(result) < count:
        if day.weekday() < 5:
            result.append(XNYSSession(day.isoformat()))
        day += timedelta(days=1)
    return tuple(result)


def corpus_174_72(calendar):
    usable = calendar[BASELINE_SESSIONS:BASELINE_SESSIONS + 72]
    return tuple(
        HistoricalFirstTradeEvent(
            event_id=f"event:{index:03d}",
            symbol=f"S{index:03d}",
            first_trade_date=usable[index % 72].session_date,
        )
        for index in range(174)
    )


def complete_evidence(plan):
    return CoverageEvidence(
        exact_announcement_event_ids=frozenset(
            plan.announcement_event_ids
        ),
        market_source_dates=frozenset(
            item.key for item in plan.source_date_requirements
        ),
        listing_symbol_dates=frozenset(
            item.key for item in plan.symbol_date_requirements
        ),
        shares_symbol_dates=frozenset(
            item.key for item in plan.symbol_date_requirements
        ),
        control_dates=frozenset(plan.control_dates),
    )


class CoveragePlannerTests(unittest.TestCase):
    def test_real_corpus_shape_matches_174_3828_72_contract(self):
        calendar = sessions()
        events = corpus_174_72(calendar)
        plan = build_coverage_plan(
            events,
            xnys_sessions=calendar,
        )
        self.assertEqual(len(plan.events), 174)
        self.assertEqual(
            len(plan.symbol_date_requirements),
            3828,
        )
        self.assertEqual(len(plan.announcement_event_ids), 174)
        self.assertEqual(len(plan.control_dates), 72)

        exact_missing = [
            item for item in plan.unresolved_gates
            if item.gate is CoverageGate.EXACT_ANNOUNCEMENT
        ]
        shares_missing = [
            item for item in plan.unresolved_gates
            if item.gate is CoverageGate.SHARES_OUTSTANDING
        ]
        controls_missing = [
            item for item in plan.unresolved_gates
            if item.gate is CoverageGate.CONTROL_METADATA
        ]
        self.assertEqual(len(exact_missing), 174)
        self.assertEqual(len(shares_missing), 3828)
        self.assertEqual(len(controls_missing), 72)
        self.assertFalse(plan.ready)

    def test_source_date_requirements_are_deduplicated(self):
        calendar = sessions(50)
        event_day = calendar[30].session_date
        events = (
            HistoricalFirstTradeEvent("event:a", "AAA", event_day),
            HistoricalFirstTradeEvent("event:b", "BBB", event_day),
        )
        plan = build_coverage_plan(
            events,
            xnys_sessions=calendar,
        )
        required_dates = {
            item.session_date for item in plan.symbol_date_requirements
        }
        self.assertEqual(len(required_dates), 22)
        self.assertEqual(
            len(plan.source_date_requirements),
            22 * len(MarketSourceFamily),
        )

    def test_unsupported_early_close_is_skipped_from_baseline(self):
        base = list(sessions(50))
        target_index = 35
        skipped_index = 25
        base[skipped_index] = XNYSSession(
            base[skipped_index].session_date,
            is_early_close=True,
            supported_for_baseline=False,
        )
        event = HistoricalFirstTradeEvent(
            "event:early-close-test",
            "ABC",
            base[target_index].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=tuple(base),
        )
        event_plan = plan.event_plans[0]
        self.assertEqual(
            len(event_plan.baseline_session_dates),
            BASELINE_SESSIONS,
        )
        self.assertIn(
            base[skipped_index].session_date,
            event_plan.skipped_early_close_dates,
        )
        self.assertNotIn(
            base[skipped_index].session_date,
            event_plan.baseline_session_dates,
        )

    def test_missing_calendar_depth_fails_closed(self):
        calendar = sessions(10)
        event = HistoricalFirstTradeEvent(
            "event:shallow",
            "ABC",
            calendar[-1].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        gates = [
            item for item in plan.unresolved_gates
            if item.gate is CoverageGate.BASELINE_CALENDAR
        ]
        self.assertEqual(len(gates), 1)
        self.assertIn("ONLY_9_OF_21", gates[0].detail)

    def test_event_session_missing_from_calendar_is_explicit_gate(self):
        calendar = sessions(30)
        event = HistoricalFirstTradeEvent(
            "event:missing-session",
            "ABC",
            "2016-01-04",
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        gate = next(
            item for item in plan.unresolved_gates
            if item.gate is CoverageGate.BASELINE_CALENDAR
        )
        self.assertEqual(
            gate.detail,
            "EVENT_SESSION_NOT_IN_SUPPLIED_XNYS_CALENDAR",
        )

    def test_complete_synthetic_fixture_closes_all_real_data_gates(self):
        calendar = sessions(60)
        event = HistoricalFirstTradeEvent(
            "event:complete",
            "ABC",
            calendar[40].session_date,
        )
        initial = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        final = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
            evidence=complete_evidence(initial),
        )
        self.assertTrue(final.ready)
        self.assertEqual(final.unresolved_gates, ())
        self.assertTrue(all(
            value == 0
            for value in final.summary()["unresolved_by_gate"].values()
        ))

    def test_artifact_bundle_has_exact_contract_filenames(self):
        calendar = sessions(60)
        event = HistoricalFirstTradeEvent(
            "event:artifact",
            "ABC",
            calendar[40].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        artifacts = plan.render_artifacts()
        self.assertEqual(
            set(artifacts),
            {
                "event_coverage_plan.csv",
                "symbol_date_requirements.csv",
                "source_date_requirements.csv",
                "announcement_timestamp_requirements.csv",
                "unresolved_gates.csv",
                "coverage_summary.json",
                "acquisition_import_plan.json",
            },
        )
        summary = json.loads(artifacts["coverage_summary.json"])
        acquisition = json.loads(
            artifacts["acquisition_import_plan.json"]
        )
        self.assertFalse(summary["ready"])
        self.assertFalse(acquisition["fetch_or_purchase_performed"])
        self.assertEqual(acquisition["scope"], summary["scope"])

    def test_duplicate_event_ids_are_rejected(self):
        calendar = sessions(50)
        day = calendar[30].session_date
        events = (
            HistoricalFirstTradeEvent("event:dup", "AAA", day),
            HistoricalFirstTradeEvent("event:dup", "BBB", day),
        )
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            build_coverage_plan(
                events,
                xnys_sessions=calendar,
            )

    def test_plan_hash_is_order_independent(self):
        calendar = sessions(60)
        day = calendar[40].session_date
        first = HistoricalFirstTradeEvent("event:a", "AAA", day)
        second = HistoricalFirstTradeEvent("event:b", "BBB", day)
        left = build_coverage_plan(
            (first, second),
            xnys_sessions=calendar,
        )
        right = build_coverage_plan(
            (second, first),
            xnys_sessions=reversed(calendar),
        )
        self.assertEqual(left.proof_hash, right.proof_hash)


if __name__ == "__main__":
    unittest.main()
