# Freight Recovery Independent Testing Laboratory

Status: **Research / synthetic engineering only. NOT production accuracy.**

This feature branch adds a runnable, deterministic probe that executes the actual
`freight.rating_engine.rate_record` code using independent TL/PER_MILE contract
arithmetic, canonical source objects, and ground-truth classifications.

## Run the actual engine probe

```bash
python -m freight.lab.actual_engine_probe --count 10000 --seed 41037
python -m pytest freight/test_lab_actual_engine_probe.py
```

Runs in batches with different explicit seeds for larger populations. Metrics
include confusion counts, exact expected amount, exact variance, source/authority
traceability, and p50/p95 per-case engine latency. The timer covers just
`rate_record` and authority resolution, **not** data generation, ingestion,
OCR, persistence, network I/O, authentication, or end-to-end throughput.

## Independent six-mode workload (separate artifact)

The chat-delivered `freight_lab_toolkit.zip` contains a standalone
`lab.py` and `test_lab.py` that generate 1,000,000 fictional shipment/
invoice lines covering PARCEL, LTL, TL, INTERMODAL, AIR, and OCEAN, plus 2,400
fictional contract profiles, synthetic source SHA-256, 12 scenario types,
adjudication labels, and immutable expected amounts in integer cents.

The full 1M compressed CSV is **not checked into Git**. This deliberately
avoids inserting a 117MB binary artifact into a product repository. Use the
downloaded dataset or rerun the provided standalone generator.

The independent tariff fixture is intentionally **different** from supported
RecoveryOS contract coverage. Do **not** claim that the six-mode dataset was
processed through the production engine, or that its truth labels are
customer-measured false-positive/false-negative rates. The actual-engine probe
is a separate supported TL subset.

## Gold classification policy

- POSITIVE: evidence-present discrepancy remaining after synthetic credits.
- NEGATIVE: no eligible discrepancy (including already-credited scenarios).
- REVIEW: conflicting/expired authority, missing POD or missing source. Zero
  automatically eligible recovery regardless of modeled disputed amounts.
- Hypothetical collection = 60% of synthetic net-eligible value; this is an
  explicit **assumption**, not predicted or demonstrated customer recoveries.

## Evidence and release boundaries

No customer data, receipts, recovered dollars, actual OCR accuracy,
carrier settlements, real-world rate exceptions, competitor results, production
performance, or provider security assurance are established by this laboratory.
Do not upload private customer evidence into a public repository or send
outreach based on these synthetic totals.

The Floot-hosted application has a separate, unpublished import-boundary
hardening change with its own six-file test suite. Do not treat this Python
PR as deployment of those application changes.

## Measured tests vs desired future tests

1. Independently adjudicated blind customer invoices for precision/recall.
2. Actual six-mode end-to-end rating/authority coverage with negotiated terms.
3. Verified real-document OCR/extraction benchmark across paper/PDF/image.
4. Multi-tenant concurrent import and database unique constraints.
5. Full claim lifecycle through confirmed credits, disputes and settlements.
6. Actual request latency/resource profiling under authentication and storage.
