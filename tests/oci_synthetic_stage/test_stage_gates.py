import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deployment/oracle-always-free'))
import stage_context as c
import stage_evidence as e

class StageGates(unittest.TestCase):
    def env(self):
        sha='a'*40
        return {'GITHUB_REPOSITORY':c.REPO,'GITHUB_REPOSITORY_ID':c.REPO_ID,
                'GITHUB_REPOSITORY_OWNER_ID':c.OWNER_ID,'GITHUB_REF':'refs/heads/main',
                'GITHUB_WORKFLOW_REF':c.WORKFLOW,'GITHUB_EVENT_NAME':'workflow_dispatch',
                'RETALLY_OCI_SYNTHETIC_STAGE_ENABLED':'true',
                'RETALLY_OCI_RUN_COMMAND_ENABLED':'true','GITHUB_SHA':sha,
                'GITHUB_INPUT_EXPECTED_SHA':sha,
                'RETALLY_OCI_SYNTHETIC_STAGE_APPROVED_SHA':sha,
                'GITHUB_INPUT_CANARY_RUN_ID':'12345','GH_TOKEN':'synthetic-only'}

    def evidence(self):
        sha='a'*40;rid=12345
        run={'id':rid,'workflow_id':c.CANARY_WORKFLOW_ID,'path':c.CANARY_PATH,
             'event':'workflow_dispatch','head_branch':'main','head_sha':sha,
             'status':'completed','conclusion':'success','run_attempt':1,
             'repository':{'id':int(c.REPO_ID),'owner':{'id':int(c.OWNER_ID)}}}
        jobs={'total_count':2,'jobs':[{'name':name,'run_id':rid,
              'status':'completed','conclusion':'success'} for name in c.REQUIRED_JOBS]}
        checks={'total_count':len(c.REQUIRED_CHECKS),'check_runs':[
             {'name':name,'head_sha':sha,'app':{'id':15368},
              'status':'completed','conclusion':'success'} for name in c.REQUIRED_CHECKS]}
        return run,jobs,checks

    def test_exact_context_acceptance(self):
        self.assertEqual(c.check_env(self.env()),('a'*40,12345))

    def test_unsafe_context_denied(self):
        for key,value in [('GITHUB_REF','refs/heads/attacker'),
                          ('GITHUB_EVENT_NAME','pull_request'),
                          ('RETALLY_OCI_RUN_COMMAND_ENABLED','false'),
                          ('RETALLY_OCI_SYNTHETIC_STAGE_ENABLED','false'),
                          ('RETALLY_OCI_SYNTHETIC_STAGE_APPROVED_SHA','b'*40),
                          ('GITHUB_INPUT_CANARY_RUN_ID','evil'),('GH_TOKEN','')]:
            with self.subTest(key=key),self.assertRaises(c.Hold):
                env=self.env();env[key]=value;c.check_env(env)

    def test_exact_manual_canary_accepted(self):
        e.inspect(*self.evidence(), 'a'*40,12345)

    def test_fake_or_skipped_canary_denied(self):
        for key,val in [('event','pull_request'),('conclusion','skipped'),
                        ('head_sha','b'*40),('workflow_id',444),
                        ('head_branch','experimental')]:
            with self.subTest(key=key),self.assertRaises(c.Hold):
                run,jobs,checks=self.evidence();run[key]=val
                e.inspect(run,jobs,checks,'a'*40,12345)
        for status in ('skipped','failure','cancelled',None):
            with self.subTest(status=status),self.assertRaises(c.Hold):
                run,jobs,checks=self.evidence()
                jobs['jobs'][1]['conclusion']=status
                e.inspect(run,jobs,checks,'a'*40,12345)

    def test_truncated_provider_pages_rejected(self):
        run,jobs,checks=self.evidence();jobs['total_count']=99
        with self.assertRaises(c.Hold):e.inspect(run,jobs,checks,'a'*40,12345)
        run,jobs,checks=self.evidence();checks['total_count']=500
        with self.assertRaises(c.Hold):e.inspect(run,jobs,checks,'a'*40,12345)

    def test_missing_exact_sha_ci_denied(self):
        run,jobs,checks=self.evidence()
        checks['check_runs'][0]['head_sha']='b'*40
        with self.assertRaises(c.Hold):e.inspect(run,jobs,checks,'a'*40,12345)

if __name__=='__main__':unittest.main()
