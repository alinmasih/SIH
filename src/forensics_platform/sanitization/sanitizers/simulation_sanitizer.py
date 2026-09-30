"""
Simulation Sanitizer module - safely simulates full drive sanitization workflows.

Ensures zero physical writes to target storage media, enabling 100% safe testing and audits.
"""

import time
from typing import Any, Callable, Dict, Optional

from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.sanitizers.base_sanitizer import (
    BaseSanitizer,
    SanitizationResult,
    SanitizationStandard,
)


class SimulationSanitizer(BaseSanitizer):
    """Safely simulates sanitization passes, throughput, and progress callbacks."""

    def __init__(self, step_delay: float = 0.05):
        """
        Args:
            step_delay: Simulated delay per progress tick in seconds.
        """
        self.step_delay = step_delay

    def sanitize(
        self,
        device: DeviceInfo,
        standard: SanitizationStandard = SanitizationStandard.NIST_800_88_CLEAR,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> SanitizationResult:
        start_time = time.time()

        # Determine pass count based on standard
        if standard == SanitizationStandard.DOD_5220_22_M:
            total_passes = 3
        elif standard == SanitizationStandard.DOD_5220_22_M_ECE:
            total_passes = 7
        else:
            total_passes = 1

        dev_size = max(1024 * 1024, device.size_bytes)
        bytes_written = 0

        for current_pass in range(1, total_passes + 1):
            steps = 10
            for step in range(1, steps + 1):
                if cancel_token and cancel_token():
                    duration = max(0.001, time.time() - start_time)
                    return SanitizationResult(
                        success=False,
                        bytes_written=bytes_written,
                        passes_completed=current_pass - 1,
                        duration_seconds=duration,
                        throughput_mb_s=round((bytes_written / (1024 * 1024)) / duration, 2),
                        standard_applied=standard.value,
                        errors=["Sanitization cancelled by user"],
                        details={"simulation": True, "cancelled": True},
                    )

                time.sleep(self.step_delay)
                chunk_bytes = dev_size // steps
                bytes_written += chunk_bytes
                pass_pct = (step / steps) * 100.0
                total_pct = (((current_pass - 1) * steps + step) / (total_passes * steps)) * 100.0

                if progress_callback:
                    progress_callback({
                        "simulation": True,
                        "current_pass": current_pass,
                        "total_passes": total_passes,
                        "pass_percent": round(pass_pct, 1),
                        "overall_percent": round(total_pct, 1),
                        "bytes_written": bytes_written,
                        "total_bytes": dev_size * total_passes,
                        "status": f"[SIMULATION] Pass {current_pass}/{total_passes} - {standard.value}",
                    })

        duration = max(0.001, time.time() - start_time)
        throughput = round((bytes_written / (1024 * 1024)) / duration, 2)

        return SanitizationResult(
            success=True,
            bytes_written=bytes_written,
            passes_completed=total_passes,
            duration_seconds=round(duration, 3),
            throughput_mb_s=throughput,
            standard_applied=standard.value,
            details={
                "simulation": True,
                "device": device.device_path,
                "passes": total_passes,
            },
        )
