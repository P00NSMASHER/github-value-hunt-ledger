import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const FILES=[['tic-mrf-ledger.yml','max_indexes',25],['urdb-ledger.yml','history_limit',100]];
for(const [name,field,limit] of FILES){
  test(name+' has main-only immutable admission and bounded resources',()=>{
    const x=readFileSync(new URL('../.github/workflows/'+name,import.meta.url),'utf8');
    assert.match(x,/\bworkflow_dispatch:/);
    assert.match(x,/push:\n    branches: \[main\]/);
    assert.match(x,/permissions:\n  contents: read/);
    assert.match(x,/concurrency:[\s\S]*?cancel-in-progress: false/);
    assert.match(x,/\bif: github.ref == 'refs\/heads\/main'/);
    assert.match(x,/\bref: \$\{\{ github.sha \}\}/);
    assert.match(x,/\bgit ls-remote --exit-code/);
    assert.match(x,/test:\n    needs: authorize/);
    assert.match(x,/\[\[ "\$LIMIT" =~ \^\[0-9\]\{1,3\}\$ \]\]/);
    assert.ok(x.includes('COUNT<= '+limit)||x.includes('COUNT<='+limit));
    assert.match(x,/RETAIN>=1 && RETAIN<=90/);
    assert.match(x,/\[\[ "\$INPUT_RETENTION_DAYS" =~ \^\[0-9\]\{1,2\}\$ \]\]/);
    assert.ok(x.includes(field));
    assert.doesNotMatch(x,/contents: write|secrets\.(?!GITHUB_TOKEN)/);
  });
}
