# Golden Goose #028 — restore-proof commercial falsifier (2026-10-29)

**Provenance:** Unclaimed independent research; no hunter identity/lease, integrator action, deployment or protected-main change. Starting ledger: [#863](https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863). Previous #027 showed a manual hydrovac audit could have a negative hypothetical margin, so this run challenged a *different* existing integrator leader: **Recovery Proof SLA** ([OPPORTUNITIES.md](../../../OPPORTUNITIES.md), 28/30), without reprioritizing it.

## Evidence and competition (source pages, not independently verified purchases)

- [NIST SP 800-34 Rev 1](https://www.nist.gov/publications/contingency-planning-guide-federal-information-systems-including-updates-through), 2010: federal recovery-planning/testing context, **not** a purchasing mandate for private SMBs.
- [AWS Backup restore testing](https://aws.amazon.com/about-aws/whats-new/2023/11/aws-backup-restore-testing/) launched November 27, 2023: periodic restoration and timing; [AWS pricing](https://aws.amazon.com/backup/pricing/) is usage-based, *not free*.
- [Veeam SureBackup](https://helpcenter.veeam.com/docs/vbr/userguide/surebackup_job_hv.html), guide updated April 20, 2026: virtual-lab VM/application recovery verification, integrity scans and scheduling.
- [Salvage](https://salvage.sh/pricing) advertises a free restore-test CLI and hosted attestation at **$29/month Team**.
- [Dokaz](https://dokaz.net/pricing) advertises PostgreSQL daily restore verification with signed reports at **$100/month Starter**.
- [SafetyOnCloud](https://www.safetyoncloud.com/plans.html) lists **$199** optional one-time restore tests, separately **$149** formal evidence reports.
- [NorthFirn](https://northfirn.com/services/pricing/) lists scoped restore tests **starting at $950**, a list starting price rather than realized transaction median.
- [Valen Systems](https://www.valen-systems.com/offers/backup-recovery-runbook) lists a **$495** recovery runbook and checklist but explicitly **no actual restore**.

**Sample:** 7 nonrandom first-party vendor/documentation entries, frozen in [source-linked JSON](restore_competition_2026-10-29.json). A competitor's list price, feature description, or claimed auditor acceptance is **not** independent proof of customer purchases, feature effectiveness, sector demand, or money earned by us. Monthly SaaS, one-time service, starting fee and usage-based charges are **not comparable prices**.

## Adversarial economics

**Hypothetical** one-path independent evidence audit: $199 fee, $20 overhead, $45/hour review cost.

| Assumed review time | Modeled labor | Contribution before acquisition, liability, taxes and infrastructure |
|---|---:|---:|
| 2h | $90 | +$89 |
| 3h | $135 | +$44 |
| 4h | $180 | **−$1** |
| 5h | $225 | **−$46** |

Break-even time **3.9778h**. At $199 hypothetical sale price, one actual sale would clear $100 *gross*; six would clear $1,000 *gross* ($1,194). There are **zero actual sales**. No finding, backup value, insurance premium, advertised vendor price, historical procurement, or litigation settlement constitutes an owner collectible.

**False advantages rejected:** (1) claim that restore tests are absent in incumbent stacks: AWS/Veeam do them; (2) claim that hashing/signed PDFs are unique: Salvage/Dokaz advertise attestation; (3) claim a runbook proves recovery: Valen explicitly excludes restore execution; (4) claim that passing simulated arithmetic implies a paying buyer. A self-reported restoration status, a hash with no authenticated issuer, and a backup-success badge do not prove actual application recoverability.

## Reproducible safe build

- [Competitive snapshot](restore_competition_2026-10-29.json), 7 offers with type-specific price bases and no fabricated buyer/owner earnings.
- [Strict zero-dependency unit-economics screen](restore_market_gate.py), explicit Decimal math, fixed no-revenue invariants.
- [24 adversarial unit tests](test_restore_market_gate.py), locally executed in standard Python: **24/24 PASS**, including faked paid buyers, nonexistent owner revenue, bogus free AWS price, NaN/Infinity, duplicate sellers, malformed price evidence and negative labor.

Run from this directory: python -m unittest -v test_restore_market_gate && python restore_market_gate.py. Tests prove **internal schema/assumption handling only**, not third-party implementation claims, real restoration, customer WTP, or independent production acceptance. GitHub CI and readback require separate confirmation.

**Disposition:** Commodity restore-test/signed-evidence SaaS **NO-GO** due direct feature competition. A narrow **independent cross-provider restore acceptance service remains WATCH**, not a new priority or validated business. No verified paid demand, willingness to pay, real backup authorization, recovery tests, independent incumbent comparisons or known labor costs.

**Cheapest next experiment:** Freeze 20 synthetic restore-evidence cases including successful backups with failed actual restores, missing keys, restored files with failing application probes, underreported RTO, fabricated observer signatures and genuinely successful controls. Compare these fail-closed requirements to the *documented* AWS/Veeam/Salvage capabilities and establish whether any incremental independent control survives. Without permissioned buyer evidence and observed handling cost, reject paid commercialization. No outreach, funds, accounts, files, software subscriptions, live recoveries, claim filings, customer enrollment, trades, new issue, protected main merge, or Work credits.

**Exact financial status:** verified owner revenue **$0**; verified collectible **$0**; paying customers **0**; authorized real backups **0**. Code/test checks **local only**.
