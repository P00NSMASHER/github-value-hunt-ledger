# Portfolio Brain seed

This directory is a relocatable Step 1 seed for the future dedicated `P00NSMASHER/portfolio-brain` repository.

It is intentionally non-operational. Nothing here grants downstream write authority, schedules autonomous work, invokes a model, deploys infrastructure, contacts customers, moves money, or trades.

## Materialization

When the dedicated repository exists, copy the **contents** of this seed to its repository root, preserving paths. The architecture contract, registration contract, validator, and CI workflow must pass unchanged before the repository is treated as the PRJ-000 foundation.

`FOUNDATION_SKELETON.json` defines the complete intended top-level structure. Directories that have no implementation yet are represented by that manifest rather than meaningless placeholder files.

## Step 1 acceptance

1. `tests/validate_foundation.py` passes.
2. The initial CI workflow runs only deterministic local checks.
3. All default capability toggles remain false.
4. No downstream repository is modified by foundation creation.
5. The dedicated repository is created and the same seed is materialized there before Step 1 is marked complete.
