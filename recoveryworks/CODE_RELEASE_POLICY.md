# RETALLY code integration policy — owner authorized

**Effective October 21, 2026. Scope:** `P00NSMASHER/github-value-hunt-ledger` RecoveryWorks seven-branch application, synthetic OCI backup transport, and their deployment scripts.

The repository owner expressly authorizes code integration **without a required separate human/independent code-review approval** for this scoped source. Previously documented human code-review prerequisites are superseded for this scope. Neither an AI simulation nor a fabricated GitHub reviewer approval is needed or permitted.

## Required automated merge conditions

1. Verify the exact proposed commit, its parent/source lineage, and diff. No unrelated changes, credentials or customer originals.
2. All required exact-head GitHub CI, security checks and repository release-policy checks must complete successfully. A pending, failing or cancelled check is not a pass.
3. Respect existing GitHub protected-branch rules and merge permissions. Do **not** force-push, dismiss checks, spoof reviews, disable verification jobs or bypass GitHub protections to achieve a merge.
4. Stage/merge dependent changes in correct order, rechecking the current target SHA. Keep changes reversible and retain test evidence.

## Separate operational and customer boundaries — NOT waived

- A code merge is **not** an approval to create billed infrastructure, turn on a VM service, publish Cloudflare DNS/tunnels, create Access Allow policies, or process customer data.
- Keep `production_release=HOLD` and simulation-only runtime restrictions until distinct live host, authentication, privacy, encrypted-backup custody/retention, and customer authorization evidence is verified.
- Case source reviews, customer audit consent, rate/contract truth, independent external bank/carrier settlement validation, customer claim authorization, and domain-specific reviewer identities remain unchanged. They are financial/operational proof, **not code review**.
- Preserve the historical OCI synthetic orphan, the immutable quarantine/attempt/acceptance receipts, and no new spending.

This owner authorization removes the **reviewer prerequisite**, not automated code validation or external evidence requirements. The owner may revise this policy in a subsequent audited source change.
