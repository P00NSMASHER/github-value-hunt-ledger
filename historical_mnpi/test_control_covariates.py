import csv
import unittest
from pathlib import Path

from historical_mnpi.control_covariates import (
    ControlCovariateFact,
    ControlSourceCoverageReceipt,
    ControlSourceFamily,
    PointInTimeControlMembership,
    REQUIRED_SOURCE_FAMILIES,
    REQUIRED_VARIABLE_ANCHORS,
    build_point_in_time_control_universe,
)
from historical_mnpi.metadata_resolver import (
    MetadataSourceKind,
    ResolutionState,
    resolve_control_universe,
)


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


VARIABLE_FAMILY = {
    "lnMCAP": ControlSourceFamily.CRSP,
    "Beta_SPY": ControlSourceFamily.CRSP,
    "invPRC": ControlSourceFamily.CRSP,
    "lnnumest": ControlSourceFamily.IBES,
    "ln_Story_Count_Relevant": ControlSourceFamily.RAVENPACK,
    "DCBS": ControlSourceFamily.MARKIT,
    "IO": ControlSourceFamily.THOMSON_REUTERS_13F,
}


def membership():
    return PointInTimeControlMembership(
        control_date="2015-08-10",
        universe_id="pit:2015-08-10",
        symbols=("BBB", "AAA"),
        availability_timestamp="2015-08-10T08:00:00-04:00",
        evidence_id="membership:2015-08-10",
        source_name="Authorized point-in-time membership fixture",
    )


def coverage(*, incomplete_family=None):
    return tuple(
        ControlSourceCoverageReceipt(
            control_date="2015-08-10",
            universe_id="pit:2015-08-10",
            source_family=family,
            availability_timestamp="2015-08-10T08:00:00-04:00",
            complete_for_universe=(family is not incomplete_family),
            evidence_id="coverage:" + family.value,
            source_name="Authorized point-in-time source coverage fixture",
        )
        for family in ControlSourceFamily
    )


def facts():
    result = []
    for symbol_index, symbol in enumerate(("AAA", "BBB"), start=1):
        for variable_index, name in enumerate(
            REQUIRED_VARIABLE_ANCHORS,
            start=1,
        ):
            result.append(ControlCovariateFact(
                control_date="2015-08-10",
                symbol=symbol,
                covariate_name=name,
                value=str(symbol_index * 100 + variable_index),
                effective_date="2015-08-07",
                availability_timestamp="2015-08-10T08:00:00-04:00",
                source_family=VARIABLE_FAMILY[name],
                evidence_id=f"fact:{symbol}:{name}",
                source_name="Authorized historical covariate fixture",
            ))
    return tuple(result)


