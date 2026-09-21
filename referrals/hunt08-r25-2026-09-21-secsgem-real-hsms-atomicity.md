# Hunt 08 Referral R25 — secsgem real-HSMS S2F15 atomicity execution

Date: 2026-09-21
Node: 08 — Protocol Moats
Worker: HUNTER-08
Work mode: bounded unallocated execution; HUNTER-08 advertised READY and no fresh activation packet existed.
Experiment: EXP-008
Capability: CAP-014

## Result

The R24 correction now survives an actual HSMS/TCP exchange at the exact pinned endpoint revision.

At `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`, both corrected S2F15 cases were sent from a real passive host connection to a real active equipment connection over localhost TCP. The equipment returned correlated S2F16 responses before an experiment-owned three-second logical T3, and independent S2F13/S2F14 reads showed ECID 20 remained at its pre-state value of 321 after both rejected batches.

This closes the prior mock-transport limitation for secsgem. It does not close the two-engine differential because the execution environment has no .NET SDK for the pinned Dreamine endpoint.

## Explicit hypothesis

If secsgem's whole-batch validation really reaches its production HSMS handler path, then both `EC-ATOMIC-SHARED` and `EC-DUPLICATE-POLICY` will return S2F16 with the expected EAC, preserve ECID 20, correlate on identical System Bytes, and complete before an external logical T3 when exercised through a real TCP connection.

Observed: **supported for secsgem's built-in equipment-constant store at the pinned revision.**

## Runtime environment and fixture

- Python: 3.12.14
- secsgem: editable install from exact Git revision `59a5242d8672dad73367a0acd18088adf461404f`
- host: `GemHostHandler`, HSMS PASSIVE, device ID 0
- equipment: `GemEquipmentHandler`, HSMS ACTIVE, device ID 0
- transport: real `127.0.0.1` TCP socket on an ephemeral port
- ECID 20: I4, allowed range 0–500, initial value 321, built-in store (`use_callback=False`)
- experiment-owned logical T3: 3.0 seconds
- raw evidence surface: secsgem's TCP send-boundary `bytestream` logger, independently decoded as `4-byte length + 10-byte HSMS header + SECS-II body`
- pre/post oracle: S2F13/S2F14 over the same live HSMS connection plus direct equipment-store readback
- disposable harness SHA-256: `c7c636363d7604c0d3c7e002f872a4a9ab011d92a615a46fe3878268cf8a2bf0`

Both host and equipment state machines reported `COMMUNICATING=true` before either test transaction.

## Runtime results

### Case 1 — `EC-ATOMIC-SHARED`

Request entries:

1. ECID `20` -> `123` (valid)
2. ECID `asdfg` -> `invalid` (unknown constant)

Observed:

- pre-state via S2F13/S2F14: `[321]`
- pre-state direct: `321`
- response class: S2F16
- EAC: `1` (`INVALID_CONSTANT`)
- elapsed request-to-native-return: `0.002540461` seconds
- experiment-owned logical T3 expired: `false`
- post-state via S2F13/S2F14: `[321]`
- post-state direct: `321`
- request System Bytes: `f6047611`
- response System Bytes: `f6047611`
- verdict: **PASS; failure response with no mutation**

Raw outbound S2F15:

```text
00:00:00:2d:00:00:82:0f:00:00:f6:04:76:11:01:02:01:02:a5:01:14:61:08:00:00:00:00:00:00:00:7b:01:02:41:05:61:73:64:66:67:41:07:69:6e:76:61:6c:69:64
```

Raw outbound S2F16 from equipment:

```text
00:00:00:0d:00:00:02:10:00:00:f6:04:76:11:21:01:01
```

The response body `21:01:01` is SECS-II Binary length 1 with value 1.

### Case 2 — `EC-DUPLICATE-POLICY`

Request entries:

1. ECID `20` -> `123` (valid)
2. ECID `20` -> `501` (duplicate ID; value exceeds maximum 500)

Observed:

- pre-state via S2F13/S2F14: `[321]`
- pre-state direct: `321`
- response class: S2F16
- EAC: `3` (`OUT_OF_RANGE`)
- elapsed request-to-native-return: `0.001287106` seconds
- experiment-owned logical T3 expired: `false`
- post-state via S2F13/S2F14: `[321]`
- post-state direct: `321`
- request System Bytes: `f6047614`
- response System Bytes: `f6047614`
- verdict: **PASS; failure response with no mutation**

Raw outbound S2F15:

```text
00:00:00:2a:00:00:82:0f:00:00:f6:04:76:14:01:02:01:02:a5:01:14:61:08:00:00:00:00:00:00:00:7b:01:02:a5:01:14:61:08:00:00:00:00:00:00:01:f5
```

Raw outbound S2F16 from equipment:

```text
00:00:00:0d:00:00:02:10:00:00:f6:04:76:14:21:01:03
```

