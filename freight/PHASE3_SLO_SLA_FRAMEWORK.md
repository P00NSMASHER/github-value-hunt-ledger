# RecoveryOS — SLO / SLA Framework

Prepared: 2026-10-07  
Status: **internal service objectives; not a contractual SLA**

## Why this is intentionally not a 99.99% SLA

Step 2 proved deterministic CPU scale to one million records and a 100K audited
database bulk-write path. It did **not** prove concurrent multi-tenant HTTP
availability, failover behavior, or a production uptime history.

Therefore RecoveryOS does not currently offer an evidence-backed 99.99% uptime
commitment.

## Pilot service objectives

These are operational targets for a bounded pilot, not guaranteed service
credits.

| Objective | Internal target | Evidence boundary |
| --- | ---: | --- |
| Hash/provenance integrity | 0 known invalid audit-chain hashes | Database verification exists |
| Population ordering violations | 0 | Machine-checked pilot protocol |
| Unsupported asserted recovered dollars | 0 | Fail-closed financial-state model |
| Deterministic replay failure | 0 | Step 2/3 CI evidence |
| Cross-tenant scope violation | 0 | Negative DB test exists |
| Review response for newly blocked case | <= 1 business day target | Human operational target, not production history |
| Pilot incident acknowledgment | <= 1 business day target | No 24x7 SOC claim |
| Pilot status update | at least weekly | Operational target |
| Provider/payment state reconciliation | next agreed review cycle | Depends on external provider evidence |

## Performance evidence

Current engineering evidence includes:

- ~4.1K records/s conservative single-process six-mode CPU benchmark at 1M;
- deterministic full replay;
- 100K audited database bulk write at ~7.1K rows/s in one synthetic transaction;
- no production HTTP requests/s claim;
- no concurrent tenant throughput claim.

## Availability

Current state: **MEASURE_BEFORE_CONTRACT**

A real SLA requires:

1. continuous production availability measurements;
2. clearly defined availability denominator/exclusions;
3. monitoring/alert ownership;
4. incident-response coverage;
5. tested provider recovery path;
6. measured RPO/RTO;
7. contractual remedies.

## Recovery objectives

RPO/RTO remain **not externally evidenced** until the exact production provider
backup/PITR path is tested.

## Future contractual SLA gate

Do not sign an availability SLA stronger than measured production evidence.
Enterprise procurement loves percentages because percentages fit neatly into
documents. The database, sadly, does not read the document.
