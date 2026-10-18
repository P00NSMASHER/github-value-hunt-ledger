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
