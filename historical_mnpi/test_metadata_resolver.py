import unittest
from datetime import date, datetime, timedelta, timezone

from historical_mnpi.coverage_planner import (
    BASELINE_SESSIONS,
    CoverageEvidence,
    HistoricalFirstTradeEvent,
    MarketSourceFamily,
    XNYSSession,
    build_coverage_plan,
)
from historical_mnpi.metadata_resolver import (
    AnnouncementTimestampEvidence,
    ControlUniverseEvidence,
    ListingExchangeEvidence,
    MetadataDataClass,
    MetadataEvidenceRef,
    MetadataSourceKind,
    ResolutionState,
    SharesOutstandingEvidence,
    resolve_announcement_timestamp,
    resolve_control_universe,
    resolve_listing_exchange,
    resolve_metadata_for_plan,
    resolve_shares_outstanding,
    validate_metadata_contract_fields,
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


def ref(
    evidence_id,
    kind,
    *,
    data_class=MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
):
    return MetadataEvidenceRef(
        evidence_id=evidence_id,
        source_kind=kind,
        source_name="Synthetic public metadata fixture",
        data_class=data_class,
    )


class MetadataResolverTests(unittest.TestCase):
    def test_edgar_acceptance_datetime_is_proxy_only(self):
        evidence = AnnouncementTimestampEvidence(
            event_id="event:one",
            timestamp="2015-08-10T16:01:02-04:00",
            evidence=ref(
                "announcement:edgar",
                MetadataSourceKind.EDGAR_ACCEPTANCE_DATETIME_PROXY,
            ),
            proves_first_public_release=False,
        )
        result = resolve_announcement_timestamp(
            "event:one",
            (evidence,),
        )
        self.assertEqual(result.state, ResolutionState.UNRESOLVED)
        self.assertIsNone(result.timestamp_utc)
        self.assertEqual(
            result.rejection_reasons,
            ("EDGAR_ACCEPTANCE_IS_PROXY_ONLY",),
        )

    def test_edgar_proxy_cannot_be_marked_as_first_public_proof(self):
        with self.assertRaisesRegex(ValueError, "only a public proxy"):
            AnnouncementTimestampEvidence(
                event_id="event:one",
                timestamp="2015-08-10T16:01:02-04:00",
                evidence=ref(
                    "announcement:bad-edgar",
                    MetadataSourceKind.EDGAR_ACCEPTANCE_DATETIME_PROXY,
                ),
                proves_first_public_release=True,
            )

    def test_exact_first_public_timestamp_resolves(self):
        evidence = AnnouncementTimestampEvidence(
            event_id="event:one",
            timestamp="2015-08-10T16:00:00-04:00",
            evidence=ref(
                "announcement:issuer",
                MetadataSourceKind.ISSUER_PUBLIC_RELEASE,
            ),
            proves_first_public_release=True,
        )
        result = resolve_announcement_timestamp(
            "event:one",
            (evidence,),
        )
        self.assertEqual(result.state, ResolutionState.RESOLVED)
        self.assertEqual(
            result.timestamp_utc,
            "2015-08-10T20:00:00+00:00",
        )

    def test_conflicting_first_public_timestamps_fail_closed(self):
        first = AnnouncementTimestampEvidence(
            event_id="event:one",
            timestamp="2015-08-10T16:00:00-04:00",
            evidence=ref(
                "announcement:first",
                MetadataSourceKind.ISSUER_PUBLIC_RELEASE,
            ),
            proves_first_public_release=True,
        )
        second = AnnouncementTimestampEvidence(
            event_id="event:one",
            timestamp="2015-08-10T16:01:00-04:00",
            evidence=ref(
                "announcement:second",
                MetadataSourceKind.OFFICIAL_PUBLIC_NEWSWIRE,
            ),
            proves_first_public_release=True,
        )
        result = resolve_announcement_timestamp(
            "event:one",
            (first, second),
        )
        self.assertEqual(result.state, ResolutionState.CONFLICT)
        self.assertIsNone(result.timestamp_utc)

    def test_taq_master_resolves_historical_primary_exchange(self):
        evidence = ListingExchangeEvidence(
            symbol="abc",
            session_date="2015-08-10",
            primary_exchange="n",
            evidence=ref(
                "listing:taq",
                MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            ),
        )
        result = resolve_listing_exchange(
            "ABC",
            "2015-08-10",
            (evidence,),
        )
        self.assertEqual(result.state, ResolutionState.RESOLVED)
        self.assertEqual(result.primary_exchange, "N")

    def test_listing_conflict_fails_closed(self):
        first = ListingExchangeEvidence(
            "ABC",
            "2015-08-10",
            "N",
            ref(
                "listing:a",
                MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            ),
        )
        second = ListingExchangeEvidence(
            "ABC",
            "2015-08-10",
            "Q",
            ref(
                "listing:b",
                MetadataSourceKind.OFFICIAL_LISTING_HISTORY,
            ),
        )
        result = resolve_listing_exchange(
            "ABC",
            "2015-08-10",
            (first, second),
        )
        self.assertEqual(result.state, ResolutionState.CONFLICT)
        self.assertIsNone(result.primary_exchange)

    def test_future_filed_shares_are_rejected_for_earlier_session(self):
        future = SharesOutstandingEvidence(
            symbol="ABC",
            effective_date="2015-08-01",
            shares_outstanding="1000000",
            public_availability_timestamp="2015-08-12T09:00:00-04:00",
            evidence=ref(
                "shares:future-filed",
                MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
            ),
        )
        result = resolve_shares_outstanding(
            "ABC",
            "2015-08-10",
            (future,),
        )
        self.assertEqual(result.state, ResolutionState.UNRESOLVED)
        self.assertIsNone(result.shares_outstanding)
        self.assertEqual(
            result.rejected_future_evidence_hashes,
            (future.proof_hash,),
        )

    def test_latest_point_in_time_shares_fact_resolves(self):
        older = SharesOutstandingEvidence(
            "ABC",
            "2015-07-01",
            "900000",
            "2015-07-01T17:00:00-04:00",
            ref(
                "shares:older",
                MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
            ),
        )
        latest = SharesOutstandingEvidence(
            "ABC",
            "2015-08-01",
            "1000000",
            "2015-08-01T17:00:00-04:00",
            ref(
                "shares:latest",
                MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            ),
        )
        result = resolve_shares_outstanding(
            "ABC",
            "2015-08-10",
            (older, latest),
        )
        self.assertEqual(result.state, ResolutionState.RESOLVED)
        self.assertEqual(result.shares_outstanding, "1000000")
        self.assertEqual(result.effective_date, "2015-08-01")

    def test_samplefirms_without_availability_timestamp_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "requires a point-in-time availability timestamp",
        ):
            ControlUniverseEvidence(
                control_date="2015-08-10",
                universe_id="SampleFirms",
                symbols=("AAA", "BBB"),
                availability_timestamp=None,
                complete_pre_event_covariates=True,
                evidence=ref(
                    "controls:samplefirms",
                    MetadataSourceKind.RETROSPECTIVE_SAMPLE_FIRMS,
                ),
            )

    def test_control_universe_requires_complete_pre_event_covariates(self):
        evidence = ControlUniverseEvidence(
            control_date="2015-08-10",
            universe_id="SampleFirms",
            symbols=("AAA", "BBB"),
            availability_timestamp="2015-08-10T08:00:00-04:00",
            complete_pre_event_covariates=False,
            evidence=ref(
                "controls:incomplete",
                MetadataSourceKind.RETROSPECTIVE_SAMPLE_FIRMS,
            ),
        )
        result = resolve_control_universe(
            "2015-08-10",
            (evidence,),
        )
        self.assertEqual(result.state, ResolutionState.UNRESOLVED)
        self.assertIn(
            "INCOMPLETE_PRE_EVENT_COVARIATES",
            result.rejection_reasons,
        )

    def test_point_in_time_control_universe_resolves(self):
        evidence = ControlUniverseEvidence(
            control_date="2015-08-10",
            universe_id="controls:2015-08-10",
            symbols=("AAA", "BBB"),
            availability_timestamp="2015-08-10T08:00:00-04:00",
            complete_pre_event_covariates=True,
            evidence=ref(
                "controls:pit",
                MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE,
            ),
        )
        result = resolve_control_universe(
            "2015-08-10",
            (evidence,),
        )
        self.assertEqual(result.state, ResolutionState.RESOLVED)
        self.assertEqual(result.symbols, ("AAA", "BBB"))

    def test_prohibited_data_classes_are_rejected_at_contract_boundary(self):
        for data_class in (
            MetadataDataClass.LIVE_STOLEN_INFORMATION,
            MetadataDataClass.LEAKED_CREDENTIALS,
            MetadataDataClass.ACCIDENTAL_PRIVATE_DISCLOSURE,
            MetadataDataClass.UNAUTHORIZED_PRIVATE_DATA,
        ):
            with self.subTest(data_class=data_class):
                with self.assertRaisesRegex(
                    ValueError,
                    "prohibited",
                ):
                    ref(
                        "prohibited:" + data_class.value,
                        MetadataSourceKind.ISSUER_PUBLIC_RELEASE,
                        data_class=data_class,
                    )

    def test_credential_like_contract_fields_are_rejected(self):
        for field_name in (
            "password",
            "api_key",
            "refresh_token",
            "private_key_pem",
            "session_cookie",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    "credential-like",
                ):
                    validate_metadata_contract_fields(
                        ("symbol", field_name)
                    )

    def test_empty_real_corpus_bundle_reproduces_zero_readiness_counts(self):
        calendar = sessions()
        events = corpus_174_72(calendar)
        plan = build_coverage_plan(
            events,
            xnys_sessions=calendar,
        )
        bundle = resolve_metadata_for_plan(plan)
        self.assertEqual(
            sum(
                item.state is ResolutionState.RESOLVED
                for item in bundle.announcements
            ),
            0,
        )
        self.assertEqual(len(bundle.announcements), 174)
        self.assertEqual(len(bundle.listings), 3828)
        self.assertEqual(len(bundle.shares), 3828)
        self.assertEqual(len(bundle.controls), 72)
        self.assertEqual(
            sum(
                item.state is ResolutionState.RESOLVED
                for item in bundle.listings
            ),
            0,
        )
        self.assertEqual(
            sum(
                item.state is ResolutionState.RESOLVED
                for item in bundle.shares
            ),
            0,
        )
        self.assertEqual(
            sum(
                item.state is ResolutionState.RESOLVED
                for item in bundle.controls
            ),
            0,
        )
        self.assertFalse(bundle.ready_metadata_gates)

    def test_synthetic_fixture_closes_four_metadata_gates_and_step16_plan(self):
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

        announcement = AnnouncementTimestampEvidence(
            event_id=event.event_id,
            timestamp=event.first_trade_date + "T16:00:00-04:00",
            evidence=ref(
                "announcement:complete",
                MetadataSourceKind.ISSUER_PUBLIC_RELEASE,
            ),
            proves_first_public_release=True,
        )
        listings = tuple(
            ListingExchangeEvidence(
                requirement.symbol,
                requirement.session_date,
                "N",
                ref(
                    "listing:"
                    + requirement.symbol
                    + ":"
                    + requirement.session_date,
                    MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
                ),
            )
            for requirement in initial.symbol_date_requirements
        )
        shares = tuple(
            SharesOutstandingEvidence(
                requirement.symbol,
                requirement.session_date,
                "1000000",
                requirement.session_date + "T08:00:00-04:00",
                ref(
                    "shares:"
                    + requirement.symbol
                    + ":"
                    + requirement.session_date,
                    MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
                ),
            )
            for requirement in initial.symbol_date_requirements
        )
        controls = (
            ControlUniverseEvidence(
                control_date=event.first_trade_date,
                universe_id="controls:" + event.first_trade_date,
                symbols=("XYZ", "DEF"),
                availability_timestamp=(
                    event.first_trade_date + "T08:00:00-04:00"
                ),
                complete_pre_event_covariates=True,
                evidence=ref(
                    "controls:complete",
                    MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE,
                ),
            ),
        )
        market_dates = frozenset(
            requirement.key
            for requirement in initial.source_date_requirements
        )
        bundle = resolve_metadata_for_plan(
            initial,
            announcement_evidence=(announcement,),
            listing_evidence=listings,
            shares_evidence=shares,
            control_evidence=controls,
            market_source_dates=market_dates,
        )
        self.assertTrue(bundle.ready_metadata_gates)

        final = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
            evidence=bundle.coverage_evidence(),
        )
        self.assertTrue(final.ready)
        self.assertEqual(final.unresolved_gates, ())

    def test_metadata_bundle_keeps_market_file_gate_separate(self):
        calendar = sessions(60)
        event = HistoricalFirstTradeEvent(
            "event:separate-market-gate",
            "ABC",
            calendar[40].session_date,
        )
        plan = build_coverage_plan(
            (event,),
            xnys_sessions=calendar,
        )
        bundle = resolve_metadata_for_plan(plan)
        evidence = bundle.coverage_evidence()
        self.assertEqual(evidence.market_source_dates, frozenset())

    def test_metadata_resolution_hash_is_order_independent(self):
        first = ListingExchangeEvidence(
            "ABC",
            "2015-08-10",
            "N",
            ref(
                "listing:one",
                MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            ),
        )
        second = ListingExchangeEvidence(
            "ABC",
            "2015-08-10",
            "N",
            ref(
                "listing:two",
                MetadataSourceKind.OFFICIAL_LISTING_HISTORY,
            ),
        )
        left = resolve_listing_exchange(
            "ABC",
            "2015-08-10",
            (first, second),
        )
        right = resolve_listing_exchange(
            "ABC",
            "2015-08-10",
            (second, first),
        )
        self.assertEqual(left.proof_hash, right.proof_hash)


if __name__ == "__main__":
    unittest.main()
