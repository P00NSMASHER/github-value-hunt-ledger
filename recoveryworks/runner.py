"""Recovery Scan 360 orchestration across operational branch adapters."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .durable_ledger import DurableRecoveryLedger
from .engine import RecoveryEngine
from .report import RecoveryScan360Report, build_scan360_report
from .store import LocalBundleStore
from .branches.ap import build_ap_observations
from .branches.ap_csv import load_obligations_csv, load_payments_csv
from .branches.duty import audit_duty_entries
from .branches.duty_csv import load_duty_assessments_csv, load_duty_entries_csv
from .branches.freight_io import (
    load_freight_audit_result_bundle,
    load_freight_truth_manifest,
)
from .branches.payer import audit_payer_lines
from .branches.payer_csv import load_payer_lines_csv, load_payer_rates_csv
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "added_finding_ids": list(self.added_finding_ids),
            "state_head_hash": self.state_head_hash,
            "exceptions": [dict(item) for item in self.exceptions],
            "report": self.report.as_dict(),
        }


def run_scan360_config(
    config: Mapping[str, Any],
    *,
    state_path: str | Path,
    base_dir: str | Path = ".",
) -> Scan360RunResult:
    """Run configured freight/AP/payer/utility/duty scans into one durable client ledger.

    This function performs detection only. It never approves, authorizes, claims,
    contacts counterparties, or marks money recovered.
    """
    if not isinstance(config, Mapping):
        raise ValueError("config must be an object")
    client_id = _required_text("client_id", config.get("client_id"))
    currency = _required_text("currency", config.get("currency", "USD")).upper()
    base = Path(base_dir)

    store = LocalBundleStore(state_path)
    ledger = store.load()
    loaded_head = ledger.journal.head_hash if ledger is not None else None
    if ledger is None:
        ledger = DurableRecoveryLedger()

    before_ids = {record.finding.finding_id for record in ledger.records()}
    added_ids: list[str] = []
    exceptions: list[dict[str, Any]] = []
    engine = RecoveryEngine()

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

        observations = build_ap_observations(
            client_id=client_id,
            payments=payments,
            obligations=obligations,
            currency=currency,
        )
        for observation in observations:
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

    for job_index, job in enumerate(_jobs(config.get("duty"), name="duty")):
        entries_path = _resolve(
            base, job.get("entries_csv"), name=f"duty[{job_index}].entries_csv"
        )
        assessments_path = _resolve(
            base,
            job.get("assessments_csv"),
            name=f"duty[{job_index}].assessments_csv",
        )
        entries = load_duty_entries_csv(
            entries_path,
            verified=_bool_setting(
                job, "entry_source_verified", context=f"duty[{job_index}]"
            ),
        )
        assessments = load_duty_assessments_csv(
            assessments_path,
            verified=_bool_setting(
                job, "assessment_source_verified", context=f"duty[{job_index}]"
            ),
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
    )
