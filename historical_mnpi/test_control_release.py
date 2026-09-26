import csv
import io
import unittest

from historical_mnpi.control_covariates import (
    REQUIRED_SOURCE_FAMILIES,
    REQUIRED_VARIABLE_ANCHORS,
    ControlCovariateFact,
    ControlSourceCoverageReceipt,
    ControlSourceFamily,
    PointInTimeControlMembership,
)
from historical_mnpi.control_external_import import ControlExternalInputImport
from historical_mnpi.control_release import (
    RELEASE_CONTRACT_VERSION,
    build_control_release_from_csv,
    build_control_release_gate,
    control_dates_from_events_csv,
)
from historical_mnpi.metadata_resolver import (
    MetadataDataClass,
    MetadataSourceKind,
    ResolutionState,
    resolve_control_universe,
)
from historical_mnpi.real_corpus_import import (
    ANNOUNCEMENT_HEADERS,
    LISTING_HEADERS,
    MARKET_SOURCE_HEADERS,
    SHARES_HEADERS,
    import_real_corpus_metadata,
)


DATES = ("2015-08-10", "2015-08-11")
SYMBOLS = ("AAA", "BBB")

ANCHOR_FAMILY = {
    "lnMCAP": ControlSourceFamily.CRSP,
    "Beta_SPY": ControlSourceFamily.CRSP,
    "invPRC": ControlSourceFamily.CRSP,
    "lnnumest": ControlSourceFamily.IBES,
    "ln_Story_Count_Relevant": ControlSourceFamily.RAVENPACK,
    "DCBS": ControlSourceFamily.MARKIT,
    "IO": ControlSourceFamily.THOMSON_REUTERS_13F,
}


def membership(day):
    return PointInTimeControlMembership(
        control_date=day,
        universe_id="controls:" + day,
        symbols=SYMBOLS,
        availability_timestamp=day + "T07:00:00-04:00",
        evidence_id="membership:" + day,
        source_name="Synthetic authorized point-in-time membership",
    )


def covariates(day):
    result = []
    for symbol_index, symbol in enumerate(SYMBOLS, start=1):
        for anchor_index, name in enumerate(
            REQUIRED_VARIABLE_ANCHORS,
            start=1,
        ):
            result.append(ControlCovariateFact(
                control_date=day,
                symbol=symbol,
                covariate_name=name,
                value=str(symbol_index * 10 + anchor_index),
                effective_date=day,
                availability_timestamp=day + "T07:15:00-04:00",
                source_family=ANCHOR_FAMILY[name],
                evidence_id=f"covariate:{day}:{symbol}:{name}",
                source_name=(
                    "Synthetic authorized historical covariate fixture"
                ),
            ))
    return tuple(result)


def coverage(day):
    return tuple(
        ControlSourceCoverageReceipt(
            control_date=day,
            universe_id="controls:" + day,
            source_family=ControlSourceFamily(family),
            availability_timestamp=day + "T07:30:00-04:00",
            complete_for_universe=True,
            evidence_id=f"coverage:{day}:{family}",
            source_name=(
                "Synthetic authorized historical source coverage fixture"
            ),
        )
        for family in REQUIRED_SOURCE_FAMILIES
    )


def complete_inputs(dates=DATES):
    return ControlExternalInputImport(
        memberships=tuple(membership(day) for day in dates),
        covariates=tuple(
            item
            for day in dates
            for item in covariates(day)
        ),
        source_coverage=tuple(
            item
            for day in dates
            for item in coverage(day)
        ),
    )


def header_only(headers):
    return ",".join(headers) + "\n"