class ControlCovariateContractTests(unittest.TestCase):
    def test_complete_point_in_time_inputs_emit_resolvable_control_universe(self):
        built = build_point_in_time_control_universe(
            membership(),
            facts(),
            coverage(),
        )
        self.assertTrue(built.resolved)
        self.assertEqual(built.missing_source_families, ())
        self.assertEqual(built.incomplete_source_families, ())
        self.assertEqual(built.missing_covariates, ())
        self.assertEqual(built.conflicting_covariates, ())
        self.assertIsNotNone(built.evidence)
        self.assertEqual(built.evidence.symbols, ("AAA", "BBB"))
        self.assertTrue(built.evidence.complete_pre_event_covariates)
        self.assertEqual(
            built.evidence.evidence.source_kind,
            MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE,
        )

        resolved = resolve_control_universe(
            "2015-08-10",
            (built.evidence,),
        )
        self.assertEqual(resolved.state, ResolutionState.RESOLVED)
        self.assertEqual(resolved.symbols, ("AAA", "BBB"))

    def test_missing_source_family_fails_closed(self):
        receipts = tuple(
            item
            for item in coverage()
            if item.source_family is not ControlSourceFamily.OPTIONMETRICS
        )
        built = build_point_in_time_control_universe(
            membership(),
            facts(),
            receipts,
        )
        self.assertFalse(built.resolved)
        self.assertIsNone(built.evidence)
        self.assertEqual(
            built.missing_source_families,
            ("OPTIONMETRICS",),
        )

    def test_incomplete_source_family_fails_closed(self):
        built = build_point_in_time_control_universe(
            membership(),
            facts(),
            coverage(incomplete_family=ControlSourceFamily.TAQ),
        )
        self.assertFalse(built.resolved)
        self.assertEqual(
            built.incomplete_source_families,
            ("TAQ",),
        )

    def test_missing_covariate_fails_closed(self):
        incomplete = tuple(
            item
            for item in facts()
            if not (
                item.symbol == "BBB"
                and item.covariate_name == "IO"
            )
        )
        built = build_point_in_time_control_universe(
            membership(),
            incomplete,
            coverage(),
        )
        self.assertFalse(built.resolved)
        self.assertEqual(
            built.missing_covariates,
            (("BBB", "IO"),),
        )

    def test_conflicting_latest_covariate_fails_closed(self):
        duplicate = ControlCovariateFact(
            control_date="2015-08-10",
            symbol="AAA",
            covariate_name="lnMCAP",
            value="999",
            effective_date="2015-08-07",
            availability_timestamp="2015-08-10T08:00:00-04:00",
            source_family=ControlSourceFamily.CRSP,
            evidence_id="fact:AAA:lnMCAP:conflict",
            source_name="Authorized conflicting fixture",
        )
        built = build_point_in_time_control_universe(
            membership(),
            facts() + (duplicate,),
            coverage(),
        )
        self.assertFalse(built.resolved)
        self.assertEqual(
            built.conflicting_covariates,
            (("AAA", "lnMCAP"),),
        )

    def test_membership_must_be_available_by_control_date(self):
        with self.assertRaisesRegex(
            ValueError,
            "available by control_date",
        ):
            PointInTimeControlMembership(
                control_date="2015-08-10",
                universe_id="pit:late",
                symbols=("AAA",),
                availability_timestamp="2015-08-11T08:00:00-04:00",
                evidence_id="membership:late",
                source_name="Late membership fixture",
            )

    def test_retrospective_sample_kind_cannot_masquerade_as_point_in_time(self):
        with self.assertRaisesRegex(
            ValueError,
            "POINT_IN_TIME_CONTROL_UNIVERSE",
        ):
            PointInTimeControlMembership(
                control_date="2015-08-10",
                universe_id="SampleFirms",
                symbols=("AAA",),
                availability_timestamp="2015-08-10T08:00:00-04:00",
                evidence_id="membership:retrospective",
                source_name="Retrospective SampleFirms fixture",
                source_kind=MetadataSourceKind.RETROSPECTIVE_SAMPLE_FIRMS,
            )

    def test_real_contract_matches_all_g4_blocker_requirements(self):
        with (CORPUS_DIR / "control_covariate_contract.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            contract = list(csv.DictReader(handle))
        with (CORPUS_DIR / "control_requirement_index.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            blockers = list(csv.DictReader(handle))

        source_rows = {
            row["name"]
            for row in contract
            if row["record_type"] == "SOURCE_FAMILY"
        }
        variable_rows = {
            row["name"]
            for row in contract
            if row["record_type"] == "VARIABLE_ANCHOR"
        }

        self.assertEqual(
            source_rows,
            set(REQUIRED_SOURCE_FAMILIES),
        )
        self.assertEqual(
            variable_rows,
            set(REQUIRED_VARIABLE_ANCHORS),
        )
        self.assertEqual(len(blockers), 72)
        for row in blockers:
            self.assertEqual(
                set(row["required_covariate_families"].split("|")),
                set(REQUIRED_SOURCE_FAMILIES),
            )
            self.assertEqual(
                set(row["required_variable_anchors"].split("|")),
                set(REQUIRED_VARIABLE_ANCHORS),
            )
            self.assertEqual(
                row["review_status"],
                "BLOCKED_POINT_IN_TIME_COVARIATES",
            )


if __name__ == "__main__":
    unittest.main()
