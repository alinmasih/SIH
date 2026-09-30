"""
Platform-specific utility functions.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    """System/platform information"""
    os_name: str             # e.g., 'Linux', 'Windows'
    os_version: str          # e.g., '7.0.0-30-generic'
    hostname: str
    architecture: str        # e.g., 'x86_64'
    python_version: str
    is_root: bool
    username: str


def get_platform_info() -> PlatformInfo:
    """Get current platform information"""
    return PlatformInfo(
        os_name=platform.system(),
        os_version=platform.release(),
        hostname=platform.node(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        is_root=os.geteuid() == 0 if hasattr(os, 'geteuid') else False,
        username=os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    )


def check_privileges() -> bool:
    """
    Check if running with elevated privileges.

    Returns:
        True if running as root/admin
    """
    if sys.platform == 'linux':
        return os.geteuid() == 0
    elif sys.platform == 'win32':
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    return False


def check_command_available(command: str) -> bool:
    """
    Check if a command-line tool is available.

    Args:
        command: Command name (e.g., 'mmls')

    Returns:
        True if command is available
    """
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_command_version(command: str, version_flag: str = '-V') -> Optional[str]:
    """
    Get version of a command-line tool.

    Args:
        command: Command name
        version_flag: Flag to get version (default '-V')

    Returns:
        Version string, or None if unavailable
    """
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else None
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        return None


def get_block_devices() -> List[str]:
    """
    List available block devices (Linux only).

    Returns:
        List of block device paths (e.g., ['/dev/sda', '/dev/nvme0n1'])
    """
    if sys.platform != 'linux':
        return []

    devices = []
    block_dir = Path('/sys/block')

    if not block_dir.exists():
        return []

    for device_dir in sorted(block_dir.iterdir()):
        device_name = device_dir.name

        # Skip loop devices, ram disks, and device-mapper
        if device_name.startswith(('loop', 'ram', 'dm-')):
            continue

        device_path = f"/dev/{device_name}"
        if Path(device_path).exists():
            devices.append(device_path)

    return devices


def get_system_disk() -> Optional[str]:
    """
    Detect the system disk (disk containing root filesystem).

    Returns:
        Device path of system disk, or None
    """
    if sys.platform != 'linux':
        return None

    try:
        # Get the device for the root filesystem
        result = subprocess.run(
            ['findmnt', '-n', '-o', 'SOURCE', '/'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            source = result.stdout.strip()
            # Strip partition number to get the base device
            # e.g., /dev/sda1 -> /dev/sda, /dev/nvme0n1p1 -> /dev/nvme0n1
            if 'nvme' in source:
                # NVMe: /dev/nvme0n1p1 -> /dev/nvme0n1
                parts = source.split('p')
                if len(parts) > 1:
                    return 'p'.join(parts[:-1])
            else:
                # SATA/IDE: /dev/sda1 -> /dev/sda
                import re
                match = re.match(r'(/dev/[a-z]+)', source)
                if match:
                    return match.group(1)
            return source
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def check_external_tools() -> Dict[str, Dict[str, str]]:
    """
    Check availability of all external tools.

    Returns:
        Dictionary with tool info: {name: {available: bool, version: str}}
    """
    tools = {
        'mmls': {'version_flag': '-V', 'description': 'The Sleuth Kit - Partition analysis'},
        'fsstat': {'version_flag': '-V', 'description': 'The Sleuth Kit - Filesystem info'},
        'fls': {'version_flag': '-V', 'description': 'The Sleuth Kit - File listing'},
        'icat': {'version_flag': '-V', 'description': 'The Sleuth Kit - File extraction'},
        'tsk_recover': {'version_flag': '-V', 'description': 'The Sleuth Kit - File recovery'},
    }

    results = {}
    for name, info in tools.items():
        available = check_command_available(name)
        version = get_command_version(name, info['version_flag']) if available else None
        results[name] = {
            'available': available,
            'version': version or 'N/A',
            'description': info['description']
        }

    return results
