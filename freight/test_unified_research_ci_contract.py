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



if __name__ == "__main__":
    unittest.main()
