"""New regression tests against the ORIGINAL offline StagingTwin, not RecoveryOS."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unified.core import load_source
from unified.staging import StagingTwin, Rejected


class OriginalStagingRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_row=load_source(1)[0]

    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.twin=StagingTwin(Path(tmp.name)/'original.sqlite3')
        self.case='SIM-CASE-ORIGINAL-REPAIR'
        self.tenant='SIM-TENANT-REPAIR'
        self.twin.create(self.source_row,self.tenant,self.case)

    def test_positive_frozen_intake(self):
        self.assertEqual(self.twin.verify()['status'],'PASS_SYNTHETIC_ONLY')

    def test_phantom_intake_journal_rejected(self):
        with sqlite3.connect(self.twin.path) as con:
            con.execute('INSERT INTO journal VALUES (?,?,?,?,?)',
                        (self.case,1,'simulated_cash','misc_receivable',100000000))
        check=self.twin.verify()
        self.assertEqual(check['status'],'FAIL')
        self.assertTrue(any(x.startswith('JOURNAL_EVENT_MISMATCH:') for x in check['errors']))

    def test_wrong_balance_rejected(self):
        with sqlite3.connect(self.twin.path) as con:
            funds=json.loads(con.execute('SELECT funds_json FROM simulated_cases').fetchone()[0])
            funds['candidate']=987654321
            con.execute('UPDATE simulated_cases SET funds_json=?',(json.dumps(funds),))
        check=self.twin.verify()
        self.assertEqual(check['status'],'FAIL')
        self.assertTrue(any(x.startswith('FUND_REPLAY_MISMATCH:') for x in check['errors']))

    def test_changed_invoice_total_without_external_update_rejected(self):
        with sqlite3.connect(self.twin.path) as con:
            invoice=json.loads(con.execute('SELECT public_invoice_json FROM simulated_cases').fetchone()[0])
            invoice['invoice_total_cents']='999999999'
            con.execute('UPDATE simulated_cases SET public_invoice_json=?',(json.dumps(invoice),))
        check=self.twin.verify()
        self.assertEqual(check['status'],'FAIL')
        self.assertTrue(any(x.startswith('SOURCE_BINDING_TAMPER:') for x in check['errors']))

    def test_string_false_not_contract_consent(self):
        with self.assertRaises(Rejected):
            self.twin.act(self.case,self.tenant,'buyer','CONSENT',{'scope_signed':'false'})
        self.assertEqual(self.twin.verify()['status'],'PASS_SYNTHETIC_ONLY')

    def test_tampered_consent_flag_rejected(self):
        with sqlite3.connect(self.twin.path) as con:
            con.execute('UPDATE simulated_cases SET consent=1')
        check=self.twin.verify()
        self.assertEqual(check['status'],'FAIL')
        self.assertTrue(any(x.startswith('CONSENT_REPLAY_MISMATCH:') for x in check['errors']))


if __name__=='__main__':
    unittest.main()
