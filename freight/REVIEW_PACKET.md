# Reviewer Work Packet

The reviewer work packet is the human-readable evidence layer between the deterministic review queue and a proof-bound human decision.

For every non-clear queue item it preserves:

- queue position and priority class;
- invoice, shipment and charge identifiers;
- billed amount, supported expected amount and supported variance;
- the exact normalized charge source hash and charge proof hash;
- every matched rule hash, authority-document ID and original document source hash;
- whether each matched rule has been verified as controlling authority;
- the generated finding ID/proof when one exists;
- the Finding Factory derivation hash and queue-item hash;
- a deterministic reviewer action hint.

Action hints are descriptive workflow directions such as reviewing a validated finding, verifying controlling authority, adding a missing applicable rule, or resolving ambiguous rules. They do not make the human decision.

The packet deliberately calls money a **variance**, not a saving. Realized savings/recovery remain downstream settlement concepts.

The packet contains customer-derived audit evidence and belongs only in the approved customer-processing environment. It must not be copied into Hunter or a public website.
