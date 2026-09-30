"""
Unit tests for ImageReader.
"""

import tempfile
from pathlib import Path
import pytest

from forensics_platform.forensics.image_reader import ImageReader, ImageFormat


def create_synthetic_mbr() -> bytes:
    """Create a 512-byte synthetic MBR sector with a valid partition entry."""
    mbr = bytearray(512)
    # Partition entry 1 at offset 446 (0x1BE)
    entry_offset = 446
    mbr[entry_offset] = 0x80         # Bootable
    mbr[entry_offset + 4] = 0x07     # NTFS / exFAT
    # Start LBA = 2048 (0x0800)
    mbr[entry_offset + 8:entry_offset + 12] = (2048).to_bytes(4, byteorder="little")
    # Sector count = 20480 (0x5000)
    mbr[entry_offset + 12:entry_offset + 16] = (20480).to_bytes(4, byteorder="little")

    # MBR boot signature 0x55AA at bytes 510-511
    mbr[510] = 0x55
    mbr[511] = 0xAA
    return bytes(mbr)


def test_image_reader_single_raw():
    """Test reading blocks from a single raw image file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_file = Path(tmpdir) / "test_image.raw"
        payload = b"A" * 1024 + b"B" * 1024 + b"C" * 1024
        img_file.write_bytes(payload)

        with ImageReader(img_file) as reader:
            assert reader.format == ImageFormat.RAW
            assert reader.get_size() == 3072
            assert reader.get_sector_count() == 6

            # Read block at beginning
            block1 = reader.read_block(0, 1024)
            assert block1 == b"A" * 1024

            # Read block in middle
            block2 = reader.read_block(1024, 1024)
            assert block2 == b"B" * 1024

            # Read crossing boundary
            block_cross = reader.read_block(512, 1024)
            assert block_cross == b"A" * 512 + b"B" * 512


def test_image_reader_split_raw():
    """Test reading seamlessly across split raw image segments (.001, .002)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        seg1 = Path(tmpdir) / "split.dd.001"
        seg2 = Path(tmpdir) / "split.dd.002"

        seg1.write_bytes(b"1" * 1000)
        seg2.write_bytes(b"2" * 1000)

        with ImageReader(seg1) as reader:
            assert reader.format == ImageFormat.SPLIT_RAW
            assert reader.get_size() == 2000
            assert len(reader.segments) == 2

            # Read data straddling segment boundary (offset 800 to 1200)
            spanning_data = reader.read_block(800, 400)
            assert len(spanning_data) == 400
            assert spanning_data == b"1" * 200 + b"2" * 200


def test_image_reader_mbr_parsing():
    """Test detecting and parsing MBR partition table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_file = Path(tmpdir) / "disk.img"
        mbr_data = create_synthetic_mbr()
        # Create 1MB disk image with MBR at sector 0
        img_file.write_bytes(mbr_data + b"\x00" * (1024 * 1024 - len(mbr_data)))

        with ImageReader(img_file) as reader:
            partitions = reader.parse_mbr_partitions()
            assert len(partitions) == 1
            part = partitions[0]
            assert part["start_sector"] == 2048
            assert part["length_sectors"] == 20480
            assert part["bootable"] is True
            assert "NTFS" in part["description"]
