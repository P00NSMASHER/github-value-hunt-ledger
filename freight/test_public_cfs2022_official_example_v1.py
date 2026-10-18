"""Census guide worked example is independently named and never treated as actual freight charges."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_cfs2022_official_example_v1 as e


class CensusOfficialMarylandGuideExample(unittest.TestCase):
    def test_exact_publisher_weighted_goods_example_and_gvf(self):
        r=e.verified_published_example()
        self.assertEqual(r["pums_md_origin_unweighted_record_count"],612317)
        self.assertEqual(r["census_published_weighted_goods_value_usd"],"198598788295")
        self.assertEqual(r["census_published_gvf_cv_percent"],"9.74")
        self.assertIsNone(r["country_or_route_total_freight_spend"])
        self.assertTrue(r["census_estimate_not_equal_faf6_md_pa_lane"])
        self.assertFalse(r["100_prefix_rows_used_to_make_estimate"])
        self.assertFalse(r["underlying_full_37576546_source_records_locally_recomputed"])
        self.assertTrue(r["no_original_customer_tariff_invoice_or_recoveries"])
        self.assertEqual(r["commercial_claim_clearance"],"NOT_ESTABLISHED")

    def _mutate(self,change):
        source=json.loads(e.SOURCE.read_text())
        change(source)
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"example.json"
            f.write_text(json.dumps(source))
            with patch.object(e,"SOURCE",f):
                with self.assertRaisesRegex(ValueError,"CFS_MD_EXAMPLE_SOURCE_OR_CLAIM_CHANGED"):
                    e.verified_published_example()

    def test_reject_forged_public_goods_value_as_customer_recovery(self):
        self._mutate(lambda d:d.update({"real_recoveries_cents":198598788295}))
        self._mutate(lambda d:d.update({"customer_overcharge_usd":"100000"}))

    def test_reject_100_prefix_row_extrapolation_promotion(self):
        self._mutate(lambda d:d.update({
            "ordinary_100_row_prefix_permitted_as_substitute":True}))
        self._mutate(lambda d:d.update({
            "this_is_official_published_example_not_locally_recomputed_from_full_file":False}))

    def test_reject_changed_census_denominator_or_variance_claim(self):
        self._mutate(lambda d:d.update({"published_example_pums_domain_records":100}))
        self._mutate(lambda d:d.update({"published_example_coefficient_of_variation_percent":"0.01"}))
        self._mutate(lambda d:d.update({"published_example_weighted_goods_value_usd":"198598788296"}))


if __name__=="__main__":
    unittest.main()
