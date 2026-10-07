# Freight Recovery Outreach Safety

Effective: 2026-10-07

## Release boundary

The repository has outreach templates and an aggregate growth planner, but no Gmail delivery adapter was found in the inspected implementation. The new gate and reservation CLI do not send mail. Direct Gmail/connector sends can bypass them. Do not resume outbound until the actual sender calls the gate and atomically persists its reservation before calling the transport.

The growth planner defaults to PREP_OUTREACH_SAFETY (0 sends) when outreach_preflight_ready is absent or false. That flag reports readiness; it is not per-message authorization. A ready planner still requires the gate on every send.

## Private record

Store company, account ID, normalized recipient, all sent dates/message IDs, response status, suppress/hold reason, route evidence, ICP qualification and current mailbox-check time in a private ledger outside the checkout. Never put prospect addresses, messages, or suppression lists in GitHub or Actions artifacts/logs. Use one account ID for all company recipient aliases. Treat Gmail DRAFT records as drafts, never as evidence of delivery. SENT is evidence of sending, not receipt by the buyer.

Permanent suppression: opt-out, negative response, hard bounce, no-fit or sequence closure. Temporary holds: unresolved qualification, audit remediation, repeated contact, active replies, or uncertain delivery. A hold is not a customer opt-out. An editorial calendar deferral is not a sales lead or an opt-out.

## Mandatory sequence

1. Reconcile all company/recipient Sent history and newer replies, including Spam/Trash and separate threads. Refresh mailbox_checked_at only after this review. Gate freshness is ten minutes.
2. Resolve account aliases and record opt-outs immediately. Do not let a new campaign or another company mailbox reset contact history.
3. Qualify buyers under ICP_V1.md: U.S. distributors/multi-site shippers, target scale, material LTL/parcel, auditable history of at least six months, verified finance owner and cited evidence. Score 65 or higher is required. Unknown inputs stay unqualified. Logistics providers from legacy lists require fresh review; do not assume they are primary buyers. Referral/editorial/directory channels require their own explicit approval and share the same suppression/history checks.
4. Select FIRST_LOOK or SECOND_LOOK. Mature controls require SECOND_LOOK. Render all variables and one evidenced personalization sentence.
5. Include sender identity, the approved physical postal address, and the explicit opt-out in every newly authored MIME alternative. The established business address is in THREE_TOUCH_OUTBOUND_SEQUENCE.md; confirm it is valid and authorized before setting postal_approved=true in the private sender configuration.
6. Run the CLI against private JSON inputs and a unique reservation ID:

```sh
node freight/outreach_preflight.mjs /private/message.json /private/ledger.json /private/sender.json unique-reservation-id
```

7. The CLI takes an exclusive lock, rechecks the ledger and writes RESERVED atomically. It outputs no recipient/body and sends nothing. Only an integrated sender may proceed after this durable reservation. A crash/timeout or uncertain transport result stays RESERVED/UNKNOWN; reconcile Sent before retrying. Never simply delete a lock or reservation and resend.
8. After a confirmed send, record SENT with its actual message ID and timestamp privately. After a definite unsent cancellation, record CANCELLED. DRAFT does not increment touches. Stop cold sequences on substantive reply/referral. Follow-ups require a matching prior message, Day 5/Day 12 timing and at least four days between sends; maximum three touches. Same-day routing responses belong to a manually reviewed active conversation, not the cold sequence.

## Input contract

sender: identity, postal_approved boolean, postal_lines array (street/box plus city/state/ZIP).

ledger: schema_version=1, audit_hold=false, mailbox_checked_at ISO timestamp, contacts array and events array. Each contact: recipient_key, account_id, route_verified, suppressed, hold, status. BUYER qualification: icp_version=ICP_V1, approved, integer score, us_distributor_or_multisite_shipper, target_scale_band, meaningful_ltl_or_parcel, numeric history_months, finance_owner_verified, disqualified=false, mature_controls and evidence URLs. Other channels use channel_approved. Every prior SENT event requires recipient_key, account_id, message_id and sent_at. Open reservations must remain in the same ledger across campaigns and workers.

message: one to address, account_id, subject, channel, touch, text and optional html. BUYER messages also require offer and personalization; follow-ups require reply_to_message_id. CC/BCC and hidden/style/script HTML are blocked. Keep HTML simple. The gate checks renderable content, not whether a claimed address or qualification fact is true; private evidence review supplies that authority.

## Validation

Run `node freight/outreach_guard.test.mjs`, `node freight/outreach_preflight.test.mjs` and `python -m pytest freight/test_free_growth_engine.py`. Fixtures are synthetic. CI runs these checks; no messages are sent. This is a bounded safeguard suite, not a legal compliance certification.
