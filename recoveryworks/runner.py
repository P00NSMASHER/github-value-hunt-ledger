"""Recovery Scan 360 orchestration across operational branch adapters."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .durable_ledger import DurableRecoveryLedger
from .engine import RecoveryEngine
from .report import RecoveryScan360Report, build_scan360_report
from .store import LocalBundleStore
from .branches.ap import audit_ap_recovery
from .branches.ap_csv import (
    load_obligations_csv,
    load_payments_csv,
    load_vendor_statements_csv,
)
from .branches.freight_io import (
    load_freight_audit_result_bundle,
    load_freight_truth_manifest,
)
from .branches.construction import audit_construction_recovery
from .branches.construction_io import (
    load_causation_reviews_csv,
    load_construction_entitlements_csv,
    load_construction_events_csv,
    load_construction_settlements_csv,
    load_event_activity_mappings_csv,
    load_schedule_versions_json,
)
from .branches.duty import audit_duty_entries
from .branches.duty_csv import load_duty_assessments_csv, load_duty_entries_csv
from .branches.insurance import audit_insurance_claims
from .branches.insurance_csv import (
    load_insurance_assessments_csv,
    load_insurance_claim_lines_csv,
    load_insurance_settlements_csv,
)
from .branches.payer import audit_payer_lines
from .branches.payer_csv import load_payer_lines_csv, load_payer_rates_csv
from .branches.rebate import audit_rebates
from .branches.rebate_io import (
    load_rebate_programs_json,
    load_rebate_purchases_csv,
    load_rebate_settlements_csv,
)
from .branches.contract_billing_csv import (
    load_contract_rates_csv,
    load_invoice_charges_csv,
    load_usage_csv,
)
from .branches.cloud import audit_cloud_billing
from .branches.cloud_signals import CloudSignal
from .branches.cloud_savings import CloudSavingsReport, build_cloud_savings_report
from .branches.cloud_remediation import CloudRemediationPlan, build_cloud_remediation_plan
from .branches.cloud_discount import audit_cloud_discount_billing
from .branches.cloud_discount_csv import load_cloud_discount_authorities_csv
from .branches.cloud_commitment import audit_cloud_commitment_billing
from .branches.cloud_commitment_csv import (
    load_cloud_commitment_authorities_csv,
    load_cloud_commitment_allocations_csv,
)
from .branches.cloud_csv import load_cloud_meter_csv
from .integrations.cletrics import load_cletrics_bundle
from .branches.merchant_fee import audit_merchant_fees
from .branches.merchant_fee_csv import (
    load_merchant_fee_agreements_csv,
    load_merchant_fee_statements_csv,
    load_merchant_transaction_summaries_csv,
)
from .branches.parcel import audit_parcel_charges
from .branches.parcel_csv import load_parcel_assessments_csv, load_parcel_charges_csv
from .branches.procurement import audit_procurement_lines
from .branches.procurement_csv import (
    load_procurement_authorities_csv,
    load_procurement_invoice_lines_csv,
    load_procurement_quantities_csv,
)
from .branches.warranty_credit import audit_warranty_credits
from .branches.warranty_credit_csv import (
    load_warranty_credit_entitlements_csv,
    load_warranty_credit_settlements_csv,
)
from .branches.payroll_benefit import audit_payroll_benefit_billing
from .branches.payroll_benefit_csv import load_payroll_benefit_units_csv
from .branches.lease import audit_lease_billing
from .branches.lease_csv import load_lease_area_csv
from .branches.saas import audit_saas_billing
from .branches.saas_csv import load_billable_seat_snapshot_csv
from .branches.telecom import audit_telecom_billing
from .branches.telecom_csv import load_cdr_usage_csv
from .branches.tax import audit_tax_lines
from .branches.tax_csv import load_tax_assessments_csv, load_tax_lines_csv
from .branches.utility import audit_utility_bills
from .branches.utility_io import (
    load_simple_tariff_definitions_json,
    load_utility_bills_csv,
)


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _bool_setting(job: Mapping[str, Any], key: str, *, context: str) -> bool:
    value = job.get(key, False)
    if type(value) is not bool:
        raise ValueError(f"{context}.{key} must be boolean")
    return value


def _jobs(section: Any, *, name: str) -> tuple[Mapping[str, Any], ...]:
    if section is None:
        return ()
    if isinstance(section, Mapping):
        return (section,)
    if isinstance(section, list) and all(isinstance(item, Mapping) for item in section):
        return tuple(section)
    raise ValueError(f"{name} must be an object or list of objects")


def _resolve(base_dir: Path, value: Any, *, name: str) -> Path:
    raw = Path(_required_text(name, value))
    return raw if raw.is_absolute() else base_dir / raw


@dataclass(frozen=True)
class Scan360RunResult:
    client_id: str
    added_finding_ids: tuple[str, ...]
    state_head_hash: str | None
    exceptions: tuple[dict[str, Any], ...]
    report: RecoveryScan360Report
    cloud_signals: tuple[CloudSignal, ...] = ()
    cloud_savings: CloudSavingsReport | None = None
    remediation_plan: CloudRemediationPlan | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "added_finding_ids": list(self.added_finding_ids),
            "state_head_hash": self.state_head_hash,
            "exceptions": [dict(item) for item in self.exceptions],
            "report": self.report.as_dict(),
            "cloud_signals": [signal.as_dict() for signal in self.cloud_signals],
            "financial_surfaces": {
                "recovery": self.report.as_dict(),
                "savings": (
                    self.cloud_savings.as_dict()
                    if self.cloud_savings is not None
                    else build_cloud_savings_report(self.cloud_signals).as_dict()
                ),
            },
            "remediation_plan": (
                self.remediation_plan.as_dict()
                if self.remediation_plan is not None
                else None
            ),
        }


def run_scan360_config(
    config: Mapping[str, Any],
    *,
    state_path: str | Path,
    base_dir: str | Path = ".",
) -> Scan360RunResult:
    """Run configured recovery branch scans into one durable client ledger.

    This function performs detection only. It never approves, authorizes, claims,
    contacts counterparties, or marks money recovered.
    """
    if not isinstance(config, Mapping):
        raise ValueError("config must be an object")
    client_id = _required_text("client_id", config.get("client_id"))
    currency = _required_text("currency", config.get("currency", "USD")).upper()
    cloud_pricing_modes = [
        name
        for name in ("cloud", "cloud_discount", "cloud_commitment")
        if config.get(name)
    ]
    if len(cloud_pricing_modes) > 1:
        raise ValueError(
            "Scan 360 accepts only one cloud recovery pricing mode per run; "
            "received " + ", ".join(cloud_pricing_modes)
        )
    base = Path(base_dir)

    store = LocalBundleStore(state_path)
    ledger = store.load()
    loaded_head = ledger.journal.head_hash if ledger is not None else None
    if ledger is None:
        ledger = DurableRecoveryLedger()

    before_ids = {record.finding.finding_id for record in ledger.records()}
    added_ids: list[str] = []
    exceptions: list[dict[str, Any]] = []
    cloud_signal_index: dict[str, CloudSignal] = {}
    engine = RecoveryEngine()

    def add_cloud_signals(signals: tuple[CloudSignal, ...]) -> None:
        for signal in signals:
            previous = cloud_signal_index.get(signal.signal_id)
            if previous is not None and previous.proof_hash != signal.proof_hash:
                raise ValueError(f"conflicting cloud signal_id: {signal.signal_id}")
            cloud_signal_index[signal.signal_id] = signal

    def add_cloud_finding(finding) -> None:
        for record in ledger.records():
            prior = record.finding
            if (
                prior.client_id == finding.client_id
                and prior.branch.value == "cloud"
                and prior.reference == finding.reference
                and prior.finding_id != finding.finding_id
            ):
                raise ValueError(
                    "cloud charge reference already has a different RecoveryOS "
                    f"finding: {finding.reference}; explicit supersession is required"
                )
        ledger.add(finding)

    for job_index, job in enumerate(_jobs(config.get("freight"), name="freight")):
        truth_path = job.get("truth_manifest_json")
        bundle_path = job.get("audit_bundle_zip")
        if bool(truth_path) == bool(bundle_path):
            raise ValueError(
                f"freight[{job_index}] requires exactly one of "
                "truth_manifest_json or audit_bundle_zip"
            )
        if truth_path:
            batch = load_freight_truth_manifest(
                _resolve(
                    base,
                    truth_path,
                    name=f"freight[{job_index}].truth_manifest_json",
                )
            )
        else:
            batch = load_freight_audit_result_bundle(
                _resolve(
                    base,
                    bundle_path,
                    name=f"freight[{job_index}].audit_bundle_zip",
                )
            )
        if batch.buyer_id != client_id:
            raise ValueError(
                f"freight[{job_index}] buyer_id does not match Scan 360 client_id"
            )
        for observation in batch.observations:
            if observation.currency.upper() != currency:
                raise ValueError(
                    f"freight[{job_index}] currency does not match Scan 360 currency"
                )
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("ap"), name="ap")):
        payments_path = _resolve(
            base, job.get("payments_csv"), name=f"ap[{job_index}].payments_csv"
        )
        payments = load_payments_csv(
            payments_path,
            verified=_bool_setting(job, "payment_source_verified", context=f"ap[{job_index}]"),
        )

        obligations = ()
        obligations_csv = job.get("obligations_csv")
        if obligations_csv:
            obligations_path = _resolve(
                base, obligations_csv, name=f"ap[{job_index}].obligations_csv"
            )
            obligations = load_obligations_csv(
                obligations_path,
                verified=_bool_setting(job, "obligation_source_verified", context=f"ap[{job_index}]"),
                default_effective_from=_required_text(
                    f"ap[{job_index}].default_effective_from",
                    job.get("default_effective_from"),
                ),
            )

        statements = ()
        statements_csv = job.get("vendor_statements_csv")
        if statements_csv:
            statement_path = _resolve(
                base,
                statements_csv,
                name=f"ap[{job_index}].vendor_statements_csv",
            )
            statements = load_vendor_statements_csv(
                statement_path,
                verified=_bool_setting(
                    job,
                    "vendor_statement_source_verified",
                    context=f"ap[{job_index}]",
                ),
                default_statement_date=job.get("default_statement_date"),
            )

        batch = audit_ap_recovery(
            client_id=client_id,
            payments=payments,
            obligations=obligations,
            statements=statements,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "ap",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("payer"), name="payer")):
        lines_path = _resolve(
            base, job.get("lines_csv"), name=f"payer[{job_index}].lines_csv"
        )
        rates_path = _resolve(
            base, job.get("rates_csv"), name=f"payer[{job_index}].rates_csv"
        )
        default_effective_from = _required_text(
            f"payer[{job_index}].default_effective_from",
            job.get("default_effective_from"),
        )
        lines = load_payer_lines_csv(
            lines_path,
            verified=_bool_setting(
                job, "line_source_verified", context=f"payer[{job_index}]"
            ),
        )
        rates = load_payer_rates_csv(
            rates_path,
            verified=_bool_setting(
                job, "rate_source_verified", context=f"payer[{job_index}]"
            ),
            default_effective_from=default_effective_from,
            jurisdiction=job.get("jurisdiction"),
        )
        batch = audit_payer_lines(
            client_id=client_id,
            lines=lines,
            rates=rates,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "payer",
                "job_index": job_index,
                "claim_surrogate_id": issue.claim_surrogate_id,
                "line_id": issue.line_id,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("utility"), name="utility")):
        bills_path = _resolve(
            base, job.get("bills_csv"), name=f"utility[{job_index}].bills_csv"
        )
        tariffs_path = _resolve(
            base, job.get("tariffs_json"), name=f"utility[{job_index}].tariffs_json"
        )
        utility_id = _required_text(
            f"utility[{job_index}].utility_id", job.get("utility_id")
        )
        default_effective_from = _required_text(
            f"utility[{job_index}].default_effective_from",
            job.get("default_effective_from"),
        )

        bills = load_utility_bills_csv(
            bills_path,
            verified=_bool_setting(job, "bill_source_verified", context=f"utility[{job_index}]"),
        )
        tariffs = load_simple_tariff_definitions_json(
            tariffs_path,
            utility_id=utility_id,
            verified=_bool_setting(job, "tariff_source_verified", context=f"utility[{job_index}]"),
            default_effective_from=default_effective_from,
            jurisdiction=job.get("jurisdiction"),
        )
        batch = audit_utility_bills(
            client_id=client_id,
            bills=bills,
            tariffs=tariffs,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "utility",
                "job_index": job_index,
                "bill_id": issue.bill_id,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)


    for job_index, job in enumerate(_jobs(config.get("saas"), name="saas")):
        charges = load_invoice_charges_csv(
            _resolve(base, job.get("charges_csv"), name=f"saas[{job_index}].charges_csv"),
            verified=_bool_setting(job, "charge_source_verified", context=f"saas[{job_index}]"),
        )
        rates = load_contract_rates_csv(
            _resolve(base, job.get("rates_csv"), name=f"saas[{job_index}].rates_csv"),
            verified=_bool_setting(job, "rate_source_verified", context=f"saas[{job_index}]"),
        )
        usage_csv = job.get("usage_csv")
        seat_snapshot_csv = job.get("seat_snapshot_csv")
        if usage_csv and seat_snapshot_csv:
            raise ValueError(
                f"saas[{job_index}] accepts only one of usage_csv or seat_snapshot_csv"
            )
        usage = ()
        if usage_csv:
            usage = load_usage_csv(
                _resolve(base, usage_csv, name=f"saas[{job_index}].usage_csv"),
                verified=_bool_setting(
                    job, "usage_source_verified", context=f"saas[{job_index}]"
                ),
            )
        elif seat_snapshot_csv:
            usage = load_billable_seat_snapshot_csv(
                _resolve(
                    base,
                    seat_snapshot_csv,
                    name=f"saas[{job_index}].seat_snapshot_csv",
                ),
                verified=_bool_setting(
                    job, "seat_source_verified", context=f"saas[{job_index}]"
                ),
            )

        batch = audit_saas_billing(
            client_id=client_id,
            charges=charges,
            rates=rates,
            usage=usage,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "saas",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("telecom"), name="telecom")):
        charges = load_invoice_charges_csv(
            _resolve(
                base,
                job.get("charges_csv"),
                name=f"telecom[{job_index}].charges_csv",
            ),
            verified=_bool_setting(
                job, "charge_source_verified", context=f"telecom[{job_index}]"
            ),
        )
        rates = load_contract_rates_csv(
            _resolve(base, job.get("rates_csv"), name=f"telecom[{job_index}].rates_csv"),
            verified=_bool_setting(
                job, "rate_source_verified", context=f"telecom[{job_index}]"
            ),
        )
        usage_csv = job.get("usage_csv")
        cdr_csv = job.get("cdr_csv")
        if usage_csv and cdr_csv:
            raise ValueError(
                f"telecom[{job_index}] accepts only one of usage_csv or cdr_csv"
            )
        usage = ()
        if usage_csv:
            usage = load_usage_csv(
                _resolve(base, usage_csv, name=f"telecom[{job_index}].usage_csv"),
                verified=_bool_setting(
                    job, "usage_source_verified", context=f"telecom[{job_index}]"
                ),
            )
        elif cdr_csv:
            usage = load_cdr_usage_csv(
                _resolve(base, cdr_csv, name=f"telecom[{job_index}].cdr_csv"),
                verified=_bool_setting(
                    job, "cdr_source_verified", context=f"telecom[{job_index}]"
                ),
            )

        batch = audit_telecom_billing(
            client_id=client_id,
            charges=charges,
            rates=rates,
            usage=usage,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "telecom",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)





    for job_index, job in enumerate(_jobs(config.get("cloud"), name="cloud")):
        rates = load_contract_rates_csv(
            _resolve(base, job.get("rates_csv"), name=f"cloud[{job_index}].rates_csv"),
            verified=_bool_setting(
                job, "rate_source_verified", context=f"cloud[{job_index}]"
            ),
        )

        cletrics_bundle = job.get("cletrics_bundle")
        charges_csv = job.get("charges_csv")
        if bool(cletrics_bundle) == bool(charges_csv):
            raise ValueError(
                f"cloud[{job_index}] requires exactly one of "
                "charges_csv or cletrics_bundle"
            )

        usage_csv = job.get("usage_csv")
        meter_csv = job.get("meter_csv")
        if cletrics_bundle:
            if usage_csv or meter_csv:
                raise ValueError(
                    f"cloud[{job_index}] cletrics_bundle cannot be combined with "
                    "usage_csv or meter_csv"
                )
            imported = load_cletrics_bundle(
                _resolve(
                    base,
                    cletrics_bundle,
                    name=f"cloud[{job_index}].cletrics_bundle",
                ),
                charge_source_verified=_bool_setting(
                    job,
                    "charge_source_verified",
                    context=f"cloud[{job_index}]",
                ),
                meter_source_verified=_bool_setting(
                    job,
                    "meter_source_verified",
                    context=f"cloud[{job_index}]",
                ),
            )
            if imported.client_id != client_id:
                raise ValueError(
                    f"cloud[{job_index}] Cletrics client_id does not match "
                    "Scan 360 client_id"
                )
            if imported.currency != currency:
                raise ValueError(
                    f"cloud[{job_index}] Cletrics currency does not match "
                    "Scan 360 currency"
                )
            charges = imported.charges
            usage = imported.usage
            add_cloud_signals(imported.signals)
        else:
            charges = load_invoice_charges_csv(
                _resolve(
                    base,
                    charges_csv,
                    name=f"cloud[{job_index}].charges_csv",
                ),
                verified=_bool_setting(
                    job,
                    "charge_source_verified",
                    context=f"cloud[{job_index}]",
                ),
            )
            if usage_csv and meter_csv:
                raise ValueError(
                    f"cloud[{job_index}] accepts only one of usage_csv or meter_csv"
                )
            usage = ()
            if usage_csv:
                usage = load_usage_csv(
                    _resolve(
                        base,
                        usage_csv,
                        name=f"cloud[{job_index}].usage_csv",
                    ),
                    verified=_bool_setting(
                        job,
                        "usage_source_verified",
                        context=f"cloud[{job_index}]",
                    ),
                )
            elif meter_csv:
                usage = load_cloud_meter_csv(
                    _resolve(
                        base,
                        meter_csv,
                        name=f"cloud[{job_index}].meter_csv",
                    ),
                    verified=_bool_setting(
                        job,
                        "meter_source_verified",
                        context=f"cloud[{job_index}]",
                    ),
                )

        batch = audit_cloud_billing(
            client_id=client_id,
            charges=charges,
            rates=rates,
            usage=usage,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "cloud",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            add_cloud_finding(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("cloud_discount"), name="cloud_discount")
    ):
        imported = load_cletrics_bundle(
            _resolve(
                base,
                job.get("cletrics_bundle"),
                name=f"cloud_discount[{job_index}].cletrics_bundle",
            ),
            charge_source_verified=_bool_setting(
                job,
                "charge_source_verified",
                context=f"cloud_discount[{job_index}]",
            ),
            meter_source_verified=_bool_setting(
                job,
                "meter_source_verified",
                context=f"cloud_discount[{job_index}]",
            ),
        )
        if imported.client_id != client_id or imported.currency != currency:
            raise ValueError(
                f"cloud_discount[{job_index}] Cletrics scope does not match Scan 360"
            )
        add_cloud_signals(imported.signals)
        rates = load_contract_rates_csv(
            _resolve(
                base,
                job.get("rates_csv"),
                name=f"cloud_discount[{job_index}].rates_csv",
            ),
            verified=_bool_setting(
                job,
                "rate_source_verified",
                context=f"cloud_discount[{job_index}]",
            ),
        )
        discounts = load_cloud_discount_authorities_csv(
            _resolve(
                base,
                job.get("discounts_csv"),
                name=f"cloud_discount[{job_index}].discounts_csv",
            ),
            verified=_bool_setting(
                job,
                "discount_source_verified",
                context=f"cloud_discount[{job_index}]",
            ),
        )
        batch = audit_cloud_discount_billing(
            client_id=client_id,
            charges=imported.charges,
            rates=rates,
            discounts=discounts,
            usage=imported.usage,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "cloud",
                "mode": "discount",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            add_cloud_finding(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("cloud_commitment"), name="cloud_commitment")
    ):
        imported = load_cletrics_bundle(
            _resolve(
                base,
                job.get("cletrics_bundle"),
                name=f"cloud_commitment[{job_index}].cletrics_bundle",
            ),
            charge_source_verified=_bool_setting(
                job,
                "charge_source_verified",
                context=f"cloud_commitment[{job_index}]",
            ),
            meter_source_verified=_bool_setting(
                job,
                "meter_source_verified",
                context=f"cloud_commitment[{job_index}]",
            ),
        )
        if imported.client_id != client_id or imported.currency != currency:
            raise ValueError(
                f"cloud_commitment[{job_index}] Cletrics scope does not match Scan 360"
            )
        add_cloud_signals(imported.signals)
        rates = load_contract_rates_csv(
            _resolve(
                base,
                job.get("rates_csv"),
                name=f"cloud_commitment[{job_index}].rates_csv",
            ),
            verified=_bool_setting(
                job,
                "rate_source_verified",
                context=f"cloud_commitment[{job_index}]",
            ),
        )
        commitments = load_cloud_commitment_authorities_csv(
            _resolve(
                base,
                job.get("commitments_csv"),
                name=f"cloud_commitment[{job_index}].commitments_csv",
            ),
            verified=_bool_setting(
                job,
                "commitment_source_verified",
                context=f"cloud_commitment[{job_index}]",
            ),
        )
        allocations = load_cloud_commitment_allocations_csv(
            _resolve(
                base,
                job.get("allocations_csv"),
                name=f"cloud_commitment[{job_index}].allocations_csv",
            ),
            verified=_bool_setting(
                job,
                "allocation_source_verified",
                context=f"cloud_commitment[{job_index}]",
            ),
        )
        batch = audit_cloud_commitment_billing(
            client_id=client_id,
            charges=imported.charges,
            rates=rates,
            commitments=commitments,
            allocations=allocations,
            usage=imported.usage,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "cloud",
                "mode": "commitment",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            add_cloud_finding(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("merchant_fee"), name="merchant_fee")
    ):
        statements = load_merchant_fee_statements_csv(
            _resolve(
                base,
                job.get("statements_csv"),
                name=f"merchant_fee[{job_index}].statements_csv",
            ),
            verified=_bool_setting(
                job,
                "statement_source_verified",
                context=f"merchant_fee[{job_index}]",
            ),
        )
        agreements = load_merchant_fee_agreements_csv(
            _resolve(
                base,
                job.get("agreements_csv"),
                name=f"merchant_fee[{job_index}].agreements_csv",
            ),
            verified=_bool_setting(
                job,
                "agreement_source_verified",
                context=f"merchant_fee[{job_index}]",
            ),
        )
        transaction_summaries = ()
        transaction_csv = job.get("transactions_csv")
        if transaction_csv:
            transaction_summaries = load_merchant_transaction_summaries_csv(
                _resolve(
                    base,
                    transaction_csv,
                    name=f"merchant_fee[{job_index}].transactions_csv",
                ),
                verified=_bool_setting(
                    job,
                    "transaction_source_verified",
                    context=f"merchant_fee[{job_index}]",
                ),
            )
        batch = audit_merchant_fees(
            client_id=client_id,
            statements=statements,
            agreements=agreements,
            transaction_summaries=transaction_summaries,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "merchant_fee",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)


    for job_index, job in enumerate(_jobs(config.get("parcel"), name="parcel")):
        charges = load_parcel_charges_csv(
            _resolve(
                base,
                job.get("charges_csv"),
                name=f"parcel[{job_index}].charges_csv",
            ),
            verified=_bool_setting(
                job, "charge_source_verified", context=f"parcel[{job_index}]"
            ),
        )
        assessments = load_parcel_assessments_csv(
            _resolve(
                base,
                job.get("assessments_csv"),
                name=f"parcel[{job_index}].assessments_csv",
            ),
            verified=_bool_setting(
                job, "assessment_source_verified", context=f"parcel[{job_index}]"
            ),
        )
        batch = audit_parcel_charges(
            client_id=client_id,
            charges=charges,
            assessments=assessments,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "parcel",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("procurement"), name="procurement")
    ):
        invoice_lines = load_procurement_invoice_lines_csv(
            _resolve(
                base,
                job.get("invoice_lines_csv"),
                name=f"procurement[{job_index}].invoice_lines_csv",
            ),
            verified=_bool_setting(
                job, "invoice_source_verified", context=f"procurement[{job_index}]"
            ),
        )
        authorities = load_procurement_authorities_csv(
            _resolve(
                base,
                job.get("authorities_csv"),
                name=f"procurement[{job_index}].authorities_csv",
            ),
            verified=_bool_setting(
                job, "authority_source_verified", context=f"procurement[{job_index}]"
            ),
        )
        quantities = load_procurement_quantities_csv(
            _resolve(
                base,
                job.get("quantities_csv"),
                name=f"procurement[{job_index}].quantities_csv",
            ),
            verified=_bool_setting(
                job, "quantity_source_verified", context=f"procurement[{job_index}]"
            ),
        )
        batch = audit_procurement_lines(
            client_id=client_id,
            invoice_lines=invoice_lines,
            authorities=authorities,
            quantity_approvals=quantities,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "procurement",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("warranty_credit"), name="warranty_credit")
    ):
        entitlements = load_warranty_credit_entitlements_csv(
            _resolve(
                base,
                job.get("entitlements_csv"),
                name=f"warranty_credit[{job_index}].entitlements_csv",
            ),
            verified=_bool_setting(
                job,
                "entitlement_source_verified",
                context=f"warranty_credit[{job_index}]",
            ),
        )
        settlements = load_warranty_credit_settlements_csv(
            _resolve(
                base,
                job.get("settlements_csv"),
                name=f"warranty_credit[{job_index}].settlements_csv",
            ),
            verified=_bool_setting(
                job,
                "settlement_source_verified",
                context=f"warranty_credit[{job_index}]",
            ),
        )
        batch = audit_warranty_credits(
            client_id=client_id,
            entitlements=entitlements,
            settlements=settlements,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "warranty_credit",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(
        _jobs(config.get("payroll_benefit"), name="payroll_benefit")
    ):
        charges = load_invoice_charges_csv(
            _resolve(
                base,
                job.get("charges_csv"),
                name=f"payroll_benefit[{job_index}].charges_csv",
            ),
            verified=_bool_setting(
                job,
                "charge_source_verified",
                context=f"payroll_benefit[{job_index}]",
            ),
        )
        rates = load_contract_rates_csv(
            _resolve(
                base,
                job.get("rates_csv"),
                name=f"payroll_benefit[{job_index}].rates_csv",
            ),
            verified=_bool_setting(
                job,
                "rate_source_verified",
                context=f"payroll_benefit[{job_index}]",
            ),
        )
        units = ()
        units_csv = job.get("units_csv")
        if units_csv:
            units = load_payroll_benefit_units_csv(
                _resolve(
                    base,
                    units_csv,
                    name=f"payroll_benefit[{job_index}].units_csv",
                ),
                verified=_bool_setting(
                    job,
                    "unit_source_verified",
                    context=f"payroll_benefit[{job_index}]",
                ),
            )
        batch = audit_payroll_benefit_billing(
            client_id=client_id,
            charges=charges,
            rates=rates,
            units=units,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "payroll_benefit",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("lease"), name="lease")):
        charges = load_invoice_charges_csv(
            _resolve(base, job.get("charges_csv"), name=f"lease[{job_index}].charges_csv"),
            verified=_bool_setting(
                job, "charge_source_verified", context=f"lease[{job_index}]"
            ),
        )
        rates = load_contract_rates_csv(
            _resolve(base, job.get("rates_csv"), name=f"lease[{job_index}].rates_csv"),
            verified=_bool_setting(
                job, "rate_source_verified", context=f"lease[{job_index}]"
            ),
        )
        usage_csv = job.get("usage_csv")
        area_csv = job.get("area_csv")
        if usage_csv and area_csv:
            raise ValueError(
                f"lease[{job_index}] accepts only one of usage_csv or area_csv"
            )
        quantity = ()
        if usage_csv:
            quantity = load_usage_csv(
                _resolve(base, usage_csv, name=f"lease[{job_index}].usage_csv"),
                verified=_bool_setting(
                    job, "usage_source_verified", context=f"lease[{job_index}]"
                ),
            )
        elif area_csv:
            quantity = load_lease_area_csv(
                _resolve(base, area_csv, name=f"lease[{job_index}].area_csv"),
                verified=_bool_setting(
                    job, "area_source_verified", context=f"lease[{job_index}]"
                ),
            )

        batch = audit_lease_billing(
            client_id=client_id,
            charges=charges,
            rates=rates,
            area=quantity,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "lease",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)


    for job_index, job in enumerate(
        _jobs(config.get("construction"), name="construction")
    ):
        entitlements = load_construction_entitlements_csv(
            _resolve(
                base,
                job.get("entitlements_csv"),
                name=f"construction[{job_index}].entitlements_csv",
            ),
            verified=_bool_setting(
                job,
                "entitlement_source_verified",
                context=f"construction[{job_index}]",
            ),
        )
        mismatched_claimants = sorted({
            entitlement.claimant_id
            for entitlement in entitlements
            if entitlement.claimant_id != client_id
        })
        if mismatched_claimants:
            raise ValueError(
                f"construction[{job_index}] Claimant_ID does not match "
                "Scan 360 client_id: " + ", ".join(mismatched_claimants)
            )

        events = load_construction_events_csv(
            _resolve(
                base,
                job.get("events_csv"),
                name=f"construction[{job_index}].events_csv",
            ),
            verified=_bool_setting(
                job,
                "event_source_verified",
                context=f"construction[{job_index}]",
            ),
        )
        mappings = load_event_activity_mappings_csv(
            _resolve(
                base,
                job.get("mappings_csv"),
                name=f"construction[{job_index}].mappings_csv",
            ),
            verified=_bool_setting(
                job,
                "mapping_source_verified",
                context=f"construction[{job_index}]",
            ),
        )
        schedules = load_schedule_versions_json(
            _resolve(
                base,
                job.get("schedules_json"),
                name=f"construction[{job_index}].schedules_json",
            ),
            verified=_bool_setting(
                job,
                "schedule_source_verified",
                context=f"construction[{job_index}]",
            ),
        )
        causation_reviews = load_causation_reviews_csv(
            _resolve(
                base,
                job.get("causation_reviews_csv"),
                name=f"construction[{job_index}].causation_reviews_csv",
            ),
            verified=_bool_setting(
                job,
                "causation_source_verified",
                context=f"construction[{job_index}]",
            ),
        )
        settlements = load_construction_settlements_csv(
            _resolve(
                base,
                job.get("settlements_csv"),
                name=f"construction[{job_index}].settlements_csv",
            ),
            verified=_bool_setting(
                job,
                "settlement_source_verified",
                context=f"construction[{job_index}]",
            ),
        )

        batch = audit_construction_recovery(
            client_id=client_id,
            entitlements=entitlements,
            events=events,
            mappings=mappings,
            schedules=schedules,
            causation_reviews=causation_reviews,
            settlements=settlements,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "construction",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if (
                finding.finding_id not in before_ids
                and finding.finding_id not in added_ids
            ):
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("duty"), name="duty")):
        entries = load_duty_entries_csv(
            _resolve(
                base,
                job.get("entries_csv"),
                name=f"duty[{job_index}].entries_csv",
            ),
            verified=_bool_setting(
                job, "entry_source_verified", context=f"duty[{job_index}]"
            ),
        )
        assessments = load_duty_assessments_csv(
            _resolve(
                base,
                job.get("assessments_csv"),
                name=f"duty[{job_index}].assessments_csv",
            ),
            verified=_bool_setting(
                job, "assessment_source_verified", context=f"duty[{job_index}]"
            ),
        )
        mismatched_importers = sorted({
            entry.importer_id for entry in entries if entry.importer_id != client_id
        })
        if mismatched_importers:
            raise ValueError(
                f"duty[{job_index}] Importer_ID does not match Scan 360 client_id: "
                + ", ".join(mismatched_importers)
            )
        batch = audit_duty_entries(
            client_id=client_id,
            entries=entries,
            assessments=assessments,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "duty",
                "job_index": job_index,
                "entry_line_id": issue.entry_line_id,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    for job_index, job in enumerate(_jobs(config.get("rebate"), name="rebate")):
        programs = load_rebate_programs_json(
            _resolve(
                base,
                job.get("programs_json"),
                name=f"rebate[{job_index}].programs_json",
            ),
            verified=_bool_setting(
                job, "program_source_verified", context=f"rebate[{job_index}]"
            ),
        )
        purchases = load_rebate_purchases_csv(
            _resolve(
                base,
                job.get("purchases_csv"),
                name=f"rebate[{job_index}].purchases_csv",
            ),
            verified=_bool_setting(
                job, "purchase_source_verified", context=f"rebate[{job_index}]"
            ),
        )
        settlements = load_rebate_settlements_csv(
            _resolve(
                base,
                job.get("settlements_csv"),
                name=f"rebate[{job_index}].settlements_csv",
            ),
            verified=_bool_setting(
                job, "settlement_source_verified", context=f"rebate[{job_index}]"
            ),
        )
        batch = audit_rebates(
            client_id=client_id,
            programs=programs,
            purchases=purchases,
            settlements=settlements,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "rebate",
                "job_index": job_index,
                "reference": issue.reference,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)


    for job_index, job in enumerate(_jobs(config.get("tax"), name="tax")):
        lines = load_tax_lines_csv(
            _resolve(
                base,
                job.get("lines_csv"),
                name=f"tax[{job_index}].lines_csv",
            ),
            verified=_bool_setting(
                job, "line_source_verified", context=f"tax[{job_index}]"
            ),
        )
        assessments = load_tax_assessments_csv(
            _resolve(
                base,
                job.get("assessments_csv"),
                name=f"tax[{job_index}].assessments_csv",
            ),
            verified=_bool_setting(
                job, "assessment_source_verified", context=f"tax[{job_index}]"
            ),
        )

        mismatched_purchasers = sorted({
            line.purchaser_id for line in lines if line.purchaser_id != client_id
        })
        if mismatched_purchasers:
            raise ValueError(
                f"tax[{job_index}] Purchaser_ID does not match Scan 360 client_id: "
                + ", ".join(mismatched_purchasers)
            )

        batch = audit_tax_lines(
            client_id=client_id,
            lines=lines,
            assessments=assessments,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "tax",
                "job_index": job_index,
                "tax_line_id": issue.tax_line_id,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)


    for job_index, job in enumerate(_jobs(config.get("insurance"), name="insurance")):
        claim_lines = load_insurance_claim_lines_csv(
            _resolve(
                base,
                job.get("claim_lines_csv"),
                name=f"insurance[{job_index}].claim_lines_csv",
            ),
            verified=_bool_setting(
                job, "claim_source_verified", context=f"insurance[{job_index}]"
            ),
        )
        assessments = load_insurance_assessments_csv(
            _resolve(
                base,
                job.get("assessments_csv"),
                name=f"insurance[{job_index}].assessments_csv",
            ),
            verified=_bool_setting(
                job, "assessment_source_verified", context=f"insurance[{job_index}]"
            ),
        )
        settlements = load_insurance_settlements_csv(
            _resolve(
                base,
                job.get("settlements_csv"),
                name=f"insurance[{job_index}].settlements_csv",
            ),
            verified=_bool_setting(
                job, "settlement_source_verified", context=f"insurance[{job_index}]"
            ),
        )

        mismatched_claimants = sorted({
            line.claimant_id for line in claim_lines if line.claimant_id != client_id
        })
        if mismatched_claimants:
            raise ValueError(
                f"insurance[{job_index}] Claimant_ID does not match Scan 360 client_id: "
                + ", ".join(mismatched_claimants)
            )

        batch = audit_insurance_claims(
            client_id=client_id,
            claim_lines=claim_lines,
            assessments=assessments,
            settlements=settlements,
            currency=currency,
        )
        for issue in batch.exceptions:
            exceptions.append({
                "branch": "insurance",
                "job_index": job_index,
                "claim_line_id": issue.claim_line_id,
                "code": issue.code,
                "detail": issue.detail,
            })
        for observation in batch.observations:
            finding = engine.evaluate(observation)
            if finding is None:
                continue
            ledger.add(finding)
            if finding.finding_id not in before_ids and finding.finding_id not in added_ids:
                added_ids.append(finding.finding_id)

    final_cloud_signals = tuple(
        cloud_signal_index[key] for key in sorted(cloud_signal_index)
    )
    cloud_savings = build_cloud_savings_report(final_cloud_signals)
    remediation_plan = None
    remediation_cfg = config.get("cloud_remediation")
    if remediation_cfg is not None:
        if not isinstance(remediation_cfg, Mapping):
            raise ValueError("cloud_remediation must be an object")
        enabled = remediation_cfg.get("enabled", False)
        execute = remediation_cfg.get("execute", False)
        if type(enabled) is not bool:
            raise ValueError("cloud_remediation.enabled must be boolean")
        if type(execute) is not bool:
            raise ValueError("cloud_remediation.execute must be boolean")
        if execute:
            raise ValueError(
                "RecoveryOS remediation integration is plan-only; execution is unsupported"
            )
        if enabled:
            remediation_plan = build_cloud_remediation_plan(final_cloud_signals)

    head = store.save(
        ledger,
        expected_head_hash=loaded_head,
        enforce_expected=True,
    )
    report = build_scan360_report(ledger, client_id)
    return Scan360RunResult(
        client_id=client_id,
        added_finding_ids=tuple(sorted(added_ids)),
        state_head_hash=head,
        exceptions=tuple(exceptions),
        report=report,
        cloud_signals=final_cloud_signals,
        cloud_savings=cloud_savings,
        remediation_plan=remediation_plan,
    )