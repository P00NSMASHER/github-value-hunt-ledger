import json
import tempfile
import unittest
from pathlib import Path
from freight.lab_phase3_release_manifest import validate, REQUIRED

class ReleaseManifestTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        for s in REQUIRED:(self.root/s).parent.mkdir(parents=True,exist_ok=True)
        for s in REQUIRED:(self.root/s).write_text('fixture')
        entries=[]
        for i in range(26):entries.append({'id':f'OLD-{i}','remediation':'OPEN_UNVERIFIED','customer_or_production_impact':'NOT_ESTABLISHED'})
        for i in range(2):entries.append({'id':f'GATE-{i}','remediation':'FIXED_AND_REGRESSION_TESTED_RESEARCH_GATE_ONLY','customer_or_production_impact':'NOT_ESTABLISHED'})
        (self.root/'freight/research/LAB_FINDINGS_CUMULATIVE.json').write_text(json.dumps({'entries':entries,'historical_open_findings':26}))
    def test_counts_unchanged_and_never_deployed(self):
        p=validate(self.root)
        self.assertEqual(p['original_findings_open'],26)
        self.assertFalse(p['merge_performed'])
        self.assertFalse(p['production_deployed'])
    def test_missing_file_fails(self):
        (self.root/REQUIRED[-1]).unlink()
        with self.assertRaisesRegex(ValueError,'MISSING_REQUIRED_CODE'):validate(self.root)
    def test_count_tamper_fails(self):
        f=self.root/'freight/research/LAB_FINDINGS_CUMULATIVE.json'
        p=json.loads(f.read_text());p['entries'].pop();f.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,'HISTORICAL_FINDINGS_COUNT_CHANGED'):validate(self.root)
if __name__=='__main__':unittest.main()
