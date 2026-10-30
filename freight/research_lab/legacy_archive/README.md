# RETALLY historical research: held archive

This is a **provenance-preserving migration of selected historical public research metadata**, not the promotion of old GitHub branches into executable production, nor an independently approved source dataset.

- `inventory_v1.json`: catalog of 40 existing refs returned by the October 30 `lab` branch search. The Git head and compare status for each ref are snapshotted in ten source-byte-pinned JSON groups under `groups/`.
- `held_public_metadata/`: three *byte-identical original Git blobs* from historical branches: historical GAO government collection summaries, FAF/EIA public market-context manifests, and a Pennine Care OGL general-accounting reconciliation research note.
- All published source-claim and rights fields remain **UNKNOWN/HOLD**, including publisher original document SHA-256, any current commercial reuse approval, and customer-specific held-out freight error labels.
- Git SHA-1 is used to verify retained repository object bytes, **not** to prove original publisher HTTP/PDF bytes or an authenticated contract, bill of lading, settlement or payment.
- The comparison endpoint listed at most 300 changed files for eight divergent branches; use a separately verified complete Git-tree/content review before deleting or retiring them. They remain untouched.
- Current single writer is `research/retally-unified-data-lab`. Existing recurring discovery and protected-main workflows are unchanged. No extra provider calls or scheduled jobs have been created.

Evaluation families must remain disjoint: original freight invoice extraction/calculation, general accounting reconciliation, freight billing-error adjudication, NYC permit scoring, and federal solicitation-history checks.

**No operational approval or recovery claim can be derived from this archive.** Tests in `freight.test_unified_research_lab.RetallyLegacyArchiveInventoryTests` fail closed on incorrect blob identities, duplicate/missing branch refs, unsupported source rights, fabricated original publisher hashes, invented independent labels, or recovered cash.
