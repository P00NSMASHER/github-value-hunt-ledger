# ConstructionRecovery ingestion contract

ConstructionRecovery identifies unpaid portions of reviewed construction
entitlements only when the commercial entitlement, contemporaneous event,
schedule impact, event-to-activity mapping, qualified causation review, and
settlement evidence form one consistent proof chain.

It is an **underpayment** branch:

`potential recovery = reviewed entitlement amount - actual compensation received`

## Important boundary

RecoveryOS calculates CPM impact deterministically. It does **not** infer legal
entitlement or factual causation from schedule math.

A VALIDATED construction finding requires both:

- a reviewed entitlement record with an explicit entitlement reviewer; and
- a verified causation review with an explicit qualified reviewer.

The qualified review may accept fewer delay days than the deterministic CPM
project-duration delta, but it may not claim more delay days than the engine can
reproduce from the supplied schedule versions.

## 1. Entitlement CSV

Default columns:

- `Entitlement_ID`
- `Claimant_ID`
- `Project_ID`
- `Counterparty_ID`
- `Change_ID`
- `Event_ID`
- `Entitled_Amount`
- `Effective_Date`
- `Entitlement_Basis`
- `Entitlement_Reviewer_ID`

`Claimant_ID` must equal the Scan 360 `client_id`. A mixed-client file is
hard rejected by the runner.

When `entitlement_source_verified=true`, every entitlement must contain an
`Entitlement_Reviewer_ID`. The adapter therefore does not treat an
automatically extracted clause or unreviewed change estimate as controlling
commercial authority.

## 2. Event CSV

Default columns:

- `Event_ID`
- `Project_ID`
- `Event_Date`
- `Description`

The event project must match the entitlement project.

Examples of source evidence can include reviewed RFI records, daily reports,
access restrictions, owner directives, approved change records, or another
lawfully supplied contemporaneous project record. The source file is hashed and
each row receives an exact locator.

## 3. Event-to-activity mapping CSV

Default columns:

- `Mapping_ID`
- `Event_ID`
- `Baseline_Activity_ID`
- `Update_Activity_ID`
- `Mapping_Basis`

A construction event must have one unambiguous mapping for the candidate.
Multiple mappings for the same event fail closed as
`AMBIGUOUS_EVENT_ACTIVITY_MAPPING`.

The mapped activity must exist in both referenced schedule versions and must
show positive earliest-finish delay before RecoveryOS will produce a recovery
candidate.

## 4. Versioned schedule JSON

The file can be a list or `{"versions": [...]}`.

Example:

```json
{
  "versions": [
    {
      "version_id": "BASE",
      "project_id": "PRJ-1",
      "data_date": "2026-08-01",
      "label": "Approved baseline",
      "activities": [
        {"activity_id": "A", "name": "Mobilize", "duration_days": 5},
        {"activity_id": "B", "name": "Affected work", "duration_days": 5}
      ],
      "relationships": [
        {
          "predecessor_id": "A",
          "successor_id": "B",
          "relationship_type": "FS",
          "lag_days": 0
        }
      ]
    },
    {
      "version_id": "UPD",
      "project_id": "PRJ-1",
      "data_date": "2026-09-01",
      "label": "September update",
      "activities": [
        {"activity_id": "A", "name": "Mobilize", "duration_days": 5},
        {"activity_id": "B", "name": "Affected work", "duration_days": 8}
      ],
      "relationships": [
        {
          "predecessor_id": "A",
          "successor_id": "B",
          "relationship_type": "FS",
          "lag_days": 0
        }
      ]
    }
  ]
}
```

### Schedule provenance

Every schedule input file is SHA-256 hashed. Each version carries:

- version ID
- project ID
- data date
- source-file hash
- object locator such as `#versions[0]`
- activity and relationship counts
- verification state

The resulting RecoveryFinding also records baseline/update source hashes and
data dates.

### Current CPM support

The first operational adapter intentionally supports deterministic
finish-to-start (**FS**) logic with non-negative integer-day lags.

It computes:

- topological schedule order
- earliest start / finish
- latest start / finish
- total float
- critical activities
- project duration

The adapter fails closed on:

