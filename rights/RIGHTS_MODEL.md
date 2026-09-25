# Canonical Rights / Provenance Model

This is an operational evidence model, not a legal opinion.

## Evidence classes

- **PUBLIC_LICENSE_VERIFIED** — the public-license basis for the exact subject/revision has been verified and recorded.
- **OWNER_ATTESTED** — the owner/operator has made a dated assertion. This is evidence of the assertion, not proof that an executed third-party agreement exists.
- **EXECUTED_PERMISSION_VERIFIED** — an executed permission/license evidence object has been independently verified and SHA-256 bound.
- **UNKNOWN_REVIEW** — the relevant right has not been resolved.
- **DENIED** — verified evidence establishes the right is denied.

Evidence classes are never silently upgraded.

## Scope states

Every subject is evaluated separately for:

commercial use; hosted/SaaS; redistribution; assignment; sublicensing; change of control; datasets; model weights; bundled assets; trademarks/patents.

Allowed scope states are:

`ALLOWED`, `ALLOWED_WITH_CONDITIONS`, `DENIED`, `UNKNOWN_REVIEW`, `NOT_APPLICABLE`.

A commercial-use grant does **not** imply hosted/SaaS, assignment, sublicensing, redistribution or change-of-control rights.

## Standing Hunter assertion

The 2026-09-19 standing owner assertion remains recorded as **OWNER_ATTESTED** provenance.

It has **automatic_scope_effect=false**.

Therefore it may inform research prioritization and analysis, but it cannot automatically promote a newly discovered repository to runtime/commercial readiness. Each subject/revision must receive an explicit canonical rights record.

## Operational stages

- **ANALYSIS** — provenance/research may proceed. No runtime permission is implied.
- **CONTROLLED_PILOT** — requires resolved commercial-use scope. `ALLOWED_WITH_CONDITIONS` yields CONDITIONAL, not READY.
- **HOSTED_SAAS** — requires both commercial-use and hosted/SaaS scopes.
- **ACQUIRER_DILIGENCE** — requires commercial use, hosted/SaaS, redistribution, assignment, sublicensing and change-of-control scopes.

Missing or denied required scopes fail closed.

## Cross-subsystem rule

Hunter, Freight, RecoveryWorks and AI Business OS all use this model. Historical notes remain historical provenance; their wording is not runtime authority.

The private production registry lives in `ai_business_os_prod.rights_*`.
The public mirror is `rights/RIGHTS_REGISTRY.json`.
