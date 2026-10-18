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
if __name__=="__main__":unittest.main()
