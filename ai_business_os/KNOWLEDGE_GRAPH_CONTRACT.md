# Knowledge Graph Contract — Step 5

The AI Business OS now has a typed, provenance-preserving relationship layer for reasoning across
technical assets, business systems, customers, experiments, and verified outcomes.

## Core node types

REPO, DATA, CAPABILITY, TECHNOLOGY, PRODUCT, BUSINESS, CUSTOMER, EXPERIMENT, OUTCOME, MEMORY.

## Core relationship examples

REPO -> IMPLEMENTS -> CAPABILITY
CAPABILITY -> ENABLES -> PRODUCT
BUSINESS -> OWNS -> PRODUCT
PRODUCT -> SERVES -> CUSTOMER
PRODUCT -> TESTED_BY -> EXPERIMENT
EXPERIMENT -> PRODUCED -> OUTCOME
OUTCOME -> ATTRIBUTED_TO -> PRODUCT
PRODUCT -> INFORMED_BY -> MEMORY

DEPENDS_ON and COMBINES_WITH are intentionally broader composition relationships. All other edge
types use explicit source/target type contracts.

## Hard invariants

1. Every node has non-empty provenance and at least one evidence reference.
2. Every edge has non-empty evidence and a SHA-256 evidence identity.
3. OUTCOME nodes require verified provenance and a stable external/business event ID.
4. An estimate, forecast, or model prediction cannot be registered as a verified outcome.
5. Typed edge contracts reject semantically invalid relations such as REPO SERVES CUSTOMER.
6. No dangling endpoints or self-edges are allowed.
7. Only one active edge may exist for the same source/type/target relationship.
8. Relationship changes use supersession; old edges remain queryable at historical timestamps.
9. Aliases resolve to canonical nodes without destructive merges.
10. Alias collisions fail closed rather than guessing.
11. Ambiguous identities across node types require an explicit node type.
12. Evidence-bearing directed paths expose a hash over the exact node provenance and edge evidence chain.
13. Outcome lineage can reconstruct upstream technical/business evidence.
14. Nodes with active relationships cannot be silently retired.
15. The graph represents evidence-backed relationships; it does not make a relationship authoritative merely because it is connected.

## Intended reasoning loop

repository / data -> capability -> product / business -> experiment -> verified outcome

This lets later agents ask questions such as:

- Which repositories actually contribute to this product?
- Which capabilities enabled a verified customer outcome?
- Which experiment supports this revenue claim?
- What changed in the relationship graph at a prior date?
- Which remembered tactic informed this product decision?

The graph complements value-weighted memory. Memory answers "what has worked?" while the graph
answers "how are the things we know connected?"