# Freight Recovery 16.x / RecoveryWorks money-integrity maintenance

**Change type:** internal deterministic parser repair, not a customer-facing recovery claim or new payable service.

A vendored freight-audit parser used binary float rounding and could misstate half-cent invoice amounts. It now parses bounded decimal dollar tokens, uses ROUND_HALF_UP, and rejects malformed/oversized/nonfinite tokens. Existing legacy callers intentionally receive zero for invalid input; that zero **must never be treated as verified invoice/settlement evidence**, and the separate validated original-document, rate, shipment, payment, incumbent and reviewer gates remain mandatory.

Targeted tests include 1.005, -1.005, 2.675, parentheses credits, thousands separators, 1000 deterministic integer-cent roundtrips, malicious/exponent tokens and >53-bit integer-cent limits. Full protected main PR checks and Windows encrypted-backup tests must pass before merge.

This is a patch to a dependency-adapter helper, not a new Freight Recovery 17.0 release or an independent validation of customer billing accuracy. The v16.0 public site and RecoveryOS 4.1 Floot application remain on their own distinct deployment lines.
