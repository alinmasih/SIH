"""
Unit tests for DeviceClassifier.
"""

from forensics_platform.sanitization.device_classifier import DeviceClassifier, DeviceType
from forensics_platform.sanitization.device_detector import DeviceInfo


def test_classify_nvme():
    dev = DeviceInfo(
        device_path="/dev/nvme0n1",
        name="nvme0n1",
        size_bytes=512 * 1024 * 1024 * 1024,
        bus_type="nvme",
        is_rotational=False,
    )
    assert DeviceClassifier.classify(dev) == DeviceType.NVME


def test_classify_ssd():
    dev = DeviceInfo(
        device_path="/dev/sda",
        name="sda",
        size_bytes=256 * 1024 * 1024 * 1024,
        bus_type="sata",
        is_rotational=False,
    )
    assert DeviceClassifier.classify(dev) == DeviceType.SSD


def test_classify_hdd():
    dev = DeviceInfo(
        device_path="/dev/sdc",
        name="sdc",
        size_bytes=2000 * 1024 * 1024 * 1024,
        bus_type="sata",
        is_rotational=True,
    )
    assert DeviceClassifier.classify(dev) == DeviceType.HDD


def test_classify_usb():
    dev = DeviceInfo(
        device_path="/dev/sdd",
        name="sdd",
        size_bytes=32 * 1024 * 1024 * 1024,
        bus_type="usb",
        is_removable=True,
    )
    assert DeviceClassifier.classify(dev) == DeviceType.USB


def test_recommend_sanitization():
    hdd = DeviceInfo(device_path="/dev/sda", name="sda", size_bytes=1000, is_rotational=True)
    ssd = DeviceInfo(device_path="/dev/nvme0n1", name="nvme0n1", size_bytes=1000, is_rotational=False)

    rec_hdd = DeviceClassifier.recommend_sanitization(hdd)
    assert "Clear" in rec_hdd["standard"]

    rec_ssd = DeviceClassifier.recommend_sanitization(ssd)
    assert "Purge" in rec_ssd["standard"]
    assert "Wear Leveling" in rec_ssd["notes"]
