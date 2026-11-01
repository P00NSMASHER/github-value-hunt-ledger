"""RETALLY final cross-workstream smoke: a hypothetical customer cannot self-promote.

This runs on source modules imported from the existing integrated commercial code.
No network, no buyer data, no new authorization mechanisms, no financial actions.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from freight.lead_qualification import AuditLeadProfile, QualificationState, qualify_free_audit
from freight.commercial.first_customer_gate import evaluate
from freight.commercial.zero_upfront_underwriting import model_scenario

HERE = Path(__file__).parent
EVIDENCE = json.loads((HERE/"first_customer_acceptance_m2g.json").read_text(encoding="utf8"))
WHAT_IF = json.loads((HERE/"fixtures"/"zero_upfront_synthetic_example.json").read_text(encoding="utf8"))


class FinalCommercialBoundary(unittest.TestCase):
    def synthetic_lead(self, **change):
        p=dict(
            annual_freight_spend_usd=2_000_000,
            monthly_shipments=400,
            invoice_count=20,
            history_months=12,
            carrier_count=3,
            mode_count=1,
            has_invoice_export=True,
            has_rate_authority=True,
            has_shipment_records=True,
            has_payment_evidence=True,
            previously_audited=True,
        )
        p.update(change)
        return AuditLeadProfile(**p)

    def test_attractive_prior_audited_lead_does_not_authorize_a_pilot(self):
        lead = qualify_free_audit(self.synthetic_lead())
        self.assertIs(lead.state, QualificationState.NEEDS_REVIEW)
        self.assertIn("prior_audit_overlap_check",lead.reasons)

        gates = evaluate(EVIDENCE)
        self.assertFalse(gates["all_customer_pilot_gates_ready"])
        self.assertFalse(gates["gates"]["confidential_pilot"]["ready"])
        self.assertFalse(gates["gates"]["claims_recovery"]["ready"])

        economics = model_scenario(WHAT_IF)
        self.assertFalse(economics["customer_kickoff_authorized"])
        self.assertFalse(economics["customer_price_or_approved_rate"])
        self.assertEqual(economics["risk_decision"], "HOLD")
        self.assertEqual(economics["cost"]["zero_recovery_loss_usd"],"2500.00")

    def test_missing_carrier_identity_does_not_become_qualified(self):
        lead=qualify_free_audit(self.synthetic_lead(
            previously_audited=False,carrier_count=0))
        self.assertIs(lead.state,QualificationState.NEEDS_REVIEW)
        self.assertIn("carrier_identity_unidentified",lead.reasons)

    def test_sample_accounting_gap_not_hidden_as_recovered_customer_cash(self):
        s=EVIDENCE["published_synthetic_sample"]
        self.assertFalse(s["customer_result"])
        self.assertEqual(s["unallocated_difference_usd"],"1650.00")
        self.assertFalse(evaluate(EVIDENCE)["gates"]["sample_publication"]["ready"])

    def test_fully_optimistic_model_flags_still_cannot_authorize_kickoff(self):
        assumptions=dict(WHAT_IF)
        for name in (
            "actual_rate_approved_in_signed_terms",
            "buyer_specific_scope_authorized",
            "buyer_data_controls_verified",
            "independent_reviewer_reserved",
        ):
            assumptions[name]=True
        economics=model_scenario(assumptions)
        self.assertFalse(economics["customer_kickoff_authorized"])
        self.assertEqual(economics["risk_decision"],
                         "HUMAN_REVIEW_REQUIRED_NOT_KICKOFF_AUTHORIZED")


    def test_public_freight_sources_never_substitute_for_buyer_evidence(self):
        """Sourced market data and census identity do not clear customer gates."""
        from freight.bts_public_evaluation import load_observations
        from freight.fmcsa_public_carrier import validate_census_response
        from freight.retally_eia_reference import reference_price

        carrier = validate_census_response(
            "1234567",
            [{"dot_number": "1234567", "legal_name": "EXAMPLE FREIGHT LLC",
              "power_units": "12"}],
            retrieved_at_utc="2026-10-08T18:00:00Z",
        )
        fuel = reference_price("2026-10-05", "US")
        airfreight = load_observations()[0]

        self.assertFalse(carrier.operating_authority_verified)
        self.assertFalse(carrier.customer_invoice_verified)
        self.assertFalse(carrier.recovery_fee_authorized)
        self.assertIn("PUBLIC_MARKET_REFERENCE_ONLY", fuel.role)
        self.assertIn("NOT_INVOICE_GROUND_TRUTH", airfreight.evidence_class)

        customer = evaluate(EVIDENCE)
        self.assertFalse(customer["gates"]["confidential_pilot"]["ready"])
        self.assertFalse(customer["gates"]["claims_recovery"]["ready"])
        self.assertFalse(customer["all_customer_pilot_gates_ready"])

    def test_identified_public_carrier_does_not_supply_rate_contract_or_invoice(self):
        """Public carrier existence plus high spending cannot clear missing facts."""
        from freight.fmcsa_public_carrier import validate_census_response

        carrier = validate_census_response(
            "1234567",
            [{"dot_number": "1234567", "legal_name": "EXAMPLE FREIGHT LLC",
              "power_units": "12"}],
            retrieved_at_utc="2026-10-08T18:00:00Z",
        )
        self.assertFalse(carrier.customer_invoice_verified)

        missing_invoices = qualify_free_audit(self.synthetic_lead(
            previously_audited=False, carrier_count=1,
            has_invoice_export=False, has_rate_authority=False,
            has_shipment_records=False, has_payment_evidence=False,
        ))
        self.assertIs(missing_invoices.state, QualificationState.INSUFFICIENT_DATA)

        missing_contract = qualify_free_audit(self.synthetic_lead(
            previously_audited=False, carrier_count=1,
            has_rate_authority=False, has_shipment_records=False,
            has_payment_evidence=False,
        ))
        self.assertIs(missing_contract.state, QualificationState.NEEDS_REVIEW)
        self.assertIn("rate_authority_needs_review", missing_contract.reasons)


if __name__=="__main__":
    unittest.main(verbosity=2)