class ControlReleaseTests(unittest.TestCase):
    def test_control_dates_from_events_csv_is_unique_and_sorted(self):
        events = (
            "event_id,first_trade_date\n"
            "e2,2015-08-11\n"
            "e1,2015-08-10\n"
            "e3,2015-08-10\n"
        )
        self.assertEqual(
            control_dates_from_events_csv(events),
            DATES,
        )

    def test_partial_input_never_emits_partial_control_metadata(self):
        inputs = complete_inputs((DATES[0],))
        result = build_control_release_gate(DATES, inputs)

        self.assertFalse(result.ready)
        self.assertIsNone(result.control_metadata_csv)
        self.assertEqual(len(result.evidence), 1)
        self.assertIn(
            "MISSING_MEMBERSHIP:2015-08-11",
            result.rejection_reasons,
        )

    def test_duplicate_membership_fails_closed(self):
        base = complete_inputs()
        inputs = ControlExternalInputImport(
            memberships=base.memberships + (membership(DATES[0]),),
            covariates=base.covariates,
            source_coverage=base.source_coverage,
        )
        result = build_control_release_gate(DATES, inputs)

        self.assertFalse(result.ready)
        self.assertIsNone(result.control_metadata_csv)
        self.assertIn(
            "AMBIGUOUS_MEMBERSHIP:2015-08-10",
            result.rejection_reasons,
        )

    def test_unexpected_external_date_blocks_release(self):
        extra = "2015-08-12"
        inputs = complete_inputs(DATES + (extra,))
        result = build_control_release_gate(DATES, inputs)

        self.assertFalse(result.ready)
        self.assertIsNone(result.control_metadata_csv)
        self.assertIn(
            "UNEXPECTED_EXTERNAL_DATE:" + extra,
            result.rejection_reasons,
        )

    def test_complete_release_round_trips_through_metadata_importer(self):
        result = build_control_release_gate(
            DATES,
            complete_inputs(),
        )
        self.assertTrue(result.ready)
        self.assertEqual(result.rejection_reasons, ())
        self.assertEqual(len(result.evidence), 2)
        self.assertIsNotNone(result.control_metadata_csv)

        rows = list(csv.DictReader(io.StringIO(
            result.control_metadata_csv
        )))
        self.assertEqual(
            [row["control_date"] for row in rows],
            list(DATES),
        )
        self.assertTrue(all(
            row["complete_pre_event_covariates"] == "true"
            for row in rows
        ))
        self.assertTrue(all(
            row["source_kind"] == "POINT_IN_TIME_CONTROL_UNIVERSE"
            for row in rows
        ))

        imported = import_real_corpus_metadata({
            "announcement_metadata.csv": header_only(
                ANNOUNCEMENT_HEADERS
            ),
            "listing_metadata.csv": header_only(LISTING_HEADERS),
            "shares_metadata.csv": header_only(SHARES_HEADERS),
            "control_metadata.csv": result.control_metadata_csv,
            "market_source_dates.csv": header_only(
                MARKET_SOURCE_HEADERS
            ),
        })
        self.assertEqual(len(imported.controls), 2)
        for day in DATES:
            resolved = resolve_control_universe(
                day,
                imported.controls,
            )
            self.assertEqual(
                resolved.state,
                ResolutionState.RESOLVED,
            )
            self.assertEqual(resolved.symbols, SYMBOLS)

    def test_release_hash_and_csv_are_input_order_independent(self):
        base = complete_inputs()
        reversed_inputs = ControlExternalInputImport(
            memberships=tuple(reversed(base.memberships)),
            covariates=tuple(reversed(base.covariates)),
            source_coverage=tuple(reversed(base.source_coverage)),
        )
        left = build_control_release_gate(DATES, base)
        right = build_control_release_gate(DATES, reversed_inputs)

        self.assertTrue(left.ready)
        self.assertTrue(right.ready)
        self.assertEqual(
            left.control_metadata_csv,
            right.control_metadata_csv,
        )
        self.assertEqual(left.proof_hash, right.proof_hash)

    def test_csv_entrypoint_imports_and_builds_complete_release(self):
        events = (
            "event_id,first_trade_date\n"
            "e1,2015-08-10\n"
            "e2,2015-08-11\n"
        )
        base = complete_inputs()

        def write_memberships():
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow((
                "control_date",
                "universe_id",
                "symbols",
                "availability_timestamp",
                "evidence_id",
                "source_kind",
                "source_name",
                "data_class",
            ))
            for item in base.memberships:
                writer.writerow((
                    item.control_date,
                    item.universe_id,
                    "|".join(item.symbols),
                    item.availability_timestamp,
                    item.evidence_id,
                    item.source_kind.value,
                    item.source_name,
                    item.data_class.value,
                ))
            return buffer.getvalue()

        def write_covariates():
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow((
                "control_date",
                "symbol",
                "covariate_name",
                "value",
                "effective_date",
                "availability_timestamp",
                "source_family",
                "evidence_id",
                "source_name",
                "data_class",
            ))
            for item in base.covariates:
                writer.writerow((
                    item.control_date,
                    item.symbol,
                    item.covariate_name,
                    item.value,
                    item.effective_date,
                    item.availability_timestamp,
                    item.source_family.value,
                    item.evidence_id,
                    item.source_name,
                    item.data_class.value,
                ))
            return buffer.getvalue()

        def write_coverage():
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow((
                "control_date",
                "universe_id",
                "source_family",
                "availability_timestamp",
                "complete_for_universe",
                "evidence_id",
                "source_name",
                "data_class",
            ))
            for item in base.source_coverage:
                writer.writerow((
                    item.control_date,
                    item.universe_id,
                    item.source_family.value,
                    item.availability_timestamp,
                    "true",
                    item.evidence_id,
                    item.source_name,
                    item.data_class.value,
                ))
            return buffer.getvalue()

        result = build_control_release_from_csv(
            events,
            {
                "membership.csv": write_memberships(),
                "covariates.csv": write_covariates(),
                "source_coverage.csv": write_coverage(),
            },
        )
        self.assertTrue(result.ready)
        self.assertEqual(
            RELEASE_CONTRACT_VERSION,
            "g4-control-release-v1",
        )
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(
            {item.evidence.data_class for item in result.evidence},
            {MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL},
        )
        self.assertEqual(
            {item.evidence.source_kind for item in result.evidence},
            {MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE},
        )


if __name__ == "__main__":
    unittest.main()
