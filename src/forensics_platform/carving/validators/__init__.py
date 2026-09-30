"""
Validators package - format-specific file structure validation.
"""

from typing import Dict, Optional

from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult
from forensics_platform.carving.validators.jpeg_validator import JPEGValidator
from forensics_platform.carving.validators.png_validator import PNGValidator
from forensics_platform.carving.validators.pdf_validator import PDFValidator
from forensics_platform.carving.validators.zip_validator import ZIPValidator
from forensics_platform.carving.validators.generic_validator import GenericValidator


class ValidatorRegistry:
    """Registry mapping file format names to validator instances."""

    def __init__(self):
        self._validators: Dict[str, BaseValidator] = {}
        self._generic_fallback = GenericValidator()
        self._register_defaults()

    def _register_defaults(self):
        jpeg_val = JPEGValidator()
        png_val = PNGValidator()
        pdf_val = PDFValidator()
        zip_val = ZIPValidator()

        self.register("jpeg", jpeg_val)
        self.register("jpg", jpeg_val)
        self.register("png", png_val)
        self.register("pdf", pdf_val)
        self.register("zip", zip_val)

    def register(self, format_name: str, validator: BaseValidator) -> None:
        """Register a format validator."""
        self._validators[format_name.lower()] = validator

    def get_validator(self, format_name: str) -> BaseValidator:
        """Retrieve validator for format name, or generic fallback."""
        return self._validators.get(format_name.lower(), self._generic_fallback)


__all__ = [
    "BaseValidator",
    "ValidationResult",
    "JPEGValidator",
    "PNGValidator",
    "PDFValidator",
    "ZIPValidator",
    "GenericValidator",
    "ValidatorRegistry",
]
