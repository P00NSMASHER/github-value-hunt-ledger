# Simulated customer data

Everything in this directory is synthetic and must never be represented as a
real customer, real counterparty, real invoice, or real recovered cash.

The seven-figure freight fixture exists solely to regression-test the
RecoveryOS hostile-examination controls. It deliberately models a validated
$1,000,000 overcharge candidate and supplies synthetic independent evidence,
reviewers, client authorization, outbound artifact, and proof-seal metadata.

Tests recompute hashes from the fixture contents rather than trusting stored
hash fields.
