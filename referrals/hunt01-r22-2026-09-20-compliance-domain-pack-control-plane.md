# Cross-lane referral — Hunter 01 Run 22 — Compliance Domain Pack Control Plane

## Why this matters
Two independent jurisdictions now expose complementary reusable primitives:
- `EPIUSECX/cohenix_local_za@060138099efe8fae399f50bef90dd047cec9354c` — effective-dated South African statutory calculations/workflows.
- `agile-technica/erpnext-indonesia-localization@82d5be95f3c89b9c58cdc05e0bbd6d319c72f5ac` — regulator-facing Coretax XML generation plus imported APPROVED/AMENDED/REJECTED state and official tax-invoice identity written back to the ERP.

The combined architecture is stronger than either repository alone:

`official authority/source -> immutable version/effective interval -> deterministic rule execution -> regulator artifact -> external regulator result -> ERP reconciliation -> evidence receipt`

This strengthens CAP-008 and RAD-008 and suggests a reusable **Compliance Domain Pack Control Plane** across country/jurisdiction ERP implementations.

## Important red-team boundary
Indonesia proves regulator round-trip state but does not yet prove explicit effective-dated rule/spec authority. South Africa proves effective-dated statutory calculations but has different regulator-output semantics. Do not promote "country localization" as compliance truth unless both authority and external-result legs are present.

`finbyz/exim@7179d0cbc6580898157b1ed1d0b9ce1f3becb999` is a useful India EXIM workflow donor (Advance Authorisation, RoDTEP/Drawback, BRC, forward contracts) but currently lacks source-identified effective-dated scheme rates and convincing invariant tests; treat it as domain vocabulary, not authority.

## Exact unanswered technical question
Can one jurisdiction implementation bind every generated regulatory artifact and every imported regulator result to an immutable receipt containing `{authority_source, rule_or_spec_version, effective_interval, artifact_hash, source_record_ids}`, then deterministically replay a historical filing after the live rules change?

## Suggested experiment
Create a jurisdiction-neutral corpus with:
1. valid historical rule version A;
2. live rule changes to B;
3. generation under A with pinned authority receipt;
4. external APPROVED, REJECTED and AMENDED outputs;
5. wrong-record identity and missing official identifier;
6. artifact-generation crash after local source mutation;
7. replay after B becomes current, requiring byte/semantic equivalence under A.

Success requires no silent fallback to current rules and no local "submitted/generated" success without durable artifact plus externally evidenced result where applicable.
