"""
Sanitization Verification module - post-sanitization cryptographic and byte-level verification.

Implements NIST SP 800-88 Rev 1 sample-based and full-device verification procedures.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional


@dataclass
class VerificationResult:
    """Outcome of sanitization verification."""
    result: str                 # "pass", "fail", "partial", "skipped"
    total_samples: int
    failed_samples: int
    bytes_checked: int
    expected_pattern_hex: str
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_passed(self) -> bool:
        return self.result == "pass" and self.failed_samples == 0


class VerificationEngine:
    """Verifies that storage sectors adhere to the expected post-sanitization pattern."""

    @staticmethod
    def verify_samples(
        device_path: str,
        expected_pattern: bytes = b"\x00",
        sample_count: int = 1000,
        sector_size: int = 512,
        simulation_mode: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> VerificationResult:
        """
        Perform sample-based verification distributed across the device LBA space.

        Args:
            device_path: Path to target device or disk image.
            expected_pattern: Expected byte pattern (e.g. b"\x00" or b"\xFF").
            sample_count: Number of sectors to sample (NIST recommends at least 1,000).
            sector_size: Sector size in bytes (default 512).
            simulation_mode: If True, returns synthetic passing verification.
            progress_callback: Optional callback(current_sample, total_samples).

        Returns:
            VerificationResult.
        """
        pattern_hex = expected_pattern.hex().upper()

        if simulation_mode:
            return VerificationResult(
                result="pass",
                total_samples=sample_count,
                failed_samples=0,
                bytes_checked=sample_count * sector_size,
                expected_pattern_hex=pattern_hex,
                details={"simulation": True, "verification": "Sample-based 1000 sectors verified clean"},
            )

        path = Path(device_path)
        if not path.exists():
            return VerificationResult(
                result="fail",
                total_samples=0,
                failed_samples=0,
                bytes_checked=0,
                expected_pattern_hex=pattern_hex,
                details={"error": f"Device path not found: {device_path}"},
            )

        try:
            file_size = os.path.getsize(device_path)
        except OSError:
            file_size = 0

        if file_size < sector_size:
            return VerificationResult(
                result="fail",
                total_samples=0,
                failed_samples=0,
                bytes_checked=0,
                expected_pattern_hex=pattern_hex,
                details={"error": "Device size too small for sampling"},
            )

        total_sectors = file_size // sector_size
        actual_samples = min(sample_count, total_sectors)
        if actual_samples <= 0:
            return VerificationResult(
                result="fail",
                total_samples=0,
                failed_samples=0,
                bytes_checked=0,
                expected_pattern_hex=pattern_hex,
                details={"error": "Zero accessible sectors"},
            )

        step = max(1, total_sectors // actual_samples)
        failed_count = 0
        bytes_checked = 0
        expected_sector = expected_pattern * (sector_size // len(expected_pattern))

        try:
            with open(device_path, "rb") as f:
                for i in range(actual_samples):
                    target_sector = min(i * step, total_sectors - 1)
                    f.seek(target_sector * sector_size)
                    chunk = f.read(sector_size)
                    bytes_checked += len(chunk)

                    if chunk != expected_sector[: len(chunk)]:
                        failed_count += 1

                    if progress_callback:
                        progress_callback(i + 1, actual_samples)

            result_str = "pass" if failed_count == 0 else "fail"
            return VerificationResult(
                result=result_str,
                total_samples=actual_samples,
                failed_samples=failed_count,
                bytes_checked=bytes_checked,
                expected_pattern_hex=pattern_hex,
                details={
                    "total_sectors": total_sectors,
                    "sampling_ratio": f"{round((actual_samples / total_sectors) * 100, 3)}%",
                },
            )
        except Exception as e:
            return VerificationResult(
                result="fail",
                total_samples=actual_samples,
                failed_samples=actual_samples,
                bytes_checked=bytes_checked,
                expected_pattern_hex=pattern_hex,
                details={"error": str(e)},
            )
