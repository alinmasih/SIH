"""
HDD Sanitizer module - patterned multi-pass block overwriter for magnetic media.

Implements NIST SP 800-88 Clear and DoD 5220.22-M multi-pass overwrites with synchronized I/O.
"""

import os
import time
from typing import Any, Callable, Dict, List, Optional

from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.sanitizers.base_sanitizer import (
    BaseSanitizer,
    SanitizationResult,
    SanitizationStandard,
)


class HDDSanitizer(BaseSanitizer):
    """Executes multi-pass block-level overwriting on physical block devices or images."""

    def __init__(self, chunk_size: int = 2 * 1024 * 1024):
        """
        Args:
            chunk_size: Buffer chunk size in bytes (default 2MB).
        """
        self.chunk_size = chunk_size

    def _get_patterns(self, standard: SanitizationStandard) -> List[Optional[bytes]]:
        """
        Return list of fill patterns per pass.
        None indicates cryptographically secure random bytes.
        """
        if standard == SanitizationStandard.DOD_5220_22_M:
            return [b"\x00", b"\xff", None]
        elif standard == SanitizationStandard.DOD_5220_22_M_ECE:
            return [b"\x00", b"\xff", None, b"\x96", b"\x00", b"\xff", None]
        elif standard == SanitizationStandard.RANDOM_OVERWRITE:
            return [None]
        else:
            # NIST_800_88_CLEAR or ZERO_OVERWRITE
            return [b"\x00"]

    def sanitize(
        self,
        device: DeviceInfo,
        standard: SanitizationStandard = SanitizationStandard.NIST_800_88_CLEAR,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> SanitizationResult:
        patterns = self._get_patterns(standard)
        total_passes = len(patterns)
        total_dev_bytes = device.size_bytes
        total_bytes_to_write = total_dev_bytes * total_passes

        start_time = time.time()
        bytes_written_total = 0
        passes_completed = 0

        target_path = device.device_path
        if not os.path.exists(target_path):
            return SanitizationResult(
                success=False,
                bytes_written=0,
                passes_completed=0,
                duration_seconds=0.0,
                standard_applied=standard.value,
                errors=[f"Device path does not exist: {target_path}"],
            )

        try:
            with open(target_path, "r+b") as f:
                fd = f.fileno()

                for pass_idx, pattern_byte in enumerate(patterns, start=1):
                    f.seek(0)
                    pass_bytes_written = 0

                    # Pre-allocate buffer for fixed patterns
                    if pattern_byte is not None:
                        chunk_buffer = pattern_byte * self.chunk_size
                    else:
                        chunk_buffer = None

                    while pass_bytes_written < total_dev_bytes:
                        if cancel_token and cancel_token():
                            duration = max(0.001, time.time() - start_time)
                            return SanitizationResult(
                                success=False,
                                bytes_written=bytes_written_total,
                                passes_completed=passes_completed,
                                duration_seconds=duration,
                                throughput_mb_s=round((bytes_written_total / (1024 * 1024)) / duration, 2),
                                standard_applied=standard.value,
                                errors=["Sanitization cancelled by user"],
                            )

                        to_write = min(self.chunk_size, total_dev_bytes - pass_bytes_written)
                        if pattern_byte is not None:
                            buf = chunk_buffer[:to_write]
                        else:
                            buf = os.urandom(to_write)

                        f.write(buf)
                        pass_bytes_written += to_write
                        bytes_written_total += to_write

                        if progress_callback:
                            elapsed = max(0.001, time.time() - start_time)
                            rate_mb = (bytes_written_total / (1024 * 1024)) / elapsed
                            pass_pct = (pass_bytes_written / total_dev_bytes) * 100.0
                            overall_pct = (bytes_written_total / total_bytes_to_write) * 100.0

                            progress_callback({
                                "current_pass": pass_idx,
                                "total_passes": total_passes,
                                "pass_percent": round(pass_pct, 1),
                                "overall_percent": round(overall_pct, 1),
                                "bytes_written": bytes_written_total,
                                "throughput_mb_s": round(rate_mb, 2),
                                "status": f"Pass {pass_idx}/{total_passes} ({round(rate_mb, 1)} MB/s)",
                            })

                    # Flush and sync at end of pass
                    f.flush()
                    try:
                        os.fdatasync(fd)
                    except OSError:
                        pass
                    passes_completed += 1

            duration = max(0.001, time.time() - start_time)
            throughput = round((bytes_written_total / (1024 * 1024)) / duration, 2)

            return SanitizationResult(
                success=True,
                bytes_written=bytes_written_total,
                passes_completed=passes_completed,
                duration_seconds=round(duration, 3),
                throughput_mb_s=throughput,
                standard_applied=standard.value,
                details={
                    "device": target_path,
                    "passes": passes_completed,
                    "chunk_size": self.chunk_size,
                },
            )

        except Exception as e:
            duration = max(0.001, time.time() - start_time)
            return SanitizationResult(
                success=False,
                bytes_written=bytes_written_total,
                passes_completed=passes_completed,
                duration_seconds=round(duration, 3),
                standard_applied=standard.value,
                errors=[str(e)],
            )
