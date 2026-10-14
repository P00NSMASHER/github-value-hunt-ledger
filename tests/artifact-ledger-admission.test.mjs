import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const FILES=[['tic-mrf-ledger.yml','max_indexes'],['urdb-ledger.yml','history_limit']];
for (const [name,field] of FILES) {
  test(name+' refuses branch-selected sources and unbounded artifact parameters',()=>{
    const data=readFileSync(new URL('../.github/workflows/'+name,import.meta.url),'utf8');
    assert.match(data,/workflow_dispatch:/);
    assert.match(data,/push:\n    branches: \[main\]/);
    assert.match(data,/permissions:\n  contents: read/);
    assert.match(data,/concurrency:[\s\S]*?cancel-in-progress: false/);
    assert.match(data,/  admission:\n/);
    assert.match(data,/test "\$GITHUB_REF" = 'refs\/heads\/main'/);
    assert.match(data,/ls-remote --exit-code/);
    assert.match(data,/test:\n    needs: admission/);
    assert.match(data,/needs: \[admission, test\]/);
    assert.match(data,/ledger_workload_parameters\.py/);
    assert.match(data,/steps\.parameters\.outputs\.retention_days/);
    assert.ok(data.includes('steps.parameters.outputs.'+field));
    assert.doesNotMatch(data,/contents: write|secrets\.(?!GITHUB_TOKEN)/);
  });
}
test('Strict workload validator retains reviewed TiC 60, URDB 100, and retention 90',()=>{
  const validator=readFileSync(new URL('../tools/ledger_workload_parameters.py',import.meta.url),'utf8');
  assert.match(validator,/"tic":\("max_indexes",60\)/);
  assert.match(validator,/"urdb":\("history_limit",100\)/);
  assert.match(validator,/MAX_RETENTION_DAYS=90/);
  assert.match(validator,/re\.fullmatch/);
  assert.match(validator,/exactly one/);
});
