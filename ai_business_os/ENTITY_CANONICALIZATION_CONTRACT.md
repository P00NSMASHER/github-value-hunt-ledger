# Entity Canonicalization Contract — Step 9

The AI Business OS now resolves duplicate real-world identities into a clean canonical view without
deleting the original source records or their provenance.

## Canonicalizable identity types

REPO, DATA, TECHNOLOGY, PRODUCT, BUSINESS, CUSTOMER.

Experiments, outcomes, memories, and capabilities are intentionally excluded from automatic identity
merging because semantic similarity is not sufficient evidence that those records represent the same
real-world identity.

## Match outcomes

- AUTO_MERGE — deterministic identity evidence is strong enough to merge safely.
- REVIEW — evidence is ambiguous; an explicit HUMAN reviewer is required.
- KEEP_SEPARATE — evidence is insufficient, node types differ, or hard identifiers conflict.

## Identity evidence

The deterministic scorer uses positive evidence from normalized names, aliases, descriptions, graph
neighbors, and hard identifiers. Hard identifiers such as EIN, tax ID, DUNS, SAM UEI, GitHub
repository ID, repository ID, and Stripe customer ID receive special treatment.

A conflicting hard identifier always forces KEEP_SEPARATE, even when display names match.

## Survivorship

Canonical fields are chosen using explicit positive source weights. The winning value, source node,
and weight are recorded for every field. Losing/conflicting values are retained in the
canonicalization ledger rather than discarded.

## Hard invariants

1. Source records are never deleted by canonicalization.
2. Canonical nodes are derived records with provenance linking every source identity.
3. Match evidence binds to the exact source provenance hashes used during comparison.
4. If source provenance changes after comparison, the merge must be recomputed.
5. Different node types never canonicalize into one identity.
6. Conflicting hard identifiers always block a merge.
7. Ambiguous REVIEW matches require an explicit HUMAN reviewer plus review evidence.
8. Source weights must be positive, finite, and specified for exactly the merged records.
9. Every conflicting field remains visible with all candidate values and source weights.
10. Source nodes become CANONICALIZED rather than deleted.
11. Original labels, canonical keys, and aliases resolve to the canonical entity after merge.
12. New aliases and new graph relationships cannot be written to inactive duplicate source nodes.
13. Existing source relationships remain intact as historical provenance.
14. Canonical views collapse duplicate semantic relationships while retaining every contributing evidence edge.
15. Canonicalization is reversible when the canonical entity has not accumulated unresolved live relationships.
16. Reversal restores source statuses and original alias bindings; the derived canonical node remains as REVERSED history.
17. Nested canonicalization resolves transitively: an original source always resolves to the newest active canonical entity.
18. Leaf-source lineage remains visible through multi-stage merges.
19. Older merges cannot be reversed while their canonical node participates in a newer active merge.
20. Candidate scanning ignores already-canonicalized duplicate source nodes.

## Corporate mergers vs identity deduplication

A corporate acquisition or legal merger is not automatically the same thing as duplicate identity.
If two legal entities retain conflicting authoritative identifiers, they remain separate graph entities
even if one later acquires the other. Corporate-event relationships should be modeled as explicit
business relationships/events, not hidden inside identity canonicalization.

## Intended result

Multiple records such as:

Federal Express Corporation
FedEx
Federal Express Corp

can resolve to one canonical customer when the evidence supports that identity, while every original
record, source, alias, field conflict, and relationship remains recoverable.

This gives the Business Brain a clean single entity view without sacrificing forensic provenance.