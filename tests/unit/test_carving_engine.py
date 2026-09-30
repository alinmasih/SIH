"""
Unit tests for CarvingEngine.
"""

import io
import struct
import zipfile
import zlib
from pathlib import Path

from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.carving.carving_engine import CarvingEngine
from forensics_platform.database.models import Operation, RecoveredFile
from forensics_platform.database.session import DatabaseManager


def _build_synthetic_jpeg() -> bytes:
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x11\x08\x00\x40\x00\x40\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"  # 64x64
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    scan_data = bytes(range(200))
    eoi = b"\xff\xd9"
    return soi + app0 + sof0 + sos + scan_data + eoi


def _build_synthetic_png() -> bytes:
    magic = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    idat_data = bytes(range(100))
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    idat_chunk = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc

    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc

    return magic + ihdr_chunk + idat_chunk + iend_chunk


def _build_synthetic_zip() -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("evidence.txt", "Top secret carved forensic data.")
    return bio.getvalue()


def test_carve_image_standalone(tmp_path):
    """Verify carving multiple formats from a raw disk image."""
    img_path = tmp_path / "raw_disk.dd"
    out_dir = tmp_path / "carved"

    # Disk size: 1MB (2048 sectors)
    disk = bytearray(1024 * 1024)

    jpeg_bytes = _build_synthetic_jpeg()
    png_bytes = _build_synthetic_png()
    zip_bytes = _build_synthetic_zip()

    # Embed files at sector offsets 0, 512, 1024
    disk[0 : len(jpeg_bytes)] = jpeg_bytes
    disk[2048 : 2048 + len(png_bytes)] = png_bytes
    disk[4096 : 4096 + len(zip_bytes)] = zip_bytes

    img_path.write_bytes(disk)

    engine = CarvingEngine()
    results = engine.carve_image(
        image_path=img_path,
        target_types=["jpeg", "png", "zip"],
        min_confidence=50,
        output_dir=out_dir,
        sector_aligned=True,
    )

    assert len(results) == 3
    types = {r["file_type"] for r in results}
    assert types == {"jpeg", "png", "zip"}

    for r in results:
        carved_path = Path(r["path"])
        assert carved_path.exists()
        assert carved_path.stat().st_size == r["size"]
        assert r["confidence_score"] >= 50
        assert len(r["sha256"]) == 64


def test_carve_image_with_db_and_audit(tmp_path):
    """Verify carving integrates with SQLite database models and audit logging."""
    db_file = tmp_path / "test.db"
    db_manager = DatabaseManager(db_file)
    db_manager.initialize()
    audit_logger = AuditLogger(db_manager.get_session)

    img_path = tmp_path / "evidence_disk.raw"
    out_dir = tmp_path / "carved_artifacts"

    disk = bytearray(512 * 1024)
    png_bytes = _build_synthetic_png()
    disk[1024 : 1024 + len(png_bytes)] = png_bytes
    img_path.write_bytes(disk)

    engine = CarvingEngine(db_manager=db_manager, audit_logger=audit_logger)
    results = engine.carve_image(
        image_path=img_path,
        target_types=["png"],
        min_confidence=50,
        output_dir=out_dir,
        case_id=None,
    )

    assert len(results) == 1
    rec_info = results[0]
    assert rec_info["id"] is not None

    # Check database persistence
    with db_manager.session() as session:
        op = session.query(Operation).filter_by(operation_type="file_carving").first()
        assert op is not None
        assert op.status == "completed"

        recovered = session.query(RecoveredFile).filter_by(id=rec_info["id"]).first()
        assert recovered is not None
        assert recovered.detected_type == "png"
        assert recovered.sha256 == rec_info["sha256"]
        assert recovered.confidence_score >= 80

    # Check audit trail integrity
    integrity = audit_logger.verify_integrity()
    assert integrity["valid"] is True
    assert integrity["total_events"] >= 3  # genesis + carving_started + file_carved + carving_completed
