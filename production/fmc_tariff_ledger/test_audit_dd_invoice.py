import unittest

import audit_dd_invoice as dd


class DDInvoiceAuditTests(unittest.TestCase):
    def base(self, **overrides):
        values = dict(
            invoice_id="INV-1",
            billing_party_type="vocc",
            billed_party_type="shipper",
            charge_type="demurrage",
            invoice_date="2026-06-20",
            invoice_due_date="2026-07-20",
            total_amount="1500",
            currency="USD",
            bill_of_lading_numbers="BOL123",
            container_numbers="CONT123",
            movement="import",
            discharge_ports="Los Angeles",
            liability_basis="Contracting shipper",
            allowed_free_time_days="4",
            free_time_start_date="2026-06-01",
            free_time_end_date="2026-06-04",
            container_availability_date="2026-06-01",
            earliest_return_date="",
            charged_dates="2026-06-05 through 2026-06-10",
            governing_rule_reference="Tariff 001 Rule 21",
            specific_rates="USD 250/day",
            dispute_contact="billing@example.test",
            dispute_instructions_url="https://example.test/disputes",
            mitigation_request_window_days="30",
            mitigation_resolution_window_days="30",
            later_resolution_date_agreed="",
            certification_fmc_rules="Charges comply with FMC rules",
            certification_billing_party_no_contribution="Billing party did not cause charges",
            charge_last_incurred_date="2026-06-10",
            upstream_invoice_date="",
        )
        values.update(overrides)
        return dd.DDInvoiceInput(**values)

    def test_complete_timely_invoice_passes_checked_fields(self):
        result = dd.audit_invoice(self.base())
        self.assertEqual(result["status"], "COMPLIANT_ON_CHECKED_FIELDS")
        self.assertEqual(result["potential_charge_relief_amount"], "0.00")

    def test_missing_required_content_routes_full_charge_to_review(self):
        result = dd.audit_invoice(self.base(bill_of_lading_numbers=""))
        self.assertEqual(result["status"], "POTENTIAL_NO_PAYMENT_OBLIGATION_REVIEW")
        self.assertIn("bill_of_lading_numbers", result["missing_required_fields"])
        self.assertEqual(result["potential_charge_relief_amount"], "1500.00")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_late_vocc_invoice_routes_full_charge_to_review(self):
        result = dd.audit_invoice(
            self.base(
                invoice_date="2026-07-12",
                charge_last_incurred_date="2026-06-10",
            )
        )
        self.assertEqual(result["status"], "POTENTIAL_NO_PAYMENT_OBLIGATION_REVIEW")
        self.assertEqual(result["days_to_issue"], 32)
        self.assertTrue(any(f["code"] == "LATE_INVOICE" for f in result["findings"]))

    def test_nvocc_uses_upstream_invoice_date_for_timing(self):
        result = dd.audit_invoice(
            self.base(
                billing_party_type="nvocc",
                invoice_date="2026-07-02",
                upstream_invoice_date="2026-06-01",
                charge_last_incurred_date="2026-05-15",
            )
        )
        self.assertEqual(result["status"], "POTENTIAL_NO_PAYMENT_OBLIGATION_REVIEW")
        self.assertEqual(result["timing_basis"], "upstream_invoice_date")
        self.assertEqual(result["days_to_issue"], 31)

    def test_missing_timing_basis_is_unverifiable_not_automatic_relief(self):
        result = dd.audit_invoice(self.base(charge_last_incurred_date=""))
        self.assertEqual(result["status"], "CONTENT_COMPLETE_TIMING_UNVERIFIABLE")
        self.assertEqual(result["potential_charge_relief_amount"], "0.00")

    def test_short_mitigation_request_window_is_process_review_only(self):
        result = dd.audit_invoice(
            self.base(mitigation_request_window_days="20")
        )
        self.assertEqual(result["status"], "PROCESS_NONCOMPLIANCE_REVIEW")
        self.assertEqual(result["potential_charge_relief_amount"], "0.00")
        self.assertTrue(any(
            f["code"] == "DISPUTE_WINDOW_NONCOMPLIANCE"
            for f in result["findings"]
        ))

    def test_resolution_over_30_days_allowed_when_later_date_agreed(self):
        result = dd.audit_invoice(
            self.base(
                mitigation_resolution_window_days="45",
                later_resolution_date_agreed="2026-08-10",
            )
        )
        self.assertEqual(result["status"], "COMPLIANT_ON_CHECKED_FIELDS")

    def test_export_requires_earliest_return_not_import_availability(self):
        item = self.base(
            movement="export",
            discharge_ports="",
            container_availability_date="",
            earliest_return_date="2026-05-29",
        )
        result = dd.audit_invoice(item)
        self.assertEqual(result["status"], "COMPLIANT_ON_CHECKED_FIELDS")
        self.assertNotIn("container_availability_date", result["required_field_presence"])
        self.assertIn("earliest_return_date", result["required_field_presence"])

    def test_pre_may_28_2024_invoice_is_outside_full_rule_gate(self):
        result = dd.audit_invoice(
            self.base(
                invoice_date="2024-05-20",
                invoice_due_date="2024-06-20",
                charge_last_incurred_date="2024-05-15",
                free_time_start_date="2024-05-01",
                free_time_end_date="2024-05-04",
                container_availability_date="2024-05-01",
                charged_dates="2024-05-05 through 2024-05-10",
            )
        )
        self.assertEqual(result["status"], "OUTSIDE_FULL_PART_541_EFFECTIVE_PERIOD")

    def test_engine_does_not_apply_vacated_541_4_proper_party_rule(self):
        result = dd.audit_invoice(self.base())
        self.assertIn("No §541.4 proper-party determination", result["excluded_rule_note"])


    def test_intercarrier_terminal_billing_never_creates_potential_recovery(self):
        # Current 46 CFR 541.2(b) excludes inter-carrier/MTO billing
        # relationships. Type evidence alone is insufficient to adjudicate
        # an actual legal exemption; scope must receive manual review.
        for biller, billed in (
            ("vocc", "nvocc"), ("vocc", "mto"),
            ("nvocc", "vocc"), ("mto", "vocc"),
            ("mto", "mto"),
        ):
            with self.subTest(biller=biller, billed=billed):
                r = dd.audit_invoice(self.base(
                    billing_party_type=biller,
                    billed_party_type=billed,
                    bill_of_lading_numbers="",
                    charge_last_incurred_date="2026-04-01",
                ))
                self.assertEqual(r["status"], "INTERCARRIER_TERMINAL_SCOPE_REVIEW")
                self.assertEqual(r["potential_charge_relief_amount"], "0.00")
                self.assertEqual(r["asserted_recovery"], "0.00")

    def test_unverified_billed_party_scope_blocks_money_even_if_other_fields_fail(self):
        for who in ("", "unrecognized-party"):
            with self.subTest(who=who):
                r = dd.audit_invoice(self.base(
                    billed_party_type=who,
                    bill_of_lading_numbers="",
                    charge_last_incurred_date="2026-01-01",
                ))
                self.assertEqual(r["status"], "BILLING_RELATIONSHIP_UNVERIFIED_REVIEW")
                self.assertEqual(r["potential_charge_relief_amount"], "0.00")
                self.assertEqual(r["asserted_recovery"], "0.00")

    def test_valid_external_billed_parties_remain_reviewable_not_5414_judgments(self):
        for party in ("shipper", "consignee", "cargo_owner",
                      "freight_forwarder", "truck_operator", "other"):
            with self.subTest(party=party):
                r=dd.audit_invoice(self.base(billed_party_type=party))
                self.assertEqual(r["status"], "COMPLIANT_ON_CHECKED_FIELDS")
                self.assertIn("No §541.4",r["excluded_rule_note"])
                self.assertEqual(r["potential_charge_relief_amount"], "0.00")

    def test_nonfinite_negative_and_subcent_money_are_rejected_without_rounding(self):
        for bad in ("NaN", "sNaN", "Infinity", "-Infinity",
                    "-1500", "1.234", "0.001", "1.235", "1e1000"):
            with self.subTest(amount=bad), self.assertRaises(ValueError):
                dd.audit_invoice(self.base(
                    total_amount=bad,
                    bill_of_lading_numbers="",
                ))
        r=dd.audit_invoice(self.base(total_amount="1500.000"))
        self.assertEqual(r["total_amount"],"1500.00")
        self.assertEqual(r["potential_charge_relief_amount"],"0.00")

    def test_invoice_before_charge_is_not_mistaken_for_timely_compliance(self):
        r=dd.audit_invoice(self.base(
            invoice_date="2026-06-20",
            charge_last_incurred_date="2026-06-25",
            bill_of_lading_numbers="",
        ))
        self.assertEqual(r["status"], "SOURCE_TIMELINE_INCONSISTENCY_REVIEW")
        self.assertEqual(r["potential_charge_relief_amount"], "0.00")
        self.assertEqual(r["asserted_recovery"], "0.00")
        self.assertIn("invoice_date_before_charge_last_incurred_date",
                      r["source_date_issues"])
        self.assertFalse(any(f["code"] == "LATE_INVOICE" for f in r["findings"]))

    def test_nvocc_invoice_before_upstream_bill_is_review_not_relief(self):
        r=dd.audit_invoice(self.base(
            billing_party_type="nvocc",
            invoice_date="2026-06-20",
            upstream_invoice_date="2026-06-25",
        ))
        self.assertEqual(r["status"], "SOURCE_TIMELINE_INCONSISTENCY_REVIEW")
        self.assertEqual(r["potential_charge_relief_amount"], "0.00")
        self.assertIn("invoice_date_before_upstream_invoice_date",
                      r["source_date_issues"])

    def test_invalid_due_date_or_free_time_sequence_is_not_compliance(self):
        examples=(
            ({"invoice_due_date":"2026-06-19"},
             "invoice_due_date_before_invoice_date"),
            ({"free_time_start_date":"2026-06-10",
              "free_time_end_date":"2026-06-01"},
             "free_time_end_before_free_time_start"),
        )
        for fields, issue in examples:
            with self.subTest(issue=issue):
                r=dd.audit_invoice(self.base(**fields))
                self.assertEqual(r["status"],"SOURCE_TIMELINE_INCONSISTENCY_REVIEW")
                self.assertEqual(r["potential_charge_relief_amount"],"0.00")
                self.assertIn(issue,r["source_date_issues"])

    def test_malformed_important_source_dates_and_days_fail_closed(self):
        for fields in (
            {"invoice_due_date":"2026-99-99"},
            {"free_time_start_date":"2026-02-30"},
            {"free_time_end_date":"tomorrow"},
            {"container_availability_date":"2026-13-01"},
            {"allowed_free_time_days":"unparseable"},
            {"later_resolution_date_agreed":"yes-no-date"},
        ):
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                dd.audit_invoice(self.base(**fields))

    def test_missing_original_timing_basis_never_counts_a_legal_violation(self):
        r=dd.audit_invoice(self.base(
            charge_last_incurred_date="",bill_of_lading_numbers="",
            billed_party_type="",
        ))
        self.assertEqual(r["status"],"BILLING_RELATIONSHIP_UNVERIFIED_REVIEW")
        self.assertEqual(r["potential_charge_relief_amount"],"0.00")
        self.assertEqual(r["asserted_recovery"],"0.00")


if __name__ == "__main__":
    unittest.main()
