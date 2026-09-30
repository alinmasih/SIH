"""
Cryptographic hashing utilities for the forensics platform.

Provides SHA-256 and MD5 hash calculation with progress callbacks.
Used for evidence integrity verification and file identification.
"""

import hashlib
from pathlib import Path
from typing import Callable, Optional, BinaryIO


# Type alias for progress callback: (bytes_processed, total_bytes) -> None
ProgressCallback = Callable[[int, int], None]


def calculate_sha256(
    file_path: Path,
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None
) -> str:
    """
    Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes (default 8KB)
        progress_callback: Optional callback(bytes_read, total_bytes)

    Returns:
        Hexadecimal hash string (64 characters)

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()
    file_size = file_path.stat().st_size
    bytes_read = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
            bytes_read += len(chunk)

            if progress_callback:
                progress_callback(bytes_read, file_size)

    return sha256_hash.hexdigest()


def calculate_md5(
    file_path: Path,
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None
) -> str:
    """
    Calculate MD5 hash of a file.

    Note: MD5 is included for legacy compatibility only.
    SHA-256 should be preferred for new operations.

    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes (default 8KB)
        progress_callback: Optional callback(bytes_read, total_bytes)

    Returns:
        Hexadecimal hash string (32 characters)

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    md5_hash = hashlib.md5()
    file_size = file_path.stat().st_size
    bytes_read = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
            bytes_read += len(chunk)

            if progress_callback:
                progress_callback(bytes_read, file_size)

    return md5_hash.hexdigest()


def calculate_hash(
    file_path: Path,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None
) -> str:
    """
    Calculate hash of a file using specified algorithm.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('sha256' or 'md5')
        chunk_size: Read chunk size in bytes
        progress_callback: Optional callback(bytes_read, total_bytes)

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported
        FileNotFoundError: If file doesn't exist
    """
    algorithm = algorithm.lower()

    if algorithm == "sha256":
        return calculate_sha256(file_path, chunk_size, progress_callback)
    elif algorithm == "md5":
        return calculate_md5(file_path, chunk_size, progress_callback)
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def verify_hash(
    file_path: Path,
    expected_hash: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Verify file hash matches expected value.

    Args:
        file_path: Path to file
        expected_hash: Expected hash value (hexadecimal)
        algorithm: Hash algorithm ('sha256' or 'md5')

    Returns:
        True if hashes match, False otherwise

    Raises:
        ValueError: If algorithm is not supported
        FileNotFoundError: If file doesn't exist
    """
    actual_hash = calculate_hash(file_path, algorithm)
    return actual_hash.lower() == expected_hash.lower()


def calculate_hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """
    Calculate hash of byte string.

    Args:
        data: Byte data to hash
        algorithm: Hash algorithm ('sha256' or 'md5')

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported
    """
    algorithm = algorithm.lower()

    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def calculate_hash_stream(
    stream: BinaryIO,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None,
    total_size: Optional[int] = None
) -> str:
    """
    Calculate hash from a binary stream.

    Args:
        stream: Binary stream to read from
        algorithm: Hash algorithm ('sha256' or 'md5')
        chunk_size: Read chunk size in bytes
        progress_callback: Optional callback(bytes_read, total_bytes)
        total_size: Optional total size for progress reporting

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported
    """
    algorithm = algorithm.lower()

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    bytes_read = 0
    while chunk := stream.read(chunk_size):
        hasher.update(chunk)
        bytes_read += len(chunk)

        if progress_callback and total_size:
            progress_callback(bytes_read, total_size)

    return hasher.hexdigest()


def calculate_multiple_hashes(
    file_path: Path,
    algorithms: list[str] = None,
    chunk_size: int = 8192,
    progress_callback: Optional[ProgressCallback] = None
) -> dict[str, str]:
    """
    Calculate multiple hashes of a file in a single pass.

    More efficient than calling calculate_hash multiple times.

    Args:
        file_path: Path to file
        algorithms: List of algorithms (default: ['sha256', 'md5'])
        chunk_size: Read chunk size in bytes
        progress_callback: Optional callback(bytes_read, total_bytes)

    Returns:
        Dictionary mapping algorithm name to hash value

    Raises:
        ValueError: If any algorithm is not supported
        FileNotFoundError: If file doesn't exist
    """
    if algorithms is None:
        algorithms = ['sha256', 'md5']

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Initialize hashers
    hashers = {}
    for algorithm in algorithms:
        algorithm = algorithm.lower()
        if algorithm == "sha256":
            hashers[algorithm] = hashlib.sha256()
        elif algorithm == "md5":
            hashers[algorithm] = hashlib.md5()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    # Read file once and update all hashers
    file_size = file_path.stat().st_size
    bytes_read = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            for hasher in hashers.values():
                hasher.update(chunk)

            bytes_read += len(chunk)

            if progress_callback:
                progress_callback(bytes_read, file_size)

    # Return results
    return {algorithm: hasher.hexdigest() for algorithm, hasher in hashers.items()}


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a text string.

    Args:
        text: Text to hash
        algorithm: Hash algorithm ('sha256' or 'md5')

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported
    """
    return calculate_hash_bytes(text.encode('utf-8'), algorithm)


def validate_hash_format(hash_value: str, algorithm: str = "sha256") -> bool:
    """
    Validate hash string format.

    Args:
        hash_value: Hash value to validate
        algorithm: Expected algorithm

    Returns:
        True if format is valid
    """
    algorithm = algorithm.lower()

    if algorithm == "sha256":
        expected_length = 64
    elif algorithm == "md5":
        expected_length = 32
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    if len(hash_value) != expected_length:
        return False

    # Check if all characters are valid hex
    try:
        int(hash_value, 16)
        return True
    except ValueError:
        return False
