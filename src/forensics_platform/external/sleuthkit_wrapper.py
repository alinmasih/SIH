"""
The Sleuth Kit (TSK) CLI Wrapper.

Provides Python bindings to The Sleuth Kit command-line tools (mmls, fsstat,
fls, icat, tsk_recover) with robust output parsing, error handling, and
pure-Python fallback capabilities.

Attribution:
The Sleuth Kit is licensed under Common Public License 1.0 (CPL 1.0).
Official Website: https://www.sleuthkit.org/
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from forensics_platform.utils.logging import get_logger


logger = get_logger(__name__)


class SleuthKitWrapper:
    """
    Wrapper for executing and parsing The Sleuth Kit (TSK) command-line utilities.
    """

    TOOLS = ["mmls", "fsstat", "fls", "icat", "tsk_recover"]

    def __init__(self, tsk_path: Optional[str] = None):
        """
        Initialize SleuthKitWrapper.

        Args:
            tsk_path: Optional directory containing TSK binaries (e.g. '/usr/bin').
        """
        self.tsk_path = Path(tsk_path) if tsk_path else None
        self._tool_paths: Dict[str, Optional[str]] = {}
        self._resolve_tools()

    def _resolve_tools(self):
        """Find executable paths for all TSK utilities."""
        for tool in self.TOOLS:
            if self.tsk_path and (self.tsk_path / tool).is_file():
                self._tool_paths[tool] = str(self.tsk_path / tool)
            else:
                self._tool_paths[tool] = shutil.which(tool)

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a specific TSK tool is installed and executable."""
        return bool(self._tool_paths.get(tool_name))

    def check_availability(self) -> Dict[str, bool]:
        """Check availability of all core TSK tools."""
        return {tool: self.is_tool_available(tool) for tool in self.TOOLS}

    def get_version(self) -> str:
        """Get The Sleuth Kit version string."""
        fls_bin = self._tool_paths.get("fls")
        if not fls_bin:
            return "Not Installed"
        try:
            res = subprocess.run([fls_bin, "-V"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout:
                return res.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get TSK version: {e}")
        return "Unknown"

    def get_partitions(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Analyze disk image partitions using `mmls`.

        Args:
            image_path: Path to disk image

        Returns:
            List of partition dictionaries:
            [{
                "slot": str,
                "start_sector": int,
                "end_sector": int,
                "length_sectors": int,
                "offset_bytes": int,
                "size_bytes": int,
                "description": str,
                "is_allocated": bool,
            }]
        """
        image_str = str(image_path)
        if not os.path.exists(image_str):
            raise FileNotFoundError(f"Disk image not found: {image_str}")

        mmls_bin = self._tool_paths.get("mmls")
        if not mmls_bin:
            logger.warning("mmls not available, attempting native MBR fallback")
            return self._fallback_mbr_partitions(image_str)

        try:
            res = subprocess.run(
                [mmls_bin, image_str],
                capture_output=True,
                text=True,
                timeout=30
            )
            if res.returncode != 0:
                logger.debug(f"mmls exited with code {res.returncode}: {res.stderr}")
                return self._fallback_mbr_partitions(image_str)

            return self._parse_mmls_output(res.stdout, image_str)
        except Exception as e:
            logger.error(f"Error executing mmls: {e}")
            return self._fallback_mbr_partitions(image_str)

    def _parse_mmls_output(self, output: str, image_path: str) -> List[Dict[str, Any]]:
        """Parse text table output from mmls."""
        sector_size = 512
        unit_match = re.search(r"Units are in (\d+)-byte sectors", output, re.IGNORECASE)
        if unit_match:
            sector_size = int(unit_match.group(1))

        partitions = []
        lines = output.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("DOS") or line_str.startswith("Offset") or line_str.startswith("Units") or line_str.startswith("Slot") or line_str.startswith("GUID"):
                continue

            # Format example:
            # 002:  000:000   0000002048   0000206847   0000204800   NTFS / exFAT (0x07)
            # 001:  -------   0000000001   0000002047   0000002047   Unallocated
            parts = re.split(r"\s+", line_str, maxsplit=5)
            if len(parts) >= 6:
                try:
                    slot = parts[1]
                    start = int(parts[2])
                    end = int(parts[3])
                    length = int(parts[4])
                    desc = parts[5]

                    is_alloc = "Unallocated" not in desc and "Meta" not in desc and "Table" not in desc

                    partitions.append({
                        "slot": slot,
                        "start_sector": start,
                        "end_sector": end,
                        "length_sectors": length,
                        "sector_size": sector_size,
                        "offset_bytes": start * sector_size,
                        "size_bytes": length * sector_size,
                        "description": desc,
                        "is_allocated": is_alloc,
                    })
                except (ValueError, IndexError):
                    continue

        if not partitions:
            # If no partitions found, treat as single volume
            return self._fallback_mbr_partitions(image_path)

        return partitions

    def _fallback_mbr_partitions(self, image_path: str) -> List[Dict[str, Any]]:
        """Pure Python fallback for reading MBR partition table directly."""
        partitions = []
        try:
            file_size = os.path.getsize(image_path)
            with open(image_path, "rb") as f:
                mbr = f.read(512)

            if len(mbr) == 512 and mbr[510:512] == b"\x55\xaa":
                # MBR signature matches
                for i in range(4):
                    entry_offset = 446 + (i * 16)
                    entry = mbr[entry_offset:entry_offset + 16]
                    part_type = entry[4]
                    if part_type == 0:
                        continue

                    start_lba = int.from_bytes(entry[8:12], byteorder="little")
                    sector_count = int.from_bytes(entry[12:16], byteorder="little")

                    type_desc = {
                        0x07: "NTFS / exFAT",
                        0x83: "Linux native (ext2/3/4)",
                        0x0B: "FAT32 (CHS)",
                        0x0C: "FAT32 (LBA)",
                        0x0E: "FAT16 (LBA)",
                        0x01: "FAT12",
                        0x82: "Linux swap",
                    }.get(part_type, f"Partition Type (0x{part_type:02X})")

                    partitions.append({
                        "slot": f"000:{i:03d}",
                        "start_sector": start_lba,
                        "end_sector": start_lba + sector_count - 1,
                        "length_sectors": sector_count,
                        "sector_size": 512,
                        "offset_bytes": start_lba * 512,
                        "size_bytes": sector_count * 512,
                        "description": type_desc,
                        "is_allocated": True,
                    })
        except Exception as e:
            logger.debug(f"MBR parse error: {e}")

        if not partitions:
            # Whole disk fallback
            size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            partitions.append({
                "slot": "000:000",
                "start_sector": 0,
                "end_sector": max(0, (size // 512) - 1),
                "length_sectors": size // 512,
                "sector_size": 512,
                "offset_bytes": 0,
                "size_bytes": size,
                "description": "Raw Volume / Image (No Partition Table)",
                "is_allocated": True,
            })

        return partitions

    def get_fsstat(self, image_path: Union[str, Path], offset_sectors: int = 0) -> Dict[str, Any]:
        """
        Analyze filesystem metadata using `fsstat`.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition offset in 512-byte sectors

        Returns:
            Dictionary with filesystem parameters
        """
        fsstat_bin = self._tool_paths.get("fsstat")
        if not fsstat_bin:
            return {"fs_type": "Unknown", "status": "fsstat not available"}

        cmd = [fsstat_bin, "-o", str(offset_sectors), str(image_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                return {"fs_type": "Raw / Unrecognized", "error": res.stderr.strip()}

            info = {"raw_output": res.stdout}
            for line in res.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k_clean = k.strip().lower().replace(" ", "_")
                    info[k_clean] = v.strip()

            fs_type = info.get("file_system_type") or info.get("fs_type") or "Unknown"
            info["fs_type"] = fs_type
            return info
        except Exception as e:
            logger.error(f"fsstat error: {e}")
            return {"fs_type": "Error", "error": str(e)}

    def list_files(
        self,
        image_path: Union[str, Path],
        offset_sectors: int = 0,
        inode: Optional[int] = None,
        deleted_only: bool = False,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List files and directories using `fls`.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition offset in sectors
            inode: Optional starting directory inode
            deleted_only: If True, list only deleted files
            recursive: If True, recurse through directories

        Returns:
            List of file dictionaries:
            [{
                "name": str,
                "inode": str,
                "is_deleted": bool,
                "is_directory": bool,
                "type": "file" | "directory" | "other",
                "raw_type": str,
            }]
        """
        fls_bin = self._tool_paths.get("fls")
        if not fls_bin:
            return []

        from forensics_platform.core.exceptions import ExternalToolError

        cmd = [fls_bin, "-o", str(offset_sectors), "-p"]
        if deleted_only:
            cmd.append("-d")
        if recursive:
            cmd.append("-r")

        cmd.append(str(image_path))
        if inode is not None:
            cmd.append(str(inode))

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or f"fls exited with code {res.returncode}"
                logger.debug(f"fls error: {err_msg}")
                raise ExternalToolError(f"fls execution failed: {err_msg}")

            return self._parse_fls_output(res.stdout)
        except ExternalToolError:
            raise
        except Exception as e:
            logger.error(f"Error executing fls: {e}")
            raise ExternalToolError(f"Failed to execute fls: {e}")

    def _parse_fls_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse fls output lines."""
        files = []
        pattern = re.compile(
            r"^[+\s]*([a-zA-Z\-]+/[a-zA-Z\-]+)\s+(\*?\s*)([0-9\-]+(?:\([a-zA-Z0-9_]+\))?):\s*(.+)$"
        )
        for line in output.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            # Format examples:
            # r/r * 145(realloc): deleted_file.pdf
            # d/d 144: SomeFolder
            # + r/r 146: active_file.txt
            # V/V 8193: $OrphanFiles
            # r/r * 145-128-3: stream.txt
            match = pattern.match(line_str)
            if match:
                type_mode = match.group(1).lower()
                deleted_flag = match.group(2)
                inode_str = match.group(3)
                filename = match.group(4).strip()

                is_deleted = "*" in deleted_flag
                is_dir = type_mode.startswith("d/")
                file_type = "directory" if is_dir else ("file" if type_mode.startswith("r/") else "other")

                files.append({
                    "name": filename,
                    "inode": inode_str,
                    "is_deleted": is_deleted,
                    "is_directory": is_dir,
                    "type": file_type,
                    "raw_mode": type_mode,
                })
        return files

    def extract_file_by_inode(
        self,
        image_path: Union[str, Path],
        offset_sectors: int,
        inode: Union[int, str],
        output_path: Union[str, Path]
    ) -> bool:
        """
        Extract file contents by inode using `icat`.

        Args:
            image_path: Disk image path
            offset_sectors: Partition offset in sectors
            inode: Inode identifier (clean integer or string)
            output_path: Destination file path

        Returns:
            True if extracted successfully
        """
        icat_bin = self._tool_paths.get("icat")
        if not icat_bin:
            return False

        # Clean inode string: strip parenthetical flags like (realloc)
        clean_inode = str(inode).split("(")[0].strip()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [icat_bin, "-o", str(offset_sectors), str(image_path), clean_inode]
        try:
            with open(output_path, "wb") as f_out:
                res = subprocess.run(cmd, stdout=f_out, stderr=subprocess.PIPE, timeout=60)
            if res.returncode == 0 and output_path.exists() and output_path.stat().st_size >= 0:
                return True
            err = res.stderr.decode(errors="ignore").strip()
            logger.error(f"icat failed: {err}")
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.error(f"icat execution error: {e}")
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            return False

    def recover_deleted_files(
        self,
        image_path: Union[str, Path],
        offset_sectors: int,
        output_dir: Union[str, Path]
    ) -> List[Path]:
        """
        Recover all unallocated / deleted files from partition using `tsk_recover`.

        Args:
            image_path: Disk image path
            offset_sectors: Partition offset
            output_dir: Directory to save recovered files

        Returns:
            List of Paths to recovered files
        """
        tsk_rec_bin = self._tool_paths.get("tsk_recover")
        if not tsk_rec_bin:
            return []

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        cmd = [tsk_rec_bin, "-o", str(offset_sectors), "-e", str(image_path), str(out_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            recovered = []
            if out_path.exists():
                for p in out_path.rglob("*"):
                    if p.is_file():
                        recovered.append(p)
            return recovered
        except Exception as e:
            logger.error(f"tsk_recover error: {e}")
            return []
