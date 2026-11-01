"""Fail-closed semantic checks for self-hashed engagement artifacts.

Use after checking each document hash and its basic state/type fields.
A digest binds provided metadata, but cannot prove real buyer approval,
signed terms, authentication, or that all historical amendments were supplied.
"""
from __future__ import annotations

from datetime import date
import math
import re

from freight.pilot_amendment import MATERIAL_SCOPE_FIELDS, ROLE_FIELDS, _price_band

_SHA = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_FIELDS = tuple(sorted(MATERIAL_SCOPE_FIELDS | ROLE_FIELDS | {"fixed_fee_usd"}))


def _text(document: dict, name: str) -> None:
    value = document.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Charter " + name + " is required")


def _charter_fields(charter: dict) -> None:
    """Check fields omitted by the resolver's legacy hash/state guard."""
    for name in (
        "activation_hash", "launch_route", "selected_offer", "price_band_usd",
        "population_rule", "buyer_truth_owner_role", "buyer_action_approver_role",
        "freight_engagement_owner_role",
    ):
        _text(charter, name)
    if _SHA.fullmatch(charter["activation_hash"]) is None:
        raise ValueError("Charter activation_hash must be lowercase SHA-256")
    if charter.get("launch_status") not in {"READY", "BLOCKED", "CONDITIONAL"}:
        raise ValueError("Charter launch_status is invalid")
    fee = charter.get("fixed_fee_usd")
    if type(fee) not in (int, float) or not math.isfinite(fee) or fee <= 0:
        raise ValueError("Charter fixed_fee_usd must be positive finite money")
    for name in ("carrier_scope", "mode_scope"):
        values = charter.get(name)
        if type(values) not in (list, tuple) or not values or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError("Charter " + name + " must contain valid entries")
    parsed_dates = {}
    for name in ("source_date_start", "source_date_end"):
        value = charter.get(name)
        if not isinstance(value, str) or _DATE.fullmatch(value) is None:
            raise ValueError("Charter " + name + " must be an ISO date")
        try:
            parsed_dates[name] = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Charter " + name + " must be an ISO date") from exc
    if parsed_dates["source_date_start"] > parsed_dates["source_date_end"]:
        raise ValueError("Charter source_date_start must not follow source_date_end")


def _same_field(a: dict, b: dict, name: str) -> bool:
    """JSON arrays and Python tuples represent the same canonical scope."""
    one, two = a.get(name), b.get(name)
    if isinstance(one, (tuple, list)) and isinstance(two, (tuple, list)):
        return list(one) == list(two)
    return one == two


def _require_flag(amendment: dict, field: str, expected: bool) -> None:
    if amendment[field] is not expected:
        raise ValueError("Amendment " + field + " contradicts approved changes")


def validate_resolution_inputs(
    base_charter: dict,
    amendments: list[dict] | tuple[dict, ...],
    replacement_charters: list[dict] | tuple[dict, ...],
) -> None:
    """Reconcile amendment metadata with the actual supplied Charter versions.

    All artifact hashes have been checked by the caller; no side effects occur.
    The supplied document set is NOT an authenticated source of completeness.
    """
    charters = [base_charter, *replacement_charters]
    for charter in charters:
        _charter_fields(charter)
    by_hash = {charter["charter_hash"]: charter for charter in charters}
    amendment_ids: set[str] = set()
    for amendment in amendments:
        base = by_hash.get(amendment["base_charter_hash"])
        if base is None:
            raise ValueError("Amendment references unknown base Charter")
        if amendment["amendment_id"] in amendment_ids:
            raise ValueError("duplicate Amendment amendment_id")
        amendment_ids.add(amendment["amendment_id"])
        changed = amendment.get("changed_fields")
        if (type(changed) not in (list, tuple) or not changed
                or any(type(name) is not str or name not in _FIELDS for name in changed)
                or len(changed) != len(set(changed))
                or tuple(changed) != tuple(sorted(changed))):
            raise ValueError("Amendment changed_fields must be unique, sorted approved fields")

        material = bool(MATERIAL_SCOPE_FIELDS.intersection(changed))
        role = bool(ROLE_FIELDS.intersection(changed))
        fee_changed = "fixed_fee_usd" in changed
        _require_flag(amendment, "requires_readiness_revalidation", material)
        _require_flag(amendment, "requires_launch_revalidation", material)
        _require_flag(amendment, "requires_reacknowledgment", material or role or fee_changed)

        state = amendment["amendment_state"]
        if state == "PENDING_ACKNOWLEDGMENT":
            _require_flag(amendment, "kickoff_suspended", False)
            _require_flag(amendment, "customer_data_authorized", False)
        elif state == "ACCEPTED_REPLACEMENT_REQUIRED":
            _require_flag(amendment, "kickoff_suspended", True)
            _require_flag(amendment, "customer_data_authorized", False)
        elif state == "SUPERSEDED_BY_REPLACEMENT":
            replacement = by_hash.get(amendment["replacement_charter_hash"])
            if replacement is None:
                # Preserve the existing resolver's named dangling-reference error.
                raise ValueError("replacement Charter hash is not supplied")
            expected_changed = tuple(
                name for name in _FIELDS if not _same_field(base, replacement, name)
            )
            if tuple(changed) != expected_changed:
                raise ValueError("Amendment changed_fields mismatch: replacement changed unapproved fields")
            _require_flag(amendment, "customer_data_authorized",
                          replacement["customer_data_authorized"] is True)
            _require_flag(amendment, "kickoff_suspended",
                          replacement["customer_data_authorized"] is not True)
            band = _price_band(base["price_band_usd"])
            out_of_band = bool(
                fee_changed and band is not None
                and not band[0] <= replacement["fixed_fee_usd"] <= band[1]
            )
            required_activation = material or out_of_band
            _require_flag(amendment, "requires_new_activation", required_activation)
            if required_activation and replacement["activation_hash"] == base["activation_hash"]:
                raise ValueError("Amendment requires a new Activation Packet activation_hash")
            if out_of_band and replacement["price_band_usd"] == base["price_band_usd"]:
                raise ValueError("Amendment out-of-band fee requires new published price band")
        else:
            raise ValueError("invalid Amendment state")

        # In a not-yet-superseded amendment, the proposed new fee amount was
        # deliberately not serialized, so out-of-band status cannot be recomputed.
        if state != "SUPERSEDED_BY_REPLACEMENT":
            if material:
                _require_flag(amendment, "requires_new_activation", True)
            elif not fee_changed:
                _require_flag(amendment, "requires_new_activation", False)
