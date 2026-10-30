"""Golden Goose #028: strict offer-data / hypothetical unit-economics gate.

Research-only. No sales, buyer demand, or proof-of-recovery is inferred.
Uses the Python standard library; does not access the network or customer data.
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json

ALLOWED_BASIS = {"usage_based", "license_dependent_unknown", "per_month", "one_time", "starting_at_one_time"}
EVIDENCE = {"vendor_price_list_only", "vendor_documentation_only"}


def dollars(value):
    if not isinstance(value, str):
        raise ValueError("Amounts must be decimal strings; float/bool/number is not allowed")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Money must be finite, nonnegative, and have no sub-cent precision")
    return amount


def hours(value):
    if not isinstance(value, str):
        raise ValueError("Hours must be explicit decimal strings")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid hours") from exc
    if not amount.is_finite() or amount < 0 or amount > 10000:
        raise ValueError("Hours outside permissible model")
    return amount


def audit_data(data):
    if data.get("id") != "golden-goose-028-restore-proof-competitive-falsifier":
        raise ValueError("Unknown research dataset")
    if data.get("snapshot_date") != "2026-10-29":
        raise ValueError("Unknown observation date")
    offers = data.get("offers")
    if not isinstance(offers, list) or not offers:
        raise ValueError("Missing offers")
    names = set()
    for offer in offers:
        name, url = offer.get("name"), offer.get("url")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("Missing/duplicate competitor")
        names.add(name)
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("First-party source URL required")
        if offer.get("price_basis") not in ALLOWED_BASIS:
            raise ValueError("Unknown price basis")
        if offer.get("value_evidence") not in EVIDENCE:
            raise ValueError("Competitor offer is NOT verified paid demand")
        if offer.get("independently_verified_customers") is not None:
            raise ValueError("No verified competitor purchase evidence collected")
        price = offer.get("advertised_price_usd")
        if price is None:
            if offer["price_basis"] not in {"usage_based", "license_dependent_unknown"}:
                raise ValueError("Missing price for stated fixed/monthly basis")
        else:
            dollars(price)
            if offer["price_basis"] in {"usage_based", "license_dependent_unknown"}:
                raise ValueError("Can't assume an unknown usage/licensing price is a flat fee")
            if offer.get("price_url") is None or not offer["price_url"].startswith("https://"):
                raise ValueError("Price requires vendor source")
    own = data.get("hypothetical_own_offer", {})
    if own.get("real_customer_count") != 0 or own.get("authorized_real_customer_backups") != 0:
        raise ValueError("This frozen no-customer experiment cannot claim customers")
    if dollars(own.get("gross_revenue_received_usd")) != 0 or dollars(own.get("verified_collectible_usd")) != 0:
        raise ValueError("Quoted competitor prices or synthetic estimates are not owner revenue")
    fee = dollars(own.get("fee_usd"))
    fixed = dollars(own.get("overhead_usd"))
    rate = dollars(own.get("reviewer_hourly_cost_usd"))
    review_hours = own.get("assumed_review_hours")
    if not isinstance(review_hours, list) or not review_hours:
        raise ValueError("No sensitivity scenarios")
    rows = []
    for h in review_hours:
        hrs = hours(h)
        contribution = fee - fixed - rate * hrs
        rows.append({"assumed_hours": h, "modeled_contribution_usd": str(contribution.quantize(Decimal('0.01')))})
    return {
        "competitor_offers_source_checked": len(offers),
        "observed_paid_buyers": None,
        "verified_owner_revenue_usd": "0.00",
        "verified_collectible_usd": "0.00",
        "gross_hypothetical_fee_usd": str(fee),
        "break_even_hours": str(((fee-fixed)/rate).quantize(Decimal('0.0001'))) if rate > 0 else None,
        "modeled_contributions": rows,
        "decision": "GENERIC_RESTORE_PROOF_NO_GO; INDEPENDENT_CROSS_PROVIDER_AUDIT_WATCH_ONLY",
        "demand_status": "NOT_TESTED"
    }


def main():
    path = Path(__file__).with_name("restore_competition_2026-10-29.json")
    print(json.dumps(audit_data(json.loads(path.read_text(encoding="utf-8"))), indent=2))


if __name__ == "__main__":
    main()
