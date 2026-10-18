"""Contract-defined parcel rating; no carrier rates or policies are inferred."""
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
from .parcel import ParcelCharge, ParcelExpectedAssessment, normalize_service, normalize_zone
from ..models import canonical_hash, normalize_sha256


def decimal(value, *, positive=False):
    try:
        result=Decimal(str(value))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError('finite decimal required') from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('invalid nonnegative decimal')
    return result


def cents(value):
    if type(value) is not int or value < 0:
        raise ValueError('nonnegative integer cents required')
    return value


@dataclass(frozen=True)
class ParcelMeasurements:
    shipment_id: str
    actual_weight: str
    length: str
    width: str
    height: str
    weight_unit: str
    dimension_unit: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self):
        for field in ('shipment_id','weight_unit','dimension_unit','source_locator'):
            if not isinstance(getattr(self,field),str) or not getattr(self,field).strip():
                raise ValueError(field+' required')
        for field in ('actual_weight','length','width','height'):
            decimal(getattr(self,field),positive=True)
        normalize_sha256('source_hash',self.source_hash)
        if type(self.verified) is not bool:
            raise ValueError('verified must be boolean')


@dataclass(frozen=True)
class ParcelRateBand:
    maximum_weight: str
    base_cents: int

    def __post_init__(self):
        decimal(self.maximum_weight,positive=True);cents(self.base_cents)


@dataclass(frozen=True)
class ParcelRateContract:
    contract_id: str
    carrier_id: str
    service_code: str
    zone: str
    effective_from: str
    effective_to: str
    weight_unit: str
    dimension_unit: str
    dimensional_divisor: str
    weight_increment: str
    bands: tuple[ParcelRateBand,...]
    discount_bps: int
    minimum_base_cents: int
    fuel_bps: int
    surcharge_cents: int
    fuel_on_surcharge: bool
    tax_bps: int
    source_hash: str
    source_locator: str
    reviewer_id: str
    verified: bool
    currency: str = "USD"

    def __post_init__(self):
        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("invalid contract currency")
        for field in ('contract_id','carrier_id','service_code','zone','weight_unit','dimension_unit','source_locator','reviewer_id'):
            if not isinstance(getattr(self,field),str) or not getattr(self,field).strip():
                raise ValueError(field+' required')
        if date.fromisoformat(self.effective_to)<date.fromisoformat(self.effective_from):
            raise ValueError('invalid contract interval')
        decimal(self.dimensional_divisor,positive=True);decimal(self.weight_increment,positive=True)
        if not self.bands or not all(isinstance(b,ParcelRateBand) for b in self.bands):
            raise ValueError('rate bands required')
        weights=[decimal(b.maximum_weight) for b in self.bands]
        if weights!=sorted(set(weights)):
            raise ValueError('bands must have strictly increasing upper bounds')
        for field in ('discount_bps','fuel_bps','tax_bps'):
            if type(getattr(self,field)) is not int or not 0<=getattr(self,field)<=10000:
                raise ValueError(field+' must be integer basis points in 0..10000')
        cents(self.minimum_base_cents);cents(self.surcharge_cents)
        if type(self.verified) is not bool or type(self.fuel_on_surcharge) is not bool:
            raise ValueError('verification and fuel scope must be boolean')
        normalize_sha256('source_hash',self.source_hash)


