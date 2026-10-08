# RETALLY Phase 2: Offline Unified Laboratory Finance Repair

**Research scope only:** This release patches the original fictional/SQLite laboratory.
It does not modify the production RecoveryOS application or certify real money.

## Install

Unzip the independent original archive and apply `PHASE2_UNIFIED_LAB.patch` at
`RecoveryOS_Unified_Development_Lab/` with `git apply`, or run the self-contained
`RETALLY_Phase2_UnifiedLab_Repaired.zip` fixture. Do not combine either with
real customer or carrier records. No secrets or paid external providers are used.

To verify an extracted patched lab:

```
FREIGHT_ORIGINAL_SYNTHETIC_SOURCE_ZIP=/tmp/nonexistent.zip python -W error::ResourceWarning -m unittest -q tests.test_unified tests.test_semantic_repair tests.test_phase2_financial
python phase2_audit_probe.py .
```

`tests.test_unified` includes legacy synthetic scenarios; the patched suite adds
20 targeted financial/authorization probes.

## Repair coverage

* Removed derived expected tariff figures and synthetic truth clues from the
  public invoice surface. The weak model no longer accesses expected charges;
  it remains uncalibrated and should not automatically submit claims.
* Introduced independently injected **synthetic test** contract HMAC keys,
  versioned historical fee percentages and signed terms, scoped to tenant and
  source customer. A free-form rate cannot invoice a fee. This is NOT buyer
  electronic-signature verification; production needs legal/authentication review.
* Corrected delayed partial credits, partial reconciliation by receipt ID,
  reversal after consent revocation, earned-but-uncollected fee reversals,
  refund liabilities, authorized write-offs and reference-specific reversals.
* Corrected collision-prone display labels; protected duplicate economic issue
  IDs and detected cross-tenant source reuse in the isolated test database.
* Updated an independent semantic replayer and synthetic truth QA oracle to
  reconstruct journal money and detect wrongful synthetic ground-truth claims.

## Evidence and limitations

The five previously reproduced weak behaviors were present in the Phase 1
baseline and absent in the isolated Phase 2 code (see `before_five.json` and
`after_five.json`). Phase 2 adds 20 targeted tests while the 68 earlier tests
continue passing. Test counts are engineering evidence, not product certification.

The new source-scoping table is *first-writer-bound*, NOT a buyer-owned identity
registry. A malicious first importer could still forge an identity. Externally
signed source custody, authentic fee-terms authority, bank remittance, tariff
validity, historical archive coverage and hosted service parity remain blocked.
Only simulated settlement data used. Findings registry PR #279 remains unmodified.

The bundled signing key is PUBLIC and has zero live authorization value.
Archive timestamps and client messages are fictional, not observed.
