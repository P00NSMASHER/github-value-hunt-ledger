"""M43: adversarial source-level chronology/provenance/ledger tests.

Every scenario runs the actual independent read-only verifier against fresh,
unconstrained fictional SQLite and must have a signed synthetic known-good
positive control. This does NOT authenticate real providers or original bugs.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from freight.lab_assurance import AssuranceRejected, digest, verify_settlement
from freight import lab_settlement_source_m43 as m43
from freight.test_lab_assurance import (
    BUYER, BU, assertions_and_fees, fee, populate, verifier,
)

DAY=date(2026,10,13)


class M43SettlementSourceAndTemporal(unittest.TestCase):
    def test_all_twelve_real_source_denials_and_unchanged_fictional_good_controls(self):
        self.assertEqual(len(m43.REJECTIONS),12)
        for scenario, reason in m43.REJECTIONS.items():
            with self.subTest(scenario=scenario):
                r=m43.replay_one(scenario)
                self.assertEqual(r["scenario"],scenario)
                self.assertEqual(r["actual_exact_denial"],reason)
                self.assertEqual(r["expected_exact_denial"],reason)
                self.assertTrue(r["positive_control_passed"])
                self.assertTrue(r["negative_counterexample_rejected"])
                self.assertTrue(r["isolated_sqlite_changed"])
                self.assertFalse(r["source_input_had_real_bank_carrier_signatures"])
                self.assertFalse(r["original_archived_vulnerable_revision_replayed"])
                self.assertFalse(r["historical_recoveryos_finding_closed"])
                self.assertNotEqual(r["isolated_before_sha256"],r["isolated_after_sha256"])

    def test_fail_closed_campaign_preserves_all_original_human_gates(self):
        report=m43.run_campaign(as_of=DAY)
        self.assertEqual(report["scope"],m43.SCOPE)
        self.assertEqual(report["existing_research_lab"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["current_verifier_negative_scenarios"],12)
        self.assertEqual(report["known_good_synthetic_positive_controls"],12)
        self.assertEqual(report["current_verifier_exact_negative_denials"],12)
        self.assertEqual(len(report["cases"]),12)
        self.assertEqual(report["historical_original_findings_open"],26)
        self.assertEqual(report["historical_original_findings_closed"],0)
        self.assertEqual(report["archived_original_vulnerable_source_replayed"],0)
        self.assertEqual(report["unmet_independent_human_pilot_controls"],18)
        self.assertEqual(report["independent_customer_invoices_observed"],0)
        self.assertIsNone(report["actual_customer_cash_recovered"])
        self.assertEqual(report["external_empirical_claims_authorized"],0)
        self.assertFalse(report["live_carrier_or_bank_evidence_used"])
        self.assertFalse(report["production_deployment_or_schedules_modified"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_positive_buyer_disqualified_fee_with_zero_eligibility_still_valid(self):
        # A genuinely ineligible fee has zero eligible cents on BOTH original
        # allocations. The cash settlement remains valid but the fee journal
        # cannot contain any unearned fee event.
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"fictional.sqlite"
            populate(db)
            with sqlite3.connect(db) as con:
                con.execute("UPDATE recovery_claims SET fee_disqualified=1")
                con.execute("UPDATE allocations SET fee_eligible_cents=0")
            proofs,events=assertions_and_fees()
            passed=verify_settlement(
                db,buyer_id=BUYER,business_unit=BU,
                assertions=proofs,fee_events=[],verifier=verifier()
            )
            self.assertEqual(passed.currency_totals["USD"]["recovered_cents"],500)
            self.assertEqual(passed.currency_totals["USD"]["earned_fee_cents"],0)
            self.assertEqual(passed.currency_totals["USD"]["collected_fee_cents"],0)

    def test_return_then_new_credit_replenishes_without_transient_overcapacity(self):
        # Total lifetime allocated can exceed 1000 after a 500 return,
        # but the LIVE balance never exceeds 1000. A gross-ever cap would
        # incorrectly reject this valid synthetic replacement.
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"fictional.sqlite"
            populate(db)
            proofs,events=assertions_and_fees()
            from hashlib import sha256
            with sqlite3.connect(db) as con:
                m43._new_credit(
                    con,event_id="m43-clean-replacement",amount=500,
                    at="2026-12-15T12:00:00Z",
                    source_hash=sha256(b"m43-clean-replacement").hexdigest(),
                    proofs=proofs
                )
                con.execute(
                    "INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                    (BUYER,BU,"m43-clean-replacement-alloc","case-1",
                     "m43-clean-replacement",500,"REVIEW",500,
                     "2026-12-16T12:00:00Z")
                )
            events.extend([
                fee("ACCRUE",100,"2026-12-17T12:00:00Z","m43-earn-replacement"),
                fee("INVOICE",100,"2026-12-17T13:00:00Z","m43-invoice-replacement"),
            ])
            result=verify_settlement(db,buyer_id=BUYER,business_unit=BU,
                assertions=proofs,fee_events=events,verifier=verifier())
            usd=result.currency_totals["USD"]
            self.assertEqual(usd["recovered_cents"],1000)
            self.assertEqual(usd["earned_fee_cents"],200)
            self.assertEqual(usd["invoiced_fee_cents"],200)
            self.assertEqual(usd["collected_fee_cents"],100)
            self.assertEqual(usd["fee_receivable_cents"],100)

    def test_peak_overallocation_even_if_end_net_recovered_is_five_dollars(self):
        # In the attack, the extra interim 900 cents is backed by synthetic
        # provider/return signers, but its interim peak is 1300 > 1000.
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"fictional.sqlite"
            populate(db)
            proofs,events=assertions_and_fees()
            proofs=m43._mutate(db,"TRANSIENT_OVER_CLAIM_LIMIT",proofs)
            with sqlite3.connect(db) as con:
                gross=con.execute(
                    "SELECT SUM(amount_cents) FROM allocations"
                ).fetchone()[0]
                reversals=con.execute(
                    "SELECT SUM(amount_cents) FROM reversal_edges"
                ).fetchone()[0]
            self.assertEqual(gross,1900)
            self.assertEqual(reversals,1400)
            self.assertEqual(gross-reversals,500)
            with self.assertRaises(AssuranceRejected) as failed:
                m43._observe(db,proofs,events)
            self.assertEqual(failed.exception.code,
                             "TRANSIENT_CLAIM_CAPACITY_EXCEEDED")

    def test_wrong_denial_mechanism_fails_complete_test(self):
        good=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1,verified_receipts=2,
            currency_totals={"USD":m43.BASELINE_USD},
        )
        with patch.object(m43,"_observe",
                          side_effect=[good,AssuranceRejected("INVALID_UNRELATED_FEE")]):
            with self.assertRaisesRegex(ValueError,"M43_WRONG_REASON_IN_NEGATIVE_ASSURANCE"):
                m43.replay_one("DUPLICATE_CREDIT_SOURCE_HASH")

    def test_false_positive_not_a_valid_rejection(self):
        good=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1,verified_receipts=2,
            currency_totals={"USD":m43.BASELINE_USD},
        )
        with patch.object(m43,"_observe",return_value=good):
            with self.assertRaisesRegex(ValueError,"M43_CURRENT_VERIFIER_ACCEPTED_UNSAFE_SETTLEMENT"):
                m43.replay_one("TRANSIENT_OVER_CLAIM_LIMIT")

    def test_unknown_scenarios_cannot_run_or_inject_arbitrary_sql(self):
        for scenario in ("",None,True,5,"allocations", "RETURN_USER_DATA",
                         "X'; DROP TABLE recovery_claims;--"):
            with self.subTest(scenario=scenario):
                with self.assertRaisesRegex(ValueError,"M43_UNKNOWN_ADVERSARIAL_SCENARIO"):
                    m43.replay_one(scenario)
                with tempfile.TemporaryDirectory() as td:
                    db=Path(td)/"s.sqlite"
                    populate(db)
                    before=db.read_bytes()
                    with self.assertRaisesRegex(ValueError,"M43_UNKNOWN_ADVERSARIAL_SCENARIO"):
                        m43._mutate(db,scenario,[])
                    self.assertEqual(before,db.read_bytes())

    def test_bad_positive_money_receipt_not_silently_accepted(self):
        bad=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1,verified_receipts=2,
            currency_totals={"USD":{**m43.BASELINE_USD,
                                    "recovered_cents":9999999}},
        )
        with patch.object(m43,"_observe",return_value=bad):
            with self.assertRaisesRegex(ValueError,"M43_POSITIVE_SYNTHETIC_MONEY_CHAIN_BROKEN"):
                m43.replay_one("SIGNED_MALFORMED_SOURCE_HASH")

    def test_report_escapes_source_names_and_rejects_public_authorization(self):
        report=m43.run_campaign(as_of=DAY)
        altered=deepcopy(report)
        altered["cases"][0]["scenario"]="<script>alert(1)</script>"
        html=m43.render_html(altered)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 original findings remain open",html)
        self.assertIn("INTERNAL ONLY",html)
        self.assertEqual(report["external_empirical_claims_authorized"],0)

    def test_malformed_date_rejected_before_source_mutation(self):
        for as_of in (None,True,1,"2026-10-13",date(2026,10,12)):
            with self.subTest(as_of=as_of):
                with self.assertRaisesRegex(ValueError,"M43_INVALID_RESEARCH_AS_OF"):
                    m43.run_campaign(as_of=as_of)

    def test_cli_writes_both_derived_reports_or_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=root/"ok"
            with patch("sys.argv",[
                "m43","--as-of-date","2026-10-13","--out",str(out)
            ]):
                m43.main()
            r=json.loads((out/"settlement_source_m43.json").read_text())
            self.assertEqual(r["current_verifier_exact_negative_denials"],12)
            self.assertEqual(r["historical_original_findings_closed"],0)
            self.assertTrue((out/"settlement_source_m43.html").is_file())
            fail=root/"no-output"
            with patch("sys.argv",[
                "m43","--as-of-date","2026-10-12","--out",str(fail)
            ]):
                with self.assertRaises(ValueError):
                    m43.main()
            self.assertFalse(fail.exists())


if __name__=="__main__":
    unittest.main()
