"""
PNG Validator - binary structure and CRC-32 validation for PNG images.
"""

import struct
import zlib
from typing import Any, Dict, List
from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class PNGValidator(BaseValidator):
    """Validates PNG magic header, chunk sequencing, CRC-32 integrity, and IEND chunk."""

    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        errors: List[str] = []
        details: Dict[str, Any] = {"chunks": []}
        score = 0

        buf = data[start_offset:]
        buf_len = len(buf)

        if buf_len < 8:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Data too small for PNG signature"],
            )

        if buf[:8] != PNG_MAGIC:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Invalid PNG magic signature"],
            )

        score += 5
        offset = 8
        first_chunk = True
        iend_found = False
        crc_failures = 0
        crc_passes = 0

        while offset + 8 <= buf_len:
            chunk_len = struct.unpack(">I", buf[offset : offset + 4])[0]
            chunk_type = buf[offset + 4 : offset + 8]

            # Enforce max chunk size sanity check (32MB)
            if chunk_len > 32 * 1024 * 1024:
                errors.append(f"Excessive chunk length: {chunk_len}")
                break

            total_chunk_size = 12 + chunk_len
            if offset + total_chunk_size > buf_len:
                errors.append("Truncated PNG chunk data")
                break

            chunk_data = buf[offset + 8 : offset + 8 + chunk_len]
            expected_crc = struct.unpack(">I", buf[offset + 8 + chunk_len : offset + total_chunk_size])[0]

            # Verify CRC-32
            computed_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
            if computed_crc == expected_crc:
                crc_passes += 1
            else:
                crc_failures += 1
                errors.append(f"CRC-32 mismatch on chunk {chunk_type!r}")

            type_str = chunk_type.decode("latin-1", errors="replace")
            details["chunks"].append(type_str)

            if first_chunk:
                first_chunk = False
                if chunk_type != b"IHDR" or chunk_len < 13:
                    errors.append(f"First chunk must be IHDR, got {chunk_type!r}")
                    break

                width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk_data[:10])
                details["width"] = width
                details["height"] = height
                details["bit_depth"] = bit_depth
                details["color_type"] = color_type

                if width > 0 and height > 0:
                    score += 10
                else:
                    errors.append("Invalid IHDR dimensions")

            if chunk_type == b"IDAT":
                score = max(score, 20)

            if chunk_type == b"IEND":
                iend_found = True
                offset += total_chunk_size
                score += 5
                break

            offset += total_chunk_size

        if crc_passes > 0 and crc_failures == 0:
            score += 5

        estimated_size = offset
        is_valid = iend_found and "width" in details and crc_failures == 0

        return ValidationResult(
            is_valid=is_valid,
            estimated_size=estimated_size,
            structure_score=min(score, 30),
            footer_found=iend_found,
            details=details,
            errors=errors,
        )
