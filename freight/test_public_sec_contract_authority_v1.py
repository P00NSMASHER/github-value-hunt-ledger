"""Public SEC rate agreements: independent, synthetic-only, adversarial tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_sec_contract_authority_v1 as sec


class OriginalSECFiledsContractAuthority(unittest.TestCase):
    def test_original_2007_local_Nebraska_index_and_2005_national_DOE_are_distinct(self):
        docs=sec.verified_source_exhibits()
        self.assertEqual(set(docs),{sec.NEDAK,sec.SWIFT})
        self.assertEqual(docs[sec.NEDAK]["base_rate_usd_per_unloaded_gallon"],"0.01299")
        self.assertEqual(docs[sec.NEDAK]["effective_date"],"2007-07-19")
        self.assertEqual(docs[sec.SWIFT]["effective_date"],"2005-02-28")
        self.assertNotEqual(docs[sec.NEDAK]["fuel_index"],docs[sec.SWIFT]["fuel_index"])
        self.assertEqual(len(docs[sec.NEDAK]["published_fuel_table"]),7)
        self.assertEqual(len(docs[sec.SWIFT]["selected_original_published_fuel_bands"]),7)

    def test_synthetic_original_2007_gallon_rated_math_never_original_invoice(self):
        o=sec.synthetic_quote(agreement=sec.NEDAK,fuel_index=sec.LOCAL_FUEL,
                              fuel_price_usd="2.749",gallons_unloaded=1000)
        self.assertEqual(o["source_base_rate_usd_per_unloaded_gallon"],"0.01299")
        self.assertEqual(o["source_surcharge_per_unloaded_gallon_usd"],"0.0003")
        self.assertEqual(o["hypothetical_unamended_freight_charge_usd"],"13.29")
        self.assertFalse(o["historic_fuel_price_actually_observed"])
        self.assertFalse(o["actual_invoice_compared"])
        self.assertEqual(o["RETALLY_overcharge_or_recovery_cents"],None)
        self.assertEqual(o["commercial_claim_clearance"],"NO_GO")

    def test_original_2005_DOE_diesel_per_mile_is_not_full_lane_rate(self):
        o=sec.synthetic_quote(agreement=sec.SWIFT,fuel_index=sec.DOE_FUEL,
                              fuel_price_usd="1.275",miles=150)
        self.assertEqual(o["source_surcharge_cents_per_mile"],1)
        self.assertEqual(o["hypothetical_FUEL_ONLY_charge_usd"],"1.50")
        self.assertEqual(o["full_freight_charge_status"],
                         "UNVERIFIED_MISSING_APPLICABLE_LANE_RATE_APPENDIX")
        self.assertEqual(o["calculation_type"],"SYNTHETIC_ARITHMETIC_NOT_A_REAL_SHIPMENT")

    def test_wrong_fuel_authority_never_uses_public_EIA_on_local_Nebraska_contract(self):
        for wrong in [sec.DOE_FUEL,"EIA_2026_NATIONAL","UPS_GROUND_FUEL",""]:
            with self.subTest(index=wrong),self.assertRaisesRegex(
                ValueError,"SEC_CONTRACT_SOURCE_INCOMPATIBLE_FUEL_INDEX"
            ):
                sec.synthetic_quote(agreement=sec.NEDAK,fuel_index=wrong,
                        fuel_price_usd="2.749",gallons_unloaded=1000)
        with self.assertRaisesRegex(ValueError,"SEC_CONTRACT_SOURCE_INCOMPATIBLE_FUEL_INDEX"):
            sec.synthetic_quote(agreement=sec.SWIFT,fuel_index=sec.LOCAL_FUEL,
                                 fuel_price_usd="1.275",miles=150)

    def test_above_table_or_between_published_tiers_not_silently_interpolated(self):
        for price in ["1.500","2.748","3.000","4.000","6.179","-1.000","NaN"]:
            with self.subTest(price=price),self.assertRaisesRegex(
                ValueError,"SEC_CONTRACT_SOURCE_"
            ):
                sec.synthetic_quote(agreement=sec.NEDAK,fuel_index=sec.LOCAL_FUEL,
                    fuel_price_usd=price,gallons_unloaded=1000)
        for price in ["1.2499","1.5499","6.179","2.749"]:
            with self.subTest(Swift=price),self.assertRaisesRegex(
                ValueError,"SEC_CONTRACT_SOURCE_"
            ):
                sec.synthetic_quote(agreement=sec.SWIFT,fuel_index=sec.DOE_FUEL,
                    fuel_price_usd=price,miles=150)

    def test_gallon_volume_cannot_be_swapped_for_mileage_or_negative_quantities(self):
        for q in [0,-1,True,100001,10.5]:
            with self.subTest(q=q),self.assertRaisesRegex(
                ValueError,"SEC_CONTRACT_SOURCE_WRONG_QUANTITY_OR_UNITS"
            ):
                sec.synthetic_quote(agreement=sec.NEDAK,fuel_index=sec.LOCAL_FUEL,
                    fuel_price_usd="2.749",gallons_unloaded=q)
        with self.assertRaisesRegex(ValueError,"SEC_CONTRACT_SOURCE_WRONG_QUANTITY_OR_UNITS"):
            sec.synthetic_quote(agreement=sec.NEDAK,fuel_index=sec.LOCAL_FUEL,
                    fuel_price_usd="2.749",gallons_unloaded=100,miles=50)
        with self.assertRaisesRegex(ValueError,"SEC_CONTRACT_SOURCE_WRONG_QUANTITY_OR_UNITS"):
            sec.synthetic_quote(agreement=sec.SWIFT,fuel_index=sec.DOE_FUEL,
                    fuel_price_usd="1.275",gallons_unloaded=1000)

    def _mutate(self,change):
        original=json.loads(sec.SOURCE.read_text())
        change(original)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"unreviewed-contract.json"
            path.write_text(json.dumps(original),encoding="utf-8")
            with patch.object(sec,"SOURCE",path):
                with self.assertRaisesRegex(ValueError,"SEC_CONTRACT_SOURCE_"):
                    sec.verified_source_exhibits()

    def test_forged_rate_tier_or_source_index_cannot_pass(self):
        self._mutate(lambda x:x["contracts"][0]["published_fuel_table"][1].update(
            {"surcharge_usd_per_unloaded_gallon":"0.0030"}))
        self._mutate(lambda x:x["contracts"][0].update({"fuel_index":sec.DOE_FUEL}))
        self._mutate(lambda x:x["contracts"][1]["selected_original_published_fuel_bands"][1].update(
            {"surcharge_cents_per_mile":6}))
        self._mutate(lambda x:x["contracts"][1].update({
            "fuel_index":"LOCAL_NONAFFILIATED_NO2_DIESEL_RETAIL_O_NEILL_NE"}))

    def test_forged_current_agreement_or_real_customer_invoice_fails(self):
        self._mutate(lambda x:x["contracts"][0].update({"current_operational_status_verified":True}))
        self._mutate(lambda x:x["contracts"][0].update({"actual_billed_shipment_invoice_seen":True}))
        self._mutate(lambda x:x["contracts"][1].update({"actual_invoice_and_lane_Appendices_seen":True}))
        self._mutate(lambda x:x["shared_controls"].update({"actual_RETALLY_customer_invoices":3}))
        self._mutate(lambda x:x["contracts"][0].update({"original_EDGAR_document_binary_hashed":True}))

    def test_adulterated_signatories_source_host_and_extra_invoice_fields_rejected(self):
        self._mutate(lambda x:x["contracts"][0].update({"carrier":"Another Freight Ltd"}))
        self._mutate(lambda x:x["contracts"][1].update({"shipper":"A Current RETALLY Customer"}))
        self._mutate(lambda x:x["contracts"][0].update({"document_url":"https://unverified.example/contract"}))
        self._mutate(lambda x:x["contracts"][0].update({"paid_invoice_cents":100000}))

    def test_latest_report_holds_both_contracts_as_externally_real_not_current_terms(self):
        r=sec.report()
        self.assertEqual(r["independently_published_original_SEC_agreements"],2)
        self.assertTrue(r["2026_EIA_prices_not_approved_for_2007_local_index"])
        self.assertTrue(r["current_signed_amendments_and_invoices_unverified"])
        self.assertEqual(r["actual_RETALLY_customer_invoices"],0)
        self.assertEqual(r["actual_RETALLY_overcharge_cents"],None)
        self.assertEqual(r["actual_RETALLY_recovery_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")


if __name__=="__main__":
    unittest.main()
