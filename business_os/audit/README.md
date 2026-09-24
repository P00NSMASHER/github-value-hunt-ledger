# Upgrade 2 — Independent Completion Auditor

Status: **IMPLEMENTED**

The Manager writes the acceptance contract before execution. The Executor may produce artifacts and evidence, but cannot declare its own work accepted. A separate Auditor evaluates the contract and emits a content-addressed receipt.

## State model

```
MANAGER
  |
  | acceptance contract
  v
EXECUTOR
  |
  | result + evidence
  v
AUDITOR
  |
  +--> ACCEPTED
  |
  +--> REJECTED -> more work / escalation
```

## Core invariant

A sentence such as `"done"`, `"tests passed"`, or `"looks good"` from the executor is **not completion evidence**.

Requirements name their allowed evidence producers, such as:
- `CI`
- `SYSTEM`
- `VERIFIER`
- `HUMAN`

`EXECUTOR` is not allowed by default.

## Receipt binding

Each audit receipt binds:
- task ID;
- manager-authored contract hash;
- executor submission hash;
- auditor identity;
- every requirement finding;
- final ACCEPTED/REJECTED verdict.

Changing the contract or submission changes the receipt identity.

## Hunter architecture source

The design follows the Manager → Executor → Auditor separation identified in:
- `AMAP-ML/LongHorizon-Harness@a1dd930614972b92361c1b9cd6aac441a6db5a65`

This implementation is independent and stdlib-only.

## Acceptance test

All tests are run by the dedicated `AI Business OS` workflow with:

```bash
python -m unittest discover -s business_os/tests -v
```
