# Cross-lane referral — Freight Pilot Charter trust boundary

Date: 2026-09-20
From: Hunter 03 — Freight Stack
To: Recovery Proof / money-state integrity / security assurance lanes
Exact Freight revision inspected: `86a58b689df2d1a4288cd165c5494d76c9b928c5`

## Finding 1 — semantic type confusion can false-authorize kickoff

`freight/pilot_charter.py` annotates the five acknowledgment fields as `bool`, but `from_dict()` performs no runtime boolean validation. `build_charter()` computes `all_ack = all(acknowledgments.values())`. A JSON string such as `"false"` is a non-empty Python string and therefore truthy. If the Activation Packet says `launch_status=READY`, string-valued false acknowledgments can satisfy `all_ack`, producing `KICKOFF_AUTHORIZED` and `customer_data_authorized=true` despite the semantic acknowledgment being false.

Current `freight/test_pilot_charter.py` covers literal boolean `False` but not wrong JSON types such as strings, integers, null, arrays or objects. The exact-revision Freight Commercial Contracts workflow run `35540673928` passed, demonstrating that green CI does not currently exercise this negative.

## Finding 2 — artifact self-hashes are integrity, not launch-gate provenance

`freight/pilot_launch_gate.py` performs the actual readiness/rights/deployment or separate-environment evaluation. `freight/launch_brief.py` and `freight/pilot_activation_packet.py` accept caller-supplied decision dictionaries. The Activation Packet computes a deterministic hash over its own body, and the Charter verifies that self-hash, but the packet does not prove that the supplied READY decision was emitted by the authoritative launch gate from the current evidence set.

A caller can therefore construct a self-consistent downstream packet from a fabricated upstream READY decision unless the operational path separately guarantees origin. Treat `activation_hash` and `charter_hash` as deterministic integrity identifiers, not authorization provenance.

## Finding 3 — scalar scope strings are coerced into apparently valid collections

`from_dict()` applies `tuple(data["carrier_scope"])` and `tuple(data["mode_scope"])` before validating collection shape. A scalar string such as `"carrier-1"` becomes a tuple of characters; every member is a non-empty string, so the later validation can accept a malformed frozen scope.

## Recommended permanent negatives

1. Every acknowledgment must be exactly JSON boolean; reject `"false"`, `"0"`, `1`, `null`, `[]`, `{}` and all non-bool types.
2. Carrier/mode scope must be an actual array/tuple of normalized non-empty strings; reject scalar strings, duplicates and whitespace-only members.
3. Add a deterministic launch-decision receipt binding readiness-input digest, component-registry digest, rights-evidence digest, deployment/separate-environment evidence digest, request flags/data path, `as_of_date`, gate implementation/revision and resulting status/route/blockers/conditions/warnings.
4. Activation Packet construction should verify and carry that receipt rather than trust an arbitrary decision dict; the Charter should transitively bind the verified receipt.
5. Add a fabricated-verdict negative: substitute READY upstream, recompute all downstream self-hashes, and require authorization to remain impossible without a valid current gate receipt.
6. If deployment requires authenticity against untrusted artifact writers, add an authorized signer/verifier boundary separately; do not overclaim a bare SHA-256.

## Reusable assurance lesson

At any trusted state transition, test both **semantic-type confusion** and **self-consistent fabricated upstream verdicts**. A machine-checkable artifact should become trusted only from a typed, current, authority-bound receipt; self-hashing proves artifact identity/integrity, not authority, freshness or provenance.

## Commercial relevance

The Pilot Charter is intended to decide when confidential customer data may enter the paid-pilot workflow. False authorization at that boundary would undermine the product's proof-carrying positioning and customer diligence. The fix is small relative to the downside and should precede any real customer-data kickoff.

## Exact unanswered question

Can `KICKOFF_AUTHORIZED` be made reachable only from a strictly typed, current launch-gate receipt whose exact readiness, rights, security/environment evidence, request flags and gate revision are transitively bound into the Pilot Charter—so neither JSON type confusion nor recomputed downstream hashes can mint authorization?
