import unittest
from datetime import date, timedelta

from historical_mnpi.coverage_planner import (
    HistoricalFirstTradeEvent,
    XNYSSession,
    build_coverage_plan,
)
from historical_mnpi.metadata_resolver import (
    ResolutionState,
    resolve_metadata_for_plan,
)
from historical_mnpi.real_corpus_import import (
    import_real_corpus_metadata,
    render_real_corpus_metadata_templates,
)


def sessions(count=60):
    result = []
    day = date(2015, 1, 2)
    while len(result) < count:
        if day.weekday() < 5:
            result.append(XNYSSession(day.isoformat()))
        day += timedelta(days=1)
    return tuple(result)


def complete_files(plan):
    event = plan.events[0]
    announcements = (
        "event_id,timestamp,evidence_id,source_kind,source_name,"
        "proves_first_public_release,data_class\n"
        f"{event.event_id},{event.first_trade_date}T16:00:00-04:00,"
        "announcement:1,ISSUER_PUBLIC_RELEASE,Synthetic issuer release,"
        "true,PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
    )
    listings = (
        "symbol,session_date,primary_exchange,evidence_id,source_kind,"
        "source_name,data_class\n"
        + "".join(
            f"{item.symbol},{item.session_date},N,"
            f"listing:{item.symbol}:{item.session_date},"
            "NYSE_DAILY_TAQ_MASTER,Synthetic TAQ Master,"
            "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
            for item in plan.symbol_date_requirements
        )
    )
    shares = (
        "symbol,effective_date,shares_outstanding,"
        "public_availability_timestamp,evidence_id,source_kind,"
        "source_name,data_class\n"
        + "".join(
            f"{item.symbol},{item.session_date},1000000,"
            f"{item.session_date}T08:00:00-04:00,"
            f"shares:{item.symbol}:{item.session_date},"
            "NYSE_DAILY_TAQ_MASTER,Synthetic TAQ Master,"
            "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
            for item in plan.symbol_date_requirements
        )
    )
    controls = (
        "control_date,universe_id,symbols,availability_timestamp,"
        "complete_pre_event_covariates,evidence_id,source_kind,"
        "source_name,data_class\n"
        + "".join(
            f"{day},controls:{day},XYZ|DEF,"
            f"{day}T08:00:00-04:00,true,controls:{day},"
            "POINT_IN_TIME_CONTROL_UNIVERSE,Synthetic controls,"
            "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
            for day in plan.control_dates
        )
    )
    market = (
        "source_family,session_date\n"
        + "".join(
            f"{item.source_family.value},{item.session_date}\n"
            for item in plan.source_date_requirements
        )
    )
    return {
        "announcement_metadata.csv": announcements,
        "listing_metadata.csv": listings,
        "shares_metadata.csv": shares,
        "control_metadata.csv": controls,
        "market_source_dates.csv": market,
    }


