"""Adversarial source-shape QA: entirely offline; no real carriers are queried."""
import io
import json
from urllib.parse import parse_qs, urlparse

import pytest

from freight.fmcsa_public_carrier import (
    API_URL, DATASET_ID, REFERENCE_KIND, FMCSAReferenceError,
    build_query_url, lookup_public_carrier, validate_census_response,
    validate_usdot,
)


class MockHTTPResponse:
    def __init__(self, document, *, status=200, raw=None):
        self.status = status
        self.content = raw if raw is not None else json.dumps(document).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.content[:size]


def row(**changes):
    base = {"dot_number": "1234567", "legal_name": "EXAMPLE FREIGHT LLC", "power_units": "12"}
    base.update(changes)
    return base


def call(document, **opts):
    seen = []

    def opener(request, *, timeout):
        seen.append((request.full_url, request.get_method(), timeout))
        return MockHTTPResponse(document)

    return lookup_public_carrier(
        "1234567", opener=opener, retrieved_at_utc="2026-10-08T18:00:00Z", **opts
    ), seen


def test_exact_source_and_bounded_allowlisted_lookup():
    url = build_query_url("1234567")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert url.startswith(API_URL + "?")
    assert parsed.scheme == "https"
    assert parsed.hostname == "data.transportation.gov"
    assert query == {
        "$select": ["dot_number,legal_name,power_units"],
        "$where": ["dot_number=1234567"],
        "$limit": ["2"],
    }
    assert DATASET_ID in url
    assert "email" not in url and "phone" not in url and "address" not in url


@pytest.mark.parametrize("bad", ["", "0", "000123", "1234567890", "12.3", "+123",
                               "-1", "１２３４", "12 34", "1' OR 1=1", 12345, None, True])
def test_invalid_or_injectable_usdot_values_rejected_before_network(bad):
    with pytest.raises(FMCSAReferenceError, match="USDOT"):
        validate_usdot(bad)
    with pytest.raises(FMCSAReferenceError, match="USDOT"):
        build_query_url(bad)


def test_real_government_schema_contract_does_not_use_obsolete_field():
    # Verified via the official 2026-10-08 columns.json, and both
    # zero-record API query probes. The old selected field returned HTTP 400.
    from freight.fmcsa_public_carrier import ALLOWED_FIELDS
    assert ALLOWED_FIELDS == frozenset({"dot_number", "legal_name", "power_units"})
    url = build_query_url("1234567")
    assert "nbr_power_unit" not in url
    query = parse_qs(urlparse(url).query)
    assert query["$select"] == ["dot_number,legal_name,power_units"]
    assert query["$where"] == ["dot_number=1234567"]


def test_obsolete_api_response_field_fails_closed():
    with pytest.raises(FMCSAReferenceError, match="unexpected"):
        call([{"dot_number": "1234567", "legal_name": "EXAMPLE FREIGHT LLC",
               "nbr_power_unit": "12"}])


def test_exactly_one_synthetic_record_from_mocked_government_response():
    result, seen = call([row()])
    assert result.usdot_number == "1234567"
    assert result.legal_name == "EXAMPLE FREIGHT LLC"
    assert result.power_units == 12
    assert result.retrieved_at_utc == "2026-10-08T18:00:00Z"
    assert result.reference_kind == REFERENCE_KIND
    assert result.operating_authority_verified is False
    assert result.customer_invoice_verified is False
    assert result.recovery_fee_authorized is False
    assert len(seen) == 1
    assert seen[0][1:] == ("GET", 5)


def test_no_matching_carrier_returns_unknown_not_inactive_or_unauthorized():
    got, calls = call([])
    assert got is None
    assert len(calls) == 1


def test_duplicate_carrier_result_rejected_not_arbitrarily_first_selected():
    with pytest.raises(FMCSAReferenceError, match="ambiguous"):
        call([row(), row()])


@pytest.mark.parametrize("bad_response", [{}, "hello", 2, None, [[], []]])
def test_response_shape_must_be_bounded_array(bad_response):
    with pytest.raises(FMCSAReferenceError):
        call(bad_response)


@pytest.mark.parametrize("wrong", ["1", "1234568", 1234567, None, ""])
def test_cross_carrier_or_type_mismatch_cannot_be_used_as_identity(wrong):
    with pytest.raises(FMCSAReferenceError, match="differs"):
        call([row(dot_number=wrong)])


@pytest.mark.parametrize("field", ["email_address", "telephone", "phy_street", "mailing_address", "social_security_number"])
def test_rejects_unrequested_contact_and_personal_fields(field):
    with pytest.raises(FMCSAReferenceError, match="contact"):
        call([row(**{field: "DO_NOT_RETAIN"})])


@pytest.mark.parametrize("name", ["", "  ", " EXAMPLE FREIGHT LLC", "EXAMPLE\nFREIGHT", "A" * 161, None])
def test_legal_name_must_be_canonical_and_bounded(name):
    with pytest.raises(FMCSAReferenceError, match="name"):
        call([row(legal_name=name)])


@pytest.mark.parametrize("value", [-1, 2, True, "2.5", "0002", "NaN", "-1", "999999999", [], {}])
def test_power_unit_count_must_be_bounded_nonnegative_integer_or_unknown(value):
    with pytest.raises(FMCSAReferenceError, match="power unit count"):
        call([row(power_units=value)])


@pytest.mark.parametrize("missing", [None, ""])
def test_missing_power_units_stays_unknown_not_zero(missing):
    result, _ = call([row(power_units=missing)])
    assert result.power_units is None


