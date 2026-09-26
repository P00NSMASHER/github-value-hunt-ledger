import unittest
from pathlib import Path

from historical_mnpi.control_covariates import (
    ControlSourceFamily,
    build_point_in_time_control_universe,
)
from historical_mnpi.control_external_import import (
    import_control_external_inputs,
)


ROOT = Path(__file__).resolve().parent
CONTROL_EXTERNAL_DIR = ROOT / "real_corpus" / "control_external"


def committed_templates():
    return {
        name: (CONTROL_EXTERNAL_DIR / name).read_text(encoding="utf-8")
        for name in (
            "membership.csv",
            "covariates.csv",
            "source_coverage.csv",
        )
    }


class ControlExternalImportTests(unittest.TestCase):
    def test_committed_external_templates_are_empty_and_importable(self):
        imported = import_control_external_inputs(committed_templates())
        self.assertEqual(imported.memberships, ())
        self.assertEqual(imported.covariates, ())
        self.assertEqual(imported.source_coverage, ())
        self.assertEqual(
            imported.counts()["membership_rows"],
            0,
        )
        self.assertEqual(
            imported.counts()["covariate_rows"],
            0,
        )
        self.assertEqual(
            imported.counts()["source_coverage_rows"],
            0,
        )
        self.assertFalse(imported.live_use_allowed)

    def test_external_import_requires_exact_three_file_contract(self):
        files = committed_templates()
        missing = dict(files)
        del missing["covariates.csv"]
        with self.assertRaisesRegex(
            ValueError,
            "missing control input files: covariates.csv",
        ):
            import_control_external_inputs(missing)

        extra = dict(files)
        extra["unexpected.csv"] = "x\n"
        with self.assertRaisesRegex(
            ValueError,
            "unexpected control input files: unexpected.csv",
        ):
            import_control_external_inputs(extra)

    def test_retrospective_membership_cannot_enter_external_builder_input(self):
        files = committed_templates()
        files["membership.csv"] += (
            "2015-08-10,controls:2015-08-10,AAA|BBB,"
            "2015-08-10T08:00:00-04:00,"
            "membership:bad,Retrospective SampleFirms,"
            "RETROSPECTIVE_SAMPLE_FIRMS,"
            "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
        )
        with self.assertRaisesRegex(
            ValueError,
            "membership source_kind must be POINT_IN_TIME_CONTROL_UNIVERSE",
        ):
            import_control_external_inputs(files)

    def test_synthetic_authorized_external_inputs_close_one_control_date(self):
        files = committed_templates()
        files["membership.csv"] += (
            "2015-08-10,controls:2015-08-10,AAA|BBB,"
            "2015-08-10T08:00:00-04:00,"
            "membership:pit,Authorized point-in-time membership,"
            "POINT_IN_TIME_CONTROL_UNIVERSE,"
            "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
        )

        covariates = (
            ("lnMCAP", "CRSP", "1"),
            ("Beta_SPY", "CRSP", "2"),
            ("invPRC", "CRSP", "3"),
            ("lnnumest", "IBES", "4"),
            ("ln_Story_Count_Relevant", "RAVENPACK", "5"),
            ("DCBS", "MARKIT", "6"),
            ("IO", "THOMSON_REUTERS_13F", "7"),
        )
        for symbol in ("AAA", "BBB"):
            for index, (name, family, value) in enumerate(
                covariates,
                start=1,
            ):
                files["covariates.csv"] += (
                    f"2015-08-10,{symbol},{name},{value},"
                    "2015-08-09,2015-08-10T07:00:00-04:00,"
                    f"{family},fact:{symbol}:{index},"
                    f"Authorized {family} point-in-time fact,"
                    "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
                )

        for family in ControlSourceFamily:
            files["source_coverage.csv"] += (
                "2015-08-10,controls:2015-08-10,"
                f"{family.value},2015-08-10T07:30:00-04:00,"
                f"true,coverage:{family.value},"
                f"Authorized complete {family.value} extract,"
                "PUBLIC_OR_AUTHORIZED_HISTORICAL\n"
            )

        imported = import_control_external_inputs(files)
        self.assertEqual(len(imported.memberships), 1)
        self.assertEqual(len(imported.covariates), 14)
        self.assertEqual(len(imported.source_coverage), 7)

        result = build_point_in_time_control_universe(
            imported.memberships[0],
            imported.covariates,
            imported.source_coverage,
        )
        self.assertTrue(result.resolved)
        self.assertIsNotNone(result.evidence)
        self.assertEqual(result.evidence.symbols, ("AAA", "BBB"))
        self.assertTrue(result.evidence.complete_pre_event_covariates)
        self.assertEqual(result.missing_source_families, ())
        self.assertEqual(result.missing_covariates, ())
        self.assertEqual(result.conflicting_covariates, ())


if __name__ == "__main__":
    unittest.main()
