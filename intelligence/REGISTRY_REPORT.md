# REPOSITORY REGISTRY REPORT

Generated directly from the hunter Markdown corpus; no monolithic registry file is round-tripped through the GitHub connector.

- Repository observations: **1,760**
- Unique repositories: **1,676**
- Unique repository/revision keys: **1,684**
- Observations beyond the first occurrence of a repo/revision: **76 (4.3%)**
- Repo/revision records with unknown revision: **82**
- Repositories appearing in more than one catalog/file: **64**
- Hunter Markdown files scanned: **56**
- Current MASTER-promoted repositories: **0**
- Current MASTER-promoted exact repo/revisions: **0**

## Disposition mix

MASTER counts below come from `MASTER.md`; all other buckets come from hunter-catalog dispositions.

| Bucket | Repo/revision records |
|---|---:|
| master | 0 |
| strong | 639 |
| watch | 463 |
| rejected | 390 |
| quarantined | 36 |
| unknown | 156 |

## Most repeatedly observed repo/revisions

| Repository | Revision | Observations | Catalogs | Dispositions |
|---|---|---:|---:|---|
| GSA/open-gsa-redesign | 494b1312e9c6436474840befe6e1964da15932b3 | 7 | 2 | strong, unknown |
| Beveren-Software-Inc/Field_Service_Management | ab6d56d1069882326475f256d09cc63236eddec1 | 3 | 3 | strong, watch |
| OmarRao/r3vp | 404f7f7aaed5b9fbc39506622175d87e628b3054 | 3 | 3 | rejected, strong |
| ahmadpiran/restoredrill | 4afc9e8864688a6151c25e8d6cc5370332feecad | 3 | 2 | strong, watch |
| danieltamas/fortified | c677ef30f750e1cc0b761dd9eed3bab2b40d18f4 | 3 | 3 | strong |
| databricks-industry-solutions/lakehouse-industry-data-models | 0157d62384960d2e0efafdaf3e7c9f9062cdcc28 | 3 | 3 | rejected, watch |
| iacosta3994/restic-drill | 0e11db6339fc86f87239b259827f6848a69886f7 | 3 | 3 | strong, watch |
| usdigitalresponse/entity-api | 9a868b54b2dee3c13d516600c433a673fe558b8d | 3 | 2 | rejected, unknown |
| BishnoiNaveen/gas-agency-management-system | c52603ff6d36972e54a8243bc5b313e24beffeb8 | 2 | 2 | quarantined, rejected |
| CodeMaru-Dreamine/Dreamine.Gem | 82604d6f03c1e95e0558de5c757989b27cd4a3d6 | 2 | 2 | strong, unknown |
| Construction-Progress-Coalition/cpc-changes-hub | 90193e4fdea00eea5eca03ebdbe9c18826e0c73c | 2 | 2 | rejected, watch |
| EffortEdutech/workledger | e78a5a6a7426f149ab89dc2707e3cc8ab1c85168 | 2 | 2 | rejected |
| Etherlabs-dev/multi-processor-reconciliation | 2f9397fbe56a76abeee42a01a37536ad1811a806 | 2 | 2 | strong |
| GRCEngClub/claude-grc-engineering | 784fd9ab375c95f867a34d865f0b2b59ac899b73 | 2 | 2 | watch |
| Grantg2002/Construction-Contract-Management | f9909099440b9dc7ff1b9ad6050c9a30f192a871 | 2 | 2 | rejected, unknown |
| Hussain0327/freight-settlement-infrastructure | 37337ad219bc1e0b361f32b83d577bcb257379ca | 2 | 2 | rejected |
| LostCat-Qian/secs4js | 41bee2cad158bd881ef12c181f85684be6dced67 | 2 | 1 | unknown |
| MassingCloud/massing-pdf | 36794b3c54fcfd62e3a0d2d5984cfc45cac83340 | 2 | 2 | strong |
| MuhDur/invoicekit | 8a9e8d74e23ab97742d56d1dfabe77a9330ec61e | 2 | 2 | strong, watch |
| ND3404/construction-change-order-rfi-analytics | 93522c5b59738d7147e7a50a8c7052b8537d210f | 2 | 2 | watch |

## Interpretation

- Repeated observations are useful only when they add new evidence, a new revision, a new capability edge or an experiment/outcome link.
- A high duplicate-observation rate is not automatically bad, but repeated deep inspections without capability/evidence delta should reduce future search priority.
- Unknown revision records should be resolved before promotion whenever the repository is load-bearing.
- This registry is recomputed from source catalogs, so it cannot silently lose older records because of connector truncation.
