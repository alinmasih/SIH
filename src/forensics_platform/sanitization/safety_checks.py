"""
Safety Checks module - safeguards preventing accidental destruction of system disks or mounted media.
"""

import os
from dataclasses import dataclass, field
from typing import List

from forensics_platform.sanitization.device_detector import DeviceInfo


@dataclass
class SafetyCheckResult:
    """Outcome of safety check evaluation."""
    is_safe: bool
    blocked: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SafetyChecker:
    """Evaluates critical safety constraints before executing drive or file erasure."""

    @staticmethod
    def evaluate_device(
        device: DeviceInfo,
        simulation_mode: bool = True,
        confirmation_count: int = 0,
        required_confirmations: int = 3,
    ) -> SafetyCheckResult:
        """
        Evaluate safety constraints for a target storage device.

        Args:
            device: DeviceInfo of the target.
            simulation_mode: If True, allow virtual execution with warnings.
            confirmation_count: Number of explicit user confirmations entered.
            required_confirmations: Number of confirmations required.

        Returns:
            SafetyCheckResult indicating if operation is permitted.
        """
        warnings: List[str] = []
        errors: List[str] = []
        blocked = False

        # 1. System Disk Protection
        if device.is_system_disk:
            msg = (
                f"CRITICAL SAFETY LOCK: {device.device_path} contains the operating system root (/) "
                f"or boot partition. Erasing this drive would destroy the host OS!"
            )
            if not simulation_mode:
                errors.append(msg)
                blocked = True
            else:
                warnings.append(f"[SIMULATION ONLY] {msg}")

        # 2. Mounted Partitions Protection
        if device.is_mounted:
            mounts = device.mountpoints[:]
            for p in device.partitions:
                mounts.extend(p.get("mountpoints", []))
            mount_str = ", ".join(mounts)
            msg = f"Device {device.device_path} has active mountpoints ({mount_str}). Media must be unmounted before sanitization."
            if not simulation_mode:
                errors.append(msg)
                blocked = True
            else:
                warnings.append(f"[SIMULATION ONLY] {msg}")

        # 3. Read-Only Media
        if device.read_only:
            msg = f"Device {device.device_path} is marked read-only by hardware or kernel."
            if not simulation_mode:
                errors.append(msg)
                blocked = True
            else:
                warnings.append(f"[SIMULATION ONLY] {msg}")

        # 4. Root / Sudo privileges for raw physical access
        if not simulation_mode and os.geteuid() != 0:
            errors.append("Superuser (root) privileges are required to perform physical block-level sanitization.")
            blocked = True

        # 5. Confirmation threshold check
        if confirmation_count < required_confirmations:
            msg = f"Insufficient user confirmations: {confirmation_count}/{required_confirmations} provided."
            errors.append(msg)
            # Not hard-blocked from system, but blocked until confirmed

        is_safe = (len(errors) == 0) and not blocked

        return SafetyCheckResult(
            is_safe=is_safe,
            blocked=blocked,
            warnings=warnings,
            errors=errors,
        )
