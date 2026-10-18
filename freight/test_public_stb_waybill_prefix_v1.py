import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from freight import public_stb_waybill_prefix_v1 as w

class STBWaybillSourceTests(unittest.TestCase):
    def test_true_public_waybill_sample_prefix_not_invoice(self):
        o=w.report()
        self.assertEqual(o["original_public_records"],100)
        self.assertFalse(o["source_archive_fully_verified"])
        self.assertTrue(o["revenue_may_be_masked"])
        self.assertFalse(o["rate_field_interpreted"])
        self.assertEqual(o["real_customer_invoice_count"],0)
    def test_official_stb_247_byte_layout_fields_and_year_hold(self):
        o=w.report()
        self.assertTrue(o["official_2024_guide_field_layout_checked"])
        self.assertEqual(o["first_waybill_date_raw"],"041118")
        self.assertEqual(o["first_stcc_raw"],"48105")
        self.assertEqual(o["waybill_date_year_interpretation"],"UNVERIFIED")
        self.assertTrue(o["revenue_may_be_masked"])
    def test_modified_member_record_must_fail(self):
        raw=w.P.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/"sample.txt"
            f.write_bytes(raw[:5]+b"X"+raw[6:])
            with patch.object(w,"P",f):
                with self.assertRaisesRegex(ValueError,"STB_SAMPLE_CONTENT_CHANGED"):
                    w.report()
if __name__=="__main__": unittest.main()
