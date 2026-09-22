# Finding Factory v1

Freight Recovery now has a deterministic boundary between normalized customer evidence and the existing frozen-finding / settlement proof system.

## What it does

The factory accepts:

- one frozen buyer/business-unit population;
- normalized invoice charge lines with source hashes;
- normalized charge rules with effective dates, source hashes and an explicit controlling-authority verification state.

It supports three intentionally narrow pricing forms:

1. **INCLUDED** — expected charge is zero.
2. **FIXED** — expected charge is an exact fixed-cent amount.
3. **PER_UNIT** — integer units multiplied by an exact integer-cent rate.

The engine then returns one of three decisions for each charge:

- **CLEAR** — one verified rule applies and billed amount is not above the calculated amount;
- **VALIDATED** — one verified rule applies and billed amount exceeds the calculated amount;
- **REVIEW** — authority is unverified, missing or ambiguous.

Missing or ambiguous rules never invent an expected dollar amount.

## Evidence binding

Generated finding IDs are content-addressed from the normalized charge evidence, matched rule proof and exact calculation. Verified rule snapshots are also content-addressed and are embedded into the frozen truth manifest.

This means changing the invoice-line source hash, rule parameters, effective dates, verification state or authority document source hash changes downstream proof hashes.

Invoice/shipment membership is matched as a structured two-field identity, not by concatenating the two values with a delimiter. The legacy `invoice|shipment` string remains display-only. This prevents distinct identifier pairs containing `|` from colliding and attaching a charge or finding to the wrong frozen population row.

Within one derivation batch, a normalized charge source hash is one-use evidence. Reusing the exact same source proof under a second internal `charge_id` fails closed instead of increasing discrepancy dollars. Different source hashes remain distinct charge lines; the engine does not merge merely similar charges.

The frozen truth schema also permits **zero findings**, so a clean audit can be represented honestly instead of forcing a discrepancy object.

## What it does not do

This is not OCR, contract interpretation, a tariff parser, carrier dispute automation or a universal rating engine. Upstream extraction and authority selection still require controlled evidence and review. The factory only turns already-normalized, explicitly scoped evidence into deterministic calculations.

Additional pricing models should be added only when a real buyer population demonstrates the need and the calculation can be specified with exact, testable semantics.
