"""
Unit tests for Sanitizers and VerificationEngine.
"""

from pathlib import Path

from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.core.config import Config
from forensics_platform.database.models import Operation, SanitizationOperation
from forensics_platform.database.session import DatabaseManager
from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.sanitizers import (
    HDDSanitizer,
    SanitizationStandard,
    SimulationSanitizer,
)
from forensics_platform.sanitization.sanitization_manager import SanitizationManager
from forensics_platform.sanitization.verification import VerificationEngine


def test_simulation_sanitizer():
    """Verify SimulationSanitizer performs multi-pass progress ticks safely."""
    dev = DeviceInfo(device_path="/dev/virtual0", name="virtual0", size_bytes=10 * 1024 * 1024)
    sanitizer = SimulationSanitizer(step_delay=0.001)

    ticks = []

    def on_prog(p):
        ticks.append(p)

    res = sanitizer.sanitize(
        device=dev,
        standard=SanitizationStandard.DOD_5220_22_M,
        progress_callback=on_prog,
    )

    assert res.success is True
    assert res.passes_completed == 3
    assert len(ticks) >= 10
    assert res.throughput_mb_s > 0


def test_simulation_sanitizer_cancel():
    """Verify cancellation token stops SimulationSanitizer."""
    dev = DeviceInfo(device_path="/dev/virtual0", name="virtual0", size_bytes=10 * 1024 * 1024)
    sanitizer = SimulationSanitizer(step_delay=0.01)

    res = sanitizer.sanitize(
        device=dev,
        standard=SanitizationStandard.DOD_5220_22_M,
        cancel_token=lambda: True,
    )

    assert res.success is False
    assert any("cancelled" in err for err in res.errors)


def test_hdd_sanitizer_real_overwrite(tmp_path):
    """Verify HDDSanitizer actually overwrites blocks with zero pattern."""
    target_file = tmp_path / "virtual_disk.raw"
    # Create file with all 0xFF bytes
    target_file.write_bytes(b"\xff" * (128 * 1024))

    dev = DeviceInfo(device_path=str(target_file), name="virtual_disk.raw", size_bytes=128 * 1024)
    sanitizer = HDDSanitizer(chunk_size=32 * 1024)

    res = sanitizer.sanitize(
        device=dev,
        standard=SanitizationStandard.NIST_800_88_CLEAR,
    )

    assert res.success is True
    assert res.passes_completed == 1
    assert res.bytes_written == 128 * 1024

    # Verify bytes are all zero
    overwritten = target_file.read_bytes()
    assert overwritten == b"\x00" * (128 * 1024)


def test_verification_engine_pass_and_fail(tmp_path):
    """Verify VerificationEngine detects clean vs non-sanitized sectors."""
    clean_file = tmp_path / "clean.raw"
    clean_file.write_bytes(b"\x00" * (64 * 1024))

    dirty_file = tmp_path / "dirty.raw"
    dirty_data = bytearray(64 * 1024)
    dirty_data[1024:1536] = b"\xaa" * 512
    dirty_file.write_bytes(dirty_data)

    ve = VerificationEngine()

    res_clean = ve.verify_samples(str(clean_file), expected_pattern=b"\x00", sample_count=50)
    assert res_clean.is_passed is True
    assert res_clean.failed_samples == 0

    res_dirty = ve.verify_samples(str(dirty_file), expected_pattern=b"\x00", sample_count=128)
    assert res_dirty.is_passed is False
    assert res_dirty.failed_samples > 0


def test_sanitization_manager_pipeline(tmp_path):
    """Verify SanitizationManager executes, logs audit events, and writes DB records."""
    db_file = tmp_path / "san_test.db"
    db_manager = DatabaseManager(db_file)
    db_manager.initialize()
    audit_logger = AuditLogger(db_manager.get_session)

    cfg = Config(simulation_mode=True, confirmation_count=3)
    mgr = SanitizationManager(db_manager=db_manager, audit_logger=audit_logger, config=cfg)

    dev = DeviceInfo(
        device_path="/dev/mock_sdb",
        name="mock_sdb",
        size_bytes=100 * 1024 * 1024,
        is_rotational=True,
    )

    san_res, ver_res = mgr.sanitize_device(
        device=dev,
        standard=SanitizationStandard.NIST_800_88_CLEAR,
        confirmation_count=3,
        case_id=None,
    )

    assert san_res.success is True
    assert ver_res.is_passed is True

    # Check DB record
    with db_manager.session() as session:
        op = session.query(Operation).filter_by(operation_type="drive_sanitization").first()
        assert op is not None
        assert op.status == "completed"

        san_op = session.query(SanitizationOperation).filter_by(operation_id=op.id).first()
        assert san_op is not None
        assert san_op.device == "/dev/mock_sdb"
        assert san_op.verification_result == "pass"

    # Check audit chain
    chain = audit_logger.verify_integrity()
    assert chain["valid"] is True
    assert chain["total_events"] >= 3  # genesis + sanitization_started + device_sanitized
