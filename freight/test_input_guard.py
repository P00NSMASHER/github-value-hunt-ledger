import csv

import pytest

from freight.input_guard import (
    IngestPolicy,
    InputStatus,
    inspect_input,
    neutralize_spreadsheet_cell,
)


def test_safe_pdf_is_accepted():
    result = inspect_input("invoice.pdf", b"%PDF-1.7\n1 0 obj\n")
    assert result.status is InputStatus.ACCEPT
    assert result.detected_format == "pdf"


def test_archive_disguised_as_pdf_is_rejected():
    result = inspect_input("invoice.pdf", b"PK\x03\x04evil")
    assert result.status is InputStatus.REJECT
    assert "archive_magic_rejected" in result.reasons
    assert "pdf_magic_mismatch" in result.reasons or result.reasons


def test_xml_doctype_and_entity_are_rejected():
    payload = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><x>&y;</x>'
    result = inspect_input("authority.xml", payload)
    assert result.status is InputStatus.REJECT
    assert "xml_doctype_rejected" in result.reasons
    assert "xml_entity_rejected" in result.reasons


def test_malformed_xml_is_typed_reject():
    result = inspect_input("authority.xml", b"<root><child></root>")
    assert result.status is InputStatus.REJECT
    assert "xml_parse_error" in result.reasons


def test_xml_depth_limit_fails_closed():
    policy = IngestPolicy(max_xml_depth=3)
    result = inspect_input("authority.xml", b"<a><b><c><d/></c></b></a>", policy)
    assert result.status is InputStatus.REJECT
    assert "xml_depth_limit_exceeded" in result.reasons


def test_xml_element_limit_fails_closed():
    policy = IngestPolicy(max_xml_elements=3)
    result = inspect_input("authority.xml", b"<a><b/><c/><d/></a>", policy)
    assert result.status is InputStatus.REJECT
    assert "xml_element_limit_exceeded" in result.reasons


def test_xml_attribute_limit_fails_closed():
    policy = IngestPolicy(max_xml_attributes_per_element=2)
    result = inspect_input("authority.xml", b'<a x="1" y="2" z="3"/>', policy)
    assert result.status is InputStatus.REJECT
    assert "xml_attribute_limit_exceeded" in result.reasons


def test_csv_formula_export_is_neutralized_without_changing_plain_values():
    assert neutralize_spreadsheet_cell("=1+1") == "'=1+1"
    assert neutralize_spreadsheet_cell("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert neutralize_spreadsheet_cell("plain") == "plain"
    assert neutralize_spreadsheet_cell(123) == 123


def test_path_traversal_filename_is_rejected():
    result = inspect_input("../invoice.csv", b"a,b\n1,2\n")
    assert result.status is InputStatus.REJECT
    assert "unsafe_filename" in result.reasons


@pytest.mark.parametrize(
    "filename",
    [
        r"..\invoice.csv",
        r"C:\temp\invoice.csv",
        r"\\server\share\invoice.csv",
        "invoice.csv:alternate",
    ],
)
def test_windows_style_or_ads_filename_is_rejected(filename):
    result = inspect_input(filename, b"a,b\n1,2\n")
    assert result.status is InputStatus.REJECT
    assert "unsafe_filename" in result.reasons


def test_oversized_input_is_rejected():
    policy = IngestPolicy(max_file_bytes=10)
    result = inspect_input("invoice.csv", b"a" * 11, policy)
    assert result.status is InputStatus.REJECT
    assert "file_too_large" in result.reasons


def test_valid_x12_is_accepted():
    result = inspect_input("invoice.edi", b"ISA*00*          *00*          ~GS*IN*X*Y~")
    assert result.status is InputStatus.ACCEPT


def test_edi_segment_limit_fails_closed():
    policy = IngestPolicy(max_edi_segment_chars=20)
    result = inspect_input("invoice.edi", b"ISA*" + b"A" * 100 + b"~", policy)
    assert result.status is InputStatus.REJECT
    assert "edi_segment_too_long" in result.reasons


def test_many_short_edi_segments_are_accepted_under_segment_limit():
    policy = IngestPolicy(max_edi_segment_chars=20)
    payload = b"ISA*00~" + b"REF*A~" * 10_000
    result = inspect_input("invoice.edi", payload, policy)
    assert result.status is InputStatus.ACCEPT


def test_zip_extension_is_rejected_even_without_zip_magic():
    result = inspect_input("bundle.zip", b"not-an-archive")
    assert result.status is InputStatus.REJECT
    assert "archive_inputs_not_supported" in result.reasons


def test_csv_field_limit_is_explicit_and_fails_closed():
    policy = IngestPolicy(max_csv_field_chars=16)
    result = inspect_input("invoice.csv", b"12345678901234567,ok\n", policy)
    assert result.status is InputStatus.REJECT
    assert "csv_field_too_long" in result.reasons


def test_csv_parser_error_is_typed_reject():
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(32)
        policy = IngestPolicy(
            max_csv_field_chars=64,
            max_text_line_chars=128,
        )
        result = inspect_input("invoice.csv", b"A" * 40 + b",ok\n", policy)
    finally:
        csv.field_size_limit(previous_limit)

    assert result.status is InputStatus.REJECT
    assert "csv_parse_error" in result.reasons


def test_csv_cells_per_row_limit_fails_closed():
    policy = IngestPolicy(max_csv_cells_per_row=3)
    result = inspect_input("invoice.csv", b"a,b,c,d\n", policy)
    assert result.status is InputStatus.REJECT
    assert "csv_cells_per_row_limit_exceeded" in result.reasons


def test_csv_wide_row_is_rejected_before_csv_reader(monkeypatch):
    def parser_should_not_run(*args, **kwargs):
        raise AssertionError("csv.reader should not receive a row beyond the preflight cell bound")

    monkeypatch.setattr("freight.input_guard.csv.reader", parser_should_not_run)
    policy = IngestPolicy(max_csv_cells_per_row=3)
    result = inspect_input("invoice.csv", b"a,b,c,d\n", policy)
    assert result.status is InputStatus.REJECT
    assert "csv_cells_per_row_limit_exceeded" in result.reasons


def test_csv_shape_preflight_respects_quoted_commas_and_newlines():
    policy = IngestPolicy(max_csv_cells_per_row=2, max_csv_rows=1)
    result = inspect_input("invoice.csv", b'"a,b\nc",d\n', policy)
    assert result.status is InputStatus.ACCEPT


def test_csv_logical_row_limit_fails_closed():
    policy = IngestPolicy(max_csv_rows=2)
    result = inspect_input("invoice.csv", b"a,b\n1,2\n3,4\n", policy)
    assert result.status is InputStatus.REJECT
    assert "csv_row_limit_exceeded" in result.reasons


def test_csv_total_cell_limit_fails_closed():
    policy = IngestPolicy(max_csv_total_cells=5)
    result = inspect_input("invoice.csv", b"a,b,c\n1,2,3\n", policy)
    assert result.status is InputStatus.REJECT
    assert "csv_total_cells_limit_exceeded" in result.reasons


@pytest.mark.parametrize(
    "field_name",
    [
        "max_csv_field_chars",
        "max_csv_rows",
        "max_csv_cells_per_row",
        "max_csv_total_cells",
        "max_xml_depth",
        "max_xml_elements",
        "max_xml_attributes_per_element",
    ],
)
def test_shape_policy_limits_must_be_positive(field_name):
    kwargs = {field_name: 0}
    with pytest.raises(ValueError, match=f"{field_name} must be positive"):
        IngestPolicy(**kwargs)
