# RETALLY Lab 15 — Continuous Public Freight Evidence Acquisition

**Status: research collector / release candidate, not production and not a real-case accuracy benchmark.** Adds an isolated companion to the existing 14 labs. Does not reset the 14-lab census, prior unverified research findings, or release controls.

## Objective

Build a continually growing, deduplicated index of authentic-looking LTL audit data sources that may later support RETALLY's independently verified second-look engine. A full audit evidence chain requires the original carrier invoice, buyer-scoped rate contract/tariff effective on the shipment date, original bill of lading or weight inspection, payment and credit records, previous auditor disposition, and independent adjudication. A linked public exhibit rarely contains all those items.

## Current behavior

- Searches seven bounded, public metadata API queries across Data.gov, Harvard Dataverse, DataCite and GitHub public repositories.
- Seeds four previously observed public bankruptcy/GAO evidence URLs; these are source references, not proof of reuse permission.
- Deduplicates by URL SHA-256; keeps the original first-seen date; preserves a deterministic, digest-checked research ledger. No changes on an unchanged repeat run.
- Fixed allowlisted API and result hosts; no credentials, POST, bypassed controls, arbitrary crawls, or user-supplied URLs. Rejects redirects, suspicious URL credentials, customer contact e-mails in paths, DNS resolving to private addresses, bad MIME/response bounds, and malformed source records.
- Default runs are offline. Network mode explicitly permits only the fixed public metadata endpoints. Individual feed failures are reported rather than silently treated as success.
- **No raw PDF or invoice bytes are stored, no extraction performed, and no third-party records copied into public GitHub.** Public URLs and generic source categories are stored; raw source titles are not replicated. It is a discovery queue, not an admitted source-data vault.
- Every source stays CANDIDATE_ONLY_RIGHTS_AND_TRUTH_UNVERIFIED, with every real-invoice/archive, signed authority, recovered cash and marketing flag fixed to false. An externally modified flag fails validation.

## Automation and isolation

The new workflow, .github/workflows/retally-lab15-public-evidence.yml, runs adversarial Python unit tests on pull requests. Its scheduled discovery runs twice per day, at 09:17 and 21:17 UTC, **but only after the workflow is approved and present on the default GitHub branch**, because GitHub does not schedule workflows solely on unmerged feature branches. On scheduled runs it checks out a separate research/retally-lab15-candidate-ledger branch, safely merges the latest main when possible, and only commits the candidate metadata file to that branch. No protected-main commits, production deploys, customer contacts, payment operations, or file downloads.

GitHub can delay scheduled actions and public APIs can be unavailable or rate-limited. The workflow includes a bounded execution time and exposes per-feed errors in its action log. GitHub Actions does not have any automatic access to licensed DAT iQ, Loop, PACER, or customer-only accounts.

Manual offline smoke test:

    python -m unittest freight.test_lab15_evidence_harvester -v
    python -m freight.lab15_evidence_harvester --report /tmp/retally-lab15-run.json

Fixed public metadata-only scan, after an explicit decision to run network fetches:

    python -m freight.lab15_evidence_harvester --network --report /tmp/retally-lab15-run.json

## Required before storing real original documents

1. Establish written owner permission and license scope to retrieve, process, persist and commercially evaluate the underlying invoice, every rate package, embedded third-party shipment documents, and related identity data. Public visibility alone does not grant commercial rights.
2. Provide an encrypted, access-controlled evidence store with separate buyer/BU boundaries, retention/deletion controls, audit logs and sandboxed parsing; public GitHub is not appropriate.
3. Conduct blinded independent truth adjudication, including clean/no-overcharge cases, credits, held disputes, negative controls and missed findings. Never equate discrepancy arithmetic with recoverable cash.
4. Complete legal/privacy, data provenance, anti-duplication, financial/release review and the existing 18 human pilot controls before importing buyer data or making superiority or fee claims.

**Audit limitation:** Lab 15 can automatically accumulate source leads after release, but cannot yet automatically acquire original licensed invoice bytes. That requires a separately approved secure ingestion backend and rights for each underlying record. Nothing here proves an actual customer recovery, accuracy rate, or superiority over incumbent auditors.
