# Freight Recovery Laboratory 03 — First-Customer & Blind Pilot

**Status (2026-10-07): OFFLINE SYNTHETIC ENGINEERING PASS. NOT real customer proof.**

This is the third completed lab in the numbered program. It reuses the first million-shipment **fictional** dataset and builds a separate, 1,000,000-pilot relationship simulator. Source invoice identities are reissued as new explicit fictional buyer scopes. Those receipts are **not** real ownership/consent/contract signatures.

## Actual executed local workload

| Check | Independently recorded |
|---|---:|
| Complete fictional pilots | 1,000,000 |
| Reusable fictional buyer profiles | 10,000 |
| Designed scenario categories | 40 |
| Independently replayed timeline events | 18,209,978 |
| Synthetic communications | 6,743,587 |
| Financial journal entries reconciled | 961,821 |
| Reconciled source shards | 100 |
| Generated compressed event files | 400 |
| Validation gates | **22/22 PASS_SYNTHETIC_ONLY** |
| Isolated intentionally invalid mutations rejected | **20,000 / 20,000** |
| Portable Python regression tests | **44/44 passed** |
| Buyer-style fictional PDFs | 120, prominently marked FICTIONAL |
| Proposed unverified QA risk hypotheses | 160 |
| Indexed searchable simulated scenarios | 1,000,000 |
| Local browser QA | 10 sections, desktop and 390px mobile; no JS errors |
| Local API QA | 8/8 read-only loopback routes/denial checks |
| Downloaded archive restoration | 14 ZIPs, 608 members, SHA-verifiable |
| Freshly extracted test suite | 44/44 passed |
| Freshly restored shard hashes | 400/400 matched |
| Real customer proof | **NOT TESTED** |
| Production RecoveryOS audit accuracy | **NOT TESTED** |
| Real carrier claims, bank transfers, fees | **NONE** |

**The locally generated money, customers, margins, and outcome percentages are artificial stress assumptions, not actual business results or statistically calibrated forecasts.** The source-gold truth is synthetic, and a deliberately weak non-RecoveryOS baseline has 14.61% positive recall on a 128,000-case TEST fold (7,661 TP, 4 FP, 44,787 FN, 58,981 TN). The scorer is *not* RecoveryOS.

## Verified source manifests and standalone release

- Source input: Lab 1 fictional 1M shipment rows; original source SHA256: `7c670a91a1a411480b35d054b821f483744267b9c07acda9fe974d910888ed81`.
- Frozen lab input manifest SHA256: `cddd697e2798bf08ee5605d3d24d7f0639f9ef03c2d3376211faa29d68a08bc9`.
- Full lifecycle manifest SHA256: `9e29ae1d1e20c5ccbc3deb7d24644c59122fe0d629b432b2902e9fed791a897c`.
- Independently replayed 1M state histories and hashes: `data/pilots_million/verification.json` in the user-downloaded toolkit.
- Release proof: `reports/LAB03_RELEASE_GATE.json`, synthetic-only outcome 22/22.
- Downloads: 3.7 MB portable toolkit, source inputs/original fictional shipments, 10 roughly 190MB full-data archives, optional ~56MB ZIP compressed SQLite search index. 14 ZIP SHA256 digests and full restore instructions are in the separate `Freight_Lab03_DOWNLOAD_MANIFEST.json` delivered in chat.
- All 14 archives passed ZIP test and digest verification. A clean fresh extraction was independently tested against 400 restored gzip hashes and all 44 Python tests.

## Real RecoveryOS integration in this draft branch

- `freight/pilot_lab03_methodology_probe.py` imports **actual** `freight.audit_acceptance` with synthetic fixture inputs.
- `freight/test_pilot_lab03_methodology_probe.py` contains 11 synthetic methodology tests for independent roles, truth/output sealing, unsupported automatic decisions, missing reviewer evidence, inadequate sample, incumbent/duplicate monetary leakage, and more.
- `.github/workflows/freight-lab03-pilot-smoke.yml` uses pinned immutable GitHub Actions SHA, read-only repository permissions, no schedule and no deployment. The required real-code CI was green on the preceding exact commit; review new-head checks after this documentation update.
- The wrapper **explicitly declassifies** `AUDIT_QUALITY_PROVEN` when its input was fabricated; only synthetic method-smoke outcomes are exported.
- No hosted Floot API was exercised with these millions of simulated relationships. No customer contact, bank or carrier action, production deployment or PR merge occurred.

## Real pilot launch blockers

No executed real-buyer contract, genuine buyer-held independent truth labeling, valid actual-data scope, authenticated live EDI/OCR endpoint accuracy, actual carrier settlement, reconciled real credit, or paid success fee has been established. A passing synthetic run does not change the commercial customer-proof gate. Actual pilot activation remains subject to existing separate environment/security, rights and engagement authorization constraints.

**Lab completion counter: 1/12 new labs delivered, 11 remain (Labs 04–14). Do not start Lab 04 without the next user instruction.**
