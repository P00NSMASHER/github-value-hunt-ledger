# RETALLY Lab 14: historical draft source archive (internal only)

This branch stores immutable Git blob copies of code, research fixtures, source observations, notes and workflows from **54 historical DRAFT PRs**. Every original file is retained at `sources/pr-NNN/<original path>` without changing its bytes. GitHub workflow source files are stored under `research/`, **never** as active workflows.

**Status: ARCHIVE / RESEARCH HOLD / NOT MERGED INTO MAIN.** This is evidence retention and backlog reconciliation, not code integration, release approval, current-source validation, legal guidance, signed buyer authority, financial proof, real customer performance, public advertising, patentable discovery or verified revenue. Some historical numeric/regulatory sources are outdated or not independently reproduced today.

Every archived file is mapped to its original PR head, original file path, change status and exact Git blob SHA in five batch manifests. Read-only GitHub Actions validation checks Git object parity. No archived code is imported or executed, no recurring schedules are created, and no customer, payment, cloud or third-party account is touched.

**Do not merge this draft to production, promote archived claims, or delete original source branches.** The originals may be closed as source-superseded only after 54/54 source-PR integrity checks and exact-hash CI pass. All original PR discussions remain available. Retally backlog tracker #901.

The fifth manifest preserves 11 later historical Lab14 drafts (#460, #476, #478, #485, #487, #492, #494–#497, #504), as inert, distinct PR-prefixed source revisions. Their dated research claims remain unvalidated for live commercialization. Archive source byte preservation does not imply legal rights, current external evidence, or acceptance for processing customer data.

The integrity workflow compares **committed Git blob identities** (`git rev-parse HEAD:<path>`), not re-encoded working-tree text. This matters because older fixed-width `.txt` source objects may retain historical CRLF bytes while modern `.gitattributes` checks them out as LF. A checkout conversion must not be falsely called evidence corruption.
