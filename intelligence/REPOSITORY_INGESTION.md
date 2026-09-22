# Elite Repository Ingestion

## Purpose

Convert the existing Markdown hunt corpus into a deterministic source-intake queue so high-value repositories do not remain trapped in prose.

This is **not** vendoring, deployment or automatic trust. It is the stage before source ingestion.

## State model

`CATALOG/MASTER evidence -> REPOSITORY_INGESTION_QUEUE -> frozen source-ingestion packet -> independent verification -> capability/component update -> experiment`

Queue states:

- `CAPABILITY_LINKED` — the repository is already named by one or more structured CAP records; freeze a source-ingestion packet next.
- `MASTER_UNMAPPED` — positive-training leader exists in MASTER but no structured CAP record currently names it.
- `ELITE_CATALOG_UNMAPPED` — 25+/30 or explicit MASTER contender/referral exists only in a thematic catalog.

## Priority

- **P0** — score >=29/30.
- **P1** — MASTER entry or score >=28/30.
- **P2** — remaining elite 25–27/30 candidates.

Priority is an intake order, not evidence of technical correctness or permission to deploy.

## Generate

```bash
python tools/ti_repository_ingestion.py
python tools/ti_repository_ingestion.py --check
```

The generated JSON and Markdown are content-addressed. Every row also gets a deterministic record hash.

## Source-ingestion packet requirements

Before source code, tests, schemas, datasets or workflows are incorporated into an internal component:

1. exact repository + revision;
2. selected source/test/schema paths and hashes;
3. intended capability role;
4. evidence boundaries and contradictions;
5. third-party data/model/standards/API caveats;
6. ingestion mode (direct component, adapter, schema/reference, benchmark fixture, comparator, or clean-room pattern);
7. deterministic acceptance test;
8. verifier identity and frozen packet hash.

Untrusted third-party code remains non-executable outside the existing sandbox boundary. A queue entry cannot write MASTER, change verifier/controller logic, alter benchmark gold, or globally promote a skill.
