"""Bounded three-buyer fictional founding pilot; NO real customers or contacts.

First synthetic path reuses the independently replayed Phase 2 settlement.
Others deliberately include a no-recovery result and a negative-risk case.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from typing import Mapping
from freight.lab_phase3_economics import (
    ContingencyAssumptions, analyze_contingency, fixed_default_contingency_bps,
)
from freight.lab_phase2_demo import build_demo
from freight.lab_assurance import digest


def simulated_cohort() -> dict:
    default=fixed_default_contingency_bps()
    common={"probability_valid_bps":6500,"probability_customer_recovery_bps":5000,
            "probability_fee_collection_bps":9000,"expected_reversal_bps":500,
            "contingency_rate_bps":default,"free_audit_minutes":110,
            "recovery_work_minutes_if_valid":180,"loaded_analyst_hourly_cents":4200,
            "acquisition_cost_cents":1800,"other_delivery_cost_cents":600,
            "recovery_delay_days":75}
    cases=(
        ("SIM-MULTISITE-DISTRIBUTOR", "PARTIAL_CREDIT_AND_REVERSAL",
         ContingencyAssumptions(opportunity_cents=200000,**common),
         "Source and fee tests are synthetic; the $5 retained credit is a fictional Phase 2 case."),
        ("SIM-PARCEL-OPERATOR", "DEFENSIBLE_NO_RECOVERY",
         ContingencyAssumptions(opportunity_cents=0,**common),
         "Clean audited fixture contains zero eligible overpayment. Never invent recovery."),
        ("SIM-INDUSTRIAL-SHIPPER", "LONG_DISPUTE_UNCERTAIN",
         ContingencyAssumptions(opportunity_cents=80000,**{**common,
             "probability_valid_bps":3000,"probability_customer_recovery_bps":2000,
             "free_audit_minutes":210,"recovery_work_minutes_if_valid":360,
             "other_delivery_cost_cents":4000,"recovery_delay_days":240}),
         "Modeled potential only; carrier approval, collection and margin are not observed."),
    )
    original,_=build_demo()
    totals=original["financial"]["financial_proof"]["currency_totals"]["USD"]
    if totals["recovered_cents"]!=500 or totals["earned_fee_cents"]!=100:
        raise RuntimeError("PRIOR_LAB_FIXTURE_DRIFT")
    cohort=[]
    for idx,(customer,state,a,notes) in enumerate(cases):
        r=analyze_contingency(a)
        current=(dict(simulated_net_recovered_cents=500,
                      simulated_fee_earned_cents=100,
                      simulated_fee_collected_cents=100) if idx==0 else
                 dict(simulated_net_recovered_cents=0,
                      simulated_fee_earned_cents=0,
                      simulated_fee_collected_cents=0))
        cohort.append({"synthetic_customer_id":customer,"state":state,
                       "audit_upfront_fee_cents":0,"actual_customer_revenue_cents":0,
                       "observed_real_recovery_cents":0,
                       "simulated_accounting":current,
                       "economic_scenario":asdict(r),"risk_note":notes,
                       "authorization_scope":"SYNTHETIC_TEST_FIXTURES_ONLY"})
    body={"scope":"SIMULATED_FOUNDING_CUSTOMER_PILOT_ONLY",
          "simulated_customer_count":3,"accepted_real_customer_count":0,
          "actual_company_revenue_cents":0,
          "actual_customer_recovery_cents":0,
          "pilot_design":"bounded, three fictional cases with one no-recovery control",
          "independent_synthetic_financial_receipt":original["financial"]["financial_proof"]["receipt_hash"],
          "cohort":cohort,"real_customer_permission_obtained":False,
          "outside_carrier_bank_or_email_activity":False}
    return {**body,"receipt_sha256":digest(body)}
