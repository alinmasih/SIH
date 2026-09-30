"""
Device Detector module - storage and block device enumeration for Linux systems.

Identifies physical and virtual block devices, partitions, mountpoints, and system disks.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Detailed hardware and state information for a storage device."""
    device_path: str
    name: str
    size_bytes: int
    model: Optional[str] = None
    vendor: Optional[str] = None
    serial: Optional[str] = None
    bus_type: str = "unknown"          # sata, nvme, usb, scsi, virtio, etc.
    is_rotational: bool = True         # True = HDD, False = SSD / NVMe
    is_removable: bool = False         # True = USB / SD Card
    is_system_disk: bool = False       # True = contains / or /boot
    mountpoints: List[str] = field(default_factory=list)
    partitions: List[Dict[str, Any]] = field(default_factory=list)
    read_only: bool = False

    @property
    def size_formatted(self) -> str:
        """Formatted human-readable size."""
        if self.size_bytes <= 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        s = float(self.size_bytes)
        i = 0
        while s >= 1024.0 and i < len(units) - 1:
            s /= 1024.0
            i += 1
        return f"{s:.2f} {units[i]}"

    @property
    def is_mounted(self) -> bool:
        """True if the device or any of its partitions are mounted."""
        if self.mountpoints:
            return True
        for part in self.partitions:
            if part.get("mountpoints"):
                return True
        return False


class DeviceDetector:
    """Detects and enumerates block devices using lsblk and sysfs."""

    def __init__(self):
        self.system_disks = self.detect_system_disks()

    @staticmethod
    def detect_system_disks() -> Set[str]:
        """
        Identify disk names that host root (/) or /boot filesystems.

        Returns:
            Set of device base names (e.g. {'sda', 'nvme0n1'}).
        """
        system_devices: Set[str] = set()
        try:
            # Read /proc/mounts to find device mounted at /
            if os.path.exists("/proc/mounts"):
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            dev, mnt = parts[0], parts[1]
                            if mnt in ("/", "/boot", "/boot/efi") and dev.startswith("/dev/"):
                                dev_name = os.path.basename(dev)
                                # Normalize partition name to base disk name
                                # e.g. sda1 -> sda, nvme0n1p2 -> nvme0n1
                                base_disk = DeviceDetector._get_base_disk_name(dev_name)
                                system_devices.add(base_disk)
        except Exception as e:
            logger.warning(f"Failed to inspect /proc/mounts: {e}")

        return system_devices

    @staticmethod
    def _get_base_disk_name(part_name: str) -> str:
        """Strip partition suffix to find root block device name."""
        if "nvme" in part_name or "mmcblk" in part_name:
            # nvme0n1p1 -> nvme0n1
            if "p" in part_name:
                return part_name.rsplit("p", 1)[0]
            return part_name
        # sda1 -> sda, vdb2 -> vdb
        return part_name.rstrip("0123456789")

    def enumerate_devices(self) -> List[DeviceInfo]:
        """
        Enumerate all block devices.

        Returns:
            List of DeviceInfo records.
        """
        devices: List[DeviceInfo] = []
        try:
            cmd = [
                "lsblk",
                "-J",
                "-b",
                "-o",
                "NAME,PATH,TYPE,SIZE,ROTA,RM,MODEL,VENDOR,SERIAL,MOUNTPOINTS,TRAN,RO",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                for item in data.get("blockdevices", []):
                    dev_info = self._parse_lsblk_device(item)
                    if dev_info:
                        devices.append(dev_info)
                return devices
        except Exception as e:
            logger.warning(f"lsblk enumeration failed, falling back to sysfs: {e}")

        # Fallback to sysfs if lsblk is unavailable or fails
        return self._enumerate_sysfs()

    def _parse_lsblk_device(self, item: Dict[str, Any]) -> Optional[DeviceInfo]:
        """Parse single lsblk JSON device entry and children."""
        dev_type = item.get("type", "")
        # Only consider primary disks, loop devices, or rom
        if dev_type not in ("disk", "loop"):
            return None

        name = item.get("name", "")
        path = item.get("path", f"/dev/{name}")
        size = int(item.get("size") or 0)
        rota = bool(item.get("rota", True))
        removable = bool(item.get("rm", False))
        read_only = bool(item.get("ro", False))

        # Mountpoints can be list or None
        mounts_raw = item.get("mountpoints") or []
        mountpoints = [m for m in mounts_raw if m]

        # Process child partitions
        partitions: List[Dict[str, Any]] = []
        is_sys = name in self.system_disks

        for child in item.get("children", []):
            child_name = child.get("name", "")
            child_mounts = [m for m in (child.get("mountpoints") or []) if m]
            if any(m in ("/", "/boot", "/boot/efi") for m in child_mounts):
                is_sys = True

            partitions.append({
                "name": child_name,
                "path": child.get("path", f"/dev/{child_name}"),
                "size_bytes": int(child.get("size") or 0),
                "mountpoints": child_mounts,
                "read_only": bool(child.get("ro", False)),
            })

        return DeviceInfo(
            device_path=path,
            name=name,
            size_bytes=size,
            model=(item.get("model") or "").strip() or None,
            vendor=(item.get("vendor") or "").strip() or None,
            serial=(item.get("serial") or "").strip() or None,
            bus_type=(item.get("tran") or "unknown").strip().lower(),
            is_rotational=rota,
            is_removable=removable,
            is_system_disk=is_sys,
            mountpoints=mountpoints,
            partitions=partitions,
            read_only=read_only,
        )

    def _enumerate_sysfs(self) -> List[DeviceInfo]:
        """Fallback block device enumeration via /sys/block."""
        devices: List[DeviceInfo] = []
        sys_block = Path("/sys/block")
        if not sys_block.exists():
            return devices

        for entry in sys_block.iterdir():
            name = entry.name
            if name.startswith(("ram", "zram")):
                continue

            dev_path = f"/dev/{name}"
            size_sectors = 0
            size_file = entry / "size"
            if size_file.exists():
                try:
                    size_sectors = int(size_file.read_text().strip())
                except Exception:
                    pass

            size_bytes = size_sectors * 512
            rota = True
            rota_file = entry / "queue" / "rotational"
            if rota_file.exists():
                try:
                    rota = (rota_file.read_text().strip() == "1")
                except Exception:
                    pass

            removable = False
            rm_file = entry / "removable"
            if rm_file.exists():
                try:
                    removable = (rm_file.read_text().strip() == "1")
                except Exception:
                    pass

            is_sys = name in self.system_disks

            devices.append(
                DeviceInfo(
                    device_path=dev_path,
                    name=name,
                    size_bytes=size_bytes,
                    is_rotational=rota,
                    is_removable=removable,
                    is_system_disk=is_sys,
                )
            )

        return devices

    def get_device_info(self, device_path: str) -> Optional[DeviceInfo]:
        """Get DeviceInfo for a specific path (e.g. /dev/sdb)."""
        devices = self.enumerate_devices()
        for d in devices:
            if d.device_path == device_path or d.name == os.path.basename(device_path):
                return d
        return None
