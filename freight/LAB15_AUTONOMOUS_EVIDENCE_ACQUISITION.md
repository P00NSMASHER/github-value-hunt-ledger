# RETALLY Lab 15 — Autonomous Public Freight Evidence Acquisition

**Status:** Reviewable source-acquisition lane. Scheduled **every six hours once merged into the GitHub default branch**. It is not a RecoveryOS deployment, paid customer pilot, commercial data license or independent billing-accuracy certification.

## Mission

Continually discover original public LTL invoice evidence, contemporary rate documents, shipment corrections, and independently reviewed overcharge decisions. Preserve stable source pointers, acquisition fingerprints and rights boundaries. Never equate a source lead with a validated recovery.

Lab 15 is independent of Labs 1–14. The unmerged Lab 14 research chain, 18 external pilot gates and historical defect findings are unchanged.

## Implemented automation

1. Seed exact public source URLs: GAO historical freight-audit decisions, Kentucky PSC freight-invoice dockets, and ABF bankruptcy carrier-invoice exhibits. Registry: freight/lab15/sources.json.
2. On explicit live runs, fetch only official GAO-authored published decision HTML (allowlisted HTTPS) for a bounded SHA-256 fingerprint. Reject redirects, unsafe URLs, incorrect MIME, oversized content and failed HTTP. Do not retain the raw document text or original document.
3. Discover newly indexed dataset **metadata** from public GitHub, Zenodo and Harvard Dataverse catalog APIs. Apply freight/invoice relevance filters; exclude self-identified fictional/demo datasets. Never access any private repository, document or customer account.
4. Append new rights-held source pointers to freight/lab15/evidence_ledger.json. Canonical URL hashes prevent duplicates; changes to known GAO public documents increment versioned source receipts.
5. Validate immutable holds on unverified payment, fee, document reuse, real accuracy and customer authority. A content hash proves the fetched bytes' identity, not correctness or permission.
6. A read-only pull-request test checks the code and ledger. Once the workflow is merged to main, a GitHub Actions run every six hours (17 */6 * * *) updates only the public **metadata ledger**, and commits only when something new or changed was seen. Job is serialized with safe non-force push. GitHub may delay or skip schedules.

## Source classifications

| Source | Automatically stored | Still missing |
| --- | --- | --- |
| GAO official opinions | Exact public URL, document content SHA-256 and size, publication identity | Individual source invoices, controlling tariff, independently matched shipment and cash |
| Kentucky public-service commission exhibits | Docket URL and provenance metadata only | Source PDF retention permission, underlying customer tariff, payment |
| Epiq bankruptcy proofs of claim | Exact public exhibit URL and provenance metadata only | Rights to store original third-party invoices and real payment/credit confirmations |
| GitHub, Zenodo, Dataverse public listings | Dataset repository/record URLs and sanitized titles | Source permissions, original carrier files, observed financial truth |

These are **real source leads**, not approved or certified commercial training data. A publicly posted or court-filed invoice is not automatically licensed for retention or commercial redistribution. The software therefore does not persist original customer or carrier PDFs in public GitHub.

## Non-negotiable ledger safeguards

Every metadata record must retain false values for:
- raw_document_stored
- commercial_test_approved
- actual_payment_verified
- independent_invoice_error_verified
- recovery_verified

Validation rejects the entire ledger if any row asserts those approvals. Cross-tenant source documents, private addresses, account credentials, contact details, signed rate contracts and financial records must never enter this public source repository.

This lab does **not** download/store raw third-party PDFs, infer an overcharge, make carrier contact, file FOIA requests, use paid services, publish proof claims, or touch RecoveryOS financial records. Some catalog APIs can fail/rate-limit; failure remains a hold, not a fabricated success. It is therefore a continuous public **discovery and provenance** system, not yet an independently valid invoice-level dataset.

## Runbook

From repository root:

    python -m unittest -v freight.test_lab15_acquisition
    python -m freight.lab15_acquisition --report /tmp/lab15-offline.json

Default is offline, with zero network access. For an explicitly authorized bounded public-source refresh:

    RETALLY_LAB15_PUBLIC_FETCH_ENABLED=1 python -m freight.lab15_acquisition --live --report /tmp/lab15-live.json

The scheduled job sets that environment guard on main only. No live acquisition runs on an unmerged draft PR.

Next expansion after proof of rights and storage security: private customer-authorized acquisition with original invoice, effective contract/rate, BOL/POD, payment/credit events, incumbent findings and independently adjudicated labels; blind test splits and a pre-registered evaluation protocol; source-specific retention and deletion. Keep those source documents outside GitHub and separate from public research metadata.
