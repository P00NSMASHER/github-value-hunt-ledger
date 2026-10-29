# RETALLY: original-invoice blind accuracy benchmark

**Status: SOURCE CENSUS PINNED; INDEPENDENT ACCURACY NOT YET SCORED.**

This connects 100 original GlobalTranz and 10 original ArcBest freight invoice
faces from the existing ephemeral original-document lab to a private, reviewed,
case-level benchmark. It does not convert an invoice, same-source statement or
historical GAO/FMC ruling into proof of a new customer overcharge.

## Available source evidence

The lab checks frozen original PDF SHA-256s, 110 unique invoice faces, 15
original face anchors, source-face catalog fingerprints, and original money
arithmetic. All 100 GlobalTranz invoice faces reconcile to original printed
charge components. An open-account statement is not bank clearing. ArcBest
includes some source-internal quote/BOL pages, not independently authenticated
accepted contracts, signed delivery and financial settlement.

The new census gate refuses source drift, missing faces, failed anchor checks
and false promotion of recovery, accuracy, source rights or commercial state.
The existing lab's source arithmetic and same-source joins are useful
engineering evidence; they are **not independent freight-rate truth**.

## Reproducible read-only baseline

Use the existing original-document lab workflow:

    python -m freight.real_document_lab --output /tmp/retally-real-document-report.json
    python -m freight.original_invoice_blind_benchmark --baseline \
      --lab-report /tmp/retally-real-document-report.json

Only source-level hashes, counts and null accuracy indicators are published.
No case IDs, original PDF content or bank-like records are included in the
receipt, repository, CI artifacts or public job summary.

## Private casebook preparation

Only run in a suitably authorized, access-controlled evidence room, with
appropriate rights for third-party source processing. Use a high-entropy
32+ byte HMAC key obtained from a secret manager, never GitHub or CLI args:

    export RETALLY_PRIVATE_BENCHMARK_HMAC_KEY='<private random secret>'
    mkdir -m 700 /private/outside/repository/freight
    python -m freight.original_invoice_blind_benchmark --prepare \
      --output /private/outside/repository/freight/census.json

Private case IDs are keyed MACs bound to issuer, exact original source SHA,
invoice identifier, source page, amount and source dates. A re-run with
identical documents/key preserves IDs. Original PDFs are read and checked in
memory; they are not saved. The output is a new-only POSIX 0600 private file
outside the Git repository. Windows preparation is disabled until an operator
provisions and verifies an appropriate protected file-vault ACL.

Do not upload this private manifest, invoices, keys, or reviewer proof files to
GitHub, Actions artifacts, public chat or cloud logs.

## Blind reviewer protocol

Pre-register a buyer-authorized scope, original population/census, issuer
strata, extraction and source coverage, independent truth owner and two
reviewers, RecoveryOS operator, legal source rights, and how the truth and
model will be independently frozen before joint unseal.

The model packet needs all frozen case IDs with labels POSITIVE, NEGATIVE or
REVIEW, exact predicted cents (REVIEW is null), model output byte hashes and
operator freeze time. The independent truth packet needs those same case IDs,
with truth POSITIVE, NEGATIVE or UNRESOLVED, adjudicated cents, two reviewers'
labels, source evidence and a truth freeze time. Unknown stays unknown.

Four separate, externally registered Ed25519 public keys must verify the
model operator, truth owner, reviewer A and reviewer B. The keys come from a
separately governed private trust store, NOT from the packets being scored.
The scorer checks immutable source-population case IDs, four signed
declarations, pre-unseal chronology, monetary semantics and documentary proof.

Each scored POSITIVE or NEGATIVE case must link ORIGINAL distinct source files
for (1) the accepted shipment-specific rate/contract, (2) BOL/delivery,
(3) independently cleared payment/credit, and (4) independent adjudication
of an overcharge or a clean negative. Artifact fields are sha256, path, issuer.
The original files must be locally present with matching hashes. Model
predictions and incomplete-source cases do not count as ground truth.
Reviewer disagreements require an explicit adjudication note.

Illustrative private signed packet fields:

    model.body = {population_sha256, operator_id, frozen_at,
       cases: [{case_id, label, variance_cents, model_output_sha256}, ...]}
    model.signatures = {operator: "<base64 Ed25519 signature>"}

    truth.body = {population_sha256, truth_owner_id, reviewer_a_id,
       reviewer_b_id, frozen_at,
       cases: [{case_id, label, variance_cents, reviewer_a_label,
          reviewer_b_label, adjudication_note,
          artifacts: {rate, shipment, payment, adjudication}}, ...]}
    truth.signatures = {truth_owner: "...", reviewer_a: "...", reviewer_b: "..."}

    trust.json = {operator: "<base64 public key>", truth_owner: "...",
       reviewer_a: "...", reviewer_b: "..."}

Scoring is strictly local and read-only:

    python -m freight.original_invoice_blind_benchmark --score \
      --population /private/census.json \
      --predictions /private/frozen-model.json \
      --truth /private/frozen-truth.json \
      --trusted-public-keys /private/trust.json \
      --unseal-at '2026-11-05T14:00:00Z'

Outputs are aggregate TP, FP, TN, FN, REVIEW/abstentions, Wilson uncertainty,
precision, recall including abstentions, false-positive dollars, missed
positive dollars, missing labels and unsupported automatic decisions.
The report does not export IDs, issuer-specific evidence rows or source bytes.

A valid source hash or Ed25519 signature does NOT independently authenticate
the signer's real identity, actual contemporaneous tariff applicability,
bank issuer authenticity, legal document rights, observed freeze chronology
or commercial authority. Those require external custody and source review.

## Commercial acceptance remains separate

This benchmark bridge NEVER approves publication, pilot launch, cash recovery
or billable fees. An authorized buyer study must separately satisfy the existing
freight/AUDIT_ACCEPTANCE_PROTOCOL_V2.md through its full executable
freight/audit_acceptance.py. That policy enforces sample sufficiency,
balanced independent double review, statistical intervals, abstention, exact
money, independent timing/roles and incumbent/duplicate leakage.

Even a complete 110-case census cannot create absent positive/negative labels,
and does not bypass a policy's prevalence or sample-size requirements.

As of October 29, 2026: **110 original invoice faces; zero independently
adjudicated private-buyer truth labels; $0 verified RETALLY cash; precision
and recall not estimable.** No carrier/customer contact, payment, production
rate change or extra scheduled worker is authorized.

## Offline checks

    python -m pytest -q freight/test_original_invoice_blind_benchmark.py

The tests use synthetic faces and independently generated local test signers
solely to validate score math and fail-closed controls. Passing them is not
a real independent freight-accuracy benchmark outcome.
