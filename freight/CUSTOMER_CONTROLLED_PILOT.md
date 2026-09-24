# Customer-controlled freight pilot

Updated: 2026-09-21. **Operating package, not deployment evidence.** The separate-environment route remains CONDITIONAL until the actual buyer environment is verified. No customer records are requested by this document.

## The practical route

Deliver the first review inside **one buyer-controlled workspace**, using its existing accounts, managed devices and approved document tools. The buyer grants a named Freight reviewer narrowly scoped, read-only access or hosts a controlled screen-sharing session. Keep working papers and reports in that same workspace. Start with manual review; do not deploy automated document ingestion for this first engagement.

This removes the need to build shared customer infrastructure before proving that someone will buy the service. Screen sharing still exposes confidential information and must pass the same authorization and applicable environment controls. The buyer must approve the conferencing provider, viewer, reviewer endpoint and any recording/transcription settings. Recording, screenshots, downloads, clipboard transfer and AI meeting assistants stay off unless separately included and approved in scope.

The public ChatGPT Sites website accepts **business contact details and scope inquiries only**. It is not the freight-document workspace. Invoices, rates, shipment records, payment records and credentials stay out of its forms, the former Netlify shell, ordinary email attachments and the Hunter repository. Contact records require their own access and retention settings; launching a marketing site does not verify a customer-data environment.

## Start now without customer files

Use a 20-minute readiness conversation to establish: buyer/entity and business unit; mode/currency and approximate invoice count; historical period; availability of rates/amendments and shipment evidence; the owners of existing audit results and later credits; and which buyer IT owner can approve the workspace. Discuss availability, not the confidential records themselves.

Record the existing offer/version and the buyer's decision criteria. Preserve
the terms of any previously accepted agreement. A small feasibility sample does
not estimate annual losses or prove recovery. The current flagship route is a
bounded free audit followed, when worthwhile, by a separately accepted
success-based recovery engagement. The legacy fixed-fee activation catalog is
used only for an expressly requested custom forensic audit; do not force a
false fee into the charter.

Confirm a qualified freight reviewer and reserve actual delivery hours before promising a completion date. Proposed prices and synthetic demonstrations are not paid-customer evidence.

## Name these owners before kickoff

| Owner | Accountable result |
|---|---|
| Buyer sponsor / truth owner | Authorizes the exact population, owns reference truth and accepts or challenges findings |
| Buyer IT / workspace administrator | Provisions and demonstrates the actual access, device, storage, conferencing, backup and deletion controls |
| Freight engagement lead | Reconciles offer and scope, maintains evidence references, runs the gates and stops affected work when evidence changes |
| Qualified freight reviewer | Checks authority, effective dates and calculations independently before a finding is asserted |
| Buyer action approver | Separately authorizes each carrier contact, dispute or other external action |

Assign actual names in the private engagement record. One person may hold compatible roles, but a component or analyst cannot independently certify its own extraction, rating and commercial conclusion. The buyer retains independent acceptance authority.

## What proves the workspace is ready

Keep evidence in the buyer-approved private diligence folder. Copy `SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json` there; leave it DRAFT while collecting evidence. Its references point to real, reviewable receipts. Compute SHA-256 from the actual receipt files and configuration snapshot. A hash proves which artifact was reviewed, not whether its claims are true.

| Control | Evidence the buyer IT owner supplies and Freight verifies |
|---|---|
| MFA and scoped access | Dated policy export or administrative screenshots showing MFA applies to every named pilot account; account/access roster, reviewer permissions and successful read-only access to the authorized folder |
| Encryption | Provider configuration/documentation identifying the actual storage and transport; managed-device encryption status for every endpoint that can retain data. Include backup storage and the conferencing path where applicable |
| Read-only sources and one buyer | Source permissions, exact buyer/BU scope and workflow showing source records remain immutable; separate report/working-paper folder. A buyer folder in shared Freight storage alone does not prove a single-tenant environment |
| Retention and deletion | Buyer-approved dates, objects and owners covering documents, working papers, local caches/downloads, meeting artifacts, logs and backups; exceptions and backup expiry stated explicitly |
| Website exclusion | Workflow and configuration evidence showing no freight-file upload, attachment intake or route from either marketing site/contact inbox into the pilot workspace; operator instructions for an accidental confidential submission |

