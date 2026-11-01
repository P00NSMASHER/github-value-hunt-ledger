import sys,unittest
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'deployment/oracle-always-free'
spec=spec_from_file_location('plan_synthetic_stage',D/'plan_synthetic_stage.py')
plan=module_from_spec(spec)
spec.loader.exec_module(plan)

class WorkflowSafety(unittest.TestCase):
    def test_plan_never_claims_host_or_customer_deployment(self):
        rec={'stage_readiness':'PASS','remote_deployment':'NOT_EXECUTED',
             'customer_release':'HOLD','source_sha':'a'*40}
        result=plan.make_plan(rec)
        self.assertEqual(result['release'],'SYNTHETIC_ONLY')
        self.assertFalse(result['operations_performed'])
        self.assertFalse(result['services_started'])
        self.assertFalse(result['public_access_enabled'])
        for k,v in [('stage_readiness','HOLD'),('remote_deployment','COMPLETE'),
                    ('customer_release','GO')]:
            bad=dict(rec);bad[k]=v
            with self.assertRaises(plan.Hold):plan.make_plan(bad)

    def test_no_oracle_write_credentials_or_schedule(self):
        body=(ROOT/'.github/workflows/retally-oci-synthetic-stage-readiness.yml').read_text()
        self.assertIn('  pull_request:',body)
        self.assertIn('  workflow_dispatch:',body)
        self.assertNotIn('  schedule:',body)
        self.assertNotIn('  push:',body)
        self.assertIn('actions: read',body)
        self.assertIn('checks: read',body)
        self.assertNotIn('id-token: write',body)
        self.assertNotIn('secrets.RETALLY_OCI',body)
        self.assertNotIn('oci instance-agent command create',body)
        self.assertIn("vars.RETALLY_OCI_RUN_COMMAND_ENABLED == 'true'",body)

if __name__=='__main__':unittest.main()
