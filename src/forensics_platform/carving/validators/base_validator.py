"""
Base Validator module - defines interface and result structure for file validators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ValidationResult:
    """Outcome of structure validation for a candidate carved file."""
    is_valid: bool
    estimated_size: int
    structure_score: int = 0      # 0 to 30 points
    footer_found: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class BaseValidator(ABC):
    """Abstract base class for format-specific binary structure validators."""

    @abstractmethod
    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        """
        Validate binary structure starting at start_offset in data.

        Args:
            data: Binary buffer starting at or before the candidate file.
            start_offset: Offset where file begins within data.

        Returns:
            ValidationResult containing status, estimated size, and score.
        """
        pass
