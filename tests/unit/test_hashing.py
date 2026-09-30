"""
Unit tests for hashing utilities.
"""

import pytest
from pathlib import Path
import tempfile

from forensics_platform.utils.hashing import (
    calculate_sha256, calculate_md5, calculate_hash,
    verify_hash, calculate_hash_bytes, hash_string,
    validate_hash_format, calculate_multiple_hashes
)


def test_calculate_sha256():
    """Test SHA-256 calculation"""
    # Create a temporary file with known content
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Hello, World!")
        temp_path = Path(f.name)

    try:
        # Calculate hash
        hash_value = calculate_sha256(temp_path)

        # Verify it's 64 characters (SHA-256 hex)
        assert len(hash_value) == 64

        # Verify it's a valid hex string
        int(hash_value, 16)

        # Calculate again - should be consistent
        hash_value2 = calculate_sha256(temp_path)
        assert hash_value == hash_value2

    finally:
        temp_path.unlink()


def test_calculate_md5():
    """Test MD5 calculation"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Test content")
        temp_path = Path(f.name)

    try:
        hash_value = calculate_md5(temp_path)

        # MD5 is 32 hex characters
        assert len(hash_value) == 32
        int(hash_value, 16)

    finally:
        temp_path.unlink()


def test_verify_hash():
    """Test hash verification"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Verify me!")
        temp_path = Path(f.name)

    try:
        # Calculate the correct hash
        correct_hash = calculate_sha256(temp_path)

        # Verify with correct hash
        assert verify_hash(temp_path, correct_hash, "sha256") == True

        # Verify with incorrect hash
        wrong_hash = "0" * 64
        assert verify_hash(temp_path, wrong_hash, "sha256") == False

    finally:
        temp_path.unlink()


def test_calculate_hash_bytes():
    """Test hashing byte strings"""
    data = b"Test data"

    hash_sha256 = calculate_hash_bytes(data, "sha256")
    assert len(hash_sha256) == 64

    hash_md5 = calculate_hash_bytes(data, "md5")
    assert len(hash_md5) == 32


def test_hash_string():
    """Test hashing text strings"""
    text = "Hello, World!"

    hash_value = hash_string(text, "sha256")
    assert len(hash_value) == 64

    # Same text should produce same hash
    hash_value2 = hash_string(text, "sha256")
    assert hash_value == hash_value2


def test_validate_hash_format():
    """Test hash format validation"""
    # Valid SHA-256
    valid_sha256 = "a" * 64
    assert validate_hash_format(valid_sha256, "sha256") == True

    # Invalid length
    assert validate_hash_format("abc", "sha256") == False

    # Invalid characters
    assert validate_hash_format("g" * 64, "sha256") == False

    # Valid MD5
    valid_md5 = "b" * 32
    assert validate_hash_format(valid_md5, "md5") == True


def test_calculate_multiple_hashes():
    """Test calculating multiple hashes in one pass"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Multi-hash test")
        temp_path = Path(f.name)

    try:
        hashes = calculate_multiple_hashes(temp_path, ['sha256', 'md5'])

        assert 'sha256' in hashes
        assert 'md5' in hashes
        assert len(hashes['sha256']) == 64
        assert len(hashes['md5']) == 32

    finally:
        temp_path.unlink()


def test_progress_callback():
    """Test progress callback functionality"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("x" * 10000)
        temp_path = Path(f.name)

    try:
        progress_updates = []

        def callback(bytes_read, total_bytes):
            progress_updates.append((bytes_read, total_bytes))

        calculate_sha256(temp_path, chunk_size=1000, progress_callback=callback)

        # Should have received progress updates
        assert len(progress_updates) > 0

        # Last update should be complete
        assert progress_updates[-1][0] == progress_updates[-1][1]

    finally:
        temp_path.unlink()


def test_unsupported_algorithm():
    """Test error handling for unsupported algorithm"""
    with pytest.raises(ValueError):
        calculate_hash_bytes(b"test", "unsupported_algorithm")
