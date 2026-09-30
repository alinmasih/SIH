"""
Forensic Disk Image Reader.

Provides low-level block reading, split-raw (.001) aggregation,
geometry detection, and native MBR partition parsing.
"""

import os
import glob
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, BinaryIO


class ImageFormat(Enum):
    """Supported disk image formats."""
    RAW = "raw"                # Single raw bit-stream (.dd, .raw, .img)
    SPLIT_RAW = "split_raw"    # Split raw segments (.001, .002, ...)
    UNKNOWN = "unknown"


class ImageReader:
    """
    High-performance block reader for forensic disk images.
    Supports single raw images and multi-segment split raw files.
    """

    def __init__(self, image_path: Union[str, Path], sector_size: int = 512):
        self.image_path = Path(image_path).resolve()
        self.sector_size = sector_size
        self.segments: List[Path] = []
        self.segment_sizes: List[int] = []
        self.total_size: int = 0
        self.format: ImageFormat = ImageFormat.UNKNOWN
        self._handles: List[BinaryIO] = []
        self._is_open = False

        self._detect_format()

    def _detect_format(self):
        """Identify if image is a single raw file or part of a split-raw set."""
        if not self.image_path.exists():
            raise FileNotFoundError(f"Image not found: {self.image_path}")

        path_str = str(self.image_path)
        # Check for split segments (.001, .dd.001, etc.)
        if path_str.endswith(".001"):
            base_pattern = path_str[:-3] + "[0-9][0-9][0-9]"
            found = sorted(glob.glob(base_pattern))
            if len(found) > 1:
                self.segments = [Path(p) for p in found]
                self.format = ImageFormat.SPLIT_RAW
            else:
                self.segments = [self.image_path]
                self.format = ImageFormat.RAW
        else:
            self.segments = [self.image_path]
            self.format = ImageFormat.RAW

        self.segment_sizes = [p.stat().st_size for p in self.segments]
        self.total_size = sum(self.segment_sizes)

    def open(self):
        """Open file handles for all segments."""
        if self._is_open:
            return
        self._handles = [open(p, "rb") for p in self.segments]
        self._is_open = True

    def close(self):
        """Close all open file handles."""
        if not self._is_open:
            return
        for h in self._handles:
            try:
                h.close()
            except Exception:
                pass
        self._handles.clear()
        self._is_open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_size(self) -> int:
        """Total disk image size in bytes."""
        return self.total_size

    def get_sector_count(self) -> int:
        """Total logical sectors in disk image."""
        return self.total_size // self.sector_size

    def read_block(self, offset: int, size: int) -> bytes:
        """
        Read arbitrary block of bytes across file segment boundaries.

        Args:
            offset: Byte offset in the aggregate image
            size: Number of bytes to read

        Returns:
            Bytes read from disk image
        """
        if not self._is_open:
            self.open()

        if offset < 0 or offset >= self.total_size:
            return b""

        # Clamp size to image boundaries
        size_to_read = min(size, self.total_size - offset)
        if size_to_read <= 0:
            return b""

        # Single file case optimization
        if len(self.segments) == 1:
            h = self._handles[0]
            h.seek(offset)
            return h.read(size_to_read)

        # Multi-segment traversal
        buffer = bytearray()
        bytes_left = size_to_read
        current_offset = offset

        for idx, seg_size in enumerate(self.segment_sizes):
            if current_offset < seg_size:
                # Segment contains part of the data
                h = self._handles[idx]
                h.seek(current_offset)
                chunk_size = min(bytes_left, seg_size - current_offset)
                read_bytes = h.read(chunk_size)
                buffer.extend(read_bytes)
                bytes_left -= len(read_bytes)
                current_offset = 0  # Next segments start at offset 0
                if bytes_left <= 0:
                    break
            else:
                current_offset -= seg_size

        return bytes(buffer)

    def parse_mbr_partitions(self) -> List[Dict[str, Any]]:
        """
        Parse MBR partition table from sector 0.

        Returns:
            List of detected partition metadata dictionaries
        """
        sector0 = self.read_block(0, 512)
        if len(sector0) < 512 or sector0[510:512] != b"\x55\xaa":
            return []

        partitions = []
        for i in range(4):
            entry_offset = 446 + (i * 16)
            entry = sector0[entry_offset:entry_offset + 16]
            part_type = entry[4]
            if part_type == 0:
                continue

            bootable = (entry[0] == 0x80)
            start_lba = int.from_bytes(entry[8:12], byteorder="little")
            sector_count = int.from_bytes(entry[12:16], byteorder="little")

            type_name = {
                0x07: "NTFS / exFAT",
                0x83: "Linux Native (ext2/3/4)",
                0x0B: "FAT32 (CHS)",
                0x0C: "FAT32 (LBA)",
                0x0E: "FAT16 (LBA)",
                0x01: "FAT12",
                0x82: "Linux Swap",
            }.get(part_type, f"Type 0x{part_type:02X}")

            partitions.append({
                "slot": f"000:{i:03d}",
                "start_sector": start_lba,
                "end_sector": start_lba + sector_count - 1,
                "length_sectors": sector_count,
                "offset_bytes": start_lba * self.sector_size,
                "size_bytes": sector_count * self.sector_size,
                "description": type_name,
                "bootable": bootable,
                "type_code": part_type,
            })

        return partitions
