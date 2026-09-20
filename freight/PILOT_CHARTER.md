# Freight Recovery — Pilot Charter

Updated: 2026-09-20

The Pilot Charter is the machine-checkable scope-freeze and acknowledgment layer
between buyer activation and delivery.

It binds the exact Pilot Activation Packet hash to:

- engagement ID;
- buyer/business-unit scope;
- population selection rule;
- source date range;
- carrier and mode scope;
- fixed fee within the published activation-packet price band;
- buyer truth-owner role;
- buyer action-approver role;
- Freight engagement-owner role;
- explicit buyer/Freight acknowledgments.

## States

### PENDING_ACKNOWLEDGMENT
One or more required operating acknowledgments are still false.

### PRELAUNCH_ACCEPTED
Both sides acknowledge the operating scope, but the authoritative Pilot Launch
Gate is still BLOCKED or CONDITIONAL. Customer data remains unauthorized.

### KICKOFF_AUTHORIZED
All acknowledgments are true **and** the Activation Packet says the machine
launch status is READY.

Only this state sets `customer_data_authorized=true`.

## Critical boundary

The charter never authorizes carrier/vendor contact, disputes, payment changes,
or other money-moving action.

`external_action_authorized` is always false and the standing policy remains:

> SEPARATE_BUYER_APPROVAL_REQUIRED

## Integrity

Before building the charter, the product recomputes the Activation Packet hash.
A modified offer, price band, launch route, data request, responsibility, or
commercial invariant therefore cannot be silently accepted downstream.

The charter receives its own deterministic SHA-256 hash after scope freeze.

## What this is not

The charter is an operational acknowledgment record. It is not an e-signature
platform, legal advice, or a substitute for the governing commercial agreement.

## Change control after Charter freeze

An accepted Charter is immutable.

Any later change to scope, dates, carriers/modes, fee or named operating roles
must go through `freight/pilot_amendment.py`.

The amendment record never edits the original Charter. Material scope changes
require fresh readiness/launch validation and a new Activation Packet before a
replacement Charter can supersede the old scope. Role-only changes still require
a replacement Charter and re-acknowledgment.

Carrier/vendor contact and money-moving action remain separately buyer-approved.
