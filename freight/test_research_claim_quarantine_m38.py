"""M38: safe internal-only values and independently unmet source replay controls."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import research_claim_quarantine_m38 as m38
from freight import research_source_lineage_m37 as m37
from freight.research_evidence_gate import canon_hash

TODAY = date(2026, 10, 12)
ROOT_IMPACT = {
    "BEA": ["M35-01", "M35-03", "M35-04", "M35-05", "M35-08"],
    "CENSUS": ["M35-02", "M35-03", "M35-04", "M35-07"],
    "BLS_PPI": ["M35-07", "M35-08"],
    "BLS_SECTORAL": ["M35-06"],
}
VALUES = {
    "M35-01": "545435.000",
    "M35-02": "402827.246",
    "M35-03": "142607.754",
    "M35-04": "73.85",
    "M35-05": "8.05",
    "M35-06": "4.02",
    "M35-07": "1.18",
    "M35-08": "0.45",
}


class ClaimQuarantineM38Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A real, independently M35/M34-policy-validated offline baseline,
        # reused only within these tests to avoid repeatedly replaying
        # hundreds of historical source policy checks.
        cls.original = m37._baseline(as_of=TODAY)

    def report(self, candidate=None):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            return m38.report_shell(as_of=TODAY, candidate=candidate)

    def candidate(self, root, value="0" * 64):
        return m37.candidate_template(as_of=TODAY, root=root, digest=value)

    def test_baseline_has_eight_original_qualified_internal_values(self):
        r = self.report()
        self.assertEqual(r["scope"], m38.SCOPE)
        self.assertEqual(r["existing_lab_number"], 14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["source_family_count"], 5)
        self.assertEqual(r["qualified_historical_source_claims"], 8)
        self.assertEqual(r["qualified_values_still_visible_for_internal_research_only"], 8)
        self.assertEqual(r["qualified_values_withheld_pending_independent_replay"], 0)
        self.assertEqual(r["quarantined_claim_ids"], [])
        self.assertEqual(r["independent_source_revalidation_queue"], [])
        self.assertEqual(r["independently_unverified_human_pilot_controls"], 18)
        self.assertEqual(r["external_claims_authorized"], 0)
        self.assertEqual(
            {c["claim_id"]: c["safe_internal_value"] for c in r["claims"][:8]}, VALUES
        )

    def test_each_single_source_blocks_only_exact_dependent_internal_values(self):
        for root, expected in ROOT_IMPACT.items():
            with self.subTest(source=root):
                r = self.report(self.candidate(root))
                self.assertEqual(r["quarantined_claim_ids"], expected)
                self.assertEqual(
                    r["qualified_values_withheld_pending_independent_replay"],
                    len(expected)
                )
                self.assertEqual(
                    r["qualified_values_still_visible_for_internal_research_only"],
                    8 - len(expected)
                )
                self.assertEqual(r["pending_source_replay_count"], 1)
                self.assertEqual(
                    r["independent_source_revalidation_queue"][0]["affected_claim_ids"],
                    expected
                )
                for c in r["claims"][:8]:
                    if c["claim_id"] in expected:
                        self.assertIsNone(c["safe_internal_value"])
                        self.assertEqual(c["internal_access_status"], m38.STATUSES["WITHHELD"])
                    else:
                        self.assertEqual(c["safe_internal_value"], VALUES[c["claim_id"]])

    def test_redacted_historical_values_do_not_leak_in_m37_json_or_m38_html(self):
        case = self.candidate("CENSUS")
        r = self.report(case)
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            old = m37.report_shell(as_of=TODAY, candidate=case)
        impacted = ROOT_IMPACT["CENSUS"]
        for row in old["claims"]:
            if row["claim_id"] in impacted:
                self.assertIsNone(row["prior_internal_value"])
                self.assertTrue(row["historical_value_withheld_for_unverified_candidate_change"])
            elif row["metric_key"] is not None:
                self.assertFalse(row["historical_value_withheld_for_unverified_candidate_change"])
        human = m38.render_html(r)
        for raw in ("402827.246", "142607.754", "73.85", "1.18"):
            self.assertNotIn(raw, human)
        self.assertIn("WITHHELD", human)
        self.assertIn("18/18", human)

    def test_all_macro_source_families_change_withholds_eight_metrics(self):
        input_ = self.candidate("BEA")
        input_["source_receipts"].update({
            "CENSUS": "1" * 64,
            "BLS_PPI": "2" * 64,
            "BLS_SECTORAL": "3" * 64,
        })
        r = self.report(input_)
        self.assertEqual(r["qualified_values_withheld_pending_independent_replay"], 8)
        self.assertEqual(r["qualified_values_still_visible_for_internal_research_only"], 0)
        self.assertEqual(r["quarantined_claim_ids"],
                         [f"M35-{n:02d}" for n in range(1, 9)])
        self.assertEqual(r["pending_source_replay_count"], 4)
        self.assertEqual(
            [q["root"] for q in r["independent_source_revalidation_queue"]],
            ["BEA", "CENSUS", "BLS_PPI", "BLS_SECTORAL"]
        )
        self.assertTrue(all(x["safe_internal_value"] is None for x in r["claims"]))

    def test_multiple_changes_make_deduplicated_union(self):
        case = self.candidate("CENSUS")
        case["source_receipts"]["BEA"] = "1" * 64
        r = self.report(case)
        self.assertEqual(r["qualified_values_withheld_pending_independent_replay"], 7)
        self.assertEqual(len(set(r["quarantined_claim_ids"])), 7)
        self.assertEqual(r["claims"][2]["changed_untrusted_source_families"],
                         ["BEA", "CENSUS"])
        self.assertEqual(r["pending_source_replay_count"], 2)
        self.assertEqual(r["external_claims_authorized"], 0)

    def test_pilot_change_does_not_change_original_statistical_sources(self):
        r = self.report(self.candidate("PILOT"))
        self.assertEqual(r["qualified_values_withheld_pending_independent_replay"], 0)
        self.assertEqual(r["qualified_values_still_visible_for_internal_research_only"], 8)
        self.assertEqual(r["pending_source_replay_count"], 1)
        task = r["independent_source_revalidation_queue"][0]
        self.assertEqual(task["root"], "PILOT")
        self.assertEqual(task["affected_claim_ids"],
                         [f"M35-{n:02d}" for n in range(1, 17)])
        self.assertFalse(task["human_approval_reported_by_this_module"])
        self.assertEqual(r["independently_unverified_human_pilot_controls"], 18)

    def test_same_date_matching_digest_proves_no_new_freshness(self):
        r = self.report(self.candidate("BEA", self.original[1]["BEA"]))
        self.assertEqual(r["candidate_source_deltas_unverified"], [])
        self.assertEqual(r["pending_source_replay_count"], 0)
        self.assertFalse(r["source_revision_independently_verified"])
        self.assertEqual(r["independent_original_publisher_replays_in_this_run"], 0)
        self.assertTrue(r["candidate_digest_matching_cannot_establish_source_freshness"])
        self.assertEqual(r["qualified_values_still_visible_for_internal_research_only"], 8)

    def test_unchanged_and_quarantined_claim_views_enforce_explicit_purpose(self):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            unchanged = m38.claim_view(as_of=TODAY, claim_id="M35-01",
                                       purpose=m38.INTERNAL)
            redacted = m38.claim_view(as_of=TODAY, claim_id="M35-02",
                                      purpose=m38.INTERNAL,
                                      candidate=self.candidate("CENSUS"))
            external = m38.claim_view(as_of=TODAY, claim_id="M35-01",
                                      purpose=m38.EXTERNAL)
        self.assertEqual(unchanged["safe_value"], "545435.000")
        self.assertEqual(unchanged["decision"], m38.STATUSES["VISIBLE"])
        self.assertIsNone(redacted["safe_value"])
        self.assertEqual(redacted["decision"], m38.STATUSES["WITHHELD"])
        self.assertIsNone(external["safe_value"])
        self.assertFalse(external["external_publication_authorized"])
        self.assertIn("BLOCKED_ALL_EXTERNAL", external["decision"])

    def test_all_eight_unsupported_real_customer_inferences_stay_blocked(self):
        for root in m38.ROOTS:
            r = self.report(self.candidate(root))
            self.assertEqual(r["prohibited_customer_market_claims_blocked"], 8)
            self.assertTrue(all(x["safe_internal_value"] is None for x in r["claims"][8:]))
            self.assertTrue(all(x["internal_access_status"] == m38.STATUSES["BLOCKED"]
                                for x in r["claims"][8:]))
            self.assertTrue(all(x["external_publication_authorized"] is False
                                for x in r["claims"]))
            self.assertIsNone(r["net_cash_recovered_usd"])
            self.assertIsNone(r["recoverable_market_tam_usd"])
            self.assertEqual(r["actual_customer_invoices_observed"], 0)

    def test_strict_claim_ids_and_audiences_not_free_form_publication(self):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            for cid in ("M35-00", "M35-17", "INVENTED", "", 123, None):
                with self.subTest(claim_id=cid), self.assertRaisesRegex(
                    ValueError, "UNKNOWN_CLAIM"
                ):
                    m38.claim_view(as_of=TODAY, claim_id=cid, purpose=m38.INTERNAL)
            for purpose in ("PUBLICATION_APPROVED", "CLIENT_CONTACT", "INTERNAL",
                            "internal_research", None, True):
                with self.subTest(purpose=purpose), self.assertRaisesRegex(
                    ValueError, "UNRECOGNIZED_CLAIM_USE"
                ):
                    m38.claim_view(as_of=TODAY, claim_id="M35-01", purpose=purpose)

    def test_forged_publisher_replay_or_real_buyer_approvals_rejected(self):
        for key in ("original_publisher_replay_verified",
                    "real_customer_evidence_verified",
                    "external_publication_authorized"):
            case = self.candidate("BEA")
            case[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(
                ValueError, "FALSE_APPROVAL"
            ):
                self.report(case)

    def test_reject_hidden_authentication_or_private_customer_data_fields(self):
        for name, value in (
            ("report_receipt", "a" * 64),
            ("verified_by", "human@example.com"),
            ("private_invoice_upload", "/tmp/client.pdf"),
            ("publisher_checksum_attested", True),
            ("claim_results", [{"id": "M35-03", "publish": True}]),
        ):
            case = self.candidate("CENSUS")
            case[name] = value
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError, "FALSE_APPROVAL"
            ):
                self.report(case)

    def test_wrong_dates_unregistered_sources_invalid_digests_fail_closed(self):
        broken = []
        a = self.candidate("BEA")
        a["as_of"] = "2026-10-13"
        broken.append(a)
        a = self.candidate("BEA")
        a["source_receipts"] = {"BROKER_INVOICES": "0" * 64}
        broken.append(a)
        a = self.candidate("BEA")
        a["source_receipts"] = {"BEA": "zero"}
        broken.append(a)
        a = self.candidate("BEA")
        a["source_receipts"] = {}
        broken.append(a)
        for item in broken:
            with self.subTest(candidate=item), self.assertRaises(ValueError):
                self.report(item)

    def test_policy_bypass_with_bool_schema_versions_rejected(self):
        for version in (True, False, 0, "1", 2, None):
            c = self.candidate("BLS_PPI")
            c["schema_version"] = version
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.report(c)

    def test_rehashed_m37_report_injecting_stale_value_is_not_accepted(self):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            source = m37.report_shell(as_of=TODAY, candidate=self.candidate("CENSUS"))
        forged = deepcopy(source)
        forged["claims"][1]["prior_internal_value"] = VALUES["M35-02"]
        forged["receipt_sha256"] = canon_hash({
            k: v for k, v in forged.items() if k != "receipt_sha256"
        })
        with patch.object(m38.m37, "report_shell", return_value=forged):
            with self.assertRaisesRegex(ValueError, "STALE_SOURCE_VALUE_EXPOSED"):
                m38.report_shell(as_of=TODAY, candidate=self.candidate("CENSUS"))

    def test_rehashed_m37_report_attempting_to_clear_quarantine_rejected(self):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            source = m37.report_shell(as_of=TODAY, candidate=self.candidate("BLS_PPI"))
        forged = deepcopy(source)
        forged["claims"][6]["source_revalidation_required"] = False
        forged["receipt_sha256"] = canon_hash({
            k: v for k, v in forged.items() if k != "receipt_sha256"
        })
        with patch.object(m38.m37, "report_shell", return_value=forged):
            with self.assertRaisesRegex(ValueError, "DID_NOT_FOLLOW_ROOT_CHANGE"):
                m38.report_shell(as_of=TODAY, candidate=self.candidate("BLS_PPI"))

    def test_m37_untrusted_report_cannot_grant_public_claims(self):
        with patch.object(m38.m37, "_baseline", return_value=self.original):
            source = m37.report_shell(as_of=TODAY)
        forged = deepcopy(source)
        forged["external_commercial_claims_authorized"] = 1
        with patch.object(m38.m37, "report_shell", return_value=forged):
            with self.assertRaisesRegex(ValueError, "BOUNDARY_BROKEN"):
                m38.report_shell(as_of=TODAY)

    def test_revalidation_task_has_source_specific_steps_not_automatic_approval(self):
        all_ = self.candidate("BEA")
        for source in m38.ROOTS:
            all_["source_receipts"][source] = "0" * 64
        r = self.report(all_)
        self.assertEqual([x["root"] for x in r["independent_source_revalidation_queue"]],
                         list(m38.ROOTS))
        for q in r["independent_source_revalidation_queue"]:
            self.assertTrue(q["hypothetical_only_not_authenticated_publisher_change"])
            self.assertFalse(q["human_approval_reported_by_this_module"])
            self.assertFalse(q["publication_authorized_by_this_module"])
            self.assertTrue(q["original_evidence_description"])
            self.assertGreaterEqual(len(q["necessary_independent_replay_steps"]), 3)
        self.assertIn("PCU484", m38.REPLAY["BLS_PPI"]["controlling_original"])
        self.assertIn("TGO105", m38.REPLAY["BEA"]["controlling_original"])
        self.assertIn("SAS-to-AIES", m38.REPLAY["CENSUS"]["controlling_original"])

    def test_date_bounds_and_type_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError, "BEFORE_EXISTING"):
            m38.report_shell(as_of=date(2026, 10, 11))
        with self.assertRaisesRegex(ValueError, "BEFORE_EXISTING"):
            m38.report_shell(as_of="2026-10-12")

    def test_local_receipt_not_independent_proof(self):
        r = self.report(self.candidate("BEA"))
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k: v for k, v in r.items() if k != "receipt_sha256"
        }))
        self.assertFalse(r["source_revision_independently_verified"])
        self.assertEqual(r["independent_original_publisher_replays_in_this_run"], 0)
        self.assertFalse(r["pilot_gate_independently_satisfied_by_this_module"])
        self.assertTrue(r["no_customer_or_carrier_contact_or_data_import"])
        self.assertTrue(r["no_new_schedule_or_production_change"])

    def test_html_escapes_supplied_text_and_no_active_scripts(self):
        r = self.report(self.candidate("BEA"))
        malicious = deepcopy(r)
        malicious["claims"][0]["mandatory_internal_caveat"] = "<script>alert(1)</script>"
        malicious["independent_source_revalidation_queue"][0][
            "original_evidence_description"] = "<img src=x onerror=alert(1)>"
        html = m38.render_html(malicious)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img", html)
        self.assertIn("0 external claims", html)

    def test_cli_writes_report_and_redacts_census_values(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            candidate = root / "hypothetical.json"
            target = root / "result"
            candidate.write_text(json.dumps(self.candidate("CENSUS")),
                                 encoding="utf-8")
            with patch("sys.argv", ["m38", "--as-of-date", TODAY.isoformat(),
                                    "--candidate", str(candidate), "--out", str(target)]):
                m38.main()
            report = json.loads((target / "claim_quarantine.json").read_text())
            self.assertEqual(report["quarantined_claim_ids"], ROOT_IMPACT["CENSUS"])
            html = (target / "claim_quarantine.html").read_text()
            self.assertNotIn("142607.754", html)
            self.assertEqual(report["external_claims_authorized"], 0)

    def test_invalid_candidate_cli_does_not_create_output_directory(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            data = self.candidate("BEA")
            data["external_publication_authorized"] = True
            candidate = root / "forged.json"
            candidate.write_text(json.dumps(data))
            target = root / "not-created"
            with patch("sys.argv", ["m38", "--as-of-date", TODAY.isoformat(),
                                    "--candidate", str(candidate), "--out", str(target)]):
                with self.assertRaisesRegex(ValueError, "FALSE_APPROVAL"):
                    m38.main()
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
