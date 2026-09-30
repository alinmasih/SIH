"""
Carving package - advanced file carving, signature scanning, structure validation,
and confidence scoring for digital forensics.
"""

from forensics_platform.carving.signature_database import FileSignature, SignatureDatabase
from forensics_platform.carving.signature_scanner import ScanCandidate, SignatureScanner
from forensics_platform.carving.confidence_engine import ConfidenceEngine, ConfidenceScore
from forensics_platform.carving.validators import (
    BaseValidator,
    ValidationResult,
    JPEGValidator,
    PNGValidator,
    PDFValidator,
    ZIPValidator,
    GenericValidator,
    ValidatorRegistry,
)
from forensics_platform.carving.carving_engine import CarvingEngine

__all__ = [
    "FileSignature",
    "SignatureDatabase",
    "ScanCandidate",
    "SignatureScanner",
    "ConfidenceEngine",
    "ConfidenceScore",
    "BaseValidator",
    "ValidationResult",
    "JPEGValidator",
    "PNGValidator",
    "PDFValidator",
    "ZIPValidator",
    "GenericValidator",
    "ValidatorRegistry",
    "CarvingEngine",
]
