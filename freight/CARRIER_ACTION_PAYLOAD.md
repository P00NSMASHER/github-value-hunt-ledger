# Carrier Action Payload

The Carrier Action Payload is the deterministic preview of the exact carrier-facing content proposed for one proof-bound Carrier Action Proposal.

It is generated from:

- one canonical carrier-action proposal;
- the proof-bound recovery-claim batch behind that proposal;
- one enumerated external action type.

## Payload contents

The payload binds:

- proposal hash;
- recovery-claim batch hash;
- action type;
- target carrier;
- target customer/payee;
- currency;
- exact claim/finding lines and proof references;
- invoice/reference identifiers;
- requested amount;
- deterministic subject;
- deterministic body text.

The payload hash changes when any bound fact or rendered content changes.

## Outbound-text safety

Invoice/reference, carrier/customer identifiers and other externally rendered fields are validated before rendering. Control characters are rejected and external field lengths are bounded. This prevents source CSV identifiers from injecting additional headers/lines into a carrier-facing preview.

## Approval boundary

Generating a payload does **not** authorize or send it.

The high-level authorization handoff:

1. rebuilds and verifies the payload from the proposal and recovery claims;
2. requires the buyer approval's proposal hash to match;
3. requires the buyer approval's action type to match;
4. requires the buyer approval's action-payload hash to equal the canonical payload hash;
5. enforces the approved dollar ceiling;
6. then invokes the existing customer/carrier/currency/finding/payload/recipient-bound External Action Authorization.

The recipient/routing reference remains a separate buyer-approved hash because the destination is deployment/customer specific.

No network request, email, carrier portal submission, money movement, settlement acceptance, account change or automatic execution occurs here.