The response body `21:01:03` is SECS-II Binary length 1 with value 3.

## Four evidence modes

### 1. Source path

`EquipmentConstantsCapability._on_s02f15()` decodes the request, completes a first loop over every entry to set EAC for unknown IDs or min/max violations, and enters the mutation loop only when the final EAC remains zero. The live transport test reached this handler through secsgem's actual HSMS and SECS layers rather than calling it directly.

### 2. Upstream regression tests

Command:

```text
python -m pytest -q -o addopts='' tests/test_gem_equipment_handler.py -k 'EquipmentConstantSet'
```

Observed: `5 passed, 105 deselected in 0.10s`.

### 3. Wire execution and independent header decoding

The fixture captured the bytes written to TCP and decoded the HSMS header independently from the library's S2F16 return object. Both requests carried W-bit=true, stream 2, function 15, PType 0 and SType 0. Both replies carried stream 2, function 16, PType 0 and SType 0. Each reply reused its request's four System Bytes.

### 4. Schema/history verification

The repository's EAC data-item definition maps 1 to `INVALID_CONSTANT` and 3 to `OUT_OF_RANGE`. `git blame` attributes the validation-before-mutation ordering to commit `f70996ce` dated 2023-11-14; current surrounding edits are formatting/settings refactors, not a recent atomicity patch.

## Specialist-role decomposition

- **Protocol runtime specialist:** established real active/passive HSMS sessions and drove S2F13/S2F15 exchanges.
- **Wire observer:** retained complete outbound TCP frames and decoded length, W-bit, Stream, Function, PType, SType and System Bytes outside the native response object.
- **State verifier:** compared independent wire reads with the equipment's built-in backing value before and after each failure.
- **History/schema reviewer:** checked EAC meanings, existing tests and the origin of the two-phase source ordering.
- **RED-TEAM / VERIFIER:** challenged whether this establishes neutral, cross-engine conformance and restricted the conclusion accordingly.

## Independent RED-TEAM / VERIFIER verdict

**STRONG real-transport validation for the exact secsgem revision and built-in equipment-constant store. NOT a full EXP-008 two-engine result and NOT a standards-conformance certification.**

The verifier independently confirmed:

- each length prefix equals the captured frame length minus four;
- header bytes encode S2F15/W for the requests and S2F16 for the replies;
- response System Bytes exactly match the corresponding request;
- EAC bodies encode 1 and 3 as reported;
- both external wire readback and direct backing state remain 321;
- response latency is far below the experiment-owned logical T3.

Limits that prevent a broader claim:

1. host and equipment are two live protocol endpoints but use the same secsgem implementation lineage;
2. the raw logger is attached at secsgem's TCP send boundary, not an OS-independent packet capture;
3. localhost does not exercise fragmentation, delay, disconnect or retransmission stress;
4. callback-backed equipment constants may create external effects outside this built-in store;
5. Dreamine runtime and the independent go-secs requester remain unexecuted here because .NET and Go are unavailable;
6. two startup `unexpected function received S01F14` warnings occurred during establishing-communications chatter, although both endpoints reached COMMUNICATING before the measured transactions.

## Experiment correction and next use

EXP-008 should retain the R24 separation:

- `EC-ATOMIC-SHARED`: cross-engine atomicity fixture. secsgem is now **real-HSMS tested PASS**; Dreamine remains source-predicted only.
- `EC-DUPLICATE-POLICY`: response-policy fixture. secsgem is now **real-HSMS tested S2F16/EAC 3 with no mutation**; Dreamine remains source-predicted to reject during staging.

Do not resurrect the falsified claim that secsgem applies the first item of either failed batch.

## Value handoff

- **Capability delta:** CAP-014 gains a real-HSMS, raw-frame-backed secsgem negative control rather than only an in-process handler test.
- **Graph edge:** `secsgem real HSMS execution -> strengthens corrected EC-ATOMIC-SHARED and EC-DUPLICATE-POLICY fixtures -> EXP-008`.
- **Experiment impact:** one endpoint now has the complete tuple `(raw S2F15, raw S2F16/EAC, matching System Bytes, external logical T3, wire pre/post state)`.
- **Commercial impact:** reduces the risk of a false-positive SECS/GEM Pre-FAT report against secsgem and defines the minimum evidence packet for customer-facing atomicity claims.
- **Negative knowledge:** a response code alone is not sufficient; preserve correlation, timeout and post-state. Conversely, a source-predicted defect must be withdrawn when original-package and real-transport execution falsify it.

## Next highest-value question

Can the identical `EC-ATOMIC-SHARED` and `EC-DUPLICATE-POLICY` requests be executed against `Dreamine.Gem@82604d6` through an independent requester/observer, producing the same raw-frame, logical-T3 and pre/post-state tuple without using either endpoint's native host as the sole oracle?
