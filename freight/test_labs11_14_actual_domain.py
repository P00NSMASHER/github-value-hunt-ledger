"""Labs 11-14 actual Python-domain probes with strictly fictional entities.

These execute real pre-existing RecoveryOS modules. They cannot prove a hosted
application SLA, external pen test, real savings, actual competitor performance
or buyer willingness to pay.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import pytest

from freight.audit_store import AuditStore
from freight.audit_ledger import AuditEventType
from freight.backup_restore import run_backup_restore_drill, workspace_summary, verify_backup_restore_result
from freight.payment_orchestration import (
    prepare_payment_instruction, authorize_payment, PaymentOrchestrator, verify_payment_snapshot,
)
from freight.accuracy_benchmark import load_fixture, build_accuracy_report
from freight.competitive_matrix import validate_competitor_evidence,validate_matrix,summarize_matrix

ROOT=Path(__file__).resolve().parents[1]
TS='2026-10-07T00:00:00Z'

def _payment():
    instruction=prepare_payment_instruction(
        instruction_id='FICTIONAL-INS-1',buyer_id='FICTIONAL-BUYER',
        business_unit='FICTIONAL-OPS',payer_id='FICTIONAL-CARRIER',
        payee_id='FICTIONAL-BUYER',currency='USD',amount_cents=6000,
        purpose='FICTIONAL-DOMAIN-TEST',finding_proof_hashes=(sha256(b'FICTIONAL').hexdigest(),),
        idempotency_key='FICTIONAL-IDEMPOTENCY-1')
    return instruction,PaymentOrchestrator(instruction)

def _auth(instr):
    return authorize_payment(instr,authorized_by='FICTIONAL-REVIEWER',
      reason='FICTIONAL-TEST',authorized_at=TS)

def _vendor():
    return json.loads((ROOT/'freight/PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json').read_text())

def _matrix():
    return json.loads((ROOT/'freight/PHASE3_COMPETITIVE_MATRIX_2026-10-07.json').read_text())

def test_lab11_actual_audit_store_immutable_and_scoped(tmp_path):
    store=AuditStore(tmp_path/'audit.sqlite3',buyer_id='FICTIONAL-BUYER',business_unit='FICTIONAL-OPS')
    store.append(event_type=AuditEventType.SOURCE_PRESENT,object_id='FICTIONAL-SOURCE',
      occurred_at=TS,evidence_hash='a'*64)
    store.append(event_type=AuditEventType.TRUTH_FROZEN,object_id='FICTIONAL-TRUTH',
      occurred_at='2026-10-07T00:01:00Z',evidence_hash='b'*64)
    store.verify()
    assert store.count()==2
    other=AuditStore(tmp_path/'audit.sqlite3',buyer_id='FICTIONAL-OTHER',business_unit='FICTIONAL-OPS')
    assert other.count()==0

def test_lab11_actual_restored_audit_semantically_equivalent(tmp_path):
    store=AuditStore(tmp_path/'audit.sqlite3',buyer_id='FICTIONAL-BUYER',business_unit='FICTIONAL-OPS')
    store.append(event_type=AuditEventType.SOURCE_PRESENT,object_id='FICTIONAL-SOURCE',
        occurred_at=TS,evidence_hash='a'*64)
    before=store.semantic_summary()
    from shutil import copy2
    restored=tmp_path/'restored.sqlite3'
    import sqlite3
    with sqlite3.connect(str(store.path)) as src,sqlite3.connect(str(restored)) as dest:
        src.backup(dest)
    again=AuditStore(restored,buyer_id='FICTIONAL-BUYER',business_unit='FICTIONAL-OPS')
    assert again.semantic_summary()==before

def test_lab11_cannot_mutate_append_only_audit(tmp_path):
    store=AuditStore(tmp_path/'audit.sqlite3',buyer_id='FICTIONAL-BUYER',business_unit='FICTIONAL-OPS')
    store.append(event_type=AuditEventType.SOURCE_PRESENT,object_id='FICTIONAL-SOURCE',
        occurred_at=TS,evidence_hash='a'*64)
    import sqlite3
    with sqlite3.connect(str(store.path)) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute('DELETE FROM audit_events WHERE buyer_id=?',('FICTIONAL-BUYER',))

def test_lab12_real_payment_denies_external_event_before_authorization():
    i,o=_payment()
    with pytest.raises(ValueError):
        o.record_provider_event(state='SETTLED',provider='FICTIONAL-PROVIDER',
           provider_reference='FICTIONAL-REF',amount_cents=6000,source_hash='a'*64,
           occurred_at='2026-10-07T00:01:00.000000Z')

def test_lab12_real_payment_denies_skipped_provider_step():
    i,o=_payment();o.authorize(_auth(i))
    with pytest.raises(ValueError):
        o.record_provider_event(state='SETTLED',provider='FICTIONAL-PROVIDER',
          provider_reference='FICTIONAL-REF',amount_cents=6000,source_hash='a'*64,
          occurred_at='2026-10-07T00:01:00.000000Z')

def test_lab12_real_payment_reversed_state_has_no_settled_cash():
    i,o=_payment();a=_auth(i);o.authorize(a)
    for n,state in enumerate(('SUBMITTED','ACCEPTED','SETTLED','REVERSED'),1):
        o.record_provider_event(state=state,provider='FICTIONAL-PROVIDER',
          provider_reference=f'FICTIONAL-REF-{n}',amount_cents=6000,source_hash='a'*64,
          occurred_at=f'2026-10-07T00:0{n}:00.000000Z')
    snap=o.snapshot()
    assert snap.current_state=='REVERSED' and snap.settled_cents==0
    verify_payment_snapshot(i,a,o.events,snap)

def test_lab12_cannot_alter_authorized_amount():
    i,o=_payment();o.authorize(_auth(i))
    with pytest.raises(ValueError):
        o.record_provider_event(state='SUBMITTED',provider='FICTIONAL-PROVIDER',
           provider_reference='FICTIONAL-REF',amount_cents=6001,source_hash='a'*64,
           occurred_at='2026-10-07T00:01:00.000000Z')

def test_lab13_real_rerating_is_historical_only_not_forecast():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    report=build_accuracy_report(fixture)
    assert report.rating['case_count']==20
    assert not hasattr(report,'future_savings')
    assert all('actual_savings_cents' not in row for row in report.rating['rows'])

def test_lab13_unsupported_authority_keeps_review_visible():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    report=build_accuracy_report(fixture)
    unresolved=[r for r in report.rating['rows'] if r['expected_truth']=='REVIEW']
    assert unresolved
    assert all(r['actual_status']=='REVIEW_REQUIRED' for r in unresolved)

def test_lab13_real_six_mode_scope_excludes_unproven_new_rule_families():
    fixture=load_fixture(ROOT/'freight/fixtures/phase3_accuracy_gold_v1.json')
    assert {r['record']['mode'] for r in fixture['rating_cases']}=={'PARCEL','LTL','TL','AIR','OCEAN','INTERMODAL'}
    assert len(fixture['rating_cases'])==20

def test_lab14_real_competitor_evidence_current_but_is_vendor_public_claim():
    e=_vendor()
    assert validate_competitor_evidence(e,as_of=date(2026,10,7))==[]
    assert all(v['evidence_type']=='vendor_public_claim' for v in e['competitors'].values())

def test_lab14_real_competitor_evidence_cannot_be_rebranded_as_certified():
    e=_vendor()
    k=next(iter(e['competitors']))
    e['competitors'][k]['evidence_type']='INDEPENDENT_CERTIFIED'
    assert validate_competitor_evidence(e,as_of=date(2026,10,7))!=[]

def test_lab14_real_matrix_is_reviewable_not_automatically_marketed():
    m=_matrix()
    assert validate_matrix(m)==[]
    report=summarize_matrix(m)
    assert report.recoveryos_rank>=1
    assert isinstance(report.recoveryos_gap_dimensions,tuple)

def test_lab14_future_stale_vendor_evidence_fails_closed():
    e=_vendor()
    assert validate_competitor_evidence(e,as_of=date(2027,1,6))!=[]
