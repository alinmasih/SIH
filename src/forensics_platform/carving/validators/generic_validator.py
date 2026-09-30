"""
Generic Validator - fallback validator using header/footer matching and boundary checks.
"""

from typing import Any, Dict, List, Optional
from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult


class GenericValidator(BaseValidator):
    """Fallback validator that locates optional footer and bounds size."""

    def __init__(self, footer: Optional[bytes] = None, max_size: int = 10 * 1024 * 1024):
        self.footer = footer
        self.max_size = max_size

    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        buf = data[start_offset:]
        buf_len = len(buf)

        if buf_len < 4:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Buffer too small"],
            )

        footer_found = False
        estimated_size = min(buf_len, self.max_size)

        if self.footer:
            f_pos = buf.find(self.footer)
            if f_pos != -1:
                footer_found = True
                estimated_size = f_pos + len(self.footer)

        score = 20 if footer_found else 10

        return ValidationResult(
            is_valid=True,
            estimated_size=estimated_size,
            structure_score=score,
            footer_found=footer_found,
            details={"generic_carve": True},
        )
