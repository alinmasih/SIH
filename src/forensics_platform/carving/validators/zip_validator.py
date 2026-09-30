"""
ZIP Validator - binary structure validation for ZIP archives and Office documents (DOCX/XLSX).
"""

import struct
from typing import Any, Dict, List
from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult

LOCAL_FILE_HEADER = b"PK\x03\x04"
CENTRAL_DIR_HEADER = b"PK\x01\x02"
EOCD_HEADER = b"PK\x05\x06"


class ZIPValidator(BaseValidator):
    """Validates ZIP local headers, central directory, and End of Central Directory record."""

    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        errors: List[str] = []
        details: Dict[str, Any] = {"files": []}
        score = 0

        buf = data[start_offset:]
        buf_len = len(buf)

        if buf_len < 30:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Data too small for ZIP header"],
            )

        if buf[:4] != LOCAL_FILE_HEADER:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Missing PK\\x03\\x04 local file header"],
            )

        score += 10

        # Read first local file header
        fn_len = struct.unpack("<H", buf[26:28])[0]
        extra_len = struct.unpack("<H", buf[28:30])[0]

        if 30 + fn_len <= buf_len:
            first_fn = buf[30 : 30 + fn_len].decode("utf-8", errors="replace")
            details["first_file"] = first_fn
            score += 5

        # Look for EOCD record
        # EOCD is minimum 22 bytes, search backwards or throughout buffer
        eocd_pos = buf.rfind(EOCD_HEADER)
        eocd_found = False
        estimated_size = 0

        if eocd_pos != -1 and eocd_pos + 22 <= buf_len:
            eocd_found = True
            score += 10

            # Unpack EOCD
            total_entries = struct.unpack("<H", buf[eocd_pos + 10 : eocd_pos + 12])[0]
            cd_size = struct.unpack("<I", buf[eocd_pos + 12 : eocd_pos + 16])[0]
            cd_offset = struct.unpack("<I", buf[eocd_pos + 16 : eocd_pos + 20])[0]
            comment_len = struct.unpack("<H", buf[eocd_pos + 20 : eocd_pos + 22])[0]

            details["total_entries"] = total_entries
            details["cd_size"] = cd_size
            details["cd_offset"] = cd_offset

            # Check consistency
            if cd_offset + cd_size <= eocd_pos:
                score += 5

            estimated_size = eocd_pos + 22 + comment_len
        else:
            errors.append("Missing or incomplete End of Central Directory (EOCD)")
            # Fallback size
            estimated_size = min(buf_len, 5 * 1024 * 1024)

        if CENTRAL_DIR_HEADER in buf:
            details["has_central_directory"] = True

        is_valid = eocd_found and score >= 20

        return ValidationResult(
            is_valid=is_valid,
            estimated_size=estimated_size,
            structure_score=min(score, 30),
            footer_found=eocd_found,
            details=details,
            errors=errors,
        )
