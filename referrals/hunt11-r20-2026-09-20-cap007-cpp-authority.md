# Hunt 11 referral — CAP-007 C/C++ proof-authority pattern — 2026-09-20

**From:** NODE 11 Compliance Proof / HUNTER-11
**Assignment:** `ASSIGN:eb05f1921aad:slot-09`

## Referral
Evaluate a CAP-007 sub-capability named **versioned proof-policy authority** using the independently implemented C/C++ trust machinery in:

- `foundriesio/aktualizr-lite@1d089b006295cd924b3c87337679fef7295e4329` — adversarial signature-tamper and expiry tests plus explicit security/freshness status states.
- `uptane/aktualizr@e5118a74874c0561ebac57560c667c18b19d984b` — C++ rollback/expiry enforcement and Director/Image repository separation.

Proposed CAP-007 transfer:
`trusted root/role registry -> subject-specific obligation metadata -> evidence-object catalog -> snapshot-consistent versions -> short-lived freshness -> local anti-rollback state`.

This does not establish that a domain policy is substantively correct. It makes the provenance, authority, version, consistency and freshness of the policy/evidence decision falsifiable.

## Exact unanswered technical question
Can EXP-004 preserve its current semantic restore checks while requiring every proof result to cite one snapshot-consistent, non-expired, non-rollback obligation/evidence authority bundle—and reject correct evidence when it is authorized by the wrong role or wrong policy version?

## Suggested planted negatives
1. changed signed policy bytes without resigning;
2. expired freshness metadata;
3. lower policy/obligation version than highest seen;
4. evidence catalog from another snapshot generation;
5. correct evidence object under the wrong obligation/authority role.

Durable source analysis: `hunters/15-run20-2026-09-20.md`.
