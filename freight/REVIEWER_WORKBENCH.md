# Offline reviewer workbench

The audit-result bundle includes `reviewer-workbench.html`: a self-contained, customer-derived review screen. It is not a public website or a hosted customer-data service. Keep it in the approved processing environment and retain the original evidence separately.

## Reviewer flow

Open the generated HTML in an approved browser. Filter or search the case list, inspect invoice billed amount, expected amount, discrepancy, effective rule and calculation, then select an explicit decision for an eligible buyer-review case. Enter whole, non-negative review minutes and save the draft. No decision is preselected. Evidence-remediation cases show the missing evidence and rerun instruction instead of decision controls.

Export draft decisions before closing. Drafts exist in browser memory only: there is no automatic server save, localStorage, analytics, external resource loading or upload. An export contains at most 2,000 decision proposals and the packet/routing/truth hashes. It is not a signature, proof of reviewer identity, buyer authorization, or permission for carrier contact.

## Approved backend handoff

The caller must obtain authentication, authorization and reviewer role outside the exported file, then import the proposals against the CURRENT canonical proof objects:

```python
from freight.reviewer_workbench import import_reviewer_decisions

batch = import_reviewer_decisions(
    data=decision_json_bytes,
    review_packet=artifacts.review_packet,
    review_routing=artifacts.review_routing,
    truth=artifacts.factory.truth,
    reviewer_role=authenticated_reviewer_role,
)
```

The importer delegates to the existing `build_buyer_review_batch` path. It rejects stale packet/routing/truth context, duplicate decisions, decisions for evidence-remediation cases, unknown properties, self-asserted reviewer-role fields, invalid dispositions, naive timestamps, noninteger effort, duplicate JSON properties, non-finite JSON values, oversize files and oversize decision lists. Partial review stays partial; unresolved is not confirmed. Persist the resulting review batch through the existing approved process; this adapter does not overwrite history or execute carrier actions.

## Integrity and display

Generation validates packet/routing/truth relationships through the buyer-review workflow before rendering. Customer values are serialized as inert JSON with HTML delimiters escaped and inserted into the DOM via `textContent`, not interpreted as HTML. A content-security policy permits only the exact bundled script/style hashes and disallows network connections and form submissions.

Economic values cross into JavaScript as decimal strings and are formatted with `BigInt`, preserving exact integer-cent values. The screen does not combine currencies, label unknown expectations as zero, or present discrepancies as recovered money. Hashes detect inconsistency against trusted originals; they do not authenticate a reviewer or make an editable browser export authoritative.

## Verification and limitations

`freight/test_reviewer_workbench.py` runs real synthetic audit fixtures through rendering and the decision importer. The separate `Freight Reviewer Workbench` CI workflow also runs existing buyer-review and bundle regressions; the full Freight Commercial Contracts workflow remains unchanged.

Local synthetic browser QA exercised 1440, 768, 390 and 320-pixel widths, explicit decision export, evidence-only cases, empty search, clean audit, and maximum int64-cent formatting. No horizontal overflow, JavaScript exceptions or external requests were observed. Chromium ran offline with locally generated HTML loaded in memory because the tool environment blocks `file:` navigation. This does not establish Safari/iOS file-opening compatibility, authentication, hosting readiness, a production security certification or real-customer audit accuracy.