- cycles
- missing relationship activities
- duplicate activity IDs
- unsupported relationship types
- negative/non-integer durations or lags

A direct Primavera XER parser is not required by this branch contract. XER/P6
data can be normalized upstream into these source-bound schedule snapshots while
preserving the original XER hash/version provenance.

## 5. Qualified causation review CSV

Default columns:

- `Review_ID`
- `Entitlement_ID`
- `Event_ID`
- `Baseline_Version_ID`
- `Update_Version_ID`
- `Accepted_Causation`
- `Accepted_Delay_Days`
- `Review_Date`
- `Qualified_Reviewer_ID`

When `causation_source_verified=true`, `Qualified_Reviewer_ID` is mandatory.

The review must:

- reference distinct baseline and update versions;
- reference the same event as the entitlement;
- occur on or after the update schedule data date;
- occur on or after the event date;
- explicitly accept causation;
- accept a positive number of delay days; and
- not accept more delay days than the deterministic CPM project-duration
  increase.

RecoveryOS does not invent or upgrade the review conclusion.

## 6. Settlement CSV

Default columns:

- `Settlement_ID`
- `Entitlement_ID`
- `Amount_Received`
- `Settlement_Date`

Multiple unique settlement rows are summed.

A zero-dollar settlement row is valid evidence that actual compensation received
was zero. If no settlement evidence exists, the adapter returns
`NO_SETTLEMENT_EVIDENCE` rather than assuming zero payment.

Duplicate settlement IDs block the affected entitlement.

## CPM/delay gates

For the schedule versions selected by the causation review:

`CPM project delay = max(update project duration - baseline project duration, 0)`

The mapped activity also must show:

`mapped finish delay = max(update mapped activity EF - baseline mapped activity EF, 0)`

Recovery is not generated when either value is zero.

The finding metadata records:

- baseline/update version IDs, hashes, and data dates
- baseline/update project durations
- CPM project-delay days
- mapped activity IDs
- mapped earliest-finish delay
- baseline/update critical status
- reviewer-accepted delay days
- qualified causation reviewer ID
- entitlement reviewer ID

## Scan 360 configuration

```json
{
  "construction": {
    "entitlements_csv": "entitlements.csv",
    "events_csv": "events.csv",
    "mappings_csv": "event_activity_mappings.csv",
    "schedules_json": "schedule_versions.json",
    "causation_reviews_csv": "causation_reviews.csv",
    "settlements_csv": "settlements.csv",

    "entitlement_source_verified": true,
    "event_source_verified": true,
    "mapping_source_verified": true,
    "schedule_source_verified": true,
    "causation_source_verified": true,
    "settlement_source_verified": true
  }
}
```

Verification flags must be actual booleans. A file hash establishes byte
identity, not substantive verification.

## Explicit failure modes

ConstructionRecovery surfaces exceptions instead of guessing, including:

- `CLAIMANT_SCOPE_MISMATCH`
- `NO_EVENT_EVIDENCE`
- `EVENT_PROJECT_MISMATCH`
- `NO_EVENT_ACTIVITY_MAPPING`
- `AMBIGUOUS_EVENT_ACTIVITY_MAPPING`
- `NO_CAUSATION_REVIEW`
- `CAUSATION_NOT_ACCEPTED`
- `MISSING_SCHEDULE_VERSION`
- `SCHEDULE_PROJECT_MISMATCH`
- `SCHEDULE_VERSION_ORDER_INVALID`
- `CAUSATION_REVIEW_PRECEDES_UPDATE`
- `CPM_CALCULATION_ERROR`
- `MAPPED_ACTIVITY_MISSING`
- `NO_CPM_PROJECT_DELAY`
- `MAPPED_ACTIVITY_NO_DELAY`
- `ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT`
- `NO_SETTLEMENT_EVIDENCE`
- duplicate entitlement/event/schedule/settlement identifiers

## External-action boundary

A VALIDATED finding is still not permission to send a claim, notice, demand,
change order, or payment request.

The common RecoveryWorks controls remain:

1. source ingestion
2. deterministic evidence/math validation
3. Recovery Ledger finding
4. human reviewer approval
5. explicit customer authorization
6. external recovery action
7. outcome/settlement recording
