"""RecoveryWorks branch registry and adapter metadata."""
from __future__ import annotations

from dataclasses import dataclass

from recoveryworks.models import Branch, RecoveryMode
from recoveryworks.policies import policy_for


@dataclass(frozen=True)
class BranchSpec:
    branch: Branch
    display_name: str
    wedge: str
    primary_inputs: tuple[str, ...]
    output: str
    integration_targets: tuple[str, ...]

    @property
    def mode(self) -> RecoveryMode:
        return policy_for(self.branch).mode


BRANCHES: dict[Branch, BranchSpec] = {
    Branch.FREIGHT: BranchSpec(
        Branch.FREIGHT,
        "FreightRecovery",
        "carrier overcharges and contract/rate leakage",
        ("invoices", "shipments", "contracts", "tariffs", "rate cards"),
        "proof-bound carrier recovery finding",
        ("existing freight/ package", "rate engines", "charge normalization"),
    ),
    Branch.PAYER: BranchSpec(
        Branch.PAYER,
        "PayerRecovery",
        "provider underpayments and downcoding",
        ("835", "837", "payer contracts", "fee schedules", "payer/CMS policy"),
        "human-reviewed appeal/recovery candidate",
        ("X12 parser", "fee schedule calculator", "policy retrieval"),
    ),
    Branch.UTILITY: BranchSpec(
        Branch.UTILITY,
        "UtilityRecovery",
        "commercial utility billing and tariff errors",
        ("bills", "meter/use data", "effective-dated tariffs"),
        "tariff-backed billing variance",
        ("bill extraction", "tariff DSL", "deterministic rate engine"),
    ),
    Branch.AP: BranchSpec(
        Branch.AP,
        "APRecovery",
        "duplicate payments, credits, and vendor-statement leakage",
        ("AP ledger", "payments", "POs", "receipts", "vendor statements"),
        "evidence-backed supplier recovery candidate",
        ("duplicate detector", "3-way match", "vendor reconciliation"),
    ),
    Branch.CONSTRUCTION: BranchSpec(
        Branch.CONSTRUCTION,
        "ConstructionRecovery",
        "change-order and delay entitlement",
        ("contract", "baseline/current schedules", "RFIs", "change orders", "daily logs"),
        "claim-preflight recovery candidate",
        ("clause extraction", "CPM/delay engine", "evidence graph"),
    ),
    Branch.DUTY: BranchSpec(
        Branch.DUTY,
        "DutyRecovery",
        "customs duty and tariff inconsistencies",
        ("entry data", "product data", "HTS versions", "Chapter 99 rules", "fees"),
        "broker/counsel-review recovery candidate",
        ("HTS resolver", "historical tariff versions", "fee calculator"),
    ),
    Branch.SAAS: BranchSpec(
        Branch.SAAS,
        "SaaSRecovery",
        "software subscription, seat, and contracted-rate leakage",
        ("vendor invoices", "subscription contracts", "seat/license snapshots"),
        "contract-backed SaaS billing variance",
        ("contract billing engine", "license inventory", "invoice exports"),
    ),
    Branch.TELECOM: BranchSpec(
        Branch.TELECOM,
        "TelecomRecovery",
        "recurring telecom service and usage billing leakage",
        ("carrier invoices", "service contracts", "CDR/usage aggregates"),
        "contract-backed telecom billing variance",
        ("contract billing engine", "CDR usage", "invoice exports"),
    ),
    Branch.REBATE: BranchSpec(
        Branch.REBATE,
        "RebateRecovery",
        "earned supplier and volume rebates not fully received",
        ("rebate programs", "purchase lines", "settlement/remittance records"),
        "tier-backed rebate underpayment finding",
        ("tier engine", "purchase reconciliation", "settlement evidence"),
    ),
    Branch.LEASE: BranchSpec(
        Branch.LEASE,
        "LeaseRecovery",
        "rent, CAM, operating-expense, and area-based lease billing leakage",
        ("landlord charges", "lease rate schedules", "area/allocation snapshots"),
        "lease-backed billing variance",
        ("contract billing engine", "lease abstracts", "CAM reconciliation"),
    ),
    Branch.TAX: BranchSpec(
        Branch.TAX,
        "TaxRecovery",
        "sales/use-tax and transaction-tax overpayments",
        ("invoice tax lines", "reviewed expected tax assessments", "rule snapshots"),
        "professionally reviewed tax overpayment finding",
        ("tax engine output", "taxability review", "invoice reconciliation"),
    ),
    Branch.INSURANCE: BranchSpec(
        Branch.INSURANCE,
        "InsuranceRecovery",
        "commercial/property insurance claim underpayments",
        ("claim lines", "reviewed policy/coverage assessments", "insurer settlements"),
        "professionally reviewed insurance underpayment finding",
        ("coverage review", "claim valuation", "settlement reconciliation"),
    ),
    Branch.CLOUD: BranchSpec(
        Branch.CLOUD,
        "CloudRecovery",
        "cloud/hosting committed-rate and metered-usage billing leakage",
        ("provider invoice charges", "effective contract rates", "independent meter/usage exports"),
        "contract-backed cloud billing variance",
        ("contract billing engine", "meter aggregation", "invoice exports"),
    ),
    Branch.MERCHANT_FEE: BranchSpec(
        Branch.MERCHANT_FEE,
        "MerchantFeeRecovery",
        "payment-processor markup, per-transaction, and fixed-fee leakage",
        ("processor fee statements", "merchant agreements", "independent transaction summaries"),
        "processor-controlled fee overpayment finding",
        ("fee agreement engine", "transaction reconciliation", "processor statements"),
    ),
}


def all_specs() -> tuple[BranchSpec, ...]:
    return tuple(BRANCHES[key] for key in Branch)
