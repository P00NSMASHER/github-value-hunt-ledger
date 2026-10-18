"""Synthetic customer journey through real adapters, access controls and journals."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from freight.contracts import AuthorityRef, PopulationRow, freeze_population, freeze_truth, make_finding
from .cli import write_private_json
from .expansion_pilot import SOURCES
from .workbench import Workspace, sha

EXPECTED = {'freight': 5000, 'ap': 10000, 'warranty_credit': 7000,
            'procurement': 2000, 'rebate': 4000, 'parcel': 800, 'utility': 500}


def seed(root):
    client = 'SIMULATED-CUSTOMER-ONLY'
    workspace, tokens = Workspace.create(root, client, simulation=True)
    rows = {
        ('ap','payments_csv'): 'PAY-1,Supplier A,INV-1,100,2026-08-01\nPAY-2,Supplier A,INV-1,100,2026-08-02\n',
        ('ap','obligations_csv'): 'Supplier A,INV-1,100,2026-08-01\n',
        ('ap','vendor_statements_csv'): 'Supplier A,INV-1,-100,2026-08-31\n',
        ('warranty_credit','entitlements_csv'): f'CR-1,{client},Supplier B,RMA-1,WARRANTY,100,2026-08-01,Simulated entitlement,SIMULATED/reviewer\n',
        ('warranty_credit','settlements_csv'): 'S-1,CR-1,30,2026-08-20,CREDIT_MEMO\n',
        ('procurement','invoice_lines_csv'): f'L-1,INV-2,{client},Supplier C,PO-1,SKU-1,2026-08-15,10,100\n',
        ('procurement','authorities_csv'): 'A-1,Supplier C,PO-1,SKU-1,2026-01-01,,10,Simulated PO\n',
        ('procurement','quantities_csv'): 'L-1,8,Simulated receiving record\n',
        ('rebate','purchases_csv'): 'P-1,Supplier D,R-1,2026-08-01,10,1000\n',
        ('rebate','settlements_csv'): 'S-1,Supplier D,R-1,10,2026-10-15\n',
        ('parcel','charges_csv'): f'SHIP-1,INV-3,{client},Carrier A,2026-08-15,GROUND,5,10,30\n',
        ('parcel','assessments_csv'): 'A-1,SHIP-1,Carrier A,2026-08-15,GROUND,5,10,22,Simulated contract,2026-08-01,SIMULATED/reviewer\n',
        ('utility','bills_csv'): 'B-1,Utility A,AC-1,SC1,2026-08-31,20,100,0,0,31,2026-08-01,2026-08-31\n',
    }
    def upload(branch, source, content):
        record = workspace.upload(tokens['customer'], branch, source, content)
        workspace.review_source(tokens['reviewer'], branch, source, record['normalized_sha256'],
                                'SIMULATION ONLY: synthetic source reviewed against fixture oracle')
    for (branch, source), content in rows.items():
        upload(branch, source, SOURCES[branch][source][0]+'\n'+content)
    upload('rebate','programs_json',json.dumps([{'supplier_id':'Supplier D','program_id':'R-1',
        'period_start':'2026-01-01','period_end':'2026-09-30','tier_mode':'retroactive',
        'measurement_basis':'spend','payment_due_date':'2026-10-15',
        'tiers':[{'min_measure':0,'max_measure':None,'rate_pct':5}]}]))
    upload('utility','tariffs_json',json.dumps([{'sc_code':'SC1','effective_date':'2026-01-01',
        'logic_steps':[{'step_name':'Customer','charge_type':'fixed_fee','value':5},
                       {'step_name':'Energy','charge_type':'per_kwh','value':0.1}]}]))
    authority = AuthorityRef('SIM-AUTH', client, 'SIM-BU', 'SIM-CUSTOMER', 'SIM-CARRIER','USD',sha(b'SIMULATED-CONTRACT'))
    population = freeze_population(client,'SIM-BU','SIMULATION ONLY',
        (PopulationRow('SIM-INV','SIM-SHIP','SIM-CUSTOMER','SIM-CARRIER','USD',sha(b'SIMULATED-INVOICE')),))
    finding = make_finding(finding_id='SIM-FREIGHT-1',buyer_id=client,business_unit='SIM-BU',
        invoice_id='SIM-INV',shipment_id='SIM-SHIP',customer_id='SIM-CUSTOMER',carrier_id='SIM-CARRIER',
        currency='USD',authority_id=authority.authority_id,expected_cents=10000,actual_cents=15000,status='VALIDATED')
    upload('freight','truth_manifest_json',json.dumps(asdict(freeze_truth(population,(authority,),(finding,)))))
    workspace.configure(tokens['operator'],'ap',{'default_effective_from':'2026-01-01'})
    workspace.configure(tokens['operator'],'utility',{'default_effective_from':'2026-01-01','utility_id':'Utility A'})
    workspace.configure(tokens['operator'],'rebate',{'as_of_date':'2026-10-18'})
    authorize_population(workspace, tokens)
    return workspace, tokens


def authorize_population(workspace, tokens, branches=None):
    """Fixture-only customer and reviewer decisions, always visibly synthetic."""
    if not workspace.meta['simulation']:
        raise ValueError('synthetic onboarding cannot authorize a live workspace')
    intake = workspace._intake()
    for branch in (branches or EXPECTED):
        record = workspace.submit_onboarding(tokens['customer'], branch, {
            'period_start': '2026-01-01', 'period_end': '2026-10-18', 'currency': 'USD',
            'account_scope': 'SIMULATED accounts in fixture', 'source_system': 'SIMULATED exports',
            'exclusions': 'None within this synthetic fixture; not a real customer population',
            'population_reconciliation': 'SIMULATED source completeness checked against fixture oracle',
            'expected_rows': {key: value['rows'] for key, value in intake['sources'].items() if value['branch'] == branch},
            'authorized_to_analyze': True})
        workspace.review_onboarding(tokens['reviewer'], branch, record['scope_hash'],
                                    'SIMULATED audit scope and complete fixture population review')


def exercise(workspace, tokens):
    if not workspace.meta['simulation']:
        raise ValueError('rehearsal cannot run in a live workspace')
    first = workspace.scan(tokens['operator'])
    if first['exceptions']:
        raise AssertionError(first['exceptions'])
    actual = {branch: item['validated_cents'] for branch,item in first['report']['branches'].items()}
    if actual != EXPECTED:
        raise AssertionError({'expected':EXPECTED,'actual':actual})
    repeated = workspace.scan(tokens['operator'])
    if repeated['added_finding_ids'] or first['state_head_hash'] != repeated['state_head_hash']:
        raise AssertionError('scan replay created duplicate recovery')
    snapshots = workspace.cases(tokens['operator'])['cases']
    for case in snapshots:
        identity = case['finding_id']
        def act(role, action, data=None):
            head=workspace.cases(tokens[role])['head_hash']
            return workspace.action(tokens[role],action,identity,head,data or {'note':'SIMULATED role decision'})
        # Demonstrate customer cannot self-approve.
        try:
            act('customer','approve')
        except PermissionError:
            pass
        else:
            raise AssertionError('customer self-approval was accepted')
        act('reviewer','hold',{'note':'SIMULATED reconciliation: original proof retained'})
        current = next(c for c in workspace.cases(tokens['independent'])['cases'] if c['finding_id']==identity)
        act('independent','resolve',{'note':'SIMULATED second review retains original proof',
            'evidence_hash':sha(('SIM-RECONCILIATION/'+identity).encode()),'expected_record_hash':current['record_hash']})
        act('reviewer','approve')
        act('independent','independent')
        act('customer','authorize')
        act('operator','claim')
        amount=EXPECTED[case['branch']]
        for suffix,cents,reverses in [('first',amount//2,None),('second',amount-amount//2,None),
                                      ('reversal',-(amount//5),identity+'/first')]:
            event_id=identity+'/'+suffix
            act('operator','cash',{'event_id':event_id,'amount_cents':cents,'fee_cents':cents*3//10,
                'source_hash':sha(('SIMULATED-CASH/'+event_id).encode()),'reverses_id':reverses})
    backup=workspace.backup(tokens['operator'])
    delivery = workspace.customer_delivery(tokens['customer'])
    if len(json.loads(delivery['json'])['cases']) != 7:
        raise AssertionError('customer delivery did not include all seven branches')
    from .workbench_health import check_workspace
    health = check_workspace(workspace.root)
    if not health['healthy']:
        raise AssertionError(health)
    final=workspace.cases(tokens['customer'])
    results={}
    for case in final['cases']:
        expected=EXPECTED[case['branch']]*4//5
        if case['recovered_cents'] != expected or case['fee_cents'] != expected*3//10:
            raise AssertionError('net recovery or fees differ from independent arithmetic')
        results[case['branch']]={'potential_cents':EXPECTED[case['branch']],
            'simulated_net_received_cents':case['recovered_cents'],'simulated_net_fee_cents':case['fee_cents'],
            'journey':'PASS','scope':'synthetic happy path + hold/release + partial receipts + reversal'}
    report={'simulation':True,'real_customers':0,'real_recovered_cents':0,'external_actions_sent':0,
        'commercially_validated':False,'branches':results,'restore_verified':backup['restore_verified'],
        'customer_scope_and_population_review':True, 'customer_delivery_verified':True,
        'local_health_and_restore_verified':True, 'production_certified':False,
        'repeat_scan_idempotent':True,'customer_self_approval_blocked':True,
        'journal_head':final['head_hash'],'limitations':['Synthetic scenarios do not measure real-world recall or market superiority.',
        'Local role credentials are not enterprise SSO. No public deployment or external claim transport is enabled.']}
    write_private_json(workspace.root/'simulation-acceptance.json',report)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True)
    parser.add_argument('--exercise',action='store_true')
    args=parser.parse_args(argv)
    workspace,tokens=seed(args.workspace)
    result=exercise(workspace,tokens) if args.exercise else workspace.scan(tokens['operator'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
