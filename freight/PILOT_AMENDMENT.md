# Freight Recovery — Pilot Amendment Control

Updated: 2026-09-20

The Pilot Charter freezes the sales-to-delivery handoff. The Pilot Amendment
Control prevents that freeze from being bypassed by informal edits.

## Core rule

**Never edit an accepted Charter in place.**

A requested change creates an immutable amendment record tied to the original
`charter_hash`. Accepted changes require a replacement Charter before the new
scope can operate.

## Change classes

### Scope/date/carrier/mode
Requires:
- readiness revalidation;
- launch revalidation;
- a new Activation Packet;
- a replacement Charter and fresh acknowledgments.

### Fixed fee
- within the existing published price band: replacement Charter + acknowledgment;
- outside the existing price band: new Activation Packet/published commercial handoff + replacement Charter.

### Operating-role change
Requires a replacement Charter and re-acknowledgment, but does not by itself
force readiness or launch revalidation.

## States

### PENDING_ACKNOWLEDGMENT
The requested change has not been accepted by both sides.

### ACCEPTED_REPLACEMENT_REQUIRED
Both sides accept the requested change. The changed-scope kickoff is suspended
until a replacement Charter is validated.

### SUPERSEDED_BY_REPLACEMENT
A replacement Charter has been validated against the amendment. Its own
`customer_data_authorized` state controls whether kickoff can proceed.

## Authorization boundary

An amendment never authorizes carrier/vendor contact, disputes, or money-moving
action. `external_action_authorized` remains false; separate buyer approval is
always required.

Buyer/business-unit changes are not amendments. They require a new engagement.