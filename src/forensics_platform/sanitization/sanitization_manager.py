"""
Sanitization Manager module - central orchestrator for storage media sanitization.

Coordinates device detection, safety checks, multi-pass sanitizers, post-erasure verification,
database persistence (SanitizationOperation), and tamper-evident audit logging.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from forensics_platform.core.config import Config

from forensics_platform.database.models import Operation, SanitizationOperation
from forensics_platform.database.session import DatabaseManager
from forensics_platform.sanitization.device_classifier import DeviceClassifier, DeviceType
from forensics_platform.sanitization.device_detector import DeviceDetector, DeviceInfo
from forensics_platform.sanitization.safety_checks import SafetyChecker, SafetyCheckResult
from forensics_platform.sanitization.sanitizers import (
    BaseSanitizer,
    HDDSanitizer,
    SanitizationResult,
    SanitizationStandard,
    SimulationSanitizer,
    SSDSanitizer,
)
from forensics_platform.sanitization.verification import VerificationEngine, VerificationResult

logger = logging.getLogger(__name__)


class SanitizationManager:
    """Manages full lifecycle of drive sanitization operations."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        audit_logger: Optional[Any] = None,
        config: Optional["Config"] = None,
    ):
        self.db = db_manager
        self.audit = audit_logger
        if config is None:
            from forensics_platform.core.config import Config
            config = Config()
        self.config = config

        self.detector = DeviceDetector()
        self.classifier = DeviceClassifier()
        self.safety_checker = SafetyChecker()
        self.verification_engine = VerificationEngine()

        self.simulation_sanitizer = SimulationSanitizer()
        self.hdd_sanitizer = HDDSanitizer()
        self.ssd_sanitizer = SSDSanitizer()

    def list_devices(self) -> List[DeviceInfo]:
        """Enumerate all available storage devices."""
        return self.detector.enumerate_devices()

    def get_device(self, device_path: str) -> Optional[DeviceInfo]:
        """Retrieve DeviceInfo for a specific path."""
        return self.detector.get_device_info(device_path)

    def check_safety(
        self,
        device: DeviceInfo,
        confirmation_count: int = 0,
        required_confirmations: Optional[int] = None,
    ) -> SafetyCheckResult:
        """Evaluate safety constraints before erasing."""
        req_count = required_confirmations if required_confirmations is not None else self.config.confirmation_count
        sim_mode = self.config.simulation_mode
        return self.safety_checker.evaluate_device(
            device=device,
            simulation_mode=sim_mode,
            confirmation_count=confirmation_count,
            required_confirmations=req_count,
        )

    def sanitize_device(
        self,
        device: DeviceInfo,
        standard: SanitizationStandard = SanitizationStandard.NIST_800_88_CLEAR,
        confirmation_count: int = 3,
        case_id: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> Tuple[SanitizationResult, VerificationResult]:
        """
        Execute sanitization, post-erasure verification, DB logging, and audit tracking.

        Args:
            device: DeviceInfo to sanitize.
            standard: Sanitization standard to apply.
            confirmation_count: Number of explicit user confirmations entered.
            case_id: Optional active case ID.
            progress_callback: Optional progress callback reporting dict.
            cancel_token: Optional callable returning True if cancellation requested.

        Returns:
            Tuple of (SanitizationResult, VerificationResult).
        """
        sim_mode = self.config.simulation_mode

        # Safety Check
        safety = self.check_safety(device, confirmation_count=confirmation_count)
        if not safety.is_safe and safety.blocked:
            error_msg = f"Sanitization BLOCKED by Safety Check: {'; '.join(safety.errors)}"
            logger.error(error_msg)
            res = SanitizationResult(
                success=False,
                bytes_written=0,
                passes_completed=0,
                duration_seconds=0.0,
                standard_applied=standard.value,
                errors=safety.errors,
            )
            ver = VerificationResult(
                result="skipped",
                total_samples=0,
                failed_samples=0,
                bytes_checked=0,
                expected_pattern_hex="00",
                details={"reason": "Blocked by safety checks"},
            )
            return res, ver

        # Classify device
        dtype = self.classifier.classify(device)
        caps = self.classifier.detect_capabilities(device)

        # Audit start
        if self.audit:
            self.audit.log_event(
                event_type="sanitization_started",
                event_data={
                    "device": device.device_path,
                    "device_type": dtype.value,
                    "standard": standard.value,
                    "simulation_mode": sim_mode,
                    "size_bytes": device.size_bytes,
                },
                case_id=case_id,
            )

        # Database Operation initialization
        op_id = None
        if self.db:
            try:
                with self.db.session() as session:
                    op = Operation(
                        case_id=case_id,
                        operation_type="drive_sanitization",
                        target=device.device_path,
                        target_type="drive",
                        start_time=datetime.now(timezone.utc),
                        status="running",
                        tool_version="SanitizationEngine 1.0 (NIST SP 800-88)",
                        parameters=json.dumps({
                            "standard": standard.value,
                            "simulation_mode": sim_mode,
                            "confirmations": confirmation_count,
                        }),
                    )
                    session.add(op)
                    session.commit()
                    op_id = op.id
            except Exception as e:
                logger.error(f"Failed to record sanitization operation in DB: {e}")

        # Select sanitizer
        if sim_mode:
            sanitizer: BaseSanitizer = self.simulation_sanitizer
        elif dtype in (DeviceType.SSD, DeviceType.NVME):
            sanitizer = self.ssd_sanitizer
        else:
            sanitizer = self.hdd_sanitizer

        # Execute Sanitization
        san_result = sanitizer.sanitize(
            device=device,
            standard=standard,
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )

        # Post-Sanitization Verification
        if san_result.success:
            ver_result = self.verification_engine.verify_samples(
                device_path=device.device_path,
                expected_pattern=b"\x00",
                sample_count=1000,
                simulation_mode=sim_mode,
            )
        else:
            ver_result = VerificationResult(
                result="skipped",
                total_samples=0,
                failed_samples=0,
                bytes_checked=0,
                expected_pattern_hex="00",
                details={"reason": "Sanitization did not succeed"},
            )

        # Audit Event Logging
        if self.audit:
            self.audit.log_event(
                event_type="device_sanitized",
                event_data={
                    "device": device.device_path,
                    "success": san_result.success,
                    "passes": san_result.passes_completed,
                    "throughput_mb_s": san_result.throughput_mb_s,
                    "verification_result": ver_result.result,
                    "simulation_mode": sim_mode,
                },
                case_id=case_id,
            )

        # Database Finalization
        if self.db and op_id:
            try:
                with self.db.session() as session:
                    op = session.get(Operation, op_id)
                    if op:
                        op.status = "completed" if san_result.success else "failed"
                        op.end_time = datetime.now(timezone.utc)
                        op.bytes_processed = san_result.bytes_written
                        op.result = json.dumps({
                            "sanitization": {
                                "success": san_result.success,
                                "passes": san_result.passes_completed,
                                "throughput_mb_s": san_result.throughput_mb_s,
                            },
                            "verification": {
                                "result": ver_result.result,
                                "failed_samples": ver_result.failed_samples,
                                "total_samples": ver_result.total_samples,
                            },
                        })

                    san_op = SanitizationOperation(
                        operation_id=op_id,
                        device=device.device_path,
                        device_type=dtype.value,
                        device_model=device.model,
                        device_serial=device.serial,
                        capacity=device.size_bytes,
                        supports_secure_erase=caps.get("supports_secure_erase", False),
                        supports_crypto_erase=caps.get("supports_crypto_erase", False),
                        supports_trim=caps.get("supports_trim", False),
                        sanitization_method=standard.name,
                        sanitization_standard=standard.value,
                        pass_count=san_result.passes_completed,
                        pattern_used="0x00 (Zero)" if "Zero" in standard.value else "Patterned",
                        verification_method="NIST SP 800-88 LBA Sampling (1000 sectors)",
                        verification_result=ver_result.result,
                        verification_details=json.dumps(ver_result.details),
                        verification_sample_count=ver_result.total_samples,
                        verification_failed_samples=ver_result.failed_samples,
                        was_system_disk=device.is_system_disk,
                        was_mounted=device.is_mounted,
                        user_confirmation_count=confirmation_count,
                    )
                    session.add(san_op)
                    session.commit()
            except Exception as e:
                logger.error(f"Failed to record SanitizationOperation record in DB: {e}")

        return san_result, ver_result
