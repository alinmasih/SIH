"""
Device Classifier module - classifies storage media and detects hardware sanitization capabilities.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict

from forensics_platform.sanitization.device_detector import DeviceInfo


class DeviceType(str, Enum):
    """Storage media device type classification."""
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    USB = "usb"
    SD_CARD = "sd_card"
    OTHER = "other"


class DeviceClassifier:
    """Classifies devices and recommends NIST SP 800-88 sanitization standards."""

    @staticmethod
    def classify(device: DeviceInfo) -> DeviceType:
        """
        Classify physical media type based on device metadata.

        Args:
            device: DeviceInfo instance.

        Returns:
            DeviceType enum value.
        """
        name = device.name.lower()
        bus = device.bus_type.lower()

        if name.startswith("nvme") or bus == "nvme":
            return DeviceType.NVME
        if device.is_removable or bus == "usb":
            return DeviceType.USB
        if name.startswith("mmcblk"):
            return DeviceType.SD_CARD
        if not device.is_rotational:
            return DeviceType.SSD
        if device.is_rotational:
            return DeviceType.HDD

        return DeviceType.OTHER

    @staticmethod
    def detect_capabilities(device: DeviceInfo) -> Dict[str, bool]:
        """
        Inspect device capabilities (TRIM, Secure Erase, Crypto Erase).

        Args:
            device: DeviceInfo instance.

        Returns:
            Dictionary with boolean capability flags.
        """
        caps = {
            "supports_trim": False,
            "supports_secure_erase": False,
            "supports_crypto_erase": False,
        }

        # Check discard support in sysfs
        discard_file = Path(f"/sys/block/{device.name}/queue/discard_max_bytes")
        if discard_file.exists():
            try:
                discard_bytes = int(discard_file.read_text().strip())
                caps["supports_trim"] = discard_bytes > 0
            except Exception:
                pass

        dtype = DeviceClassifier.classify(device)
        if dtype in (DeviceType.SSD, DeviceType.NVME):
            caps["supports_secure_erase"] = True
            if dtype == DeviceType.NVME:
                caps["supports_crypto_erase"] = True

        return caps

    @staticmethod
    def recommend_sanitization(device: DeviceInfo) -> Dict[str, Any]:
        """
        Recommend sanitization standard and method according to NIST SP 800-88 Rev 1.

        Args:
            device: DeviceInfo instance.

        Returns:
            Dictionary with recommended standard, method name, passes, and technical notes.
        """
        dtype = DeviceClassifier.classify(device)
        if dtype == DeviceType.HDD:
            return {
                "standard": "NIST SP 800-88 Rev 1 Clear",
                "recommended_method": "Full-Disk Overwrite (1-Pass Zero or Random)",
                "recommended_passes": 1,
                "notes": (
                    "For magnetic hard drives (HDDs), NIST SP 800-88 Rev 1 states that a single "
                    "full-disk overwrite pass is sufficient to prevent recovery via laboratory techniques. "
                    "DoD 5220.22-M (3 passes) is also supported for defense legacy compliance."
                ),
            }
        elif dtype in (DeviceType.SSD, DeviceType.NVME):
            return {
                "standard": "NIST SP 800-88 Rev 1 Purge",
                "recommended_method": "Firmware Cryptographic Erase / ATA Secure Erase",
                "recommended_passes": 1,
                "notes": (
                    "WARNING: Solid-state drives (SSDs and NVMe) utilize Wear Leveling and Flash Translation "
                    "Layers (FTL). Standard block overwriting cannot guarantee that spare blocks or over-provisioned "
                    "cells are erased. NIST Purge (Cryptographic Erase or Secure Erase) is strongly recommended."
                ),
            }
        else:
            return {
                "standard": "NIST SP 800-88 Rev 1 Clear",
                "recommended_method": "Multi-Pass Overwrite",
                "recommended_passes": 1,
                "notes": "Removable Flash media: full addressable logical block overwrite.",
            }
