"""
Unit tests for DeviceDetector and DeviceInfo.
"""

from forensics_platform.sanitization.device_detector import DeviceDetector, DeviceInfo


def test_device_info_properties():
    """Verify DeviceInfo helper properties."""
    dev = DeviceInfo(
        device_path="/dev/sdb",
        name="sdb",
        size_bytes=1000 * 1024 * 1024 * 1024,  # ~1000 GB
        model="Samsung 870 EVO",
        is_rotational=False,
        mountpoints=[],
        partitions=[{"name": "sdb1", "mountpoints": ["/mnt/data"]}],
    )
    assert dev.is_mounted is True
    assert "GB" in dev.size_formatted
    assert "Samsung" in dev.model


def test_base_disk_name_parsing():
    """Verify partition name to base device name resolution."""
    assert DeviceDetector._get_base_disk_name("sda1") == "sda"
    assert DeviceDetector._get_base_disk_name("sdb12") == "sdb"
    assert DeviceDetector._get_base_disk_name("nvme0n1p2") == "nvme0n1"
    assert DeviceDetector._get_base_disk_name("mmcblk0p1") == "mmcblk0"


def test_enumerate_devices():
    """Verify device detector runs on current system without throwing exceptions."""
    detector = DeviceDetector()
    devices = detector.enumerate_devices()
    assert isinstance(devices, list)
    # If any devices found, check attributes
    for d in devices:
        assert d.device_path.startswith("/dev/")
        assert d.size_bytes >= 0
