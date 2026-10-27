"""Superseded historical freight decision: offline provenance/label guardrails."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from freight.unified_research_lab import SEEDS, safe_url

PACK = Path(__file__).with_name("fixtures") / "gao_b215958_supersession_candidate_v0.json"
URLS = ("https://www.gao.gov/products/b-215958",
        "https://www.gao.gov/products/b-215958-2")

class GAOB215958SupersessionTests(unittest.TestCase):
    @staticmethod
    def read():
        return json.loads(PACK.read_text(encoding="utf-8"))

    def assert_contract(self, x):
        self.assertEqual(set(x), {"schema_version","evaluation_family","engines",
            "provenance","sources","decision_facts","rights","cohort",
            "synthetic_negative_controls","acceptance"})
        self.assertEqual(x["schema_version"],"0.1.0")
        self.assertEqual(x["evaluation_family"],
                         "GAO_FREIGHT_SUPERSEDED_DECISION_PAIR_HISTORICAL_NEGATIVE_CONTROL")
        self.assertEqual(x["engines"], ["freightrecovery","recoveryos"])
        p=x["provenance"]
        self.assertEqual(p["canonical_repository"],"P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(p["operational_writer"],"research/retally-unified-data-lab")
        for k in ("operational_writer_modified","provider_allowlist_changed",
                  "original_publisher_byte_hash_verified"):
            self.assertIs(p[k],False)
        self.assertEqual(len(x["sources"]),2)
        expected=(("GAO_B215958_1984","1984-12-05",
                   "INITIAL_REFUND_INSTRUCTION_LATER_OVERRULED"),
                  ("GAO_B215958_1986","1986-02-18",
                   "RECONSIDERATION_OVERRULED_1984_SUSTAINED_GSA_DEDUCTIONS"))
        keys={"id","url","publisher","decision_date","decision_outcome",
              "publisher_html_highlights_reviewed","original_publisher_response_bytes_acquired",
              "original_publisher_response_sha256","original_gbl_or_governing_tariff_pages_custodied",
              "tariff_effective_date","independent_cash_refund_receipt"}
        for row,url,(ident,date,outcome) in zip(x["sources"],URLS,expected):
            self.assertEqual(set(row),keys)
            self.assertEqual((row["id"],row["url"],row["decision_date"],row["decision_outcome"]),
                             (ident,url,date,outcome))
            self.assertEqual(row["publisher"],"U.S. Government Accountability Office")
            self.assertIs(row["original_publisher_response_bytes_acquired"],False)
            self.assertIsNone(row["original_publisher_response_sha256"])
            self.assertIs(row["original_gbl_or_governing_tariff_pages_custodied"],False)
            self.assertIsNone(row["tariff_effective_date"])
            self.assertEqual(row["independent_cash_refund_receipt"],"UNKNOWN")
        d=x["decision_facts"]
        self.assertEqual((d["gbls_initially_at_issue"],d["gbls_noting_seal_numbers"],
                          d["other_gbls"]),(55,53,2))
        for k in ("initial_decision_instructed_refund","initial_decision_overruled",
                  "gsa_deduction_sustained_on_reconsideration"):
            self.assertIs(d[k],True)
        for k in ("seal_notation_alone_satisfies_written_exclusive_use_request",
                  "shipper_written_exclusive_use_request_established",
                  "initial_decision_final_binding_outcome"):
            self.assertIs(d[k],False)
        for k in ("current_customer_freight_error_ground_truth",
                  "actual_subsequent_refund_received",
                  "contemporary_tariff_or_legal_applicability"):
            self.assertEqual(d[k],"UNKNOWN")
        r=x["rights"]
        self.assertEqual(r["terms_url"],"https://www.gao.gov/copyright")
        for k in ("gao_authored_material_us_public_domain",
                  "publisher_attribution_required","no_implied_endorsement"):
            self.assertIs(r[k],True)
        for k in ("third_party_material_cleared","commercial_customer_engine_use_approved"):
            self.assertIs(r[k],False)
        c=x["cohort"]
        self.assertEqual(c["official_historical_decisions"],2)
        for k in ("original_gbls_in_custody","independent_held_out_real_customer_labels",
                  "verified_current_customer_errors","verified_retally_customer_cash_cents"):
            self.assertEqual(c[k],0)
        self.assertIs(c["freight_error_scoring_eligible"],False)
        controls=x["synthetic_negative_controls"]
        self.assertEqual(len(controls),5)
        self.assertEqual(len(set(c["id"] for c in controls)),5)
        for c in controls:
            self.assertEqual(set(c),{"id","kind","expected","real_customer_ground_truth"})
            self.assertTrue(c["id"].startswith("SYNTH_B215958_"))
            self.assertEqual(c["kind"],"SYNTHETIC")
            self.assertIsNone(c["real_customer_ground_truth"])
        a=x["acceptance"]
        self.assertIs(a["source_pointers_already_in_existing_candidate"],True)
        for k in ("independent_qa_passed","guarded_release_authorized",
                  "production_code_changed"):
            self.assertIs(a[k],False)

    def test_real_publisher_refs_already_preserved_without_new_seeds(self):
        self.assert_contract(self.read())
        for url in URLS:
            self.assertEqual(safe_url(url),url)
            self.assertEqual(SEEDS["freightrecovery"].count(url),1)

    def test_mutations_do_not_promote_superseded_decision_or_refund_to_truth(self):
        x=self.read()
        changes=[
            ("decision_facts","initial_decision_overruled",False),
            ("decision_facts","initial_decision_final_binding_outcome",True),
            ("decision_facts","seal_notation_alone_satisfies_written_exclusive_use_request",True),
            ("decision_facts","actual_subsequent_refund_received","PAID"),
            ("decision_facts","gbls_noting_seal_numbers",55),
            ("rights","commercial_customer_engine_use_approved",True),
            ("rights","third_party_material_cleared",True),
            ("cohort","independent_held_out_real_customer_labels",53),
            ("cohort","verified_retally_customer_cash_cents",1),
            ("acceptance","guarded_release_authorized",True)]
        for section,key,value in changes:
            bad=copy.deepcopy(x)
            bad[section][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):
                self.assert_contract(bad)
        bad=copy.deepcopy(x)
        bad["sources"][0]["unreviewed_claim_of_payment"]="PAID"
        with self.assertRaises(AssertionError):
            self.assert_contract(bad)

if __name__ == "__main__":
    unittest.main()
