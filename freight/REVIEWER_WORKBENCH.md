# Offline reviewer workbench

The audit-result ZIP includes `reviewer-workbench.html`, a self-contained screen
for customer-derived evidence. It is not a public site or hosted data service.
Keep the HTML, exported decisions, and source documents inside the approved
customer-processing environment. No carrier or settlement action occurs here.

## Review, pause, and continue

Search/filter the case list, inspect billed charge, expected amount, discrepancy,
effective rule and calculation, then explicitly select a decision for an eligible
buyer-review case. Enter whole non-negative review minutes and save the draft.
No decision is preselected. Evidence-remediation cases show evidence/rerun
instructions instead of approval controls.

Unfinished edits survive case navigation, search, and filter changes. Save or
discard all unfinished edits before exporting or reopening a file. Use **Not
drafted** and **Next undrafted case** to continue. Drafts and unfinished edits
exist in memory only; closing this HTML does not save them automatically.

Export decisions as JSON before closing. An export request is not proof that a
file was saved. Verify the downloaded file in the approved location. To continue
past a 2,000-decision batch, acknowledge that the export was saved and checked,
then start another batch. Earlier exported cases are excluded from subsequent
batches during that session and remain labelled **not approved**. Editing a
decision invalidates the prior saved-file acknowledgement.

Open a saved JSON draft to resume this exact audit. Existing identical drafts
are retained; conflicting/stale files and remediation decisions are rejected
before any current drafts change. Original review timestamps are retained.
Earlier-batch tracking is in-memory and session-local, not durable backend history.

## Approved backend handoff

Browser exports are untrusted proposals, not signatures, authenticated identity,
authorizations, or permission to contact a carrier. The caller must authenticate
and authorize the reviewer outside the file, supply the current canonical proof
objects, and persist a new review batch only after the complete import succeeds.

A single-file import remains available as `import_reviewer_decisions`. For split
exports or continuation of a prior reviewed batch:

```python
from freight.reviewer_workbench import import_reviewer_decision_files

batch = import_reviewer_decision_files(
    files=exported_json_files,  # iterable of bytes
    review_packet=artifacts.review_packet,
    review_routing=artifacts.review_routing,
    truth=artifacts.factory.truth,
    reviewer_role=authenticated_reviewer_role,
    previous_batch=previous_verified_batch,  # None for initial handoff
)
```

The combined importer validates every export, then calls the existing
`build_buyer_review_batch` proof-validation path once. Partial work stays partial;
unresolved decisions do not become confirmed. Unknown/remediation cases remain
ineligible. This importer performs no persistence or external action.

Repeated files and identical decisions across files are idempotent. Duplicate
rows within one file remain invalid. Different dispositions, effort, or review
instants for the same case reject the entire handoff. Equivalent known UTC
offsets normalize to the same instant. A supplied prior batch is re-verified
against current proofs, all its decisions are retained, and it cannot be
relabelled to another reviewer role. Conflicts with prior decisions require
explicit resolution, not last-file-wins replacement.

## Limits and validation

Each file permits 1 MiB and 2,000 proposals. A combined handoff permits 32 supplied
files, 16 MiB total input, and 20,000 unique decisions including a prior batch.
Repeated files/bytes still count toward input limits. An empty decision export
is valid and preserves prior decisions; an absent file collection is rejected.

The importer rejects unexpected identity/authority fields, duplicate JSON
properties, invalid dispositions, non-integer effort, malformed timestamps,
non-finite numbers, stale proof context, conflicting decisions, and exceeded
limits. The combined parser also rejects unknown `-00:00` offsets and timestamps
outside the supported UTC range. Source-file hashes identify input bytes; they
do not authenticate their author.

## Display and data handling

Generation validates packet/routing/truth relationships through the existing
buyer-review workflow. Evidence is inert escaped JSON, inserted using
`textContent`, never interpreted as HTML. Hash-based CSP allows only the exact
bundled script/style and blocks network connections and form submission.
There is no analytics, browser storage, external resource loading, or upload.

Decimal strings and `BigInt` preserve exact integer cents. The screen preserves
currency per case, never adds currencies together, does not render unknown
expectations as zero, and does not label discrepancies as realized savings.

## Release verification

The saved browser upgrade was re-tested locally: **27 Chromium tests passed**
using system Chromium. The new pure Python export parser/assembly suite has
**47 passing tests**, including a 2,001-decision package. These are scoped local
checks, not a passing full repository gate.

Nine additional real-pipeline handoff regressions are included for CI, covering
prior-batch preservation, conflict rejection, role separation, remediation
exclusion, replay, and 2,001 findings. The CI handoff job includes the existing
renderer/importer, buyer-review, and audit-result bundle suites. A separate job
runs the browser suite with pinned test tooling.

The full backend/repository suite has not been demonstrated passing for this
revision. Keep PR #107 in draft until the complete Freight Commercial Contracts
and Freight Reviewer Workbench workflows succeed on the final head. Local tests
use offline Chromium with HTML loaded in memory; Safari/iOS file-opening,
production authentication/hosting, and real-customer accuracy are not verified.
