"""
Unit tests for format structure validators (JPEG, PNG, PDF, ZIP).
"""

import io
import struct
import zipfile
import zlib

from forensics_platform.carving.validators import (
    JPEGValidator,
    PNGValidator,
    PDFValidator,
    ZIPValidator,
    ValidatorRegistry,
)


def test_jpeg_validator_valid():
    """Test JPEGValidator on synthetic valid JPEG bytes."""
    val = JPEGValidator()

    # Synthetic JPEG
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x11\x08\x00\x64\x00\x64\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"  # 100x100
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    scan_data = b"\x12\x34\x56\xff\x00\x78"
    eoi = b"\xff\xd9"
    trailing_junk = b"\x00" * 512

    jpeg_bytes = soi + app0 + sof0 + sos + scan_data + eoi + trailing_junk

    res = val.validate(jpeg_bytes)
    assert res.is_valid is True
    assert res.footer_found is True
    assert res.details.get("width") == 100
    assert res.details.get("height") == 100
    assert res.estimated_size == len(soi + app0 + sof0 + sos + scan_data + eoi)
    assert res.structure_score >= 25


def test_jpeg_validator_corrupt():
    """Test JPEGValidator rejecting corrupted header."""
    val = JPEGValidator()
    res = val.validate(b"\x00\x00\x00\x00RandomData")
    assert res.is_valid is False
    assert res.footer_found is False


def test_png_validator_valid():
    """Test PNGValidator on synthetic valid PNG bytes."""
    val = PNGValidator()

    magic = b"\x89PNG\r\n\x1a\n"
    # IHDR: 100x50, 8-bit, RGB
    ihdr_data = struct.pack(">IIBBBBB", 100, 50, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # IDAT: 4 bytes
    idat_data = b"\x78\x9c\x03\x00"
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    idat_chunk = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc

    # IEND: 0 bytes
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc

    png_bytes = magic + ihdr_chunk + idat_chunk + iend_chunk + (b"\x00" * 256)

    res = val.validate(png_bytes)
    assert res.is_valid is True
    assert res.footer_found is True
    assert res.details.get("width") == 100
    assert res.details.get("height") == 50
    assert res.estimated_size == len(magic + ihdr_chunk + idat_chunk + iend_chunk)


def test_png_validator_crc_mismatch():
    """Test PNGValidator detecting corrupted CRC."""
    val = PNGValidator()
    magic = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 100, 50, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", 0xDEADBEEF)  # BAD CRC
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)

    res = val.validate(magic + ihdr_chunk + iend_chunk)
    assert res.is_valid is False
    assert any("CRC-32 mismatch" in err for err in res.errors)


def test_pdf_validator_valid():
    """Test PDFValidator on synthetic PDF."""
    val = PDFValidator()
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"trailer\n<< /Root 1 0 R >>\n"
        b"startxref\n120\n"
        b"%%EOF\n"
    )
    res = val.validate(pdf_bytes + b"\x00" * 128)
    assert res.is_valid is True
    assert res.footer_found is True
    assert res.details.get("version") == "1.4"
    assert res.details.get("has_objects") is True


def test_zip_validator_valid():
    """Test ZIPValidator on actual generated in-memory ZIP."""
    val = ZIPValidator()

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("test.txt", "Forensic carving test content")

    zip_bytes = bio.getvalue() + (b"\x00" * 256)

    res = val.validate(zip_bytes)
    assert res.is_valid is True
    assert res.footer_found is True
    assert res.details.get("total_entries") == 1
    assert res.details.get("first_file") == "test.txt"
    assert res.estimated_size == len(bio.getvalue())


def test_validator_registry():
    """Test ValidatorRegistry retrieval and fallback."""
    reg = ValidatorRegistry()
    assert isinstance(reg.get_validator("jpeg"), JPEGValidator)
    assert isinstance(reg.get_validator("png"), PNGValidator)
    assert isinstance(reg.get_validator("pdf"), PDFValidator)
    assert isinstance(reg.get_validator("zip"), ZIPValidator)
    # Unknown format fallback
    fallback = reg.get_validator("nonexistent_format")
    assert fallback is not None
