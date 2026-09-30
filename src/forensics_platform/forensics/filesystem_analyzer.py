"""
Filesystem Analyzer.

Coordinates disk partition discovery, volume analysis, and directory
tree inspection using The Sleuth Kit and native block readers.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper
from forensics_platform.forensics.image_reader import ImageReader
from forensics_platform.utils.logging import get_logger


logger = get_logger(__name__)


class FilesystemAnalyzer:
    """
    Analyzes partition structures and filesystem contents of forensic disk images.
    """

    def __init__(self, tsk_wrapper: Optional[SleuthKitWrapper] = None):
        self.tsk = tsk_wrapper or SleuthKitWrapper()

    def get_image_info(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Inspect image format, size, and sector metrics."""
        with ImageReader(image_path) as reader:
            return {
                "path": str(image_path),
                "format": reader.format.value,
                "size_bytes": reader.get_size(),
                "sector_count": reader.get_sector_count(),
                "segments": [str(s) for s in reader.segments],
            }

    def analyze_partitions(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Detect partition map and volumes.

        Args:
            image_path: Path to disk image

        Returns:
            List of partitions with offsets and descriptions
        """
        # Primary: The Sleuth Kit mmls
        parts = self.tsk.get_partitions(image_path)
        if parts:
            return parts

        # Fallback: Native ImageReader MBR parser
        with ImageReader(image_path) as reader:
            mbr_parts = reader.parse_mbr_partitions()
            if mbr_parts:
                return mbr_parts

            # Whole disk raw fallback
            return [{
                "slot": "000:000",
                "start_sector": 0,
                "end_sector": max(0, reader.get_sector_count() - 1),
                "length_sectors": reader.get_sector_count(),
                "sector_size": 512,
                "offset_bytes": 0,
                "size_bytes": reader.get_size(),
                "description": "Raw Volume / Image (No Partition Table)",
                "is_allocated": True,
            }]

    def analyze_filesystem(
        self,
        image_path: Union[str, Path],
        offset_sectors: int = 0
    ) -> Dict[str, Any]:
        """
        Retrieve filesystem information (NTFS, EXT4, FAT32, etc.) at sector offset.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition starting sector

        Returns:
            Filesystem metadata dictionary
        """
        return self.tsk.get_fsstat(image_path, offset_sectors=offset_sectors)

    def list_files(
        self,
        image_path: Union[str, Path],
        offset_sectors: int = 0,
        inode: Optional[int] = None,
        deleted_only: bool = False,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Enumerate files and directories within a partition.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition sector offset
            inode: Optional directory inode
            deleted_only: If True, returns only deleted files
            recursive: If True, traverses directories

        Returns:
            List of file and directory metadata dicts
        """
        return self.tsk.list_files(
            image_path,
            offset_sectors=offset_sectors,
            inode=inode,
            deleted_only=deleted_only,
            recursive=recursive
        )
