import unittest
from unittest import mock

import run


class ProductionEntrypointTests(unittest.TestCase):
    def test_production_crawl_wrapper_sets_parser_version(self):
        fake = {
            "source": object(),
            "snapshots": [],
            "terms": [],
            "errors": [],
        }
        with mock.patch.object(
            run,
            "_CORE_CRAWL_ONE",
            return_value=fake.copy(),
        ):
            result = run.crawl_one_location_production(
                object(),
                object(),
                1,
                1,
                1,
                1,
            )
        self.assertEqual(
            result["parser_version"],
            run.PRODUCTION_PARSER_VERSION,
        )

    def test_production_parser_version_is_not_reparse_or_retry_label(self):
        self.assertEqual(run.PRODUCTION_PARSER_VERSION, "fmc-ledger-v3-crawl")
        self.assertNotIn("reparse", run.PRODUCTION_PARSER_VERSION)
        self.assertNotIn("retry", run.PRODUCTION_PARSER_VERSION)


if __name__ == "__main__":
    unittest.main()
