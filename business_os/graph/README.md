# Upgrade 5 — Provenance-Preserving Knowledge Graph

Status: **IMPLEMENTED**

The Business OS now has a durable graph that can represent:

```
REPO
  -> IMPLEMENTS -> CAPABILITY
  -> ENABLES    -> PRODUCT
  -> SERVES     -> CUSTOMER
  -> TESTED_BY  -> EXPERIMENT
  -> PRODUCES   -> OUTCOME
```

## Node types

The initial schema includes:
- REPO
- CAPABILITY
- TECHNOLOGY
- BUSINESS
- PRODUCT
- CUSTOMER / PROSPECT
- OPPORTUNITY
- EXPERIMENT
- OUTCOME
- TOOL
- DOCUMENT
- DECISION
- METRIC

## Provenance

Every node and edge carries:
- a source reference;
- a SHA-256 source identity;
- timestamps;
- structured properties.

Node updates preserve an append-only version record, so the latest state can
change without erasing the evidence lineage that produced older states.

## Queries

The implementation supports:
- typed node lookup;
- inbound/outbound neighbors;
- relation filtering;
- cycle-safe shortest path;
- deterministic machine-readable export.

## Hunter lineage

The graph mirrors the Hunter architecture:

`REPO -> CAPABILITY -> TECHNOLOGY -> OPPORTUNITY -> EXPERIMENT -> OUTCOME`

but extends it to operating businesses, products, prospects and customers.
