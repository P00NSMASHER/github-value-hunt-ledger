# Hunt 08 Referral R24 — secsgem S2F15 atomicity correction

Date: 2026-09-21
Node: 08 — Protocol Moats
Work mode: unallocated bounded fixture execution; no generated activation packet was available.
Experiment: EXP-008
Capability: CAP-014

## Result

The previously recorded source-predicted divergence for the SECS/GEM equipment-constant probe is **falsified at the pinned secsgem revision**.

At `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`, `_on_s02f15()` uses two distinct loops:

1. validate every requested ECID and every min/max bound, accumulating a non-zero EAC on any failure;
2. call `_set_ec_value()` for the batch only when the final EAC is zero.

The implementation therefore does not apply an earlier valid equipment-constant value before discovering a later unknown or out-of-range entry. `git blame` attributes this two-phase logic to commit `f70996ce` from 2023-11-14, so it is not a recent repair after the pinned revision.

## Runtime evidence

Environment:

- Python `3.12.14`
- editable install of the exact pinned secsgem checkout
- pytest using the repository's real `GemEquipmentHandler`, message encoder/decoder and `MockProtocol`

Baseline command:

```text
python -m pytest -q -o addopts='' tests/test_gem_equipment_handler.py -k 'EquipmentConstantSet'
```

Observed: **5 passed, 105 deselected**.

Two planted tests were then added only to the disposable checkout and executed:

```text
python -m pytest -q -o addopts='' tests/test_gem_equipment_handler.py \
  -k 'AtomicValidThenUnknown or AtomicDuplicateValidThenRangeFailure'
```

Observed: **2 passed, 110 deselected**.

### Probe A — valid first, unknown second

Initial state:

- ECID `20` = `321`
- ECID `EC2` = `sample ec`

Request:

- ECID `20` -> `123`
- ECID `asdfg` -> `invalid`

Observed:

- response EAC = `1`
- ECID `20` remained `321`
- ECID `EC2` remained `sample ec`

### Probe B — duplicate ECID, valid then out of range

Initial state:

- ECID `20` = `321`

Request:

- ECID `20` -> `123`
- ECID `20` -> `501` where maximum is `500`

Observed:

- response EAC = `3`
- ECID `20` remained `321`

## Dreamine comparison boundary

`CodeMaru-Dreamine/Dreamine.Gem@82604d6` was inspected from the exact public revision. `E30WireCodec.EquipmentConstantUpdates()` stages the S2F15 entries and explicitly rejects duplicate ECID values before the equipment router applies the batch. The exact Dreamine runtime was **not run** because the execution environment has no .NET SDK.

This creates an important corpus distinction:

- **Shared atomicity probe:** valid first ECID plus a different later unknown/out-of-range ECID. This can test no-mutation rejection across both engines.
- **Parser-policy probe:** duplicate ECID in one S2F15. Dreamine rejects the malformed duplicate at decode/staging; secsgem returns an EAC based on validation. This is a response-semantics difference, not evidence of partial mutation.

The earlier proposed `duplicate-ECID S2F15 -> Dreamine all-or-nothing versus secsgem partial first-item mutation` discriminator should therefore be withdrawn.

## Claims and evidence state

### LOCALLY_TESTED

- secsgem rejects a valid-first/unknown-second batch without changing the first value.
- secsgem rejects a duplicate valid-first/out-of-range-second batch without changing the value.
- the repository's five existing equipment-constant set tests pass in the same environment.

### SOURCE_INSPECTED

- secsgem's two-phase validation-before-mutation path exists at the pinned revision and dates to 2023.
- Dreamine stages the update list and rejects duplicate ECIDs in its wire codec.

### NOT VERIFIED

- the same probes through a real HSMS socket against both running equipment endpoints;
- Dreamine runtime behavior at the pinned revision;
- raw inbound frame, System Bytes, S2F16/S9 classification and external logical-T3 evidence through `go-secs`;
- behavior under callback-backed secsgem equipment constants where user callbacks themselves may introduce external side effects.

## Red-team verdict

**STRONG falsification of the previously predicted secsgem partial-mutation behavior for built-in equipment constants. NOT a complete end-to-end interoperability result.**

The disposable tests exercise the real S2F15 handler and message encode/decode path but use the repository's in-process mock transport rather than a TCP/HSMS connection. Callback-backed constants may also have external side effects outside the built-in value store and deserve a separate ownership-boundary probe.

## Experiment correction

EXP-008 should replace the old predicted state-divergence claim with two separate hypotheses:

1. **EC-ATOMIC-SHARED:** valid first + different invalid second; both implementations are now source-predicted to reject without mutation. Execute over HSMS to verify.
2. **EC-DUPLICATE-POLICY:** duplicate ECID values; compare Dreamine malformed-request handling against secsgem EAC behavior, while separately asserting no state mutation.

Do not use either implementation as the standards oracle. Preserve wire response and post-state as separate facts.

## Value handoff

- **Capability delta:** CAP-014 gains a corrected negative-control design and avoids building a product claim around a false secsgem defect.
- **Graph edge:** `secsgem runtime falsification -> corrects EXP-008 EC atomicity hypothesis -> preserves Dreamine/secsgem differential corpus`.
- **Experiment impact:** one predicted endpoint state divergence is removed; a narrower response-policy differential remains plausible.
- **Commercial impact:** prevents a false-positive customer report that would incorrectly label secsgem as partially applying failed S2F15 batches.
- **Negative knowledge:** source summaries must preserve control-flow ordering. Seeing `_set_ec_value()` inside the handler is insufficient; the preceding whole-batch validation gate changes the conclusion.

## Next highest-value question

Can the shared valid-first/different-invalid S2F15 probe and the separate duplicate-ECID policy probe be executed through real HSMS sockets against both pinned endpoints, producing `(raw frames, response class/EAC, external logical T3, pre-state, post-state)` without relying on either native requester as the oracle?
