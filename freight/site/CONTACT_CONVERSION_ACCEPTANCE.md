# RETALLY — truthful email-draft conversion acceptance (2026-10-09)

## Confirmed underlying defects

1. **False conversion signal:** The existing `prepareEmailDraft()` path emitted
   `freight_audit_form_completed` even though only a `mailto:` draft was
   prepared. A visitor who closes the email client without sending could
   therefore be incorrectly counted as a completed inquiry.
2. **No correction route:** The ready screen hid the filled form and offered
   only reopen/copy actions. A visitor discovering a typo after preparing
   the email had to reload and re-enter their information.

## Repair

The manual path now emits **only**
`freight_audit_request_prepared` with `deliveryConfirmed:false`. The
`freight_audit_form_completed` event remains reserved for the separate
confirmed durable `/api/inquiry` receipt; this does **not** assert mailbox
delivery. The screen still states “Email prepared — not sent.”

Added an **Edit request details** control that preserves the customer's
entered fields, hides the stale draft, disables its previous mailto URL and
returns to the form. A second preparation creates a new reference and body
from the edited values. After a real durable online receipt, the Edit button
is hidden along with all email-only actions.

## Regression evidence and boundary

- Source unit tests forbid `auditFormCompleted` inside the draft function
  and require the existing durable-receipt assertion.
- Real Chromium mobile and desktop visual acceptance now intercepts the
  `freight:analytics` events, reproduces invalid → prepare → edit → reprepare,
  verifies the new mailto details and confirms **zero completed events**.
- No test sends email, submits an online inquiry, or stores customer data.
- The Cloudflare feature flags remain disabled pending real provider-to-Zoho
  delivery verification. A Gmail SENT message is not receiving-inbox proof.

Public-facing copy, rate handling, brand masters and business identity are
unchanged. A released draft is **not** verified delivered contact.
