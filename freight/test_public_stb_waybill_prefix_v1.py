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
        self.assertEqual(o["first_accounting_period_raw"],"0324")
        self.assertEqual(o["waybill_year_histogram"],
                         {"2018":14,"2020":1,"2021":20,"2022":65})
        self.assertEqual(o["accounting_year_histogram"],{"2024":100})
        self.assertTrue(o["year_pairing_consistent_with_stb_guide"])
        self.assertTrue(o["2024_accounting_year_not_equal_2024_shipment_year"])
        self.assertEqual(o["reason_older_waybills_entered_2024_accounts"],"UNVERIFIED")
        self.assertTrue(o["revenue_may_be_masked"])
    def test_accounting_year_must_be_2024_in_original_frozen_prefix(self):
        from pathlib import Path
        import tempfile,json
        from unittest.mock import patch
        original=json.loads(w.M.read_text())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"manifest.json"
            original["frozen_prefix_accounting_year_histogram"]={"2025":100}
            p.write_text(json.dumps(original))
            with patch.object(w,"M",p):
                with self.assertRaisesRegex(ValueError,"STB_SOURCE_DATE_DISTRIBUTION_CHANGED"):
                    w.report()

    def test_older_waybill_year_is_not_mislabeled_as_2024_movement(self):
        r=w.report()
        self.assertEqual(r["accounting_year_histogram"]["2024"],100)
        self.assertNotIn("2024",r["waybill_year_histogram"])
        self.assertEqual(sum(r["waybill_year_histogram"].values()),100)

    def test_modified_member_record_must_fail(self):
        raw=w.P.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/"sample.txt"
            f.write_bytes(raw[:5]+b"X"+raw[6:])
            with patch.object(w,"P",f):
                with self.assertRaisesRegex(ValueError,"STB_SAMPLE_CONTENT_CHANGED"):
                    w.report()
if __name__=="__main__": unittest.main()