@pytest.mark.parametrize("timeout", [0, 11, "5", True, 0.5])
def test_invalid_timeouts_block_before_network(timeout):
    called = []
    def opener(*args, **kwargs):
        called.append(True)
        raise AssertionError("should not contact network")

    with pytest.raises(FMCSAReferenceError, match="timeout"):
        lookup_public_carrier("1234567", opener=opener, timeout_seconds=timeout)
    assert not called


def test_oversize_document_rejected_before_parse():
    def opener(request, *, timeout):
        return MockHTTPResponse(None, raw=b"[" + b" " * 8194 + b"]")
    with pytest.raises(FMCSAReferenceError, match="exceeds bounded size"):
        lookup_public_carrier("1234567", opener=opener)


@pytest.mark.parametrize("malformed", [b"not json", b"[{}", b"\xff"])
def test_invalid_json_or_encoding_rejected(malformed):
    def opener(request, *, timeout):
        return MockHTTPResponse(None, raw=malformed)
    with pytest.raises(FMCSAReferenceError, match="invalid JSON"):
        lookup_public_carrier("1234567", opener=opener)


def test_server_http_failure_does_not_produce_carrier_identity():
    def opener(request, *, timeout):
        return MockHTTPResponse([], status=503)
    with pytest.raises(FMCSAReferenceError, match="HTTP 200"):
        lookup_public_carrier("1234567", opener=opener)


def test_request_failure_does_not_manufacture_a_record():
    def opener(request, *, timeout):
        raise OSError("simulated provider outage")
    with pytest.raises(FMCSAReferenceError, match="service unavailable"):
        lookup_public_carrier("1234567", opener=opener)


@pytest.mark.parametrize("timestamp", ["2026-10-08T18:00:00", "2026-10-08T14:00:00-04:00",
                                      "2026-10-08", "invalid", 123])
def test_timestamp_cannot_misrepresent_non_utc_or_unknown_vintage(timestamp):
    with pytest.raises(FMCSAReferenceError, match="timestamp|UTC"):
        validate_census_response("1234567", [row()], retrieved_at_utc=timestamp)


def test_census_records_are_never_claim_or_operating_authority_labels():
    record = validate_census_response("1234567", [row()], retrieved_at_utc="2026-10-08T18:00:00Z")
    assert record.historical_point_in_time_verified is False
    assert record.operating_authority_verified is False
    assert record.customer_invoice_verified is False
    assert record.recovery_fee_authorized is False
    assert "PUBLIC_CENSUS_REGISTRATION_CONTEXT" in record.reference_kind
    assert not any("overcharge" in attr or "claim" in attr for attr in record.__dataclass_fields__)



def test_redirect_handler_rejects_all_location_targets_without_following_them():
    import urllib.request
    from freight.fmcsa_public_carrier import _RejectRedirects

    request = urllib.request.Request(build_query_url("1234567"))
    for code, url in [
        (301, "https://elsewhere.example/collect?dot=1234567"),
        (302, "https://data.transportation.gov/another-api"),
        (307, "http://data.transportation.gov/resource/az4n-8mr2.json"),
        (308, "https://elsewhere.example/collect"),
    ]:
        with pytest.raises(FMCSAReferenceError, match="redirects are not permitted"):
            _RejectRedirects().redirect_request(request, None, code, "redirect", {}, url)


def test_default_network_path_installs_redirect_denial_without_live_network(monkeypatch):
    import urllib.request
    from freight.fmcsa_public_carrier import _RejectRedirects

    checks = []

    class FakeOpener:
        def open(self, request, *, timeout):
            checks.append(("request", request.get_method(), timeout))
            return MockHTTPResponse([row()])

    def fake_build_opener(*handlers):
        checks.append(("handler", tuple(type(h) for h in handlers)))
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)
    result = lookup_public_carrier(
        "1234567", retrieved_at_utc="2026-10-08T18:00:00Z"
    )
    assert result.usdot_number == "1234567"
    assert checks == [
        ("handler", (_RejectRedirects,)),
        ("request", "GET", 5),
    ]


def test_unexpected_final_response_url_rejected_without_reading_data():
    class WrongOriginResponse(MockHTTPResponse):
        def geturl(self):
            return "https://not-fmcsa.example/resource/az4n-8mr2.json"

        def read(self, size=-1):
            raise AssertionError("should not read redirected response")

    def opener(request, *, timeout):
        return WrongOriginResponse([row()])

    with pytest.raises(FMCSAReferenceError, match="response origin or query changed"):
        lookup_public_carrier("1234567", opener=opener)


def test_same_host_different_query_is_not_source_identical():
    class WrongQueryResponse(MockHTTPResponse):
        def geturl(self):
            return "https://data.transportation.gov/resource/az4n-8mr2.json?$limit=99999"

    with pytest.raises(FMCSAReferenceError, match="response origin or query changed"):
        lookup_public_carrier("1234567", opener=lambda request, *, timeout: WrongQueryResponse([row()]))


@pytest.mark.parametrize("payload", [
    b'[{"dot_number":"1234567","dot_number":"1234567","legal_name":"EXAMPLE FREIGHT LLC","power_units":"12"}]',
    b'[{"dot_number":"1234567","legal_name":"EXAMPLE FREIGHT LLC","power_units":"12","power_units":"999"}]',
    b'[{"dot_number":"1234567","legal_name":"EXAMPLE FREIGHT LLC","power_units":"12","nested":{"x":1,"x":2}}]',
])
def test_duplicate_json_keys_rejected_even_if_last_value_looks_valid(payload):
    def opener(request, *, timeout):
        return MockHTTPResponse(None, raw=payload)

    with pytest.raises(FMCSAReferenceError, match="duplicate government JSON field"):
        lookup_public_carrier("1234567", opener=opener)



def test_empty_lookup_does_not_pretend_carrier_is_out_of_service():
    assert validate_census_response("1234567", [], retrieved_at_utc="2026-10-08T18:00:00Z") is None
