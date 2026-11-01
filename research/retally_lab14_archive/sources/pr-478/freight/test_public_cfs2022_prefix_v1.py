import unittest
from freight import public_cfs2022_prefix_v1 as c
class CfsTest(unittest.TestCase):
    def test_official_source_prefix(self):
        r=c.report()
        self.assertEqual(r["sample_rows"],100)
        self.assertFalse(r["national_estimate_authorized"])
        self.assertFalse(r["full_source_downloaded"])
        self.assertEqual(r["validated_invoice_count"],0)
        self.assertTrue(r["shipment_value_is_not_freight_charge"])
    def test_official_guidance_rejects_national_estimate_from_100_prefix_rows(self):
        r=c.report()
        self.assertTrue(r["official_CFS_2022_PUMS_guide_applied"])
        self.assertEqual(r["full_source_record_count_from_guide_only"],37576546)
        self.assertFalse(r["actual_original_full_source_record_count_verified"])
        self.assertTrue(r["sample_not_representative_or_weighted"])
        self.assertTrue(r["disclosure_modified_values_not_original_invoices"])
        self.assertTrue(r["WGT_FACTOR_meaning_documented_but_not_used_for_population_extrapolation"])
        self.assertTrue(r["published_official_CFS_tables_preferred_for_population_estimates"])
        self.assertFalse(r["national_estimate_authorized"])

    def test_manually_rewritten_manifest_cannot_promote_sample_to_national_estimate(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        original=json.loads((c.HERE/"fixtures/public_census_cfs2022_pums_first100_manifest.json").read_text())
        original["weight_policy"]["per_sample_100_row_extrapolation_authorized"]=True
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"fixtures").mkdir()
            from shutil import copy2
            copy2(c.HERE/"fixtures/public_census_cfs2022_pums_first100.csv",
                  root/"fixtures/public_census_cfs2022_pums_first100.csv")
            (root/"fixtures/public_census_cfs2022_pums_first100_manifest.json").write_text(json.dumps(original))
            with patch.object(c,"HERE",root):
                with self.assertRaisesRegex(ValueError,"CFS_GUIDE_OR_INFERENCE_POLICY_CHANGED"):
                    c.report()

    def test_rehashed_bogus_large_weight_does_not_bypass_numeric_controls(self):
        import hashlib,tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"fixtures").mkdir()
            raw=(c.HERE/"fixtures/public_census_cfs2022_pums_first100.csv").read_bytes()
            self.assertIn(b",50.0",raw)
            altered=raw.replace(b",50.0",b",999999999.9",1)
            (root/"fixtures/public_census_cfs2022_pums_first100.csv").write_bytes(altered)
            m=json.loads((c.HERE/"fixtures/public_census_cfs2022_pums_first100_manifest.json").read_text())
            m["fixture_sha256"]=hashlib.sha256(altered).hexdigest()
            m["fixture_bytes"]=len(altered)
            (root/"fixtures/public_census_cfs2022_pums_first100_manifest.json").write_text(json.dumps(m))
            with patch.object(c,"HERE",root):
                with self.assertRaisesRegex(ValueError,"CFS_INVALID_TABULATION_FACTOR"):
                    c.report()

    def test_any_single_value_mutation_is_rejected_by_original_sample_checksum(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        raw=(c.HERE/"fixtures/public_census_cfs2022_pums_first100.csv").read_bytes()
        self.assertIn(b"00000001",raw)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"fixtures").mkdir()
            (root/"fixtures/public_census_cfs2022_pums_first100.csv").write_bytes(
                raw.replace(b"00000001",b"00000002",1))
            source=(c.HERE/"fixtures/public_census_cfs2022_pums_first100_manifest.json").read_bytes()
            (root/"fixtures/public_census_cfs2022_pums_first100_manifest.json").write_bytes(source)
            with patch.object(c,"HERE",root):
                with self.assertRaisesRegex(ValueError,"CFS_ORIGINAL_ROW_BYTES_CHANGED"):
                    c.report()
if __name__=="__main__":unittest.main()
