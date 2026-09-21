# Audit Run Manifest

One Freight Recovery audit run now has a single canonical identifier.

The manifest is customer-data-minimized: it contains hashes, scope identifiers, counts, and proof-object references rather than invoice rows. It binds:

- the accepted invoice file and normalized invoice adapter;
- the evidence-derived frozen population;
- all normalized authority-rule batches and original authority-document hashes;
- every normalized rule proof;
- Finding Factory output and frozen truth;
- deterministic review queue;
- deterministic reviewer work packet.

The builder re-derives the canonical queue and reviewer packet before issuing the manifest. It also checks scope consistency, population/factory linkage, rule-proof uniqueness, and truth/queue/factory relationships.

Changing source invoice evidence, population selection, rule evidence, authority documents, findings, queue order, or reviewer packet content changes the run hash.

The manifest identifies the **pre-human-decision audit state**. Proof-bound human reviews, external-action authorization, and later settlement/reporting remain separate downstream artifacts because they occur after this run state is assembled.
