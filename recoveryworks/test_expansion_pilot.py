import json
import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.expansion_pilot import create_kit, main, preflight


class ExpansionPilotTests(unittest.TestCase):
    def test_empty_kits_block_runs_and_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for stage in ('1', '2', '3'):
                root = Path(tmp) / stage
                config_path = create_kit(root, 'SYNTHETIC-ONLY', stage)
                config = json.loads(config_path.read_text())
                self.assertTrue(preflight(config, root))
                self.assertEqual(main(['run', '--config', str(config_path), '--state', str(root / 'state.json'), '--report', str(root / 'report.json')]), 2)
                self.assertFalse((root / 'state.json').exists())
                with self.assertRaises(FileExistsError):
                    create_kit(root, 'other-client', stage)
                if os.name == 'posix':
                    self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)

    def test_populated_synthetic_kits_execute_all_six_engines(self):
        rows = {
            'ap_payments_csv.csv': 'PAY-1,Supplier A,INV-1,100,2026-08-01\nPAY-2,Supplier A,INV-1,100,2026-08-02\n',
            'ap_obligations_csv.csv': 'Supplier A,INV-1,100,2026-08-01\n',
            'ap_vendor_statements_csv.csv': 'Supplier A,INV-1,-100,2026-08-31\n',
            'warranty_credit_entitlements_csv.csv': 'CR-1,SYNTHETIC-ONLY,Supplier B,RMA-1,WARRANTY,100,2026-08-01,Approved credit,synthetic-reviewer\n',
            'warranty_credit_settlements_csv.csv': 'S-1,CR-1,30,2026-08-20,CREDIT_MEMO\n',
            'procurement_invoice_lines_csv.csv': 'L-1,INV-2,SYNTHETIC-ONLY,Supplier C,PO-1,SKU-1,2026-08-15,10,100\n',
            'procurement_authorities_csv.csv': 'A-1,Supplier C,PO-1,SKU-1,2026-01-01,,10,Approved PO\n',
            'procurement_quantities_csv.csv': 'L-1,8,Independent receiving record\n',
            'rebate_purchases_csv.csv': 'P-1,Supplier D,R-1,2026-08-01,10,1000\n',
            'rebate_settlements_csv.csv': 'S-1,Supplier D,R-1,10,2026-10-15\n',
            'parcel_charges_csv.csv': 'SHIP-1,INV-3,SYNTHETIC-ONLY,Carrier A,2026-08-15,GROUND,5,10,30\n',
            'parcel_assessments_csv.csv': 'A-1,SHIP-1,Carrier A,2026-08-15,GROUND,5,10,22,Reviewed contract,2026-08-01,synthetic-reviewer\n',
            'utility_bills_csv.csv': 'B-1,Utility A,AC-1,SC1,2026-08-31,20,100,0,0,31,2026-08-01,2026-08-31\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            for stage, expected in [('1', {'ap': 10000, 'warranty_credit': 7000}), ('2', {'procurement': 2000, 'rebate': 4000}), ('3', {'parcel': 800, 'utility': 500})]:
                root = Path(tmp) / stage
                config_path = create_kit(root, 'SYNTHETIC-ONLY', stage)
                config = json.loads(config_path.read_text())
                for path in root.glob('*.csv'):
                    if path.name in rows:
                        path.write_text(path.read_text() + rows[path.name])
                for branch in ('ap', 'utility'):
                    if branch in config:
                        config[branch]['default_effective_from'] = '2026-01-01'
                if stage == '2':
                    (root / 'rebate_programs_json.json').write_text(json.dumps([{'supplier_id': 'Supplier D', 'program_id': 'R-1', 'period_start': '2026-01-01', 'period_end': '2026-09-30', 'tier_mode': 'retroactive', 'measurement_basis': 'spend', 'tiers': [{'min_measure': 0, 'max_measure': None, 'rate_pct': 5}]}]))
                if stage == '3':
                    config['utility']['utility_id'] = 'Utility A'
                    (root / 'utility_tariffs_json.json').write_text(json.dumps([{'sc_code': 'SC1', 'effective_date': '2026-01-01', 'logic_steps': [{'step_name': 'Customer', 'charge_type': 'fixed_fee', 'value': 5}, {'step_name': 'Energy', 'charge_type': 'per_kwh', 'value': 0.1}]}]))
                self.assertEqual(preflight(config, root), [])
                # Verification here is solely a synthetic fixture setting.
                for job in config.values():
                    if isinstance(job, dict):
                        for key in job:
                            if key.endswith('_verified'):
                                job[key] = True
                config_path.write_text(json.dumps(config))
                args = ['run', '--config', str(config_path), '--state', str(root / 'state.json'), '--report', str(root / 'report.json')]
                self.assertEqual(main(args), 0)
                report = json.loads((root / 'report.json').read_text())
                self.assertEqual(report['exceptions'], [])
                for branch, cents in expected.items():
                    self.assertEqual(report['report']['branches'][branch]['validated_cents'], cents)
                self.assertEqual(report['report']['totals']['recovered_cents'], 0)
                self.assertFalse(report['expansion_pilot']['commercially_validated'])
                self.assertEqual(main(args), 0)
                replay = json.loads((root / 'report.json').read_text())
                self.assertEqual(replay['added_finding_ids'], [])
                self.assertEqual(report['state_head_hash'], replay['state_head_hash'])

    def test_bad_headers_and_non_boolean_verification_fail_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'pilot'
            path = create_kit(root, 'client', '1')
            config = json.loads(path.read_text())
            config['ap']['payment_source_verified'] = 'true'
            (root / config['ap']['payments_csv']).write_text('wrong\n1\n')
            errors = preflight(config, root)
            self.assertTrue(any('must be boolean' in e for e in errors))
            self.assertTrue(any('missing columns' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
