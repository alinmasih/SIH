"""
Unit tests for ConfidenceEngine.
"""

from forensics_platform.carving.confidence_engine import ConfidenceEngine
from forensics_platform.carving.signature_database import FileSignature
from forensics_platform.carving.validators.base_validator import ValidationResult


def test_calculate_entropy():
    """Verify entropy calculations for uniform zeros vs high-entropy bytes."""
    ce = ConfidenceEngine()

    zeroes = b"\x00" * 1024
    ent_zero = ce.calculate_entropy(zeroes)
    assert ent_zero == 0.0

    # Pattern with all 256 byte values repeated equally
    pattern = bytes(range(256)) * 4
    ent_max = ce.calculate_entropy(pattern)
    assert 7.9 <= ent_max <= 8.0


def test_confidence_evaluation_high():
    """Verify high confidence score for a well-formed file."""
    ce = ConfidenceEngine()
    sig = FileSignature(
        name="PNG Image",
        file_type="png",
        extensions=["png"],
        mime_type="image/png",
        header=b"\x89PNG\r\n\x1a\n",
        footer=b"IEND\xaeB`\x82",
        min_size=32,
        max_size=1024 * 1024,
    )
    val = ValidationResult(
        is_valid=True,
        estimated_size=512,
        structure_score=30,
        footer_found=True,
    )
    # High-entropy dummy payload starting with header
    data = sig.header + bytes(range(256)) + bytes(range(256))

    score = ce.evaluate(sig, val, data)
    assert score.total >= 80
    assert score.classification == "High"
    assert score.signature_match == 20
    assert score.structure_valid == 30
    assert score.footer_valid == 20


def test_confidence_evaluation_low():
    """Verify low confidence score for sparse or invalid data."""
    ce = ConfidenceEngine()
    sig = FileSignature(
        name="JPEG Image",
        file_type="jpeg",
        extensions=["jpg"],
        mime_type="image/jpeg",
        header=b"\xff\xd8\xff",
        footer=b"\xff\xd9",
        min_size=128,
        max_size=1024 * 1024,
    )
    val = ValidationResult(
        is_valid=False,
        estimated_size=64,
        structure_score=5,
        footer_found=False,
    )
    # All zeros payload
    data = b"\x00" * 64

    score = ce.evaluate(sig, val, data)
    assert score.total < 50
    assert score.classification == "Low"
