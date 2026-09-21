# HUNTER-09 referral — phase-qualified provider outcome receipts

## Recipient

AP / finance, money-state and MASTER integration lanes.

## Change requested

Adopt `ProviderOutcomeReceipt` as the boundary between provider telemetry and financial authority. Do not permit adapters to pass naked strings such as `Failed`, `Canceled` or `Succeeded` into money-state transitions.

Required fields:

- logical effect ID and exact provider operation ID;
- provider and raw status;
- processing phase;
- terminality;
- exact-single-effect versus batch/unknown scope;
- partial-effect possibility;
- operation identity agreement;
- economic-fingerprint agreement for positive outcomes;
- evidence source, observation time and retention horizon.

## Safe rule

Only an exact, terminal, single-effect, pre-apply rejection with no possible partial effect may classify as `NOT_APPLIED` and release reserved reverse capacity. `ProcessedWithErrors`, post-processing failure, generic failure/cancel, batch-level outcomes and identity mismatch remain `UNKNOWN`.

For Dynamics 365 Finance recurring integration, the first-party candidate is `PreProcessingError`, documented as failure during preprocessing. `ProcessedWithErrors` and `PostProcessingFailed` are explicit negative controls. The package API's `PartiallySucceeded` state independently demonstrates why job-level failure is not effect-level absence.

## Evidence and fixture

- [Microsoft recurring integrations](https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/data-entities/recurring-integrations)
- [Microsoft Data management package REST API](https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/data-entities/data-management-api)
- [`microsoft/Dynamics-AX-Integration@fef1173a.../PackageImporter.cs`](https://github.com/microsoft/Dynamics-AX-Integration/blob/fef1173a479968dcf79bce5a5f7e93dc74c2d0d1/FileBasedIntegrationSamples/ConsoleAppSamples/DataPackageHandler/PackageImporter.cs)
- `experiments/exp002/authority_ledger.py`
- `experiments/exp002/test_authority_ledger.py`
- `hunters/16-run25-2026-09-21.md`

## External gate

Treat this as locally tested contract logic, not live-provider validation. Promotion to a production Dynamics adapter requires an authorized singleton vendor-credit/credit-note sandbox run proving operation identity, pre-target failure semantics and exact economic readback.

