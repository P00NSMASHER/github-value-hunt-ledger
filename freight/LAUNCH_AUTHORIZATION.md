# Freight Recovery — Launch Authorization Receipt

Updated: 2026-09-20

The final launch gate answers whether a data-handling path is READY. The launch
authorization receipt binds that READY decision to the exact scope and evidence
that will be used by the pilot.

## Purpose

Prevent time-of-check/time-of-use drift such as:

- approving Buyer A but ingesting Buyer B data;
- approving one business unit and using another;
- approving one release but executing under a different release provenance;
- approving one environment evidence snapshot and later substituting another;
- carrying a READY decision past the environment evidence expiry.

## Receipt contents

`freight/launch_authorization.py` binds:

- engagement ID;
- buyer ID;
- business unit;
- selected data path and launch route;
- multi-tenant/parser requirements;
- environment scope ID;
- issued and valid-through dates;
- buyer-readiness hash;
- launch-request hash;
- READY launch-decision hash;
- release-provenance hash;
- component-rights-registry hash;
- rights-evidence hash;
- exact environment-evidence hash;
- final receipt hash.

The builder re-runs the launch gate itself. It does **not** accept a caller
assertion that the decision was READY.

## Data-room binding

A pilot data-room manifest must carry the launch-authorization receipt/hash and
match the authorization's buyer/BU scope. The final pilot package then inherits
that authorization hash.

This creates the chain:

**launch authorization → data-room manifest → population/truth/incumbent package**

## Claim boundary

The receipt is deterministic application-level binding, not an external digital
signature or trusted timestamp. External signing/attestation remains a separate
diligence item.
