# Fifteen Scheduled Hunter Roles

This layer gives the existing 14 research workers plus Hunt 15 / MASTER Integrator a recurring public-GitHub scouting feed. It is subordinate to intelligence/WORKER_RUNBOOK.md, verifier gates and the canonical ledgers.

## Flow

1. HUNTER-01 through HUNTER-14 run bounded thematic public-repository searches from automation/hunter_schedule.json.
2. The scout records public metadata, exact default-branch head revision, published SPDX metadata when exposed by GitHub, root engineering signals, the discovery query and a non-authoritative triage score.
3. It suppresses candidates already represented by the same repository + exact revision in durable ledgers.
4. Explicit offensive-payload descriptors such as credential stealers, ransomware builders, exploit kits, phishing kits and botnet builders are sent to metadata-only RISK_REVIEW_ONLY; code is not inspected by this scout.
5. Each worker owns one queue snapshot under intelligence/scout_queue/HUNTER-XX.json.
6. HUNTER-15 merges those snapshots into automation/SCOUT_DIGEST.md, deduplicated by repository + exact revision.

The queue and digest are **pre-verification scheduling evidence only**. They do not establish A-F score, correctness, commercial value, safety, license sufficiency, verifier independence or MASTER eligibility.

## Rights/provenance

The scout preserves actual published license/provenance metadata and follows the ledger's standing rights posture for repository-owned public code/content. That posture does not automatically extend to independently governed datasets, model weights, standards/specifications, trademarks, patents, bundled media/assets, APIs/services, customer data, private data or accidentally exposed secrets.

## Scheduling

The companion GitHub Actions workflow has fifteen recurring roles: fourteen staggered research scouts and one integrator pass. Manual dispatch supports a single worker, all research workers, or integration.

## Triage

Automated triage rewards signs that a repository is more than a README shell: source/test directories, schemas/migrations, CI/deployment files, substantive size, recency and community evidence. Obscure repositories remain intentionally searchable; low stars do not exclude a candidate.

## Authoritative next step

Promising candidates must still enter the existing worker path: preflight durable memory, acquire a valid assignment where applicable, inspect implementation/tests/schemas/deployments beyond README where practical, record exact-revision evidence, respect STOP/safety gates, submit immutable telemetry, then pass verifier/integrator handling.
