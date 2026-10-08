# RETALLY Mission 13 | Read-only inquiry operations

**DRAFT, review-only. No production activation.** This capability reads non-sensitive *aggregate counts* from the existing Cloudflare D1 inquiry database. It is not a CRM, secure customer-document intake, verified email delivery, or operator-case tracking system.

## Confirmed risk

The current main-branch file functions/api/inquiry.js contains this unconditional cleanup:

    DELETE FROM inquiries WHERE accepted_at < ?

It does not check notification_status, human response, or an active retention/legal hold. A synthetic SQLite counterexample demonstrates that a 91-day-old pending request disappears when an ordinary later submission runs this cleanup. A retention deadline does not excuse deleting a still-unresolved inquiry without documented disposition. The read-only code on this branch deliberately does not modify the conflicting active PR #307 or authorize production changes.

## Use

Requires Node 22+ with no npm packages. For dry-run review, requiring no credentials or network:

    node freight/inquiry_ops/reconcile.mjs --dry-run --as-of=2026-10-08T16:00:00Z

For an approved operator to execute fixed read-only D1 queries, provision the following environment variables using an approved credential manager; do not paste their values into chat or GitHub:

    CLOUDFLARE_ACCOUNT_ID
    CLOUDFLARE_D1_DATABASE_ID
    CLOUDFLARE_API_TOKEN

Then run:

    node freight/inquiry_ops/reconcile.mjs --live

The tool uses only three fixed SQL SELECT statements and emits non-identifying aggregate counts, severity codes, timestamps and operator instructions. It cannot retrieve names, emails, invoice content, private notes, credentials, or raw IP addresses. It never edits D1, sends email, triggers carrier activity, or schedules anything. However, external credentials could independently have broader permissions; scope credentials appropriately.

Any failed API request, missing query result, malformed count, unknown state or inconsistent total fails closed rather than reporting zero leads.

## Status semantics

- pending: A D1 receipt exists, but notification provider acceptance is not confirmed.
- provider_accepted: Cloudflare acknowledged the intended recipient as queued or delivered. This is NOT proof of arrival in Zoho or human follow-up.
- delivery_verified: A delivery-verification state exists, but does NOT independently prove human follow-up, authorization or closure.

The existing schema does not provide an independently verifiable named operator acknowledgment, handled-at timestamp, legal-hold disposition, or final closure record. Without those controls, zero-lost-leads certification is unsupported.

## Operational alert thresholds

- P0: pending inquiry older than one hour, provider-accepted but no inbox proof older than one day, retention-expired unresolved cases, and missing human-handling assurance.
- P1: any pending/provider-only request, or old delivered requests requiring individualized review.
- P2: expired rate-limit buckets that need an authorized cleanup.

These are proposed internal targets, not customer service-level commitments.

## Human procedures

1. Assign an inquiry owner and backup reviewer and document a real review cadence. No automation is established by this PR.
2. Verify actual Zoho receipt with non-sensitive controlled messages, not Gmail Sent or provider HTTP 200.
3. Run read-only reconciliation. If it fails, classify status UNKNOWN and escalate.
4. Review each pending reference in authorized restricted D1 tools; confirm mailbox delivery, without writing personal data to terminal or CI logs.
5. Document actual human handling separately. This requires an approved workflow because the existing D1 schema lacks a handled or legal-hold state.
6. Before deletion, review case-level closure, retention policy, legal holds and evidence of notice/actions. This tool cannot delete.
7. Only then consider a separately approved safe deletion mechanism and verified 90-day retention process.
8. Preserve the public email-draft fallback until a real full-path browser-to-Zoho-to-operator proof is completed.

## Acceptance checks

    node --check freight/inquiry_ops/reconcile.mjs
    node --test freight/inquiry_ops/test_reconcile.mjs
    node freight/inquiry_ops/reconcile.mjs --dry-run --as-of=2026-10-08T16:00:00Z

No feature flags, scheduled tasks, production deploys, customer emails, existing D1 records or financial operations are changed. This code does not close legal/contractual customer-data intake gates. **Production direct-submit verdict: NO-GO.**
