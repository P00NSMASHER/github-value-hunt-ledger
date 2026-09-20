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


def test_csv_formula_export_is_neutralized_without_changing_plain_values():
    assert neutralize_spreadsheet_cell("=1+1") == "'=1+1"
    assert neutralize_spreadsheet_cell("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert neutralize_spreadsheet_cell("plain") == "plain"
    assert neutralize_spreadsheet_cell(123) == 123


def test_path_traversal_filename_is_rejected():
    result = inspect_input("../invoice.csv", b"a,b\n1,2\n")
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
    result = inspect_input("invoice.edi", b"ISA*" + b"A" * 100 + b"~")
    assert result.status is InputStatus.REJECT
    assert "edi_segment_too_long" in result.reasons


def test_zip_extension_is_rejected_even_without_zip_magic():
    result = inspect_input("bundle.zip", b"not-an-archive")
    assert result.status is InputStatus.REJECT
    assert "archive_inputs_not_supported" in result.reasons
