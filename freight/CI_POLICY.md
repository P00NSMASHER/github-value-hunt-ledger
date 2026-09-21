# Freight CI routing policy

Freight Recovery uses separate CI lanes so proof quality stays high without running the full commercial-contract suite on every intermediate commit.

## Heavy Freight gate

Workflow: `.github/workflows/freight-contracts.yml`

Use for product/control changes under `freight/**` other than the static marketing site and canonical Hunter gap register, plus the production prototype files that the Freight gate explicitly exercises.

Rules:

- feature-branch **pushes do not run** the heavy suite;
- pull requests targeting `main` run the heavy suite when relevant product files changed;
- pushes to `main` run the heavy suite after merge when relevant product files changed;
- a newer run cancels an older in-progress run for the same PR/ref;
- `freight/site/**` is intentionally excluded;
- `freight/GAP_REGISTER.json` and the intelligence ledgers are intentionally excluded and belong to Technology Intelligence CI.

The merge rule remains the same: product/control code should not be merged unless the required heavy gate actually executes and succeeds.

## Freight site gate

Workflow: `.github/workflows/freight-site.yml`

Marketing-site-only changes use a small publication gate:

1. run the source/publication boundary tests;
2. syntax-check the JavaScript;
3. build the exact four-file public bundle with a fixture verified contact;
4. assert no unexpected files are emitted.

This workflow runs for `freight/site/**` changes and its own workflow file only. Site changes do not need the 550+ backend/product contracts when no product code changed.

## Technology Intelligence gate

Workflow: `.github/workflows/technology-intelligence.yml`

Hunter/search/ledger changes remain in their own lane.

Rules:

- feature-branch pushes do not duplicate PR validation;
- PRs targeting `main` validate Technology Intelligence changes;
- main pushes validate and, when appropriate, persist generated ledgers;
- a newer run cancels an older in-progress run for the same PR/ref.

The Freight heavy gate must not be re-triggered merely because intelligence JSONL, `CAPABILITIES.md`, or `freight/GAP_REGISTER.json` changed.

## Manual reruns

All three workflows support `workflow_dispatch` so a controlled manual validation can be requested without changing product files.

## Why

The purpose is not to weaken validation. It is to make the expensive gate run at the decision points that matter:

- PR validation before merge;
- final `main` validation after merge.

Intermediate branch commits, static marketing edits and research-ledger churn should use their narrower gates. This keeps Actions capacity available for the tests that protect customer data, money attribution, external-action authorization, settlement evidence and release provenance.
