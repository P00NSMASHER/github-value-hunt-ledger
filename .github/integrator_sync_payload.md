MARKER: <!-- INTEGRATOR-R11-LABOR-PAYROLL-2026-09-20T0106-0400 -->

=== APPEND COMBINATIONS.md ===
## Labor-to-Payroll Assurance v2 — roster -> physical actuals -> approved OT -> payroll -> settlement
- Add `WilfredTinega/Upande-TA@af15de1fb844afd81221829c3be07dba8b5d98df` as a rare installed-base biometric actual-time adapter between planned schedule truth and payroll posting. Pair RosterSpec/minimum-disruption schedule truth -> customer-authorized ZKTeco/ERPNext check-in events -> Upande overtime/Additional Salary linkage -> existing payroll-reconciliation/accounting/payment evidence.
- Buyer/problem: ERPNext/Frappe employers using biometric clocks face missed/duplicate punches, overnight-shift ambiguity, direction errors and approved-vs-paid overtime drift that can become payroll leakage or review labor.
- First paid wedge: **Biometric Time-to-Payroll Acceptance Audit** on one closed period. Freeze device/check-in facts, shift assignment, manager-approved OT, Additional Salary/payroll output and later payment; report exceptions with source lineage rather than silently correcting payroll.
- Critical boundary from source inspection: Upande's direction normalizer intentionally writes `log_type` directly with `frappe.db.set_value`, bypassing document validation, linked-attendance guards and duplicate checks for the flip itself. Its heuristic can turn a trailing IN into OUT or the first all-OUT scan into IN. That is useful repair logic, but **a repaired direction is inferred state, not physical ground truth**.
- Hard invariant: automatic direction repairs must remain separately labeled `inferred/repaired`; they cannot by themselves establish compensable hours or a recoverable payroll discrepancy. Hard-dollar findings require corroborating shift/policy/approval/payroll/payment authority.
- Validation: synthetic fixtures for duplicate punch, lost scan, overnight shift, trailing IN, all-OUT, employee/device remap, OT overlap/cancellation and a deliberately misleading scan sequence. Compare raw-only, repaired and independently adjudicated truth; measure false payroll-dollar creation as a first-class failure metric.

=== APPEND COMPONENTS.md ===
### WilfredTinega/Upande-TA — biometric actual-time / overtime-to-payroll bridge
- Revision: `af15de1fb844afd81221829c3be07dba8b5d98df`.
- Integrator score after source-level recheck: **27/30 — A5 B4 C5 D5 E3 F5**. Hunter score was 28/30; evidence/completeness is reduced because the check-in normalizer deliberately mutates direction with direct DB writes that bypass normal document validation/linked-attendance/duplicate guards, making independent provenance essential.
- Rights: MIT repository code. ZKTeco hardware/PUSH SDK, Node-RED, ERPNext/Frappe services, customer biometric/time records and labor/payroll policy remain separately governed.
- Capability inspected: duplicate check-in prevention on normal inserts; shift-aware/overnight grouping and heuristic direction normalization; overtime period/overlap checks; linked submitted `Additional Salary` creation and cancellation for bulk overtime.
- Important caveat: the overtime override bypasses some native duplicate-date/overtime-type/max-hours checks for bulk-generated slips and trusts precomputed amounts. The formula/policy is not labor-law authority. Repaired check-in direction and precomputed OT amount must be independently approved/validated before payroll-dollar conclusions.
- Integration: Labor-to-Payroll Assurance v2; RosterSpec planned state -> raw biometric facts -> labeled repair/adjudication -> OT approval -> Additional Salary/payroll -> accounting/payment proof.
- Promotion gate: pass a synthetic adversarial clock corpus with no false compensable-hours creation and prove expected->actual->approved->paid lineage on an authorized closed period. Keep out of MASTER until then.

=== APPEND OPPORTUNITIES.md ===
## Biometric Time-to-Payroll Acceptance Audit
- Core: planned roster + immutable/raw biometric events + shift-aware exception/adjudication + approved overtime + payroll artifact + payment evidence.
- Buyer: ERPNext/Frappe employers, payroll service firms and multi-site operators with ZKTeco-style clocks.
- First paid wedge: one closed payroll period; quantify missing/duplicate punches, inferred-direction exceptions, approved-but-unpaid OT, unsupported OT and payroll-review time.
- Revenue path: fixed diagnostic -> recurring pre-payroll exception assurance -> broader labor/payroll reconciliation.
- Safety/integrity: biometric/person records are customer-controlled sensitive data; use only explicitly authorized customer data. Automated scan-direction repair is never sufficient evidence by itself for a wage/payment conclusion.

=== APPEND SEARCH_QUEUE.md ===
## Labor-to-payroll refinement from Hunter 32
- Use `WilfredTinega/Upande-TA@af15de1fb844afd81221829c3be07dba8b5d98df` as the current biometric installed-base adapter, but treat its direct-DB direction repair as **inference requiring review/corroboration**, not source truth. Build a synthetic adversarial corpus around duplicate/lost scans, overnight shifts, trailing IN/all-OUT, remaps and OT overlap/cancellation; measure false compensable-hour and false payroll-dollar creation.
- Search next only for authoritative time-clock event provenance, manager exception approval/receipt, payroll-provider posted/paid evidence and current customer/labor-policy authority. Stop generic attendance/payroll CRUD and generic biometric integrations unless they add an independently verifiable device-event or settlement invariant.
- Keep Upande at COMPONENT/combination level despite clearing 24; promote only if the repair/adjudication layer proves no false-money behavior and one authorized closed-period trace reaches paid payroll.