def rate_parcel(charge: ParcelCharge, measurements: ParcelMeasurements,
                contract: ParcelRateContract, *, currency="USD") -> ParcelExpectedAssessment:
    if currency != contract.currency:
        raise ValueError("contract currency mismatch")
    if measurements.shipment_id!=charge.shipment_id:
        raise ValueError('measurement shipment scope mismatch')
    if (contract.carrier_id,normalize_service(contract.service_code),normalize_zone(contract.zone)) != (
        charge.carrier_id,charge.normalized_service,charge.normalized_zone):
        raise ValueError('contract carrier/service/zone mismatch')
    if not date.fromisoformat(contract.effective_from)<=date.fromisoformat(charge.ship_date)<=date.fromisoformat(contract.effective_to):
        raise ValueError('shipment outside reviewed contract interval')
    if (measurements.weight_unit,measurements.dimension_unit)!=(contract.weight_unit,contract.dimension_unit):
        raise ValueError('unit conversion requires separate reviewed authority')
    dimensional=decimal(measurements.length)*decimal(measurements.width)*decimal(measurements.height)/decimal(contract.dimensional_divisor)
    increment=decimal(contract.weight_increment)
    weight=(max(decimal(measurements.actual_weight),dimensional)/increment).to_integral_value(rounding=ROUND_CEILING)*increment
    band=next((b for b in contract.bands if weight<=decimal(b.maximum_weight)),None)
    if band is None:
        raise ValueError('billable weight outside contracted rate table')
    def rounded(value):
        return int(value.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    base=max(contract.minimum_base_cents,rounded(Decimal(band.base_cents)*(10000-contract.discount_bps)/10000))
    fuel_basis=base+(contract.surcharge_cents if contract.fuel_on_surcharge else 0)
    fuel=rounded(Decimal(fuel_basis)*contract.fuel_bps/10000)
    subtotal=base+contract.surcharge_cents+fuel
    tax=rounded(Decimal(subtotal)*contract.tax_bps/10000)
    trace={'dimensional_weight':str(dimensional),'billable_weight':str(weight),'base_cents':base,
           'surcharge_cents':contract.surcharge_cents,'fuel_cents':fuel,'tax_cents':tax,
           'contract_hash':canonical_hash(asdict(contract)),'measurement_hash':canonical_hash(asdict(measurements)),
           'measurement_source_hash':measurements.source_hash,'measurement_source_locator':measurements.source_locator}
    # Bind both authorities. Retain the invoice weight as identity; independently rated weight is in the trace.
    digest=canonical_hash(trace)
    return ParcelExpectedAssessment(assessment_id='rated:'+digest,shipment_id=charge.shipment_id,
        carrier_id=charge.carrier_id,ship_date=charge.ship_date,service_code=charge.service_code,
        zone=charge.zone,billed_weight=charge.billed_weight,expected_total_cents=subtotal+tax,
        rate_basis='Explicit contract bands, dimensional divisor, discount, minimum, fuel scope and tax',
        source_hash=digest,source_locator=contract.source_locator,verified=contract.verified and measurements.verified,
        rate_snapshot_date=contract.effective_from,rate_reviewer_id=contract.reviewer_id,metadata=trace)


def load_rating_bundle(path, charges, *, verified=False, currency="USD"):
    """Load explicitly reviewed contracts and measurements; reject ambiguous matches."""
    import json
    from pathlib import Path
    payload=json.loads(Path(path).read_text())
    if not isinstance(payload,dict) or set(payload)!={'contracts','measurements'}:
        raise ValueError('rating bundle requires contracts and measurements only')
    contracts=[]
    for item in payload['contracts']:
        fields=dict(item)
        fields['bands']=tuple(ParcelRateBand(**b) for b in fields['bands'])
        fields['verified']=verified
        contracts.append(ParcelRateContract(**fields))
    measured={}
    for item in payload['measurements']:
        measurement=ParcelMeasurements(**{**item,'verified':verified})
        if measurement.shipment_id in measured:
            raise ValueError('duplicate shipment measurements')
        measured[measurement.shipment_id]=measurement
    results=[]
    for charge in charges:
        candidates=[c for c in contracts if c.carrier_id==charge.carrier_id and
                    normalize_service(c.service_code)==charge.normalized_service and
                    normalize_zone(c.zone)==charge.normalized_zone and
                    c.effective_from<=charge.ship_date<=c.effective_to]
        if len(candidates)!=1 or charge.shipment_id not in measured:
            raise ValueError('exactly one in-scope contract and measurement required per shipment')
        results.append(rate_parcel(charge,measured[charge.shipment_id],candidates[0],currency=currency))
    return tuple(results)
