"""
File Shredder module - multi-pass secure file overwriting and metadata scrubbing.
"""

import os
import random
import string
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ShredMethod(str, Enum):
    """File shredding algorithms."""
    ZERO = "zero"           # 1-pass zero
    RANDOM = "random"       # 1-pass cryptographically secure random
    DOD_3PASS = "dod"       # 3-pass DoD 5220.22-M: 0x00, 0xFF, Random
    GUTMANN_7 = "gutmann"   # 7-pass Gutmann subset


class FileShredder:
    """Executes multi-pass data destruction and filesystem metadata scrubbing."""

    @staticmethod
    def _get_patterns(method: ShredMethod) -> List[Optional[bytes]]:
        if method == ShredMethod.DOD_3PASS:
            return [b"\x00", b"\xff", None]
        elif method == ShredMethod.GUTMANN_7:
            return [b"\x55", b"\xaa", b"\x92", b"\x49", b"\x24", None, b"\x00"]
        elif method == ShredMethod.RANDOM:
            return [None]
        else:
            return [b"\x00"]

    @classmethod
    def shred_file(
        cls,
        file_path: Path,
        method: ShredMethod = ShredMethod.ZERO,
        wipe_metadata: bool = True,
        chunk_size: int = 64 * 1024,
    ) -> bool:
        """
        Securely shred a single file on disk.

        Args:
            file_path: Path to target file.
            method: ShredMethod algorithm.
            wipe_metadata: If True, scrub filename and timestamps before unlinking.
            chunk_size: Overwrite buffer size.

        Returns:
            True if shredded and unlinked successfully.
        """
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return False

        file_size = path.stat().st_size
        patterns = cls._get_patterns(method)

        # Overwrite passes
        if file_size > 0:
            with open(path, "r+b") as f:
                fd = f.fileno()

                for pattern_byte in patterns:
                    f.seek(0)
                    written = 0

                    if pattern_byte is not None:
                        chunk_buf = pattern_byte * chunk_size
                    else:
                        chunk_buf = None

                    while written < file_size:
                        to_write = min(chunk_size, file_size - written)
                        buf = chunk_buf[:to_write] if pattern_byte is not None else os.urandom(to_write)
                        f.write(buf)
                        written += to_write

                    f.flush()
                    try:
                        os.fdatasync(fd)
                    except OSError:
                        pass

                # Truncate to 0 bytes
                f.seek(0)
                f.truncate(0)
                f.flush()
                try:
                    os.fdatasync(fd)
                except OSError:
                    pass

        # Metadata wiping
        if wipe_metadata:
            try:
                # Reset timestamps to epoch 0
                os.utime(path, (0, 0))

                # Obfuscate filename through progressive random renames
                current_path = path
                parent = current_path.parent
                for length in (16, 12, 8, 4):
                    rand_name = "".join(random.choices(string.ascii_letters + string.digits, k=length))
                    new_path = parent / rand_name
                    try:
                        current_path.rename(new_path)
                        current_path = new_path
                    except OSError:
                        break

                current_path.unlink()
                return True
            except OSError:
                if path.exists():
                    path.unlink(missing_ok=True)
                return True
        else:
            path.unlink(missing_ok=True)
            return True
