# Research & Science

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings
### PyLabRobot/pylabrobot
- Repository: https://github.com/PyLabRobot/pylabrobot
- Commit / revision: c3c59eebf45c4f6bb2fc78dbfd30f6e458653494
- Date discovered: 2026-09-19
- What it contains: Hardware-agnostic Python SDK for laboratory automation spanning liquid handlers, plate readers, pumps, scales, heater-shakers, centrifuges, thermocyclers, storage, barcode scanners, and many vendor-specific backends.
- Why it matters: The repository compresses a large amount of specialized device-integration work behind a common software interface and is actively maintained.
- Commercial possibilities: Protocol automation layer for specialized lab workflow products, remote execution/control, reproducibility tooling, lab-operations orchestration, or vertical services that sit above existing robots.
- Build-time savings: Very high for cross-vendor device control and lab-instrument abstractions.
- Evidence inspected: README.md; repository metadata updated 2026-09-18; MIT LICENSE; source tree contains many vendor/device modules plus liquid_handling backends, testing infrastructure, and broad hardware adapters.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: Very High
  - Commercial value: Medium-High, depending on access to lab customers/hardware
  - Rarity: High
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: Medium
  - High-ticket potential: High
- Next action: Search for narrow, expensive lab workflows where PyLabRobot already supports the installed hardware and where software/orchestration is the bottleneck rather than hardware procurement.
