"""
Confidence Engine module - computes mathematical recovery confidence scores (0-100).
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict

from forensics_platform.carving.signature_database import FileSignature
from forensics_platform.carving.validators.base_validator import ValidationResult


@dataclass
class ConfidenceScore:
    """Confidence score breakdown and final classification."""
    signature_match: int        # 0 to 20 points
    structure_valid: int        # 0 to 30 points
    footer_valid: int           # 0 to 20 points
    size_consistent: int        # 0 to 15 points
    entropy_consistent: int     # 0 to 15 points
    total: int                  # 0 to 100 points
    classification: str         # "High", "Medium", "Low"
    factors: Dict[str, Any] = field(default_factory=dict)


class ConfidenceEngine:
    """Evaluates multi-factor confidence for candidate carved files."""

    @staticmethod
    def calculate_entropy(data: bytes, max_sample_size: int = 16384) -> float:
        """
        Calculate Shannon entropy (0.0 to 8.0) over a byte sample.

        Args:
            data: Binary data.
            max_sample_size: Maximum bytes to sample for speed.

        Returns:
            Shannon entropy as a float between 0.0 and 8.0.
        """
        if not data:
            return 0.0

        sample = data[:max_sample_size]
        sample_len = len(sample)
        counts = Counter(sample)

        entropy = 0.0
        for count in counts.values():
            p = count / sample_len
            entropy -= p * math.log2(p)

        return round(entropy, 2)

    def evaluate(
        self,
        signature: FileSignature,
        validation: ValidationResult,
        data: bytes,
    ) -> ConfidenceScore:
        """
        Compute confidence score based on signature, validation, and content payload.

        Args:
            signature: FileSignature definition matched.
            validation: ValidationResult from format validator.
            data: Carved bytes.

        Returns:
            ConfidenceScore instance.
        """
        factors: Dict[str, Any] = {}

        # 1. Signature match (up to 20 pts)
        sig_pts = 0
        if len(signature.header) > 0 and data.startswith(signature.header):
            sig_pts = 20
        elif len(signature.header) > 0:
            sig_pts = 10
        factors["signature_points"] = sig_pts

        # 2. Structure validity (up to 30 pts)
        struct_pts = min(30, max(0, validation.structure_score))
        factors["structure_points"] = struct_pts

        # 3. Footer validity (up to 20 pts)
        footer_pts = 0
        if validation.footer_found:
            footer_pts = 20
        elif signature.footer is None:
            # Format has no strict footer (e.g. some PDFs or streams)
            footer_pts = 10
        factors["footer_points"] = footer_pts

        # 4. Size consistency (up to 15 pts)
        size_pts = 0
        data_len = len(data)
        if signature.min_size <= data_len <= signature.max_size:
            size_pts = 15
        elif data_len > 0:
            size_pts = 5
        factors["size_points"] = size_pts
        factors["file_size"] = data_len

        # 5. Entropy check (up to 15 pts)
        entropy_pts = 0
        entropy = self.calculate_entropy(data)
        factors["entropy"] = entropy

        if signature.file_type in ("jpeg", "jpg", "png", "zip"):
            # Compressed formats should exhibit high entropy (> 5.0)
            if entropy >= 5.5:
                entropy_pts = 15
            elif entropy >= 4.0:
                entropy_pts = 10
            elif entropy >= 2.0:
                entropy_pts = 5
            else:
                entropy_pts = 0  # Likely sparse or zero-padded false positive
        elif signature.file_type == "pdf":
            # PDFs contain mixed text and compressed object streams (entropy 3.0 to 7.8)
            if 3.5 <= entropy <= 7.8:
                entropy_pts = 15
            elif entropy > 1.5:
                entropy_pts = 8
            else:
                entropy_pts = 0
        else:
            # Generic
            if entropy >= 2.0:
                entropy_pts = 15
            else:
                entropy_pts = 5

        factors["entropy_points"] = entropy_pts

        total = sig_pts + struct_pts + footer_pts + size_pts + entropy_pts
        total = min(100, max(0, total))

        if total >= 80:
            classification = "High"
        elif total >= 50:
            classification = "Medium"
        else:
            classification = "Low"

        return ConfidenceScore(
            signature_match=sig_pts,
            structure_valid=struct_pts,
            footer_valid=footer_pts,
            size_consistent=size_pts,
            entropy_consistent=entropy_pts,
            total=total,
            classification=classification,
            factors=factors,
        )
