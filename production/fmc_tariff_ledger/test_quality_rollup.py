import json
import tempfile
import unittest
from pathlib import Path

import quality_rollup


class QualityRollupTests(unittest.TestCase):
    def test_rollup_aggregates_recovery_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for idx, values in enumerate([
                {
                    "before": {"terms": 100, "effective_dated_terms": 40},
                    "after": {"terms": 150, "effective_dated_terms": 90},
                    "validation": {
                        "bogus_rule_terms_removed": 5,
                        "terms_quarantined_shared_generic": 7,
                    },
                    "reparse": {
                        "terms_inserted": 150,
                        "effective_dates_added": 3,
                    },
                    "retry": {
                        "targets": 2,
                        "recovered": 1,
                        "failed": 1,
                        "reason_counts": {"http:503": 2},
                    },
                },
                {
                    "before": {"terms": 200, "effective_dated_terms": 100},
                    "after": {"terms": 260, "effective_dated_terms": 156},
                    "validation": {
                        "bogus_rule_terms_removed": 8,
                        "terms_quarantined_shared_generic": 9,
                    },
                    "reparse": {
                        "terms_inserted": 260,
                        "effective_dates_added": 4,
                    },
                    "retry": {
                        "targets": 3,
                        "recovered": 2,
                        "failed": 1,
                        "reason_counts": {
                            "http:503": 1,
                            "fetch:ConnectTimeout": 2,
                        },
                    },
                },
            ]):
                shard = root / f"fmc-metadata-shard-{idx}"
                shard.mkdir()
                (shard / "summary_prevalidation.json").write_text(
                    json.dumps(values["before"])
                )
                (shard / "summary.json").write_text(
                    json.dumps(values["after"])
                )
                (shard / "revalidation.json").write_text(
                    json.dumps(values["validation"])
                )
                (shard / "reparse.json").write_text(
                    json.dumps(values["reparse"])
                )
                (shard / "retry_transient.json").write_text(
                    json.dumps(values["retry"])
                )

            result = quality_rollup.build_rollup(root)
            self.assertEqual(result["shards_found"], 2)
            self.assertEqual(result["before"]["terms"], 300)
            self.assertEqual(result["after"]["terms"], 410)
            self.assertEqual(result["delta"]["terms"], 110)
            self.assertEqual(result["revalidation"]["bogus_rule_terms_removed"], 13)
            self.assertEqual(
                result["revalidation"]["terms_quarantined_shared_generic"],
                16,
            )
            self.assertEqual(result["retry"]["targets"], 5)
            self.assertEqual(result["retry"]["recovered"], 3)
            self.assertEqual(
                result["retry"]["reason_counts"],
                {"http:503": 3, "fetch:ConnectTimeout": 2},
            )
            self.assertTrue(
                result["notes"]["effective_dates_are_source_extracted_not_observation_inferred"]
            )


if __name__ == "__main__":
    unittest.main()
