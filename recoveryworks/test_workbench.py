import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from recoveryworks.seven_branch_simulation import seed, exercise, EXPECTED
from recoveryworks.workbench import Workspace
from recoveryworks.workbench_server import make_server


class WorkbenchTests(unittest.TestCase):
    def test_real_cash_ui_cannot_advertise_unverified_recovery_as_available(self):
        from recoveryworks.workbench_server import ASSETS
        script = (ASSETS / 'app.js').read_text(encoding='utf-8')
        self.assertIn('Live recovered-cash posting is disabled', script)
        self.assertIn('Record operator-reported external submission', script)
        self.assertIn('issuer proof not established', script)
        self.assertIn('Post simulated receipt', script)
        self.assertNotIn("button('Post reviewed receipt / reversal'", script)

    def test_seven_branch_customer_journey(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=seed(Path(directory)/'client')
            report=exercise(workspace,tokens)
            self.assertEqual(set(report['branches']),set(EXPECTED))
            self.assertTrue(report['restore_verified'])
            self.assertEqual(report['real_recovered_cents'],0)
            self.assertFalse(report['commercially_validated'])

    def test_mapped_intake_rejects_ambiguity_and_source_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'client','client')
            content='ID,Supplier,Invoice,Total,Date\np1,v,i1,100,2026-01-01\n'
            mapping={'Payment_Number':'ID','Vendor':'Supplier','Invoice_Number':'Invoice','Amount':'Total','Payment_Date':'Date'}
            record=workspace.upload(tokens['customer'],'ap','payments_csv',content,mapping)
            self.assertEqual(record['rows'],1)
            with self.assertRaises(PermissionError):
                workspace.review_source(tokens['customer'],'ap','payments_csv',record['normalized_sha256'],'self review')
            workspace.review_source(tokens['reviewer'],'ap','payments_csv',record['normalized_sha256'],'checked')
            self.assertTrue(workspace.read_source(tokens['customer'],record['id'])['content'].startswith('Payment_Number'))
            original=workspace.root/'sources'/(record['id']+'.original')
            preserved=original.read_bytes()
            original.write_bytes(preserved+b' ')
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.read_source(tokens['customer'],record['id'])
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.review_source(tokens['reviewer'],'ap','payments_csv',record['normalized_sha256'],'recheck')
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.upload(tokens['customer'],'ap','payments_csv',content,mapping)
            original.write_bytes(preserved)
            self.assertTrue(workspace.read_source(tokens['customer'],record['id'])['content'].startswith('Payment_Number'))
            (workspace.root/record['path']).write_text('tampered')
            with self.assertRaises(ValueError):
                workspace.read_source(tokens['customer'],record['id'])
            with self.assertRaises(ValueError):
                workspace.upload(tokens['customer'],'ap','payments_csv',content,{**mapping,'Vendor':'ID'})

    def test_http_role_origin_tenant_isolation_and_static_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'client','client')
            _,other=Workspace.create(Path(directory)/'other','other')
            server=make_server(workspace)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            def get(path,token=None,extra=None):
                headers={'Authorization':'Bearer '+token} if token else {}
                headers.update(extra or {})
                return urlopen(Request(base+path,headers=headers),timeout=5)
            try:
                with get('/') as response:
                    self.assertEqual(response.headers['Cache-Control'],'no-store')
                    self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
                    self.assertIn(b'RETALLY',response.read())
                for token,extra in ((None,{}),(other['customer'],{}),(tokens['customer'],{'Origin':'https://attacker.invalid'}),(tokens['customer'],{'Host':'attacker.invalid'})):
                    with self.subTest(token=bool(token),extra=extra),self.assertRaises(HTTPError) as caught:
                        get('/api/state',token,extra)
                    self.assertEqual(caught.exception.code,403)
                with get('/api/state',tokens['customer']) as response:
                    self.assertEqual(json.load(response)['client_id'],'client')
                with self.assertRaises(HTTPError) as caught:
                    get('/credentials.json')
                self.assertEqual(caught.exception.code,404)
            finally:
                server.shutdown();server.server_close();thread.join()

    def test_scan_rejects_original_evidence_tampering_before_any_recovery_action(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=seed(Path(directory)/'client')
            record=next(iter(workspace._intake()['sources'].values()))
            original=workspace.root/'sources'/(record['id']+'.original')
            original.write_bytes(original.read_bytes()+b' tampered')
            head=workspace.store.current_head_hash()
            # The original readback and the onboarding scan reject the same
            # tampering at different boundaries with different fail-closed errors.
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace._verified_evidence_bytes(record)
            with self.assertRaisesRegex(ValueError,'source integrity failure|original evidence bytes changed'):
                workspace.scan(tokens['operator'])
            self.assertEqual(workspace.store.current_head_hash(),head)

    def test_live_case_original_document_tamper_blocks_review_and_cash(self):
        """Only synthetic documents: edited originals cannot inherit prior reviews."""
        from recoveryworks.durable_ledger import DurableRecoveryLedger
        from recoveryworks.test_durable_ledger import verified_finding
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'live','client-1',simulation=False)
            finding=verified_finding()
            ledger=DurableRecoveryLedger()
            ledger.add(finding)
            workspace.store.save(ledger)
            content='{"synthetic_proof": "reviewed", "source": "no customer data"}'
            record=workspace.upload_document(tokens['operator'],finding.finding_id,'cash_event',content)
            original=workspace.root/'sources'/(record['id']+'.original')
            preserved=original.read_bytes()
            original.write_bytes(preserved+b' ')
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.review_document(tokens['reviewer'],record['id'],
                    record['normalized_sha256'],'synthetic reviewer')
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.read_source(tokens['reviewer'],record['id'])
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.upload_document(tokens['operator'],finding.finding_id,'cash_event',content)
            original.write_bytes(preserved)
            workspace.review_document(tokens['reviewer'],record['id'],
                record['normalized_sha256'],'synthetic reviewer')
            self.assertEqual(workspace._reviewed_document(record['id'],finding.finding_id,
                'cash_event')['synthetic_proof'],'reviewed')
            original.write_bytes(preserved+b' ')
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace._reviewed_document(record['id'],finding.finding_id,'cash_event')
            head=workspace.store.current_head_hash()
            with self.assertRaisesRegex(ValueError,'original evidence bytes changed'):
                workspace.action(tokens['operator'],'cash',finding.finding_id,head,
                                 {'document_id':record['id']})
            self.assertEqual(workspace.store.current_head_hash(),head)

    def test_live_workspace_cannot_use_simulated_claim_or_cash_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'live','client',simulation=False)
            with self.assertRaises(ValueError):
                exercise(workspace,tokens)

    def test_restore_rejects_tamper_and_traversal_before_writing(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            workspace,tokens=seed(root/'client')
            workspace.scan(tokens['operator'])
            receipt=workspace.backup(tokens['operator'])
            snapshot=json.loads((workspace.root/('backups/'+receipt['snapshot_id']+'.json')).read_text())
            changed=copy.deepcopy(snapshot)
            changed['files']['intake.json']['content']='{}'
            with self.assertRaises(ValueError):
                Workspace.restore_snapshot(changed,root/'tampered')
            self.assertFalse((root/'tampered').exists())
            changed=copy.deepcopy(snapshot)
            changed['files']['../outside']=changed['files']['intake.json']
            with self.assertRaises(ValueError):
                Workspace.restore_snapshot(changed,root/'traversal')
            restored=Workspace.restore_snapshot(snapshot,root/'restored')
            with self.assertRaises(PermissionError):
                restored.cases(tokens['customer'])
            restored.manage_credential('customer', reason='restore access')
            fresh=json.loads((restored.root/'credentials.json').read_text())
            self.assertEqual(restored.cases(fresh['customer'])['head_hash'],receipt['journal_head'])

    def test_corrected_case_can_be_reviewed_without_double_counting(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=seed(Path(directory)/'client')
            workspace.scan(tokens['operator'])
            record=workspace._intake()['sources']['procurement/invoice_lines_csv']
            content=workspace.read_source(tokens['customer'],record['id'])['content'].replace(',10,100\n',',10,110\n')
            updated=workspace.upload(tokens['customer'],'procurement','invoice_lines_csv',content)
            workspace.review_source(tokens['reviewer'],'procurement','invoice_lines_csv',updated['normalized_sha256'],'SIMULATED correction')
            from recoveryworks.seven_branch_simulation import authorize_population
            authorize_population(workspace,tokens,['procurement'])
            result=workspace.scan(tokens['operator'])
            conflict=next(e for e in result['exceptions'] if e['code']=='ECONOMIC_LOSS_CONFLICT')
            old=conflict['existing_finding_id']
            head=workspace.cases(tokens['reviewer'])['head_hash']
            workspace.action(tokens['reviewer'],'hold',old,head,{'note':'SIMULATED review of corrected source'})
            state=workspace.cases(tokens['independent'])
            case=next(c for c in state['cases'] if c['finding_id']==old)
            workspace.action(tokens['independent'],'revise',old,state['head_hash'],{
                'note':'SIMULATED independent review','evidence_hash':updated['normalized_sha256'],
                'expected_record_hash':case['record_hash'],'replacement_id':conflict['replacement']['finding_id']})
            cases=workspace.cases(tokens['customer'])['cases']
            self.assertEqual(len(cases),7)
            self.assertEqual(next(c for c in cases if c['branch']=='procurement')['potential_cents'],3000)

    def test_live_claim_and_cash_paths_reject_simulation_shortcuts(self):
        from recoveryworks.durable_ledger import DurableRecoveryLedger
        from recoveryworks.test_durable_ledger import verified_finding
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'live','client-1',simulation=False)
            ledger=DurableRecoveryLedger();finding=verified_finding();ledger.add(finding)
            ledger.approve(finding.finding_id,'reviewer','checked')
            ledger.independent_approve(finding.finding_id,'independent','checked')
            ledger.authorize(finding.finding_id,'customer-authorized')
            workspace.store.save(ledger,enforce_expected=True)
            for action in ('claim','cash'):
                with self.subTest(action=action),self.assertRaisesRegex(ValueError,'reviewed in-scope'):
                    workspace.action(tokens['operator'],action,finding.finding_id,ledger.journal.head_hash,{})
            self.assertEqual(workspace.store.current_head_hash(),ledger.journal.head_hash)

    def test_stale_action_does_not_write_and_customer_cannot_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=seed(Path(directory)/'client')
            workspace.scan(tokens['operator'])
            state=workspace.cases(tokens['reviewer']);case=state['cases'][0]
            with self.assertRaises(ValueError):
                workspace.action(tokens['reviewer'],'approve',case['finding_id'],'stale',{'note':'review'})
            with self.assertRaises(PermissionError):
                workspace.scan(tokens['customer'])
            self.assertEqual(workspace.store.current_head_hash(),state['head_hash'])

    def test_live_workflow_requires_reviewed_proof_documents(self):
        """Synthetic evidence exercising live controls; no external messages or money."""
        from dataclasses import asdict, replace
        from recoveryworks.durable_ledger import DurableRecoveryLedger
        from recoveryworks.test_seven_figure_assurance import million_finding, authority, source_attestation, calculation, review, CREATED
        from recoveryworks import freeze_case_proof, authorize_case_action, prepare_external_action
        from recoveryworks.assurance import case_bundle_to_payload, authorization_to_payload, external_action_to_payload
        from recoveryworks.financial_events import CashEvent
        from recoveryworks.workbench import sha, timestamp
        with tempfile.TemporaryDirectory() as directory:
            workspace,tokens=Workspace.create(Path(directory)/'live','client-1',simulation=False)
            finding=replace(million_finding(),actual_cents=10005000)
            ledger=DurableRecoveryLedger();ledger.add(finding);workspace.store.save(ledger,enforce_expected=True)
            bundle=freeze_case_proof(finding=finding,authority=authority(),source_attestations=(source_attestation(),),
                calculation=calculation(finding),reviews=(review(finding,'r1','reviewer','primary'),review(finding,'r2','independent','independent')),
                challenges=(),deadlines=(),created_at=CREATED,created_by='synthetic-case-builder',scan_batch_hash=sha(b'fixture'))
            authorization=authorize_case_action(bundle,authorization_id='SYNTHETIC-AUTH',client_actor_id='customer',
                approved_action_type='claim',authorized_at=CREATED,maximum_amount_cents=5000,note='SYNTHETIC ONLY')
            def document(role,kind,payload,reviewer='reviewer'):
                record=workspace.upload_document(tokens[role],finding.finding_id,kind,json.dumps(payload))
                workspace.review_document(tokens[reviewer],record['id'],record['normalized_sha256'],'SYNTHETIC test evidence review')
                return record['id']
            bundle_id=document('reviewer','case_bundle',case_bundle_to_payload(bundle),'independent')
            auth_id=document('customer','authorization',authorization_to_payload(authorization))
            def act(role,action,data):
                return workspace.action(tokens[role],action,finding.finding_id,workspace.store.current_head_hash(),data)
            act('reviewer','approve',{'note':'synthetic primary review'})
            act('independent','independent',{'note':'synthetic independent review'})
            act('customer','authorize',{'note':'synthetic authorization','bundle_document_id':bundle_id,'authorization_document_id':auth_id})
            artifact='SYNTHETIC external submission record — NOT SENT'
            envelope=prepare_external_action(bundle,authorization,artifact_kind='claim',artifact_bytes=artifact.encode(),
                artifact_locator='fixture://claim',action_amount_cents=5000,prepared_by='operator',prepared_at=CREATED)
            action_id=document('operator','external_action',{'envelope':external_action_to_payload(envelope),
                'artifact_text':artifact,'submitted_at':CREATED,'submission_reference':'SYNTHETIC-NOT-SENT'})
            result=act('operator','claim',{'document_id':action_id,'bundle_document_id':bundle_id,'authorization_document_id':auth_id})
            self.assertFalse(result['external_action_sent'])
            event=CashEvent('SYNTHETIC-RECEIPT',finding.finding_id,2000,600,'USD',sha(b'synthetic bank record'),
                           'fixture://bank',timestamp(),False)
            receipt=workspace.upload_document(tokens['operator'],finding.finding_id,'cash_event',json.dumps(asdict(event)))
            with self.assertRaises(ValueError):
                act('operator','cash',{'document_id':receipt['id']})
            workspace.review_document(tokens['reviewer'],receipt['id'],receipt['normalized_sha256'],'SYNTHETIC receipt review')
            original_head = workspace.store.current_head_hash()
            with self.assertRaisesRegex(ValueError, 'INDEPENDENT_CASH_SETTLEMENT_VERIFIER_NOT_IMPLEMENTED'):
                act('operator','cash',{'document_id':receipt['id']})
            # Even a forged verified=True document, with a valid source hash,
            # a distinct reviewer and prior authorization, is not bank proof.
            forged = workspace.upload_document(
                tokens['operator'], finding.finding_id, 'cash_event',
                json.dumps(asdict(replace(event, verified=True))))
            workspace.review_document(tokens['independent'], forged['id'],
                                      forged['normalized_sha256'],
                                      'SYNTHETIC fake bank verification flag')
            with self.assertRaisesRegex(ValueError, 'INDEPENDENT_CASH_SETTLEMENT_VERIFIER_NOT_IMPLEMENTED'):
                act('operator','cash',{'document_id':forged['id']})
            self.assertEqual(workspace.store.current_head_hash(), original_head)
            self.assertEqual(workspace.store.load().get(finding.finding_id).recovered_cents, 0)
            self.assertEqual(workspace.cases(tokens['customer'])['cases'][0]['recovered_cents'], 0)