The schema's legacy `customer_data_excluded_from_current_netlify` control remains required. Its evidence bundle must also document the new ChatGPT Sites exclusion; do not rename the existing field or treat migration as an automatic pass.

Use a unique environment ID, actual provider/host, verifier role and verification dates. Set expiry no later than 90 days after verification, and reassess immediately after a material configuration change. `single_tenant=true` and `parser_runtime_used=false` must describe the actual scoped workflow. A general-purpose buyer document viewer is still part of the assessed tool chain; introducing Freight/OCR/LLM ingestion requires fresh parser-runtime assessment. If shared customer storage or automated parsing is required, collect the additional isolation/sandbox evidence required by the existing validator rather than marking it not applicable.

Only after the verifier has inspected the receipts may controls become true and the manifest become VERIFIED. The validator checks structure and completeness; human verification supplies the underlying assurance.

## Four acceptance gates

1. **Metadata fit:** named owners, feasible source availability, compatible existing terms and funded reviewer capacity. Missing items produce an owner and next date, not a document request.
2. **Verified environment:** actual manifest passes `python -m freight.separate_environment_evidence /approved/private/path/environment.json --expect VERIFIED`. This example path must be replaced inside the approved environment; do not upload evidence here to run it.
3. **Authorized kickoff:** buyer/data readiness, rights and the separate-environment launch gate all pass; the current activation packet and acknowledged charter reach `KICKOFF_AUTHORIZED`. Environment verification alone is insufficient. Confirm the path with `python -m freight.pilot_launch_gate /approved/private/path/readiness.json --data-path separate --separate-evidence-json /approved/private/path/environment.json --rights-manifest-json /approved/private/path/rights-evidence.json --expect READY` before generating the acknowledged charter. The repository's default rights manifest is intentionally blocked because executed permission evidence is not attached.
4. **Accepted report:** every sampled invoice has a disposition; findings have independently reviewed support; totals reconcile; the buyer receives missing-evidence and disagreement lists. A report may contain no supported discrepancy. Track later credits/refunds separately and net observed returns before claiming recovery.

## Smallest useful record request after authorization

For the existing 20-invoice feasibility proposal, use one buyer/BU, one supported mode and **USD** for the current automated reporting path, with a prespecified historical selection rule. Request only those invoice/shipment rows; the controlling rates, effective amendments and supporting BOL/POD/weight/accessorial records needed for the selected checks; the sealed incumbent result for the same population; and the location/owner of later settlement evidence. Exclude passwords, payment credentials and unrelated records. Do not request whole mailboxes, whole accounting exports or every contract.

Follow `PILOT_PROTOCOL.md`: freeze population; seal incumbent source; independently freeze buyer-owned truth; then open the incumbent output and compare. Keep source references and hashes in the private data-room manifest. An unavailable source is unresolved, not a clean result. Hunter receives only authorized, minimized lessons and evidence-backed outcome summaries.

## Closeout and exceptions

Before kickoff, the buyer IT owner demonstrates a small authorized backup/restore or version-recovery exercise for the chosen workspace, records what it covers and agrees recovery objectives. Repository tests are not proof of deployed recovery. If no pilot copies are made, document how the buyer can recover source records and working papers; do not invent a Freight backup service.

For mistaken sharing or suspected exposure, stop the affected review, notify the named buyer incident owner through the agreed channel, restrict access, preserve the incident record in the approved location and follow `INCIDENT_RESPONSE.md`. Record an actual contact and response arrangement before kickoff.

At closeout, hand over the report, source/disposition register and any pending settlement questions. The buyer administrator revokes temporary access and supplies deletion/return receipts for the agreed objects, including caches and conferencing artifacts. Backups may expire on their documented schedule; report those remaining copies explicitly. Deletion remains unconfirmed until actual confirmation exists. Record accepted work, actual labor and actual payment separately; only then use the result to decide whether a recurring service is worth offering.
