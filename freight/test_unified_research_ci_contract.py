"""Reject CI command folding that silently omits research evaluation exercises.

This checks executable lines inside the GitHub Actions verify job. It does not
claim independent ground-truth labels or approval of external source rights.
"""
from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "retally-unified-research-lab.yml"


class ResearchCIVerificationContract(unittest.TestCase):
    def test_node_bridge_and_frozen_pack_are_separate_executable_commands(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n  verify:\n"), 1)
        self.assertEqual(text.count("\n  discover:\n"), 1)
        verify = text.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        expected = (
            "          node --test freight/research_lab_worker.test.mjs",
            "          python -m unittest -q freight.test_research_eval_bridge freight.test_unified_research_ci_contract",
            "          python -m freight.real_world_eval_v1",
        )
        lines = verify.splitlines()
        for command in expected:
            with self.subTest(command=command.strip()):
                self.assertEqual(lines.count(command), 1, "Missing or folded CI evaluation command")
        self.assertIn("        run: |", verify)
        self.assertNotIn("node --test freight/research_lab_worker.test.mjs freight.test_research_eval_bridge", verify)


    def test_dob_source_scope_evidence_is_really_executed_on_pr_and_push(self):
        """Prevent green CI that silently omits the DOB provenance fixtures."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verify = workflow.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        executable = "          python -m unittest -q freight.test_nyc_dob_source_scope_v1 freight.test_nyc_dob_excluded_scope_v1"
        self.assertEqual(verify.splitlines().count(executable), 1)
        triggers = workflow.split("\npermissions:\n", 1)[0]
        for pattern in (
            '      - "freight/fixtures/nyc_dob_*_v1.json"',
            '      - "freight/test_nyc_dob_*_v1.py"',
        ):
            with self.subTest(path=pattern):
                self.assertEqual(triggers.splitlines().count(pattern), 2)


    def test_freight_gao_controls_run_in_verify_and_existing_nightly(self):
        """Guard both decision-level positive and negative freight regressions.

        These cases do not establish customer invoices, modern tariff authority,
        verified overcharges, source-specific rights, or recovered cash.
        """
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verify = workflow.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        nightly = workflow.split("\n  nightly-real-data-replay:\n", 1)[1]
        names = ("freight.test_gao_b221594_negative_control",
                 "freight.test_gao_b189100_classification")
        verify_line = next((line for line in verify.splitlines()
                            if line.strip().startswith("python -m unittest -v ")), "")
        nightly_line = (
            "          python -m unittest -q "
            "freight.test_gao_b221594_negative_control "
            "freight.test_gao_b189100_classification"
        )
        for module in names:
            with self.subTest(module=module):
                self.assertIn(module, verify_line)
                self.assertIn(module, nightly_line)
        self.assertEqual(nightly.splitlines().count(nightly_line), 1)
        self.assertIn("python -m pytest -q freight/test_real_world_eval_v1.py", nightly)
        self.assertIn("python -m freight.research_eval_bridge", nightly)
        triggers = workflow.split("\npermissions:\n", 1)[0]
        for name in ("freight/test_gao_b221594_negative_control.py",
                     "freight/test_gao_b189100_classification.py"):
            self.assertEqual(triggers.splitlines().count('      - "' + name + '"'), 2)
        # Still exactly two pre-existing Cron expressions: no new scheduler.
        self.assertEqual(triggers.count('cron: "4-59/5 * * * *"'), 1)
        self.assertEqual(triggers.count('cron: "19 3 * * *"'), 1)


    def test_real_original_signed_freight_replay_is_not_silently_removed(self):
        """Prove v2 adjustment compatibility is actually tested, not claimed."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verify = workflow.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        nightly = workflow.split("\n  nightly-real-data-replay:\n", 1)[1]
        command = "          python -m unittest -q freight.test_real_document_lab"
        self.assertEqual(verify.splitlines().count(command), 1)
        for key in (
            "canonical_v2_original_invoice_adjustment_lab",
            "canonical_invoice_records_with_exact_source_net",
            "canonical_v2_adjustment_records_with_exact_source_net",
            "canonical_v1_charge_only_records_with_exact_source_net",
            "discount_bearing_v2_records",
            "rate_review_required",
            "independent_invoice_overcharge_labels",
            "source_bound_adjustment_sha256",
            "unknown_cases_preserved",
        ):
            with self.subTest(key=key):
                self.assertIn(key, nightly)
        self.assertIn("assert signed['unsafe_auto_money_or_nondeterministic'] == 0", nightly)
        self.assertIn("assert signed['commercial_rate_authority_verified'] is False", nightly)
        self.assertIn("assert signed['recovered_cash_cents'] == 0", nightly)
        triggers = workflow.split("\npermissions:\n", 1)[0]
        for path in ("freight/real_document_lab.py", "freight/test_real_document_lab.py"):
            with self.subTest(path=path):
                self.assertEqual(triggers.splitlines().count('      - "' + path + '"'), 2)
        self.assertEqual(triggers.count('cron: "4-59/5 * * * *"'), 1)
        self.assertEqual(triggers.count('cron: "19 3 * * *"'), 1)


    def test_gsa_reference_chain_readiness_runs_without_claim_promotion(self):
        """Never silently remove the source-BOL-rate-payment readiness gate."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        triggers = workflow.split("\npermissions:\n", 1)[0]
        verify = workflow.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        nightly = workflow.split("\n  nightly-real-data-replay:\n", 1)[1]
        for source in (
            "freight/freight_evidence_chain_readiness.py",
            "freight/test_freight_evidence_chain_readiness.py",
        ):
            self.assertEqual(triggers.splitlines().count(f'      - "{source}"'), 2)
        self.assertEqual(
            verify.splitlines().count(
                "          python -m unittest -q freight.test_freight_evidence_chain_readiness"),
            1,
        )
        required = (
            "python -m freight.frei"
            "ght_evidence_chain_readiness --source /tmp/retally-real-lab.json",
            "chain['original_invoice_faces_observed'] == 110",
            "chain['original_net_amounts_reconciled_to_signed_components'] == 100",
            "chain['eligible_independently_scored_customer_invoices'] == 0",
            "chain['verified_retally_recovered_cash_cents'] == 0",
            "chain['modern_rate_authority_proven'] is False",
            "chain['federal_guidance_scope']",
            "chain['missing_chain_evidence_from_current_lab']",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, nightly)
        self.assertEqual(triggers.count('cron: "4-59/5 * * * *"'), 1)
        self.assertEqual(triggers.count('cron: "19 3 * * *"'), 1)


    def test_arcbest_printed_rate_and_bol_census_cannot_earn_tariff_authority(self):
        """Source-printed ABF/VPQ headers are classified, never rerated."""
        source = WORKFLOW.read_text(encoding="utf-8")
        verify = source.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        nightly = source.split("\n  nightly-real-data-replay:\n", 1)[1]
        for expected in (
            "source_printed_rate_bol_reference_census",
            "arc['source_page_identity_bound_count'] == 10",
            "arc['unbound_original_source_pages'] == 0",
            "arc['printed_tariff_reference_class_counts']",
            "arc['printed_bol_header_class_counts']",
            "arc['printed_pricing_bol_joint_class_counts']",
            "arc['printed_vpq_with_bol_header_identifier_only'] == 1",
            "arc['printed_vpq_without_bol_header_identifier'] == 1",
            "arc['original_bol_quote_id_correspondence_independently_verified'] == 0",
            "arc['printed_bol_header_is_not_original_bol_custody'] is True",
            "chain['arcbest_source_printed_pricing_bol_joint_classes']",
            "chain['arcbest_original_bol_quote_id_correspondence_verified'] == 0",
            "chain['arcbest_source_printed_category_sha256']",
            "arc['shipment_effective_customer_rate_authorities_verified'] == 0",
            "arc['independently_custodied_original_bol_documents'] == 0",
            "arc['independently_scored_customer_overcharges'] == 0",
            "arc['original_source_identifiers_exported'] == 0",
            "embedded_original_vpq_quote_source_replay",
            "quotation['embedded_original_vpq_quotation_pages'] == 2",
            "quotation['same_pdf_exact_quotation_id_invoice_joins'] == 2",
            "quotation['invoice_dates_within_printed_quote_effective_window'] == 2",
            "quotation['printed_invoice_quoted_weights_agree'] == 2",
            "quotation['invoice_amount_equals_printed_quote_minimum'] == 1",
            "quotation['conditional_printed_length_formula_matches'] == 1",
            "quotation['invoice_quote_money_unresolved'] == 0",
            "quotation['conditional_length_footage_is_independently_certified'] is False",
            "quotation['original_signed_bol_quotes_independently_verified'] == 0",
            "quotation['separate_quote_acceptance_independently_verified'] == 0",
            "quotation['independent_customer_invoice_overcharge_labels'] == 0",
            "quotation['verified_retally_recovered_cash_cents'] == 0",
            "quotation['raw_invoice_quote_bol_identifiers_exported'] == 0",
            "chain['arcbest_embedded_quote_match_class_sha256']",
            "chain['arcbest_same_pdf_quotes_not_independent_customer_rate_authorization'] is True",
            "co_bundled_motor_carrier_bol_source_replay",
            "bol['co_bundled_motor_carrier_bol_first_pages'] == 4",
            "bol['original_truckload_invoice_faces'] == 2",
            "bol['source_invoice_load_reference_matching_bol_pages'] == 4",
            "bol['source_invoice_printed_weight_matches_on_bol_copies'] == 4",
            "bol['source_invoice_pickup_date_matches_on_bol_copies'] == 4",
            "bol['repeated_load_groups_with_piece_count_disagreements'] == 1",
            "bol['duplicate_co_bundled_bol_copy_pages_not_new_shipments'] == 2",
            "bol['unresolved_reason_counts'] == {}",
            "bol['independently_authenticated_signed_bol_acceptances'] == 0",
            "bol['independent_custody_original_bol_verified'] == 0",
            "bol['independently_adjudicated_customer_overcharges'] == 0",
            "bol['commercial_reuse_authorized'] is False",
            "bol['verified_retally_cash_recovered_cents'] == 0",
            "chain['arcbest_cobundled_bol_page_class_sha256']",
            "chain['arcbest_original_bol_signatures_independently_authenticated'] == 0",
            "chain['arcbest_cobundled_bol_copies_not_independent_custody'] is True",
            "chain['arcbest_cobundled_pickup_date_copy_matches'] == 4",
            "chain['original_globaltranz_invoice_to_statement_exact_date_matches'] == 100",
            "chain['original_globaltranz_statement_max_date_gap_days'] == 0",
            "chain['original_us_date_fixes_not_payment_or_delivery_proof'] is True",
            "audit['date_fields_legacy_uk_first_misparsed'] == expected['misparsed_fields']",
            "audit['invoice_faces_affected_by_legacy_uk_first_parser'] == expected['affected_faces']",
            "audit['us_month_day_year_source_semantics_enforced'] is True",
            "audit['independent_delivery_or_payment_proof_created'] is False",
            "stmt['bank_payment_reconciliation'] == 'NOT_POSSIBLE_NO_BANK_RECORD'",
        ):
            with self.subTest(line=expected):
                self.assertIn(expected, nightly)
        self.assertEqual(
            verify.splitlines().count(
                "          python -m unittest -q freight.test_real_document_lab"
            ), 1,
        )
        self.assertEqual(source.count('cron: "4-59/5 * * * *"'), 1)
        self.assertEqual(source.count('cron: "19 3 * * *"'), 1)



    def test_original_real_document_ci_refuses_old_uk_first_us_freight_date_baselines(self):
        """The separate original-PDF workflow must run the same US date gates."""
        source = (WORKFLOW.parent / "retally-real-document-lab.yml").read_text(
            encoding="utf-8")
        for expected in (
            "stmt['face_to_statement_original_amount']['matched_invoices'] == 100",
            "stmt['face_to_statement_original_amount']['by_rule']['exact'] == 100",
            "identities['source_date_gaps_over_180_days'] == 0",
            "identities['maximum_face_to_statement_recorded_date_gap_days'] == 0",
            "US_SOURCE_DATE_LOCALE_BASELINE",
            "audit['date_fields_legacy_uk_first_misparsed'] == expected['misparsed_fields']",
            "audit['invoice_faces_affected_by_legacy_uk_first_parser'] == expected['affected_faces']",
            "audit['normalized_invoice_date_catalog_sha256'] == expected['catalog_sha256']",
            "audit['independent_delivery_or_payment_proof_created'] is False",
            "bol['source_invoice_pickup_date_matches_on_bol_copies'] == 4",
            "bol['unresolved_reason_counts'] == {}",
            "bol['commercial_reuse_authorized'] is False",
            "bol['verified_retally_cash_recovered_cents'] == 0",
        ):
            with self.subTest(required=expected):
                self.assertIn(expected, source)


    def test_cbca_rate_decisions_are_executed_in_main_lab_and_nightly(self):
        """No green CI if the CBCA negative/outcome control silently disappears."""
        source = WORKFLOW.read_text(encoding="utf-8")
        verify = source.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        nightly = source.split("\n  nightly-real-data-replay:\n", 1)[1]
        discovery = source.split("\n  discover:\n", 1)[1].split(
            "\n  nightly-real-data-replay:\n", 1)[0]
        executable = "          python -m unittest -q freight.test_cbca_rate_billing_controls"
        for expected in (
            "freight.test_cbca_rate_billing_controls",
            "freight.cbca_rate_billing_controls.py",
        ):
            self.assertIn(expected, verify)
        self.assertEqual(discovery.splitlines().count(executable), 1)
        self.assertEqual(nightly.splitlines().count(executable), 1)
        self.assertIn(
            "git show origin/research/retally-unified-data-lab:"
            "freight/research_lab/cbca_rate_billing_controls_v1.json", nightly)
        self.assertIn(
            "python -m freight.cbca_rate_billing_controls "
            "--output /tmp/retally-cbca-billing-v1.json --verify", nightly)
        for path in (
            "freight/cbca_rate_billing_controls.py",
            "freight/test_cbca_rate_billing_controls.py",
            "freight/fixtures/cbca_rate_billing_controls_v1.json",
        ):
            self.assertEqual(source.count('      - "' + path + '"'), 2)
        self.assertIn("d['private_customer_invoice_truth_cases'] == 0", discovery)
        self.assertIn("d['commercial_reuse_approved'] is False", discovery)
        self.assertIn("d['verified_retally_cash_recovery_cents'] == 0", discovery)
        self.assertEqual(source.count('cron: "4-59/5 * * * *"'), 1)
        self.assertEqual(source.count('cron: "19 3 * * *"'), 1)


if __name__ == "__main__":
    unittest.main()
