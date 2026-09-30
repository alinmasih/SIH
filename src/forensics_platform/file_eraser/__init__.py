"""
File Eraser package - secure file and directory destruction.
"""

from forensics_platform.file_eraser.shredder import FileShredder, ShredMethod
from forensics_platform.file_eraser.file_eraser import FileEraser

__all__ = [
    "FileShredder",
    "ShredMethod",
    "FileEraser",
]
