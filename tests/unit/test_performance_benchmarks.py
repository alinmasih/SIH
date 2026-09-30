"""
Performance Benchmarking Tests for Forensics Platform.

Validates throughput and scalability across core operational workloads:
1. Cryptographic stream hashing (SHA-256 / MD5) throughput (MB/s)
2. File carving engine throughput on synthetic raw media
3. Cryptographic audit log chain verification latency & scaling
"""

import os
import time
import io
import struct
import zipfile
import zlib
from pathlib import Path
import pytest

from forensics_platform.carving.carving_engine import CarvingEngine
from forensics_platform.utils.hashing import calculate_multiple_hashes
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.database.session import DatabaseManager


def _build_synthetic_jpeg() -> bytes:
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x11\x08\x00\x40\x00\x40\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
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
        zf.writestr("perf_test.txt", "Forensics performance benchmarking payload.")
    return bio.getvalue()


def test_hashing_throughput_benchmark(tmp_path):
    """Benchmark SHA-256 and MD5 streaming hash calculation throughput on 8MB payload."""
    test_file = tmp_path / "stream_hash_test.bin"
    chunk_size = 1024 * 1024  # 1MB
    target_mb = 8
    target_bytes = target_mb * chunk_size

    # Generate test data
    pattern = b"A" * chunk_size
    with open(test_file, "wb") as f:
        for _ in range(target_mb):
            f.write(pattern)

    assert test_file.stat().st_size == target_bytes

    start_time = time.perf_counter()
    hashes = calculate_multiple_hashes(test_file, algorithms=["sha256", "md5"])
    elapsed = time.perf_counter() - start_time

    assert "sha256" in hashes
    assert "md5" in hashes
    assert len(hashes["sha256"]) == 64

    throughput_mb_s = target_mb / max(elapsed, 0.0001)
    print(f"\n[Hashing Benchmark] {target_mb}MB hashed in {elapsed:.4f}s ({throughput_mb_s:.2f} MB/s)")
    # Must achieve at least 30 MB/s on modern systems
    assert throughput_mb_s >= 30.0


def test_carving_throughput_benchmark(tmp_path):
    """Benchmark carving engine throughput across a 2MB disk image with embedded files."""
    img_path = tmp_path / "carve_bench.dd"
    out_dir = tmp_path / "carved_bench"
    img_size_bytes = 2 * 1024 * 1024  # 2MB
    disk = bytearray(img_size_bytes)

    jpeg = _build_synthetic_jpeg()
    png = _build_synthetic_png()
    zip_f = _build_synthetic_zip()

    # Embed at aligned offsets
    disk[0 : len(jpeg)] = jpeg
    disk[512 * 200 : 512 * 200 + len(png)] = png
    disk[512 * 1000 : 512 * 1000 + len(zip_f)] = zip_f

    img_path.write_bytes(disk)

    engine = CarvingEngine()
    start_time = time.perf_counter()
    results = engine.carve_image(
        image_path=img_path,
        target_types=["jpeg", "png", "zip"],
        min_confidence=40,
        output_dir=out_dir,
        sector_aligned=True,
    )
    elapsed = time.perf_counter() - start_time

    assert len(results) == 3
    throughput_mb_s = (img_size_bytes / (1024 * 1024)) / max(elapsed, 0.0001)
    print(f"\n[Carving Benchmark] 2MB disk carved in {elapsed:.4f}s ({throughput_mb_s:.2f} MB/s)")
    # Sector-aligned scanner should achieve at least 1.0 MB/s
    assert throughput_mb_s >= 1.0


def test_audit_chain_verification_scaling_benchmark(tmp_path):
    """Benchmark cryptographic verification scaling for 200 consecutive chained audit events."""
    db_file = tmp_path / "audit_perf.db"
    db_mgr = DatabaseManager(db_file)
    db_mgr.initialize()

    logger = AuditLogger(db_mgr.get_session)

    # Insert 200 audit events
    total_events = 200
    for i in range(total_events):
        logger.log_event(
            event_type=f"benchmark_event_{i % 5}",
            event_data={"index": i, "status": "ok", "action": f"action_{i}"},
            event_category="system",
            user=f"user_{i % 2}",
        )

    # Measure chain verification time
    start_time = time.perf_counter()
    res = logger.verify_integrity()
    elapsed = time.perf_counter() - start_time

    assert res["valid"] is True
    # 200 events plus the initial genesis event created during db initialization
    assert res["verified_events"] == total_events + 1
    print(f"\n[Audit Chain Benchmark] {res['verified_events']} events verified in {elapsed:.4f}s ({res['verified_events'] / max(elapsed, 0.0001):.1f} records/s)")
    # Verification of 200 records should take less than 1.5 seconds
    assert elapsed < 1.5
