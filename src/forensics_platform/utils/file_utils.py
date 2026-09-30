"""
File utility functions for the forensics platform.
"""

from pathlib import Path
from typing import Optional
import shutil


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if necessary.

    Args:
        path: Directory path

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """
    Convert filename to safe format (remove invalid characters).

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def get_file_size_human(size_bytes: int) -> str:
    """
    Convert byte size to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def copy_file_with_progress(
    source: Path,
    destination: Path,
    progress_callback: Optional[callable] = None
) -> Path:
    """
    Copy file with progress reporting.

    Args:
        source: Source file path
        destination: Destination file path
        progress_callback: Optional callback(bytes_copied, total_bytes)

    Returns:
        Destination path
    """
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    file_size = source.stat().st_size
    bytes_copied = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    with open(source, 'rb') as src, open(destination, 'wb') as dst:
        while chunk := src.read(chunk_size):
            dst.write(chunk)
            bytes_copied += len(chunk)

            if progress_callback:
                progress_callback(bytes_copied, file_size)

    return destination


def get_available_disk_space(path: Path) -> int:
    """
    Get available disk space at path.

    Args:
        path: Directory path

    Returns:
        Available space in bytes
    """
    stat = shutil.disk_usage(path)
    return stat.free


def is_path_under(child: Path, parent: Path) -> bool:
    """
    Check if child path is under parent path.

    Args:
        child: Child path
        parent: Parent path

    Returns:
        True if child is under parent
    """
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
