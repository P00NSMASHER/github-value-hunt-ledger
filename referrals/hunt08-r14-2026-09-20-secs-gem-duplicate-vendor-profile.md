# Hunt 08 referral — S2F15 duplicate ECID vendor-profile evidence

Date: 2026-09-20
Lane: Node 08 — Protocol Moats / CAP-014 / EXP-008
Status: evidence delta; duplicate-specific cross-engine runtime remains NOT_RUN

## Starting hypothesis
The exact duplicate-ECID S2F15 fixture is valuable only if the predicted implementation disagreement can be tied to an independent operational profile. A real equipment-vendor manual may show whether duplicate ECIDs are treated as a legal ordered list or as malformed input, while source/history inspection can establish that the two pinned implementations genuinely differ.

## Discovery / verification modes
1. SOURCE TRACE — inspect the exact pinned S2F15 parser/router path in `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`.
2. INDEPENDENT IMPLEMENTATION TRACE — inspect the exact pinned S2F15 schema/handler in `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`.
3. HISTORY TRACE — inspect file history to determine whether the duplicate policy is a recent regression or a stable design choice.
4. EXTERNAL PROFILE / AUTHORITY SEARCH — search public equipment-vendor SECS/GEM manuals for duplicate-ECID S2F15 behavior. Treat vendor behavior as implementation evidence, not SEMI standards authority.
5. RED-TEAM/VERIFIER — try to disprove the conclusion by checking whether Dreamine itself claims standards conformance or whether the external manual merely describes malformed-input behavior rather than duplicate semantics.

## Source evidence
### Dreamine.Gem — duplicate rejected before service mutation
Pinned revision: `82604d6f03c1e95e0558de5c757989b27cd4a3d6`

`Protocol/E30/E30WireCodec.cs` decodes S2F15 into an immutable list and explicitly rejects repeated ECIDs:
- `ReadEquipmentConstantUpdates(...)`
- `if (result.Select(...Key).Distinct().Count() != result.Length) throw Malformed("S2F15 contains duplicate ECID values")`

`Protocol/E30/E30EquipmentRouter.cs` catches `E30WireFormatException` in `InvokeHandlerAsync(...)` and sends `StreamNine(primary, 7)`. Therefore the duplicate never reaches `GemEquipmentConstantService.SetValues(...)` and no S2F16 is generated from the normal handler path.

The same router maps ordinary S2F15 service outcomes to S2F16 only after successful decode. The manifest explicitly labels the implementation an `E30-0611 derived subset profile v1`, says it is **not** a standards-conformance verdict, and marks S2F13/14 + S2F15/16 as `ImplementedUnverified` with external verification outstanding.

History: `E30WireCodec.cs` appears in the initial 2026-08-12 commit `422cefcd047f98044e302859abee3d98c803202c` (`Add E30 derived profile and TCP demo`). No later path-specific commit was returned, so duplicate rejection is a stable design decision in the pinned lineage rather than a recently introduced patch.

### secsgem — duplicate list accepted and applied in order
Pinned revision: `59a5242d8672dad73367a0acd18088adf461404f`

`secsgem/secs/functions/s02f15.py` defines S2F15 as an ordered list of `<ECID, ECV>` pairs with no uniqueness rule.

`secsgem/gem/equipment_constants_capability.py::_on_s02f15(...)` performs two passes:
1. validate each pair for unknown ECID / min / max;
2. if aggregate `eac == 0`, iterate the same list again and call `_set_ec_value(...)` for every pair.

No duplicate guard exists in the inspected path. Therefore repeated valid ECIDs are source-predicted to be applied sequentially, leaving the final value from the last list entry and returning S2F16 EAC=0.

History inspection shows the handler's recent path history is formatting/doc/access cleanup in 2024, not a duplicate-policy change. The ordered-list behavior is therefore not a one-off recent edit at the pinned revision.

## New external operational evidence
A public mirror of **ITW EAE / Despatch Protocol Manager Pro SECS/GEM Owner's Manual, Revision 2.1.0, May 30 2025, MDLN PMPro, SOFTREV 3.2.3** contains an explicit S2F15 rule:

- if the message is correctly formatted and all ECIDs/ECVs are valid, values are changed and S2F16 EAC=0 is returned;
- if **duplicate valid ECIDs** appear in S2F15, the Equipment Constant is changed to the **last ECV in the message** for that ECID;
- format errors produce S9F7, no Equipment Constant changes, and no S2F16.

The manual's revision history says S2F15 response documentation was corrected in the 2022 revision, and the 2025 manual retains the duplicate-last-value rule.

Public mirror used for this research: `https://manualzz.com/doc/85197703/despatch-protocol-manager-pro-secs-gem-owner-s-manual`.

Important evidence boundary: this is a vendor implementation/compliance profile surfaced through a third-party mirror, **not the SEMI standard text and not a universal conformance authority**. It is nevertheless independent real-equipment-profile evidence that duplicate ECIDs can be intentionally legal and last-value-wins.

## Independent RED-TEAM / VERIFIER verdict
**STRONG EVIDENCE DELTA; RUNTIME DIFFERENTIAL STILL UNVERIFIED.**

The new vendor-profile evidence materially changes interpretation of the source-predicted disagreement:
- secsgem's `EAC=0 + last-value-wins` behavior aligns with at least one current commercial equipment profile;
- Dreamine's duplicate-as-malformed rule is a stricter frozen-derived-profile choice and would likely reject a host transaction that the Despatch profile intentionally accepts;
- because Dreamine explicitly says its E30 subset is not a conformance verdict and external verification is outstanding, this is best treated as an **interoperability defect candidate / profile mismatch**, not proof that Dreamine violates SEMI E30.

A contrary possibility remains: another vendor or a particular customer profile may intentionally forbid duplicate ECIDs. Therefore the paid pre-FAT system must compare against the customer's authoritative equipment/profile contract and should never substitute majority implementation behavior for standards/customer authority.

## Commercial implication
This is stronger than a generic simulator disagreement. It demonstrates why a pre-FAT acceptance service should normalize at least:
- normal S2F16 acceptance/rejection;
- S9F7 structural error;
- original W-bit transaction liveness/T3;
- post-state/readback;
- customer/vendor profile authority.

A buyer-facing report can say: **"this host request is accepted by profile A and source-predicted accepted by secsgem, but rejected as malformed by Dreamine's frozen profile"** without calling either side standards-correct.

## Capability / experiment handoff
- CAPABILITY DELTA: CAP-014 gains external vendor-profile evidence for a concrete edge case, not only cross-library source inference.
- GRAPH EDGE: EXP-008 duplicate-ECID fixture now has a plausible real-world expected-behavior comparator for one equipment family.
- RADAR SIGNAL: RAD-007 strengthens toward customer/profile-specific semantic acceptance rather than generic protocol conformance.
- EXPERIMENT IMPACT: execute the exact duplicate fixture against both pinned packages when runtime materialization is available; preserve `reply class + SHEAD/System Bytes + T3 + post-state`. Compare result to the customer's/vendor's authoritative profile, with Despatch PMPro as one independent operational comparator.
- COMMERCIAL IMPACT: pre-FAT product should sell profile-specific incompatibility evidence, not blanket SEMI certification.
- NEGATIVE KNOWLEDGE: do not classify duplicate ECID as syntactically malformed merely because one implementation does; do not infer standards truth from one vendor manual either.

## Next highest-value question
Can the exact duplicate-ECID S2F15 W-bit fixture be executed against both pinned packages and, if the predicted divergence appears, does the target customer's authoritative profile specify duplicate semantics explicitly enough to classify the mismatch without consulting restricted standards text?
