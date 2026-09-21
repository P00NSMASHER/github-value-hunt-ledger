# Evidence Remediation Plan

The Evidence Remediation Plan is the deterministic operator artifact for review cases that are **not** ready for buyer confirmation.

It is derived from the verified Reviewer Work Packet and the canonical Review Routing artifact. It cannot reclassify cases on its own.

## Remediation actions

- **VERIFY_AUTHORITY_AND_RERUN** — obtain a documented controlling-authority determination and trusted source/scope evidence for the authority used.
- **ADD_RULE_AND_RERUN** — add the applicable governing rate/rule with its source-document hash and trusted customer/carrier/currency context.
- **RESOLVE_RULE_SET_AND_RERUN** — resolve overlapping applicable rules so one controlling rule applies to the case.
- **INVESTIGATE_AND_RERUN** — obtain case-specific invoice/shipment/accessorial/authority evidence sufficient to establish one supported expected charge or a defensible no-finding result.

Each plan item is bound to the exact review-case hash, queue position, current expected/variance values, matched rule hashes, routing hash, and packet hash.

## Rerun rule

Remediation never edits or promotes the existing finding in place.

Authority/rule/evidence changes can alter:

- rule hashes;
- expected amounts;
- finding IDs/proof hashes;
- frozen truth;
- review queue;
- reviewer packet;
- routing;
- canonical audit-run hash.

Therefore every remediation item explicitly requires a fresh audit workflow run after the corrected evidence is supplied. Prior artifacts remain historical evidence.

## Boundary

The plan is an internal/customer-processing workflow artifact. It does not:

- make the buyer's review decision;
- authorize carrier/vendor contact;
- submit a dispute;
- accept settlement;
- move money;
- convert discrepancy dollars into realized savings.
