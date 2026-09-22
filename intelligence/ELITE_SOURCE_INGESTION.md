# Elite source ingestion queue

Pinned at exact revisions from the current Hunter elite set. This queue is the machine-readable bridge from research value to implementation work.

**Sources:** 58  
**States:** STARTED 1 · QUEUED 48 · MAPPED 9  
**Started:** bsaffel/moneybin

## Operating rules

- A queue entry is not proof that code has been installed, validated, or deployed.
- Exact revisions are mandatory; default-branch drift is not accepted.
- Preserve independent comparators/falsifiers when combining them would destroy test value.
- Third-party datasets, standards, services, model weights, assets, trademarks, patents, and customer data stay separately governed.
- Sensitive or accidentally exposed material is never an ingestion source.
- Runtime ingestion must land behind existing evidence, review, authorization, and external-action gates.

## Ordered queue

| Priority | State | Score | Repository | Target | Revision |
|---|---|---:|---|---|---|
| P0 | STARTED | 28 | bsaffel/moneybin | shared_evidence | `fd34d99962c8` |
| P0 | QUEUED | 30 | acqagent/far-collector | capturebrief | `40789a073134` |
| P0 | QUEUED | 30 | acqagent/rfo-deviations | capturebrief | `ccf311075080` |
| P0 | QUEUED | 30 | GSA/GSA-Acquisition-DFARS | capturebrief | `7e609f791af9` |
| P0 | QUEUED | 29 | fedspendingtransparency/data-act-broker-backend | capturebrief | `76dcae4ccbf6` |
| P0 | QUEUED | 29 | getcoherence/openpartner | settlement_recovery | `eeff532ee758` |
| P0 | QUEUED | 29 | GSA/GSA-Acquisition-FAR | capturebrief | `da52ccbbe114` |
| P0 | QUEUED | 29 | kingsleyonoh/invoice-reconciliation-engine | ap_recovery | `754533080616` |
| P0 | QUEUED | 29 | MassingCloud/massing-pdf | construction | `36794b3c54fc` |
| P0 | QUEUED | 29 | opensanctions/nomenklatura | shared_identity | `844dba09fafc` |
| P0 | QUEUED | 29 | pedrocodesforcoffee/builder-api | construction | `3a9d2f3af61b` |
| P0 | QUEUED | 29 | pialmmh/billing-dotnetcore | telecom | `ec9e0abacce7` |
| P0 | QUEUED | 29 | Superheld/summae | shared_ledger | `9c5292af99ba` |
| P0 | QUEUED | 28 | alanbld/utf8proj | construction | `92d962681590` |
| P0 | QUEUED | 28 | aurelianware/cloudhealthoffice | payer_recovery | `85c8e18146d1` |
| P0 | QUEUED | 28 | fedspendingtransparency/usaspending-api | capturebrief | `1692d484b38c` |
| P0 | QUEUED | 28 | finnertallon-png/contract-deadline-agent | construction | `c891f5ff391a` |
| P0 | QUEUED | 28 | payops-labs/solana-payment-ops | shared_settlement | `7e4d9cc8d137` |
| P0 | QUEUED | 28 | prathamesh-git9/effect-broker | shared_settlement | `eb273640a3a8` |
| P0 | MAPPED | 29 | A-Jatin/freight-ratecon-extraction | freight | `a3dbbfec7f6b` |
| P0 | MAPPED | 29 | cmdrvl/canon | shared_identity | `45e9702ba7f3` |
| P0 | MAPPED | 29 | emoss08/Trenova | freight | `95fcf8165620` |
| P0 | MAPPED | 29 | kodekinetics79/opstrax-enterprise-build | freight | `fec2ba1432d6` |
| P0 | MAPPED | 29 | mgilbir/formalis | ap_recovery | `2b3895a0c2c5` |
| P0 | MAPPED | 29 | OmarFaig/Assay | shared_evidence | `821303935ef2` |
| P0 | MAPPED | 29 | srthck/trustmesh | shared_evidence | `5a93d70b37aa` |
| P0 | MAPPED | 28 | sengtha/Kareya-Silo | freight | `a43eedea03ad` |
| P0 | MAPPED | 28 | vidyesh95/qatoto-backend | freight | `4f5f270f6ba5` |
| P1 | QUEUED | 29 | AccelerationConsortium/HELIOS | lab_automation | `1e5765ec694d` |
| P1 | QUEUED | 29 | adamleap02/PermitBuild | permitplate | `ff795137e0c6` |
| P1 | QUEUED | 29 | Benchling-Open-Source/allotropy | lab_automation | `ecc574986b74` |
| P1 | QUEUED | 29 | ChelseaKR/constituent-reconciler | shared_identity | `dbc09d25baec` |
| P1 | QUEUED | 29 | ersinkoc/Kronos | recovery_readiness | `541d06069459` |
| P1 | QUEUED | 29 | GRIDAPPSD/CIMHub | grid_intelligence | `5ba4c63fa525` |
| P1 | QUEUED | 29 | joschiservice/RosterSpec | workforce | `f7e701c694bf` |
| P1 | QUEUED | 29 | kirilurbonas/FireDrill | recovery_readiness | `1e532b17e49e` |
| P1 | QUEUED | 29 | mehdi-arfaoui/Stronghold | recovery_readiness | `776fe21f159b` |
| P1 | QUEUED | 29 | owgreen-dev/grid-crunch | grid_intelligence | `5f0c9a074d92` |
| P1 | QUEUED | 29 | probavi/probavi | recovery_readiness | `3f0dd3bd9425` |
| P1 | QUEUED | 29 | sandialabs/DREAMS | grid_intelligence | `3eb6c6089ead` |
| P1 | QUEUED | 29 | suoten/ProtoForge | industrial_validation | `7c61b10d9ae4` |
| P1 | QUEUED | 28 | carabiner-dev/ampel | shared_evidence | `5cf19bc2786c` |
| P1 | QUEUED | 28 | duke5am/pg-restore-drill | recovery_readiness | `e914caddd14a` |
| P1 | QUEUED | 28 | mnmn0/mukuroji | recovery_readiness | `34ec66604443` |
| P1 | QUEUED | 28 | nearai/pg-backup | recovery_readiness | `6836158bdfd3` |
| P1 | QUEUED | 28 | NotAbdelrahmanelsayed/paymob_integration | shared_settlement | `8999a6799c56` |
| P1 | QUEUED | 28 | nzebrian/eruofood-ai | settlement_recovery | `9c191ece9b27` |
| P1 | QUEUED | 28 | OCA/rma | warranty_recovery | `9416b2a5f5e1` |
| P1 | QUEUED | 28 | odoo/odoo | ap_recovery | `c55c82dac628` |
| P1 | QUEUED | 28 | slicedearth/contract-delta-au | capturebrief | `630d1903507e` |
| P2 | QUEUED | 28 | Illumina/interop | lab_automation | `015a85ec100c` |
| P2 | QUEUED | 28 | Jaskeeratr/grid-reliability-analytics | grid_intelligence | `24e59a7318db` |
| P2 | QUEUED | 28 | labscript-suite/labscript-devices | lab_automation | `424b9f4b0de9` |
| P2 | QUEUED | 28 | labscript-suite/labscript-suite | lab_automation | `0ab902d0d8bc` |
| P2 | QUEUED | 28 | NationalGenomicsInfrastructure/scilifelab_epps | lab_automation | `fbbe16f9a5ee` |
| P2 | QUEUED | 28 | SemaphoreSolutions/s4-clarity-lib | lab_automation | `ad577fff3a3c` |
| P2 | QUEUED | 28 | snapetech/DuneAwakeningSelfHost | recovery_readiness | `8d3bac1df38f` |
| P2 | QUEUED | 25 | open-eid/SiVa | recovery_readiness | `0c9c5f2490b1` |

## First active ingestion

`bsaffel/moneybin@fd34d99962c833de87bdb45351f0ace142db3f63` is the first active cross-cutting source. Its high-value semantic is now being translated into RecoveryWorks source-coverage receipts so `VERIFIED_EMPTY` remains distinct from `PARTIAL` or `UNAVAILABLE`. Legacy observations retain their prior identity until an adapter explicitly opts into the stronger receipt model.

## Next P0 batches

1. Shared settlement/effect safety: `prathamesh-git9/effect-broker`, `payops-labs/solana-payment-ops`, `getcoherence/openpartner`.
2. Shared accounting truth: `Superheld/summae`.
3. AP assurance: `kingsleyonoh/invoice-reconciliation-engine` plus `mgilbir/formalis` and Odoo counter-event semantics.
4. ConstructionRecovery completion: `MassingCloud/massing-pdf`, `pedrocodesforcoffee/builder-api`, `alanbld/utf8proj`, `finnertallon-png/contract-deadline-agent`.
5. CaptureBrief authority stack: GSA FAR/DFARS, acqagent FAR/deviation sources, USAspending and DATA Act normalization.
