# Freight Recovery — Engagement State Resolver

Updated: 2026-09-20

Charters and Amendments are immutable historical artifacts. The Engagement State
Resolver answers one downstream operating question:

> Which Charter is operative now, and may customer-data work proceed?

## Why this exists

Once an engagement can have replacement Charters and Amendments, downstream
workers must not select the "newest-looking" JSON file or infer authorization
from filenames.

`freight/engagement_state.py` walks the immutable Charter/Amendment chain and
returns a deterministic resolution hash.

## States

- `PRELAUNCH` — operative Charter does not authorize customer data.
- `ACTIVE` — operative Charter is KICKOFF_AUTHORIZED.
- `PRELAUNCH_WITH_PENDING_AMENDMENT` — an unaccepted change request exists;
  current prelaunch Charter remains operative.
- `ACTIVE_WITH_PENDING_AMENDMENT` — an unaccepted change request exists;
  current authorized Charter remains operative.
- `SUSPENDED_PENDING_REPLACEMENT` — an amendment was accepted but no validated
  replacement Charter has superseded it. Customer-data processing stops.

## Fail-closed rules

The resolver rejects:
- tampered Charter or Amendment hashes;
- duplicate hashes;
- multiple Amendments against the same base Charter;
- dangling replacement Charter hashes;
- engagement/buyer/business-unit mismatches;
- replacement cycles;
- any artifact that claims external-action authorization.

## Downstream rule

Audit processing, report generation and settlement processing should require a
current resolver result with their corresponding `*_allowed=true` flag.

Carrier/vendor contact, disputes and money-moving action remain separately
buyer-approved and are always `external_action_authorized=false` here.