class RealCorpusImportTests(unittest.TestCase):
    def test_header_only_templates_cover_all_five_files(self):
        templates = render_real_corpus_metadata_templates()
        self.assertEqual(
            set(templates),
            {
                "announcement_metadata.csv",
                "listing_metadata.csv",
                "shares_metadata.csv",
                "control_metadata.csv",
                "market_source_dates.csv",
            },
        )
        for text in templates.values():
            self.assertEqual(len(text.strip().splitlines()), 1)

    def test_complete_import_closes_one_event_plan(self):
        calendar = sessions()
        event = HistoricalFirstTradeEvent(
            "event:one",
            "ABC",
            calendar[40].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        imported = import_real_corpus_metadata(
            complete_files(plan)
        )
        bundle = resolve_metadata_for_plan(
            plan,
            announcement_evidence=imported.announcements,
            listing_evidence=imported.listings,
            shares_evidence=imported.shares,
            control_evidence=imported.controls,
            market_source_dates=imported.market_source_dates,
        )
        self.assertTrue(bundle.ready_metadata_gates)
        final = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
            evidence=bundle.coverage_evidence(),
        )
        self.assertTrue(final.ready)
        self.assertEqual(
            bundle.announcements[0].state,
            ResolutionState.RESOLVED,
        )

    def test_import_counts_are_deterministic(self):
        calendar = sessions()
        event = HistoricalFirstTradeEvent(
            "event:one",
            "ABC",
            calendar[40].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        imported = import_real_corpus_metadata(
            complete_files(plan)
        )
        counts = imported.counts()
        self.assertEqual(counts["announcement_rows"], 1)
        self.assertEqual(
            counts["listing_rows"],
            len(plan.symbol_date_requirements),
        )
        self.assertEqual(
            counts["shares_rows"],
            len(plan.symbol_date_requirements),
        )
        self.assertEqual(counts["control_rows"], 1)
        self.assertEqual(
            counts["market_source_date_rows"],
            len(plan.source_date_requirements),
        )
        self.assertEqual(len(counts["import_hash"]), 64)
        self.assertFalse(counts["live_use_allowed"])

    def test_missing_file_is_rejected(self):
        templates = render_real_corpus_metadata_templates()
        del templates["shares_metadata.csv"]
        with self.assertRaisesRegex(ValueError, "missing metadata import files"):
            import_real_corpus_metadata(templates)

    def test_unexpected_file_is_rejected(self):
        templates = render_real_corpus_metadata_templates()
        templates["passwords.csv"] = "password\nsecret\n"
        with self.assertRaisesRegex(ValueError, "unexpected metadata import files"):
            import_real_corpus_metadata(templates)

    def test_header_order_is_exact_and_fail_closed(self):
        templates = render_real_corpus_metadata_templates()
        templates["announcement_metadata.csv"] = (
            "timestamp,event_id,evidence_id,source_kind,source_name,"
            "proves_first_public_release,data_class\n"
        )
        with self.assertRaisesRegex(ValueError, "headers must exactly equal"):
            import_real_corpus_metadata(templates)

    def test_boolean_values_do_not_accept_truthy_shorthand(self):
        templates = render_real_corpus_metadata_templates()
        templates["announcement_metadata.csv"] += (
            "event:one,2015-08-10T16:00:00-04:00,"
            "announcement:1,ISSUER_PUBLIC_RELEASE,Issuer release,"
            "yes,PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
        )
        with self.assertRaisesRegex(ValueError, "exactly true or false"):
            import_real_corpus_metadata(templates)

    def test_prohibited_data_class_is_rejected(self):
        templates = render_real_corpus_metadata_templates()
        templates["announcement_metadata.csv"] += (
            "event:one,2015-08-10T16:00:00-04:00,"
            "announcement:1,ISSUER_PUBLIC_RELEASE,Issuer release,"
            "true,LIVE_STOLEN_INFORMATION\n"
        )
        with self.assertRaisesRegex(ValueError, "prohibited"):
            import_real_corpus_metadata(templates)

    def test_edgar_proxy_cannot_be_imported_as_exact_release(self):
        templates = render_real_corpus_metadata_templates()
        templates["announcement_metadata.csv"] += (
            "event:one,2015-08-10T16:00:00-04:00,"
            "announcement:1,EDGAR_ACCEPTANCE_DATETIME_PROXY,EDGAR,"
            "true,PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
        )
        with self.assertRaisesRegex(ValueError, "only a public proxy"):
            import_real_corpus_metadata(templates)

    def test_blank_required_fields_are_rejected(self):
        templates = render_real_corpus_metadata_templates()
        templates["listing_metadata.csv"] += (
            ",2015-08-10,N,listing:1,NYSE_DAILY_TAQ_MASTER,"
            "TAQ Master,PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
        )
        with self.assertRaisesRegex(ValueError, "symbol is required"):
            import_real_corpus_metadata(templates)

    def test_blank_rows_are_rejected(self):
        templates = render_real_corpus_metadata_templates()
        templates["market_source_dates.csv"] += ",\n"
        with self.assertRaisesRegex(ValueError, "blank rows are not allowed"):
            import_real_corpus_metadata(templates)


if __name__ == "__main__":
    unittest.main()
