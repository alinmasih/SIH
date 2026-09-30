"""
Unit tests for SignatureDatabase and FileSignature.
"""

from pathlib import Path
from forensics_platform.carving.signature_database import FileSignature, SignatureDatabase


def test_builtin_signatures_loaded():
    """Verify built-in fallback signatures are available immediately."""
    db = SignatureDatabase(signatures_dir=None)
    sigs = db.list_signatures()
    assert len(sigs) >= 4

    types = {s.file_type for s in sigs}
    assert "jpeg" in types
    assert "png" in types
    assert "pdf" in types
    assert "zip" in types


def test_get_signature_by_type_and_extension():
    """Verify lookup by file_type and extension."""
    db = SignatureDatabase()
    jpg_sig = db.get_signature("jpeg")
    assert jpg_sig is not None
    assert jpg_sig.file_type == "jpeg"
    assert "jpg" in jpg_sig.extensions
    assert jpg_sig.header.startswith(b"\xff\xd8")

    # Lookup by extension
    by_ext = db.get_by_extension("png")
    assert by_ext is not None
    assert by_ext.file_type == "png"

    # Lookup with leading dot
    by_dot = db.get_by_extension(".pdf")
    assert by_dot is not None
    assert by_dot.file_type == "pdf"


def test_register_custom_signature():
    """Verify registering a custom signature."""
    db = SignatureDatabase()
    custom = FileSignature(
        name="Custom Binary",
        file_type="custom_bin",
        extensions=["cbin"],
        mime_type="application/x-custom",
        header=b"\x12\x34\x56\x78",
        footer=b"\x99\xAA",
        max_size=1024 * 1024,
    )
    db.register_signature(custom)

    retrieved = db.get_signature("custom_bin")
    assert retrieved is not None
    assert retrieved.name == "Custom Binary"
    assert retrieved.header == b"\x12\x34\x56\x78"
    assert db.get_by_extension("cbin") == retrieved


def test_load_from_json_directory(tmp_path):
    """Verify loading from JSON signature definitions."""
    json_content = """{
        "name": "Test Format",
        "file_type": "tst",
        "extensions": ["tst"],
        "mime_type": "text/plain",
        "header_hex": "41424344",
        "footer_hex": "58595A",
        "max_size": 2048,
        "sector_aligned": false
    }"""
    sig_file = tmp_path / "test.json"
    sig_file.write_text(json_content)

    db = SignatureDatabase(signatures_dir=tmp_path)
    sig = db.get_signature("tst")
    assert sig is not None
    assert sig.header == b"ABCD"
    assert sig.footer == b"XYZ"
    assert sig.sector_aligned is False
