#!/bin/bash
# Run on a disposable, freshly cloned upstream repository, without credentials.
set -eu
cd "$1"
[[ $(git rev-parse HEAD) == e311d6495124cf0bdc629c813fc97a39a9a3054d ]]
git diff --quiet HEAD --
[[ -z $(git ls-files --others --exclude-standard) ]]
npm ci --no-audit
for package in tui ai agent coding-agent; do
    (cd "packages/$package" && ../../node_modules/.bin/tsgo -p tsconfig.build.json)
done
cd packages/coding-agent
npm run copy-assets
npm run bundle
