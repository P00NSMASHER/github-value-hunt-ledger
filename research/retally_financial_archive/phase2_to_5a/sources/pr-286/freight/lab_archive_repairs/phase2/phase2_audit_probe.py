"""Original Phase1 five-issue reproduction against a supplied extracted lab.

Each output `reproduced` means the original failure occurred; no production claim.
Run in isolated subprocess per source tree, so imported modules never mix.
"""
import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from unified.core import load_source,public_invoice
from unified.staging import StagingTwin,Rejected
from unified.customers import persona_for

rows=load_source(2000)
row=next(r for r in rows if int(r['invoice_total_cents'])>1500)
TENANT='SIM-TENANT-001'
results={}
results['expected_tariff_values_in_benchmark_input']=all(k in public_invoice(row) for k in ('expected_base_cents','expected_fuel_cents','expected_accessorial_cents'))

def till_settle(tw,cid,total=1000):
 def go(actor,kind,**p):return tw.act(cid,TENANT,actor,kind,p)
 go('buyer','CONSENT',scope_signed=True)
 go('operator','FREEZE',evidence_ref='SIM-EVIDENCE-FREEZE')
 go('operator','CANDIDATE',amount_cents=total)
 go('reviewer','REVIEW',amount_cents=total,evidence_ref='SIM-EVIDENCE-REVIEW')
 go('buyer','AUTHORIZE',amount_cents=total,evidence_ref='SIM-EVIDENCE-AUTH')
 go('operator','SUBMIT');go('carrier_mock','ACKNOWLEDGE')
 go('carrier_mock','OFFER',amount_cents=total)
 go('carrier_mock','SETTLE',amount_cents=total,evidence_ref='SIM-EVIDENCE-SETTLE')
 return go

with tempfile.TemporaryDirectory() as d:
 tw=StagingTwin(Path(d)/'money.sqlite');cid='SIM-CASE-FEE';tw.create(row,TENANT,cid)
 go=till_settle(tw,cid)
 go('finance','CREDIT',amount_cents=1000,provider_ref='SIM-CREDIT-A',evidence_ref='SIM-EVIDENCE-CREDIT')
 go('finance','RECONCILE',amount_cents=1000,evidence_ref='SIM-EVIDENCE-RECON')
 try:
  go('finance','FEE_INVOICE',fee_bps=5000,evidence_ref='SIM-EVIDENCE-FEE');results['unbound_50_percent_fee_accepted']=tw.view(cid,TENANT)['funds']['fee_earned']==500
 except Rejected:results['unbound_50_percent_fee_accepted']=False

with tempfile.TemporaryDirectory() as d:
 tw=StagingTwin(Path(d)/'revocation.sqlite');cid='SIM-CASE-REVOKE';tw.create(row,TENANT,cid)
 go=till_settle(tw,cid)
 go('finance','CREDIT',amount_cents=1000,provider_ref='SIM-CREDIT-A',evidence_ref='SIM-EVIDENCE-CREDIT')
 go('finance','RECONCILE',amount_cents=1000,evidence_ref='SIM-EVIDENCE-RECON')
 go('buyer','REVOKE')
 try:
  go('finance','REVERSE',amount_cents=1000,credit_ref='SIM-CREDIT-A',evidence_ref='SIM-EVIDENCE-REV');results['reversal_blocked_after_revocation']=False
 except Rejected:results['reversal_blocked_after_revocation']=True

with tempfile.TemporaryDirectory() as d:
 tw=StagingTwin(Path(d)/'installments.sqlite');cid='SIM-CASE-INSTALLMENTS';tw.create(row,TENANT,cid)
 go=till_settle(tw,cid)
 go('finance','CREDIT',amount_cents=400,provider_ref='SIM-CREDIT-A',evidence_ref='SIM-EVIDENCE-CREDIT')
 try:
  go('finance','CREDIT',amount_cents=600,provider_ref='SIM-CREDIT-B',evidence_ref='SIM-EVIDENCE-CREDIT');results['second_partial_credit_blocked']=False
 except Rejected:results['second_partial_credit_blocked']=True

ids={r['customer_id'] for r in rows}
labels={persona_for({'customer_id':customer})['name'] for customer in ids}
results['fictional_company_name_collisions']=len(labels)<len(ids)
print(json.dumps({'scope':'OFFLINE_STAGING_TWIN_ONLY','source_root':str(Path(sys.argv[1]).resolve()),
 'original_failure_reproduced':results,'failure_count':sum(results.values())},sort_keys=True,indent=2))
