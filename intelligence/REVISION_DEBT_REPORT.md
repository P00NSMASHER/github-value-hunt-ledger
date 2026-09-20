# REVISION / CATALOG PROVENANCE DEBT

Pinned revisions are essential for reproducible technical intelligence. This report prioritizes records whose repository identity is known but whose inspected revision is not recoverable from the hunter catalog.

- Unknown-revision observations: **88**
- Unique repositories with unknown revision: **88**
- Current MASTER promotions without matching exact hunter-catalog observation: **2**

## Unknown revision mix

| Bucket | Count |
|---|---:|
| unknown | 33 |
| strong | 20 |
| rejected | 18 |
| watch | 14 |
| quarantined | 3 |

## Highest-priority records to resolve

| Repository | Catalog | State | Disposition | Priority |
|---|---|---|---|---:|
| BroadbandForum/usp-data-models | hunters/35.md | current | strong | 10 |
| BroadbandForum/usp-test | hunters/35.md | current | strong | 10 |
| CANopenNode/CANopenNode | hunters/12.md | current | strong | 10 |
| OPCFoundation/UA-.NETStandard | hunters/12.md | current | strong | 10 |
| OpenCommissioning/OC_TcPnScanner | hunters/12.md | current | strong | 10 |
| OpenEtherCATsociety/SOEM | hunters/12.md | current | strong | 10 |
| TcHaxx/TcPnScanner | hunters/12.md | current | strong | 10 |
| eclipse-kura/kura | hunters/12.md | current | strong | 10 |
| eclipse-wakaama/wakaama | hunters/35.md | current | strong | 10 |
| ethercrab-rs/ethercrab | hunters/12.md | current | strong | 10 |
| flownexus-lwm2m/flownexus | hunters/35.md | current | strong | 10 |
| frappe/erpnext | hunters/16-run11-2026-09-20.md | current | strong | 10 |
| industrial-aiops/industrial-aiops | hunters/12.md | current | strong | 10 |
| leducp/KickCAT | hunters/12.md | current | strong | 10 |
| localhots/SimulaTR69 | hunters/35.md | current | strong | 10 |
| opcua-lads/lads-server-collection | hunters/12.md | current | strong | 10 |
| openconfig/kne | hunters/35.md | current | strong | 10 |
| openconfig/ondatra | hunters/35.md | current | strong | 10 |
| systerel/S2OPC | hunters/12.md | current | strong | 10 |
| wazuh/wazuh | hunters/15-run19-2026-09-20.md | current | strong | 10 |
| BroadbandForum/cwmp-xml-tools | hunters/35.md | current | watch | 8 |
| CANopenNode/CANopenLinux | hunters/12.md | current | watch | 8 |
| IoTKETI/IPE-LWM2M | hunters/35.md | current | watch | 8 |
| OpenAutomationTechnologies/openPOWERLINK_V2 | hunters/12.md | current | watch | 8 |
| OpenEtherCATsociety/SOES | hunters/12.md | current | watch | 8 |
| SiemensIndustryPL/OpennessProfinetEditor | hunters/12.md | current | watch | 8 |
| f0rw4rd/hartip | hunters/12.md | current | watch | 8 |
| f0rw4rd/profinet-py | hunters/12.md | current | watch | 8 |
| imdtouch/EthernetIP-Simulator | hunters/12.md | current | watch | 8 |
| libremfg/PackML-MQTT-Simulator | hunters/12.md | current | watch | 8 |
| optim-enterprises-bv/ac-client | hunters/35.md | current | watch | 8 |
| pasrom/profinet-rs | hunters/12.md | current | watch | 8 |
| shensi8312/secsgem-driver | hunters/12.md | current | watch | 8 |
| tokeyjs/TinySECSGem | hunters/12.md | current | watch | 8 |
| AD-SDL/MADSci | hunters/21-run19-2026-09-20.md | current | unknown | 7 |
| ANI-IN/Call-Center-Intelligence-System | hunters/37.md | current | unknown | 7 |
| AstorisTheBrave/Rostra | hunters/37.md | current | unknown | 7 |
| Emma-V/support-triage | hunters/37.md | current | unknown | 7 |
| Five9DeveloperProgram/Five9-Agent-Sup-REST-API-Python-Pack | hunters/37.md | current | unknown | 7 |
| GenesysCloudBlueprints/cx-as-code-cicd-gitactions-blueprint | hunters/37.md | current | unknown | 7 |
| Hesper-Labs/owly | hunters/37.md | current | unknown | 7 |
| Josh-Gi3r/stablecoin-payroll | hunters/01-run15-2026-09-20.md | current | unknown | 7 |
| Kazaam-sudo/CallQuanta | hunters/37.md | current | unknown | 7 |
| Kim-Hakseong/NOKTRA-secsgem-workbench | hunters/12.md | current | unknown | 7 |
| LQVCohan/cohan-restaurant-app | hunters/01-run15-2026-09-20.md | current | unknown | 7 |
| Madhumitha-28/enterprise-contact-center-platform | hunters/37.md | current | unknown | 7 |
| OCA/field-service | hunters/37.md | current | unknown | 7 |
| Practitionist/familiarise_web | hunters/01-run17-2026-09-20.md | current | unknown | 7 |
| Raunak-Sarmacharya/LocalCooksCommunity | hunters/01-run15-2026-09-20.md | current | unknown | 7 |
| Tests/history | hunters/04-run12-2026-09-20.md | current | unknown | 7 |

## MASTER catalog provenance gaps

- `emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65` is in current MASTER but lacks a matching exact hunter-catalog observation.
- `GSA/GSA-Acquisition-DFARS@7e609f791af9cc6d8e7d75a7b05c83b1f62c0cb8` is in current MASTER but lacks a matching exact hunter-catalog observation.

## Policy

- Resolve current strong/watch records before archival/rejected records.
- Do not invent a historical SHA. If the original inspected revision cannot be recovered from Git history, record the uncertainty and reinspect a new pinned revision as a new observation.
- MASTER can remain authoritative, but load-bearing elite components should also have durable catalog evidence tied to the exact revision.
- Revision debt is evidence-quality debt, not a reason to erase useful historical findings.
