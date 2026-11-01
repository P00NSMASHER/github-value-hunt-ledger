# RETALLY synthetic red-team historical source archive

**REVIEW ONLY. DO NOT DEPLOY OR AUTOMATICALLY MERGE INTO PRODUCTION.**

This branch preserves the exact original Git blobs from draft PRs
[#646](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/646),
[#653](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/653), and
[#656](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/656).

- 11 original source-file records across the 3 PRs, including two identical
  v2/v3 Python source revisions intentionally preserved under each source PR.
- Original CI workflow definitions are **inert text under this research path**.
  No schedules, actions, deployments or access permissions are carried over.
- All customers, invoices, contracts, reversals and mode labels are synthetic.
  Tests are evidence of designed failure modes, **not** actual customer accuracy,
  real cash recovery, carrier authority or commercial readiness.
- Archive validation only verifies original Git blob identity and parses Python
  syntax. It intentionally does not run the historical red-team source in the
  current production module namespace or change any freight engine.

Run: `python research/retally-redteam-archive/verify_archive.py`.
Manifest `SOURCE_MANIFEST.json` records original PR/head/file/Git SHA exactly.
Each PR branch and discussion remains an independent historical source.
