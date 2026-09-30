"""
Unit tests for SignatureScanner.
"""

from pathlib import Path
from forensics_platform.carving.signature_database import FileSignature
from forensics_platform.carving.signature_scanner import SignatureScanner


def test_scan_buffer_sector_aligned():
    """Verify sector-aligned scanning finds matches only at 512-byte multiples."""
    sig = FileSignature(
        name="Test",
        file_type="test",
        extensions=["tst"],
        mime_type="test/test",
        header=b"TESTSIG!",
    )
    scanner = SignatureScanner([sig])

    # Construct 2048-byte buffer
    data = bytearray(2048)
    # Put signature at unaligned offset 123
    data[123:131] = b"TESTSIG!"
    # Put signature at sector boundary 1024
    data[1024:1032] = b"TESTSIG!"

    candidates = scanner.scan_buffer(bytes(data), base_offset=0, sector_aligned=True, sector_size=512)
    assert len(candidates) == 1
    assert candidates[0].start_offset == 1024


def test_scan_buffer_unaligned():
    """Verify unaligned scanning finds matches anywhere in the buffer."""
    sig = FileSignature(
        name="Test",
        file_type="test",
        extensions=["tst"],
        mime_type="test/test",
        header=b"TESTSIG!",
    )
    scanner = SignatureScanner([sig])

    data = bytearray(2048)
    data[123:131] = b"TESTSIG!"
    data[1024:1032] = b"TESTSIG!"

    candidates = scanner.scan_buffer(bytes(data), base_offset=0, sector_aligned=False)
    assert len(candidates) == 2
    assert candidates[0].start_offset == 123
    assert candidates[1].start_offset == 1024


def test_scan_file_streaming(tmp_path):
    """Verify streaming file scan handles chunk boundaries correctly."""
    sig = FileSignature(
        name="JPEG",
        file_type="jpeg",
        extensions=["jpg"],
        mime_type="image/jpeg",
        header=b"\xff\xd8\xff",
    )
    scanner = SignatureScanner([sig])

    # Create file with signature across chunk boundary
    # Let chunk size be 1024 bytes, put signature at byte 1024
    file_path = tmp_path / "stream_test.dd"
    data = bytearray(4096)
    data[1024:1027] = b"\xff\xd8\xff"
    data[3072:3075] = b"\xff\xd8\xff"
    file_path.write_bytes(data)

    progress_ticks = []

    def on_prog(processed, total):
        progress_ticks.append((processed, total))

    results = list(
        scanner.scan_file(
            file_path,
            chunk_size=1024,
            sector_aligned=True,
            sector_size=512,
            progress_callback=on_prog,
        )
    )

    assert len(results) == 2
    assert results[0].start_offset == 1024
    assert results[1].start_offset == 3072
    assert len(progress_ticks) > 0
