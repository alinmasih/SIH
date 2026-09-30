"""
Signature Database module - file signature definitions and management.

Provides FileSignature models and SignatureDatabase for forensic carving.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union


@dataclass
class FileSignature:
    """Represents a file format signature for carving."""
    name: str
    file_type: str
    extensions: List[str]
    mime_type: str
    header: bytes
    header_offset: int = 0
    footer: Optional[bytes] = None
    max_size: int = 50 * 1024 * 1024
    min_size: int = 16
    sector_aligned: bool = True
    validator: str = "generic"

    @classmethod
    def from_dict(cls, data: Dict) -> "FileSignature":
        """Construct a FileSignature from dictionary / JSON format."""
        header_hex = data.get("header_hex", "")
        header_bytes = bytes.fromhex(header_hex) if header_hex else b""

        footer_hex = data.get("footer_hex")
        footer_bytes = bytes.fromhex(footer_hex) if footer_hex else None

        return cls(
            name=data.get("name", "Unknown"),
            file_type=data.get("file_type", "").lower(),
            extensions=[ext.lower().lstrip(".") for ext in data.get("extensions", [])],
            mime_type=data.get("mime_type", "application/octet-stream"),
            header=header_bytes,
            header_offset=data.get("header_offset", 0),
            footer=footer_bytes,
            max_size=data.get("max_size", 50 * 1024 * 1024),
            min_size=data.get("min_size", 16),
            sector_aligned=data.get("sector_aligned", True),
            validator=data.get("validator", "generic"),
        )

    def to_dict(self) -> Dict:
        """Convert signature to dictionary."""
        return {
            "name": self.name,
            "file_type": self.file_type,
            "extensions": self.extensions,
            "mime_type": self.mime_type,
            "header_hex": self.header.hex().upper(),
            "header_offset": self.header_offset,
            "footer_hex": self.footer.hex().upper() if self.footer else None,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "sector_aligned": self.sector_aligned,
            "validator": self.validator,
        }


# Hardcoded fallback signatures in case external JSON files are unavailable
BUILTIN_FALLBACK_SIGNATURES = [
    {
        "name": "JPEG Image",
        "file_type": "jpeg",
        "extensions": ["jpg", "jpeg"],
        "mime_type": "image/jpeg",
        "header_hex": "FFD8FF",
        "header_offset": 0,
        "footer_hex": "FFD9",
        "max_size": 52428800,
        "min_size": 128,
        "sector_aligned": True,
        "validator": "jpeg",
    },
    {
        "name": "Portable Network Graphics",
        "file_type": "png",
        "extensions": ["png"],
        "mime_type": "image/png",
        "header_hex": "89504E470D0A1A0A",
        "header_offset": 0,
        "footer_hex": "49454E44AE426082",
        "max_size": 52428800,
        "min_size": 64,
        "sector_aligned": True,
        "validator": "png",
    },
    {
        "name": "Portable Document Format",
        "file_type": "pdf",
        "extensions": ["pdf"],
        "mime_type": "application/pdf",
        "header_hex": "25504446",
        "header_offset": 0,
        "footer_hex": "2525454F46",
        "max_size": 104857600,
        "min_size": 64,
        "sector_aligned": True,
        "validator": "pdf",
    },
    {
        "name": "ZIP Archive",
        "file_type": "zip",
        "extensions": ["zip"],
        "mime_type": "application/zip",
        "header_hex": "504B0304",
        "header_offset": 0,
        "footer_hex": "504B0506",
        "max_size": 104857600,
        "min_size": 22,
        "sector_aligned": True,
        "validator": "zip",
    },
    {
        "name": "Graphics Interchange Format",
        "file_type": "gif",
        "extensions": ["gif"],
        "mime_type": "image/gif",
        "header_hex": "47494638",
        "header_offset": 0,
        "footer_hex": "3B",
        "max_size": 52428800,
        "min_size": 32,
        "sector_aligned": True,
        "validator": "gif",
    },
]


class SignatureDatabase:
    """Manages collection of file signatures for carving."""

    def __init__(self, signatures_dir: Optional[Union[str, Path]] = None):
        """
        Initialize signature database.

        Args:
            signatures_dir: Optional path to directory with signature JSON files.
        """
        self._signatures: Dict[str, FileSignature] = {}

        # 1. Load builtins first
        for item in BUILTIN_FALLBACK_SIGNATURES:
            sig = FileSignature.from_dict(item)
            self.register_signature(sig)

        # 2. Look for project signatures directory if not provided
        if signatures_dir is None:
            # Check relative to module root or project root
            possible_paths = [
                Path(__file__).resolve().parent.parent.parent.parent / "data" / "signatures",
                Path.cwd() / "data" / "signatures",
            ]
            for p in possible_paths:
                if p.exists() and p.is_dir():
                    signatures_dir = p
                    break

        if signatures_dir is not None:
            self.load_from_directory(signatures_dir)

    def register_signature(self, signature: FileSignature) -> None:
        """Register or update a file signature."""
        self._signatures[signature.file_type.lower()] = signature

    def get_signature(self, file_type: str) -> Optional[FileSignature]:
        """Retrieve signature by file type (e.g. 'jpeg', 'png')."""
        return self._signatures.get(file_type.lower())

    def get_by_extension(self, extension: str) -> Optional[FileSignature]:
        """Retrieve signature by file extension (e.g. 'jpg', 'pdf')."""
        clean_ext = extension.lower().lstrip(".")
        for sig in self._signatures.values():
            if clean_ext in sig.extensions:
                return sig
        return None

    def list_signatures(self) -> List[FileSignature]:
        """List all registered file signatures."""
        return list(self._signatures.values())

    def load_from_directory(self, directory: Union[str, Path]) -> int:
        """
        Load signature JSON definitions from directory.

        Returns:
            Number of signatures loaded.
        """
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return 0

        count = 0
        for json_file in dir_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sig = FileSignature.from_dict(data)
                    self.register_signature(sig)
                    count += 1
            except Exception as e:
                # Log or skip malformed JSON files gracefully
                print(f"Warning: Failed to load signature from {json_file}: {e}")

        return count
