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


## Canonical calculation check

Review-packet construction does not trust a persisted derivation merely because its hashes are internally consistent.

For every queued case, the packet builder independently runs the Finding Factory calculation again from the exact normalized charge and complete supplied rule set. The fresh derivation must equal the derivation bound into the factory batch.

This creates two separate checks:

1. factory verification rejects stale or internally inconsistent derivation/finding/truth objects;
2. packet construction rejects a self-consistent re-hashed derivation whose calculation disagrees with the actual charge and rule evidence.

The reviewer therefore sees amounts that are tied to the same deterministic calculation that can be reproduced from the packet inputs.
