import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const names=["freight-contracts.yml","freight-outreach-safety.yml","production-contracts.yml","recoveryworks.yml","repository-release-gate.yml","ai-business-os.yml"];
for (const name of names) {
  test(name+' main-only CI and noncanceling protected release',()=>{
    const data=readFileSync(new URL('../.github/workflows/'+name, import.meta.url),'utf8');
    assert.match(data,/pull_request:/);
    assert.match(data,/push:\n    branches: \[main\]/);
    assert.match(data,/concurrency:/);
    assert.match(data,/cancel-in-progress: \$\{\{ github\.event_name == 'pull_request' \}\}/);
    assert.match(data,/permissions:\n  contents: read/);
    assert.doesNotMatch(data,/secrets\.[A-Z_]+/);
    if(name==='freight-outreach-safety.yml')assert.doesNotMatch(data,/fix\/freight-outreach-safety-20261007/);
    if(name==='repository-release-gate.yml'){
      for (const lane of ['ai-business-os:','freight:','recoveryworks:','technology-intelligence:','release-gate:'])
        assert.ok(data.includes('\n  '+lane), 'Missing original release lane: '+lane);
      assert.match(data,/\bif: always\(\)/);
    }
  });
}
