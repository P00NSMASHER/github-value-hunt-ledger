"""Deterministic source generator for 100 structurally DIFFERENT fictional freight buyers.

Every original customer, source, remittance and term is invented. No real
carrier, identity, negotiated pricing, bank clearance, or legal authorization.
Quoted carriage modes are dataset metadata; charge-level CSV audit is NOT
a verified six-mode production rating test.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import csv
import io
import json
import random

SEED = 20261022
SOURCE_SCHEMA = "retally-diverse-100-freight-source-v2"
PERSONAS = (
    "rural-hospital-network", "medical-supplies-importer", "pharma-cold-chain",
    "agricultural-cooperative", "small-family-retailer", "government-contractor",
    "refrigerated-food-producer", "oil-field-maintenance", "automotive-assembly",
    "industrial-distributor", "retail-returns-3PL", "electronics-recycler",
    "port-import-forwarder", "specialty-building-products", "university-system",
    "school-food-service", "disaster-relief-logistics", "renewable-energy-service",
    "printed-packaging-exporter", "marine-parts-warehouse", "apparel-wholesaler",
    "pet-food-distributor", "aerospace-components", "hospitality-equipment",
    "telecom-field-service",
)
CASE_STRESSORS = (
    "carrier-insolvency-and-appeal", "wrong-payee-credit", "partial-credit-split",
    "tariff-supersession-conflict", "repeated-remittance-reference",
    "invoice-sent-after-service-dispute", "bank-return-before-allocation",
    "full-credit-reversal", "buyer-demand-to-skip-review",
    "new-affiliate-payment-direction", "two-carrier-overlap",
    "misclassified-freight-accessorial", "historical-credit-and-incumbent",
    "one-invoice-many-shipment-lines", "shared-ledger-race",
    "malformed-credit-source", "customer-insists-on-guarantee",
    "regulatory-document-retention", "diluted-split-credit",
    "incorrect-currency-remittance", "fuel-surcharge-contract-ambiguity",
    "shipment-date-mismatch", "carrier-denial-and-time-bar",
    "audit-proof-hash-mismatch", "supplier-duplicate-line",
)
CURRENCIES = ("USD", "EUR", "GBP", "CAD", "AUD")
CONTEXT_MODES = ("LTL", "PARCEL", "TL", "INTERMODAL", "AIR", "OCEAN")
CHARGE_CODES = (
    "DETENTION", "LIFTGATE", "STORAGE", "REWEIGH", "REDELIVERY",
    "FUEL_SURCHARGE", "OVERSIZE", "RESIDENTIAL", "ADDRESS_CORRECTION",
    "DIM_WEIGHT", "LAYOVER", "TOLL", "CHASSIS", "DUTY_ADJUSTMENT",
    "DRAYAGE", "LUMPER", "INSIDE_DELIVERY", "CUSTOMS_REVIEW",
    "PROOF_OF_DELIVERY", "OVERNIGHT_HANDLING", "FREIGHT_CLASS",
    "LIMITED_ACCESS", "APPOINTMENT", "PICKUP_ATTEMPT",
)
CATEGORIES = ("VERIFIED", "UNVERIFIED", "MISSING", "OVERLAP", "EXPIRED", "WRONG_SCOPE")
MODELS = ("FIXED", "PER_UNIT", "INCLUDED")
INVOICE_HEADERS = (
    "invoice_id", "shipment_id", "customer_id", "carrier_id",
    "currency", "charge_id", "charge_code", "service_date",
    "quantity_units", "billed_cents",
)
RULE_HEADERS = (
    "charge_code", "pricing_model", "effective_from", "effective_to",
    "fixed_cents", "unit_rate_cents",
)


def H(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def csv_bytes(headers, rows) -> bytes:
    out = io.StringIO(newline="")
    w = csv.DictWriter(out, fieldnames=headers, lineterminator="\n")
    w.writeheader()
    for item in rows:
        w.writerow(item)
    return out.getvalue().encode("utf-8")


@dataclass(frozen=True)
class FictionalDataset:
    index: int
    buyer: str
    business_unit: str
    persona: str
    stressor: str
    carriage_mode_context: str
    invoice_count: int
    carrier_count: int
    customer_count: int
    currency_count: int
    invoice_rows: tuple[dict, ...]
    contracts: tuple[dict, ...]
    independent_charge_oracle: tuple[dict, ...]
    scenario_sha256: str


def generate(i: int) -> FictionalDataset:
    if type(i) is not int or not 0 <= i < 100:
        raise ValueError("only 100 frozen fictional datasets indexed 0..99")
    rng = random.Random(SEED*10007 + 31847*i)
    # Original study held EVERY buyer to three identical invoice rows.
    # This study intentionally uses radically different record dimensions.
    n_invoices = (1, 2, 5, 9, 15, 25, 40)[(i*3+i//7) % 7]
    n_carriers = 1 + (i // 5) % 4
    n_customers = 1 + (i // 11) % 3
    n_currencies = 1 + (i // 4) % 3
    currencies = tuple(CURRENCIES[(i//3 + j*2) % len(CURRENCIES)]
                       for j in range(n_currencies))
    buyers = tuple(f"SYN-CUSTOMER-{i:03d}-{j}" for j in range(n_customers))
    carriers = tuple(f"SYN-CARRIER-{i:03d}-{j}" for j in range(n_carriers))
    groups: dict[tuple[str,str,str], list[tuple[str,dict,str]]] = {}
    invoices = []
    oracles = []
    # Use a separate stable rate recipe per group+charge code; never infer
    # contract rate from the same invoice we are evaluating.
    rate_recipes = {}
    for n in range(n_invoices):
        customer = buyers[(n*7 + i) % n_customers]
        carrier = carriers[(n*5 + i) % n_carriers]
        currency = currencies[(n*5 + i) % n_currencies]
        key = (customer, carrier, currency)
        invoice_id = f"SYN-INV-{i:03d}-{n:03d}"
        shipment_id = f"SYN-SHIP-{i:03d}-{n:03d}-{rng.randrange(100000,999999)}"
        # The *number* of charge lines changes for every shipment.
        n_lines = 1 + rng.randrange(1, 7)
        for k in range(n_lines):
            # Each group has diverse real-ish commercial charge codes,
            # not unique invented field names.
            code = CHARGE_CODES[(i*17 + n*3 + k*7) % len(CHARGE_CODES)]
            recipe_key = (*key, code)
            if recipe_key not in rate_recipes:
                category = CATEGORIES[(i*2 + len(rate_recipes)*5 + n) % len(CATEGORIES)]
                model = MODELS[(i+n+k) % len(MODELS)]
                fixed = rng.randrange(200, 25000) if model == "FIXED" else None
                unit = rng.randrange(100, 5300) if model == "PER_UNIT" else None
                rate_recipes[recipe_key] = (category, model, fixed, unit)
            category, model, fixed, unit = rate_recipes[recipe_key]
            qty = rng.randrange(1, 18)
            expected = (fixed if model == "FIXED"
                        else qty*unit if model == "PER_UNIT" else 0)
            variation = (i + n*3 + k*5) % 6
            if variation == 0:
                billed = expected
            elif variation == 1:
                billed = max(expected - rng.randrange(0, max(expected,1)+1), 0)
            else:
                billed = expected + rng.randrange(100, 12000)
            charge_id = f"SYN-CH-{i:03d}-{n:03d}-{k:02d}"
            invoice = {
                "invoice_id": invoice_id, "shipment_id": shipment_id,
                "customer_id": customer, "carrier_id": carrier,
                "currency": currency, "charge_id": charge_id,
                "charge_code": code, "service_date": f"2026-09-{1+(n+i)%28:02d}",
                "quantity_units": str(qty), "billed_cents": str(billed),
            }
            invoices.append(invoice)
            decision = ("VALIDATED" if category == "VERIFIED" and billed > expected
                        else "CLEAR" if category == "VERIFIED"
                        else "REVIEW")
            oracles.append({
                "charge_id": charge_id, "decision": decision,
                "category": category, "pricing_model": model,
                "expected_cents": expected if category in
                ("VERIFIED", "UNVERIFIED") else None,
                "independent_expected_positive_cents": (
                    billed-expected if decision == "VALIDATED" else 0
                ),
            })
    # A customer's negotiated contract is grouped by customer, carrier,
    # currency, verification class. Two overlapping, effective verified
    # rules intentionally produce REVIEW rather than auto-selection.
    grouped: dict[tuple[str,str,str,str], list[dict]] = {}
    for (customer,carrier,currency,code), (category,model,fixed,unit) in sorted(rate_recipes.items()):
        if category == "MISSING":
            continue
        kind = "UNVERIFIED" if category == "UNVERIFIED" else (
            "WRONG_SCOPE" if category == "WRONG_SCOPE" else "VERIFIED"
        )
        key = (customer,carrier,currency,kind)
        base = {
            "charge_code": code, "pricing_model": model,
            "effective_from": "2026-09-01",
            "effective_to": "2026-08-31" if category == "EXPIRED" else "2026-09-30",
            "fixed_cents": "" if fixed is None else str(fixed),
            "unit_rate_cents": "" if unit is None else str(unit),
        }
        # Do not generate structurally invalid date windows for expired rate
        # proofs; a prior wholly expired window is still a valid contract.
        if category == "EXPIRED":
            base["effective_from"] = "2026-08-01"
        grouped.setdefault(key,[]).append(base)
        if category == "OVERLAP":
            shadow = dict(base)
            if model == "FIXED":
                shadow["fixed_cents"] = str(int(base["fixed_cents"])+37)
            elif model == "PER_UNIT":
                shadow["unit_rate_cents"] = str(int(base["unit_rate_cents"])+11)
            else:
                shadow["pricing_model"] = "FIXED"
                shadow["fixed_cents"] = "900"
            grouped[key].append(shadow)
    contracts=[]
    for n,(key,rows) in enumerate(sorted(grouped.items())):
        cust,carrier,currency,kind=key
        body=csv_bytes(RULE_HEADERS,rows)
        authority=f"SYNTHETIC-CONTROLLING-DOCUMENT-{i:03d}-{n:03d}"
        contracts.append({
            "filename": f"contract-{n:03d}.csv",
            "customer_id": cust, "carrier_id": (
                carrier + "-WRONG" if kind=="WRONG_SCOPE" else carrier
            ),
            "currency": currency, "authority_document_id": authority,
            "verified_controlling_authority": kind!="UNVERIFIED",
            "source_document_bytes": (
                f"TEST ONLY: fictional buyer contract {i}, {n}, {kind}"
            ).encode("ascii"),
            "data": body,
        })
    manifest = {
        "schema": SOURCE_SCHEMA, "buyer": f"SYN-BUYER-{i:03d}",
        "unit": f"SYN-UNIT-{i:03d}", "persona": PERSONAS[i % len(PERSONAS)],
        "stressor": CASE_STRESSORS[(i*13+i//5)%len(CASE_STRESSORS)],
        "mode_context": CONTEXT_MODES[(i+i//8)%len(CONTEXT_MODES)],
        "invoices": invoices,
        "contracts": [
            {"filename":x["filename"],"content_sha256":H(x["data"]),
             "source_sha256":H(x["source_document_bytes"]),
             "verified":x["verified_controlling_authority"],
             "scope":(x["customer_id"],x["carrier_id"],x["currency"])}
            for x in contracts
        ],
        "oracle": oracles,
    }
    return FictionalDataset(
        index=i,buyer=f"SYN-BUYER-{i:03d}",business_unit=f"SYN-UNIT-{i:03d}",
        persona=PERSONAS[i%len(PERSONAS)],
        stressor=CASE_STRESSORS[(i*13+i//5)%len(CASE_STRESSORS)],
        carriage_mode_context=CONTEXT_MODES[(i+i//8)%len(CONTEXT_MODES)],
        invoice_count=n_invoices,carrier_count=n_carriers,customer_count=n_customers,
        currency_count=n_currencies,invoice_rows=tuple(invoices),
        contracts=tuple(contracts),independent_charge_oracle=tuple(oracles),
        scenario_sha256=H(canonical(manifest)),
    )


def source_files(dataset: FictionalDataset) -> dict[str,bytes]:
    files={"invoice_charges.csv":csv_bytes(INVOICE_HEADERS,dataset.invoice_rows)}
    for rule in dataset.contracts:
        files[rule["filename"]]=rule["data"]
    files["fictional_manifest.json"] = (
        json.dumps({
            "schema": SOURCE_SCHEMA, "index": dataset.index,
            "buyer": dataset.buyer, "business_unit": dataset.business_unit,
            "persona": dataset.persona, "stressor": dataset.stressor,
            "carriage_mode_context_not_rate_authority": dataset.carriage_mode_context,
            "invoice_count": dataset.invoice_count,
            "charge_count": len(dataset.invoice_rows),
            "carrier_count": dataset.carrier_count,
            "customer_count": dataset.customer_count,
            "currency_count": dataset.currency_count,
            "contract_documents": len(dataset.contracts),
            "source_sha256": dataset.scenario_sha256,
            "real_customer_data": False,
            "authoritative_buyer_contracts": False,
            "authenticated_bank_recoveries": False,
        },sort_keys=True,indent=2)+"\n"
    ).encode("utf-8")
    return files
