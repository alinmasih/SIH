"""
Base Sanitizer module - defines abstract interface and standards for drive sanitizers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from forensics_platform.sanitization.device_detector import DeviceInfo


class SanitizationStandard(str, Enum):
    """Sanitization standards supported by the platform."""
    NIST_800_88_CLEAR = "NIST SP 800-88 Rev 1 Clear"
    NIST_800_88_PURGE = "NIST SP 800-88 Rev 1 Purge"
    DOD_5220_22_M = "DoD 5220.22-M (3 Passes)"
    DOD_5220_22_M_ECE = "DoD 5220.22-M ECE (7 Passes)"
    ZERO_OVERWRITE = "Single-Pass Zero Overwrite"
    RANDOM_OVERWRITE = "Single-Pass Random Overwrite"


@dataclass
class SanitizationResult:
    """Outcome of a drive sanitization operation."""
    success: bool
    bytes_written: int
    passes_completed: int
    duration_seconds: float
    throughput_mb_s: float = 0.0
    standard_applied: str = ""
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class BaseSanitizer(ABC):
    """Abstract base class for storage media sanitizers."""

    @abstractmethod
    def sanitize(
        self,
        device: DeviceInfo,
        standard: SanitizationStandard = SanitizationStandard.NIST_800_88_CLEAR,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> SanitizationResult:
        """
        Execute sanitization on target storage device.

        Args:
            device: DeviceInfo representing target media.
            standard: SanitizationStandard to execute.
            progress_callback: Optional callback reporting live progress dict.
            cancel_token: Optional callable returning True if cancellation requested.

        Returns:
            SanitizationResult.
        """
        pass
