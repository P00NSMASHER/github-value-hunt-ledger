# Rights evidence transfer checklist

Updated: 2026-09-23

This checklist converts rights evidence held in another account into verifiable diligence metadata without committing confidential agreement bytes to the source repository. It is an operational process, not a legal opinion.

## For each separately permitted component

The current gate expects evidence for the pinned revisions of:

- `emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65`
- `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045`

For each component:

1. Export the complete executed license, permission, order form, and incorporated terms from the account that holds them.
2. Preserve the original file bytes; do not print-to-PDF, redact, rename, or re-save the verification copy before hashing.
3. Store the bytes in the access-controlled diligence room.
4. Calculate a lowercase SHA-256 of that exact stored object.
5. Record a stable diligence-room reference that an authorized reviewer can resolve.
6. Have an authorized human reviewer confirm the parties, signatures, effective date, component/revision coverage, and scope conclusions.
7. Update a private copy of `RIGHTS_EVIDENCE_MANIFEST.json`; do not commit agreement bytes, credentials, private URLs, or access tokens.
8. Reconcile `COMPONENT_RIGHTS_REGISTRY.json` only to conclusions actually supported by the executed evidence.
9. Run both the pilot and annual validators, preserving their JSON output with the diligence record.

PowerShell can hash an exported file without changing it:

```powershell
(Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\path\to\executed-agreement.pdf').Hash.ToLowerInvariant()
```

## Minimum private manifest fields

For a scope to be treated as resolved, the matching entry must contain:

```json
{
  "evidence_status": "ATTACHED_VERIFIED",
  "evidence_location": "diligence-room/stable-reference",
  "evidence_sha256": "64-lowercase-hex-characters",
  "scopes": {
    "commercial_use": "CONFIRMED_ALLOWED",
    "hosted_saas": "CONFIRMED_ALLOWED",
    "assignment": "UNKNOWN_REVIEW",
    "sublicensing": "UNKNOWN_REVIEW",
    "change_of_control": "CONFIRMED_ALLOWED"
  }
}
```

Those scope values are structural examples, not conclusions about either component. Use only `UNKNOWN_REVIEW`, `CONFIRMED_ALLOWED`, `CONFIRMED_DENIED`, or `NOT_APPLICABLE` as supported by the executed terms. `CONFIRMED_DENIED` and `NOT_APPLICABLE` are valid only when that is the reviewed conclusion. Do not substitute an owner assertion for an executed document or guess at an unresolved scope.

## Gate checks

Run against the private manifest path:

```bash
python freight/rights_evidence.py --manifest /secure/path/RIGHTS_EVIDENCE_MANIFEST.json --stage pilot --expect CLEAR
python freight/rights_evidence.py --manifest /secure/path/RIGHTS_EVIDENCE_MANIFEST.json --stage annual --expect CLEAR
```

Pilot clearance requires attached, verified evidence and confirmed commercial use for every separately permitted runtime component. Annual/acquirer clearance additionally resolves hosted-SaaS and change-of-control scope and fails when a required scope is confirmed denied.

## Evidence that does not clear the gate

- an account screenshot without the executed terms;
- a statement that the owner has rights;
- a purchase receipt that does not identify the licensed scope;
- a public repository or source archive;
- an unverified diligence-room link;
- a hash that was calculated from different bytes;
- a permission covering a different component or revision.

Until the private manifest passes against the executed evidence, the repository correctly remains blocked for customer-data pilot launch even though synthetic demonstrations and static marketing preparation can continue.
