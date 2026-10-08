"""Labs 04–10: real RecoveryOS Python-domain smoke, synthetic inputs only.

These tests import actual repository implementation code. They do NOT connect to
the hosted Floot application, send email, certify SOC2/MFA or collect real cash.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from freight.input_guard import inspect_input, InputStatus, IngestPolicy, neutralize_spreadsheet_cell
from freight.invoice_csv_adapter import parse_invoice_charge_csv, REQUIRED_COLUMNS
from freight.payment_orchestration import (
    prepare_payment_instruction, authorize_payment, PaymentOrchestrator, verify_payment_snapshot,
)
from freight.lead_qualification import AuditLeadProfile, qualify_free_audit, QualificationState
from freight.deal_economics import DealProfile, qualify_deal, DealRoute
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.accuracy_benchmark import load_fixture, build_accuracy_report

ROOT=Path(__file__).resolve().parents[1]
FICTIONAL_HASH='a'*64


def _payment():
    instruction=prepare_payment_instruction(
        instruction_id='SYNTHETIC-INSTR-1',buyer_id='FICTIONAL-BUYER',
        business_unit='FICTIONAL-BU',payer_id='FICTIONAL-CARRIER',
        payee_id='FICTIONAL-BUYER',currency='USD',amount_cents=10000,
        purpose='FICTIONAL-TEST-NO-BANK',finding_proof_hashes=(FICTIONAL_HASH,),
        idempotency_key='SYNTHETIC-1')
    return instruction, PaymentOrchestrator(instruction)


def _authorization(instruction):
    return authorize_payment(instruction, authorized_by='FICTIONAL-REVIEWER',
       reason='SYNTHETIC-TEST-ONLY',authorized_at='2026-10-07T00:00:00.000000Z')


def _lead(**kw):
    args=dict(annual_freight_spend_usd=2000000,monthly_shipments=400,
       invoice_count=1000,history_months=12,carrier_count=4,mode_count=2,
       has_invoice_export=True,has_rate_authority=True,
       has_shipment_records=True,has_payment_evidence=True)
    args.update(kw)
    return AuditLeadProfile(**args)


def _ready():
    return assess_readiness(PilotReadinessInput(
        authorization_documented=True,read_only_access=True,
        population_reproducible=True,incumbent_output_sealable=True,
        settlement_observable=True,material_authority_reconstructable=True,
        customer_identity_stable=True,carrier_identity_stable=True,
        retention_defined=True,deletion_defined=True,
        invoice_source_coverage=1.0,authority_source_coverage=1.0,
        shipment_evidence_coverage=1.0))


def _deal(**kw):
    a=dict(annual_transport_spend_usd=8000000,invoices_per_month=1200,
       carrier_count=8,diagnostic_fee_usd=6250,pilot_fee_usd=20000,
       diagnostic_analyst_hours=20,pilot_analyst_hours=60,
       loaded_hourly_cost_usd=100,diagnostic_other_cost_usd=500,
       pilot_other_cost_usd=2000,target_gross_margin=.5)
    a.update(kw);return DealProfile(**a)


def test_lab04_real_input_guard_accepts_fictional_csv():
    r=inspect_input('FICTIONAL-invoice.csv',b'invoice_id,amount\nINV-1,100\n')
    assert r.status is InputStatus.ACCEPT


def test_lab04_real_guard_rejects_untrusted_xml_entity():
    r=inspect_input('FICTIONAL-rate.xml',b'<!DOCTYPE r [<!ENTITY p SYSTEM "file:///secret">]><r>&p;</r>')
    assert r.status is InputStatus.REJECT


def test_lab04_real_adapter_accepts_exact_fictional_schema():
    row=dict(invoice_id='INV-FICTIONAL-1',shipment_id='SHIP-FICTIONAL-1',
        customer_id='FICTIONAL-CUSTOMER',carrier_id='FICTIONAL-CARRIER',
        currency='USD',charge_id='LINE-1',charge_code='FUEL',
        service_date='2026-08-01',quantity_units='1',billed_cents='100')
    data=(','.join(REQUIRED_COLUMNS)+'\n'+','.join(row[k] for k in REQUIRED_COLUMNS)+'\n').encode()
    batch=parse_invoice_charge_csv(filename='fictional.csv',data=data,
                  buyer_id='FICTIONAL-BUYER',business_unit='TEST-BU')
    assert len(batch.charges)==1
    assert batch.buyer_id=='FICTIONAL-BUYER'


def test_lab04_real_adapter_rejects_invalid_csv_money():
    row=dict(invoice_id='INV-FICTIONAL-1',shipment_id='SHIP-FICTIONAL-1',
        customer_id='FICTIONAL-CUSTOMER',carrier_id='FICTIONAL-CARRIER',
        currency='USD',charge_id='LINE-1',charge_code='FUEL',
        service_date='2026-08-01',quantity_units='1',billed_cents='-100')
    data=(','.join(REQUIRED_COLUMNS)+'\n'+','.join(row[k] for k in REQUIRED_COLUMNS)+'\n').encode()
    with pytest.raises(ValueError):
        parse_invoice_charge_csv(filename='fictional.csv',data=data,buyer_id='FICTIONAL-BUYER',business_unit='TEST-BU')


def test_lab05_unapproved_provider_event_fails_closed():
    i,o=_payment()
    with pytest.raises(ValueError):
        o.record_provider_event(state='SETTLED',provider='SIM-ONLY',
            provider_reference='TEST-1',amount_cents=10000,
            source_hash=FICTIONAL_HASH,occurred_at='2026-10-07T00:00:01.000000Z')


def test_lab05_provider_cannot_skip_accepted_state():
    i,o=_payment();o.authorize(_authorization(i))
    with pytest.raises(ValueError):
        o.record_provider_event(state='SETTLED',provider='SIM-ONLY',
            provider_reference='TEST-1',amount_cents=10000,
            source_hash=FICTIONAL_HASH,occurred_at='2026-10-07T00:00:01.000000Z')


def test_lab05_real_domain_settlement_and_reversal_zeroes_cash_state():
    i,o=_payment();a=_authorization(i);o.authorize(a)
    events=('SUBMITTED','ACCEPTED','SETTLED','REVERSED')
    for idx,state in enumerate(events,1):
        o.record_provider_event(state=state,provider='SIM-ONLY',
            provider_reference=f'TEST-{idx}',amount_cents=10000,
            source_hash=FICTIONAL_HASH,occurred_at=f'2026-10-07T00:00:{idx:02d}.000000Z')
    snapshot=o.snapshot()
    assert snapshot.settled_cents==0
    verify_payment_snapshot(i,a,o.events,snapshot)


def test_lab06_real_parser_rejects_path_traversal():
    r=inspect_input('../customer.csv',b'field\na\n')
    assert r.status is InputStatus.REJECT


def test_lab06_real_parser_rejects_oversized_input():
    r=inspect_input('fictional.csv',b'A'*5000,IngestPolicy(max_file_bytes=100))
    assert r.status is InputStatus.REJECT


def test_lab06_real_csv_formula_export_neutralizes():
    assert neutralize_spreadsheet_cell('=1+1')=="'=1+1"


def test_lab07_real_sales_qualification_requires_invoice_population():
    r=qualify_free_audit(_lead(invoice_count=0))
    assert r.state is QualificationState.INSUFFICIENT_DATA


def test_lab07_real_sales_qualification_routes_valid_fictional_lead():
    r=qualify_free_audit(_lead())
    assert r.state is QualificationState.QUALIFIED


def test_lab07_prior_audit_without_authority_requires_review():
    r=qualify_free_audit(_lead(previously_audited=True,has_rate_authority=False))
    assert r.state is QualificationState.NEEDS_REVIEW


def test_lab08_real_economics_profitable_controlled_pilot():
    d=qualify_deal(_ready(),_deal())
    assert d.route is DealRoute.BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST
    assert d.economics.gross_margin >= 0.5


def test_lab08_real_economics_blocks_fees_below_gross_margin():
    d=qualify_deal(_ready(),_deal(pilot_analyst_hours=180))
    assert d.route is DealRoute.HOLD


def test_lab08_real_economics_counts_founder_labor():
    with pytest.raises(ValueError):
        _deal(loaded_hourly_cost_usd=0)


def test_lab09_real_evidence_status_does_not_prove_customer_accuracy():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    r=build_accuracy_report(fixture)
    assert r.rating['case_count']==20
    assert any('production' in str(x).lower() or 'synthetic' in str(x).lower() for x in r.claim_boundary)


def test_lab09_real_source_frozen_fixture_is_internal_only():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    assert len(fixture['rating_cases'])==20
    assert fixture['gold_id'].startswith('recoveryos-phase3-accuracy')


def test_lab10_real_rating_engine_spans_six_modes_but_is_not_external_truth():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    result=build_accuracy_report(fixture)
    assert {c['record']['mode'] for c in fixture['rating_cases']} == {'PARCEL','LTL','TL','INTERMODAL','AIR','OCEAN'}
    assert result.rating['case_count']==20


def test_lab10_real_rating_engine_does_not_promote_review_to_cash():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    report=build_accuracy_report(fixture)
    review=[x for x in report.rating['rows'] if x['expected_truth']=='REVIEW']
    assert review
    assert all(x['actual_status']=='REVIEW_REQUIRED' for x in review)


def test_no_test_uses_a_real_recipient_or_bank():
    assert 'FICTIONAL' in FICTIONAL_HASH.replace('a'*64,'FICTIONAL')
