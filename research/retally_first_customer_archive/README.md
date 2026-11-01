# RETALLY original first-customer code, immutable historical archive

**REVIEW-ONLY / NOT APPROVED FOR DEPLOYMENT, CUSTOMER USE OR FINANCIAL ACTION.**

This preserves all 86 original source Git blobs from historical draft #329 under inert paths. No original source or CI workflow runs from this archive, no real customer information is ingested, and no original branch is deleted. See `SOURCE_MANIFEST.json` for exact Git blob identity and original path. The 45 historical missing files were initially proposed for direct integration in #929. Genuine CI rejected that attempt: the first candidate produced 272 Freight test failures, 7 errors, and unused-variable lint failures against modern APIs. These are genuine compatibility issues, not reasons to weaken the protected release gate. Source is therefore quarantined, **not** marked implemented.

Never use historical commercial terms, cash events, reviewer claims, contracts or issuer financial evidence as current legal/financial authorization. Existing independent real-cash verification, security, rights and customer-release holds on protected main remain authoritative. All staged original files are inert; publication or commercial use requires separate modern compatibility engineering, exact-head tests and authorization.

Reproduce the source-bytes audit with:

```sh
python3 research/retally_first_customer_archive/verify_archive.py
```

The manifest can be used to identify individual source-level opportunities for **separate** reviewed integration, never a blanket merge. Backlog #901.
