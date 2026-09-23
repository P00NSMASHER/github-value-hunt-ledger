# Freight Recovery controlled synthetic pilot demo

Updated: 2026-09-23

Status: buyer-shareable technical demonstration using fictional data. It is not customer proof, permission to process customer records, a security certification, or rights clearance.

## Purpose

`freight.synthetic_pilot_bundle` turns the current controlled rehearsal into one deterministic ZIP that a buyer or reviewer can inspect without receiving customer data. It demonstrates that the current code can carry a fixed fictional population through:

1. readiness and bounded scope;
2. invoice and rule ingestion;
3. source-linked finding construction;
4. human review and blind incumbent comparison;
5. a simulated buyer-authorized carrier-action receipt;
6. settlement allocation and a later return;
7. a layered buyer report with non-interchangeable totals.

The carrier-action objects are proof fixtures. No message is transmitted, no carrier is contacted, and no money moves.

## Fixed scenario

The bundle uses three fictional invoices and two verified fictional rules. A third candidate rule is deliberately routed through review and rejected as controlling authority.

| Measure | Synthetic amount | Interpretation |
| --- | ---: | --- |
| Reviewed discrepancy | $100 | All positive differences reviewed; not savings |
| Validated findings | $50 | Two findings supported by the frozen fictional truth; not yet realized |
| Challenger-only validated | $25 | Validated amount absent from the frozen fictional incumbent output |
| Settlement-proven realized | $40 | Two fictional credits totaling $45, less a later fictional $5 return |
| Fee-eligible realized | $15 | Net amount that also passes the fictional attribution policy |

The amounts are intentionally different. They must never be collapsed into a single "savings" number or extrapolated to a buyer population.

## Build and verify

From the repository root:

```bash
python -m freight.synthetic_pilot_bundle /tmp/freight-recovery-synthetic-demo.zip
python -m freight.synthetic_pilot_bundle --verify /tmp/freight-recovery-synthetic-demo.zip
```

The verifier re-runs the current scenario and requires the exact entry set, exact bytes, SHA-256 values, sizes, safe paths, and manifest hash. Duplicate or modified entries fail verification. Fixed ZIP metadata and sorted entries make two builds from the same source byte-identical.

The public-site builder performs the same build, embeds the archive SHA-256 in the page, and publishes it as `synthetic-pilot-demo.zip` inside the exact five-file public boundary.

## Archive contents

- `README.md` &mdash; scope and claim boundary;
- `EXECUTIVE_REPORT.md` &mdash; buyer-facing report from the final state;
- `REVIEW_PACKET.md` &mdash; reviewer evidence and decision packet;
- `REHEARSAL_RECEIPT.json` &mdash; states, hashes, receipts, and separate metrics;
- `TRACE_SUMMARY.txt` &mdash; concise end-to-end workflow receipt;
- `inputs/` &mdash; the five exact fictional CSV inputs;
- `BUNDLE_MANIFEST.json` &mdash; entry hashes, sizes, scenario identity, and boundary claims.

## Safe sales use

Allowed:

- share the generated ZIP or public download as a controlled product walkthrough;
- demonstrate how evidence, review, action authorization, settlement, and reversals remain separate;
- ask a buyer whether the report and decision trail would answer a real operational question;
- verify and quote the archive SHA-256.

Not allowed:

- describe any synthetic amount as a customer recovery, revenue, conversion, benchmark, or expected result;
- imply the simulated external receipt means a carrier was contacted;
- present the archive as production hosting, penetration testing, compliance certification, or rights evidence;
- replace fictional inputs with customer files outside an authorized controlled-data route;
- alter an output while retaining the old manifest or digest.

## Change control

Any workflow or scenario change intentionally changes the ZIP digest. Rebuild the archive, rerun verification, update any published page, and review the claim boundary before sharing the new artifact. Never promise a stable digest across source revisions.
