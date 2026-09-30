"""
Signature Scanner module - binary multi-pattern scanning for file signatures.

Detects candidate file headers across raw buffers and disk images.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Union

from forensics_platform.carving.signature_database import FileSignature


@dataclass
class ScanCandidate:
    """Represents a signature match candidate identified during scanning."""
    file_type: str
    start_offset: int
    header_bytes: bytes
    signature: FileSignature


class SignatureScanner:
    """
    Binary scanner that locates file signatures across byte buffers and disk images.
    """

    def __init__(self, signatures: Optional[List[FileSignature]] = None):
        """
        Initialize scanner with target signatures.

        Args:
            signatures: List of FileSignatures to scan for.
        """
        self.signatures = signatures or []

    def set_signatures(self, signatures: List[FileSignature]) -> None:
        """Update active signatures for scanning."""
        self.signatures = signatures

    def scan_buffer(
        self,
        data: bytes,
        base_offset: int = 0,
        sector_aligned: bool = False,
        sector_size: int = 512,
    ) -> List[ScanCandidate]:
        """
        Scan a memory buffer for registered signatures.

        Args:
            data: Raw bytes to scan.
            base_offset: Absolute offset of this buffer in the overall image/file.
            sector_aligned: If True, only inspect sector boundaries (0, 512, 1024...).
            sector_size: Sector size in bytes (default 512).

        Returns:
            List of ScanCandidate matches.
        """
        candidates: List[ScanCandidate] = []
        if not data or not self.signatures:
            return candidates

        data_len = len(data)

        if sector_aligned:
            # Step in sector increments
            # Calculate alignment relative to base_offset
            rem = base_offset % sector_size
            start_idx = (sector_size - rem) % sector_size

            for idx in range(start_idx, data_len, sector_size):
                for sig in self.signatures:
                    sig_len = len(sig.header)
                    if sig_len == 0:
                        continue
                    header_start = idx + sig.header_offset
                    if header_start + sig_len <= data_len:
                        if data[header_start : header_start + sig_len] == sig.header:
                            candidates.append(
                                ScanCandidate(
                                    file_type=sig.file_type,
                                    start_offset=base_offset + idx,
                                    header_bytes=sig.header,
                                    signature=sig,
                                )
                            )
        else:
            # Byte-level search using Python's fast find() for each signature
            for sig in self.signatures:
                sig_len = len(sig.header)
                if sig_len == 0:
                    continue

                pos = 0
                while pos < data_len:
                    found_pos = data.find(sig.header, pos)
                    if found_pos == -1:
                        break

                    candidate_start = found_pos - sig.header_offset
                    if candidate_start >= 0:
                        candidates.append(
                            ScanCandidate(
                                file_type=sig.file_type,
                                start_offset=base_offset + candidate_start,
                                header_bytes=sig.header,
                                signature=sig,
                            )
                        )
                    pos = found_pos + 1

        # Sort candidates by start_offset
        candidates.sort(key=lambda c: c.start_offset)
        return candidates

    def scan_file(
        self,
        file_path: Union[str, Path],
        start_offset: int = 0,
        length: Optional[int] = None,
        chunk_size: int = 2 * 1024 * 1024,  # 2MB chunks
        sector_aligned: bool = True,
        sector_size: int = 512,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Iterator[ScanCandidate]:
        """
        Stream and scan a file or disk image yielding ScanCandidate matches.

        Args:
            file_path: Target disk image or file path.
            start_offset: Starting byte offset.
            length: Number of bytes to scan (None for entire file).
            chunk_size: Read buffer chunk size.
            sector_aligned: Optimize by checking only sector boundaries.
            sector_size: Sector size in bytes.
            progress_callback: Optional callback(bytes_processed, total_bytes).

        Yields:
            ScanCandidate objects as they are discovered.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        file_size = path.stat().st_size
        scan_end = file_size if length is None else min(start_offset + length, file_size)
        total_to_scan = max(0, scan_end - start_offset)

        if total_to_scan == 0:
            return

        max_header_len = max((len(s.header) + s.header_offset for s in self.signatures), default=64)
        overlap = max(max_header_len, sector_size)

        bytes_processed = 0
        current_offset = start_offset

        with open(path, "rb") as f:
            f.seek(current_offset)
            prev_tail = b""

            while current_offset < scan_end:
                to_read = min(chunk_size, scan_end - current_offset)
                chunk = f.read(to_read)
                if not chunk:
                    break

                read_len = len(chunk)
                buffer = prev_tail + chunk
                buffer_base = current_offset - len(prev_tail)

                # Scan buffer
                candidates = self.scan_buffer(
                    buffer,
                    base_offset=buffer_base,
                    sector_aligned=sector_aligned,
                    sector_size=sector_size,
                )

                # Yield candidates strictly within the new chunk range
                for cand in candidates:
                    if current_offset <= cand.start_offset < current_offset + read_len:
                        yield cand

                bytes_processed += read_len
                current_offset += read_len

                if progress_callback:
                    progress_callback(bytes_processed, total_to_scan)

                # Prepare overlap tail
                if overlap > 0 and read_len >= overlap:
                    prev_tail = chunk[-overlap:]
                else:
                    prev_tail = chunk
