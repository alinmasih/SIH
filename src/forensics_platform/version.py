"""Version information for the platform"""

from datetime import datetime

VERSION = "1.0.0"
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

BUILD_DATE = "2026-09-08"
RELEASE_TYPE = "alpha"  # alpha, beta, rc, stable

VERSION_INFO = {
    "version": VERSION,
    "major": VERSION_MAJOR,
    "minor": VERSION_MINOR,
    "patch": VERSION_PATCH,
    "build_date": BUILD_DATE,
    "release_type": RELEASE_TYPE,
}

def get_version_string() -> str:
    """Get human-readable version string"""
    return f"v{VERSION}-{RELEASE_TYPE}"

def get_full_version_info() -> dict:
    """Get complete version information"""
    return VERSION_INFO.copy()
