"""
PDF Validator - binary structure validation for Adobe PDF documents.
"""

import re
from typing import Any, Dict, List
from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult

PDF_HEADER_REGEX = re.compile(rb"^%PDF-(\d\.\d)")
EOF_MARKER = b"%%EOF"


class PDFValidator(BaseValidator):
    """Validates PDF header, version, stream/object structure, and %%EOF marker."""

    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        errors: List[str] = []
        details: Dict[str, Any] = {}
        score = 0

        buf = data[start_offset:]
        buf_len = len(buf)

        if buf_len < 32:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Data too small for PDF structure"],
            )

        match = PDF_HEADER_REGEX.match(buf[:16])
        if not match:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Invalid or missing %PDF- header"],
            )

        score += 5
        version_str = match.group(1).decode("ascii", errors="replace")
        details["version"] = version_str
        score += 5

        # Check for obj / endobj
        has_obj = b"obj" in buf and b"endobj" in buf
        if has_obj:
            score += 10
            details["has_objects"] = True

        # Find last %%EOF
        last_eof = buf.rfind(EOF_MARKER)
        eof_found = False
        estimated_size = 0

        if last_eof != -1:
            eof_found = True
            score += 10
            # Include %%EOF and trailing whitespace/newline
            eof_end = last_eof + len(EOF_MARKER)
            while eof_end < buf_len and buf[eof_end : eof_end + 1] in b"\r\n \t":
                eof_end += 1
            estimated_size = eof_end
            details["eof_offset"] = last_eof
        else:
            errors.append("Missing %%EOF footer")
            # If no EOF found, estimate up to next sector or end
            estimated_size = min(buf_len, 1024 * 1024)

        if b"startxref" in buf:
            details["has_startxref"] = True

        is_valid = eof_found and score >= 20

        return ValidationResult(
            is_valid=is_valid,
            estimated_size=estimated_size,
            structure_score=min(score, 30),
            footer_found=eof_found,
            details=details,
            errors=errors,
        )
