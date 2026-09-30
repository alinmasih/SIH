"""
Unit tests for SafetyChecker.
"""

from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.safety_checks import SafetyChecker


def test_system_disk_blocked_in_real_mode():
    """Verify system disk is strictly blocked when simulation_mode is False."""
    sys_dev = DeviceInfo(
        device_path="/dev/nvme0n1",
        name="nvme0n1",
        size_bytes=512 * 1024 * 1024 * 1024,
        is_system_disk=True,
    )

    res = SafetyChecker.evaluate_device(
        device=sys_dev,
        simulation_mode=False,
        confirmation_count=3,
        required_confirmations=3,
    )
    assert res.blocked is True
    assert res.is_safe is False
    assert any("CRITICAL SAFETY LOCK" in err for err in res.errors)


def test_system_disk_warning_in_simulation_mode():
    """Verify system disk generates non-blocking warning in simulation mode."""
    sys_dev = DeviceInfo(
        device_path="/dev/nvme0n1",
        name="nvme0n1",
        size_bytes=512 * 1024 * 1024 * 1024,
        is_system_disk=True,
    )

    res = SafetyChecker.evaluate_device(
        device=sys_dev,
        simulation_mode=True,
        confirmation_count=3,
        required_confirmations=3,
    )
    assert res.blocked is False
    assert res.is_safe is True
    assert any("SIMULATION ONLY" in w for w in res.warnings)


def test_insufficient_confirmations():
    """Verify operation is blocked when confirmations are below threshold."""
    dev = DeviceInfo(
        device_path="/dev/sdb",
        name="sdb",
        size_bytes=1000,
        is_system_disk=False,
    )

    res = SafetyChecker.evaluate_device(
        device=dev,
        simulation_mode=True,
        confirmation_count=1,
        required_confirmations=3,
    )
    assert res.is_safe is False
    assert any("Insufficient user confirmations" in err for err in res.errors)
