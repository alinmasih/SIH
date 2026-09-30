"""
Hash chain implementation for tamper-evident audit logging.

Each event is chained to the previous via SHA-256 hash, forming
a verifiable chain of custody for all forensic operations.
"""

import json
from datetime import datetime
from typing import Optional

from forensics_platform.utils.hashing import hash_string


def calculate_event_hash(
    timestamp: str,
    user: str,
    event_type: str,
    event_data: str,
    previous_hash: Optional[str]
) -> str:
    """
    Calculate the SHA-256 hash for an audit event.

    Hash is computed over: timestamp + user + event_type + event_data + previous_hash

    Args:
        timestamp: ISO-format timestamp string
        user: User who triggered the event
        event_type: Type of event
        event_data: JSON-serialized event data
        previous_hash: Hash of the previous event (None for genesis)

    Returns:
        SHA-256 hex digest (64 characters)
    """
    previous = previous_hash or "GENESIS"
    payload = f"{timestamp}|{user}|{event_type}|{event_data}|{previous}"
    return hash_string(payload, algorithm="sha256")


def verify_event_hash(
    timestamp: str,
    user: str,
    event_type: str,
    event_data: str,
    previous_hash: Optional[str],
    expected_hash: str
) -> bool:
    """
    Verify that an event hash is correct.

    Args:
        timestamp: ISO-format timestamp string
        user: User who triggered the event
        event_type: Type of event
        event_data: JSON-serialized event data
        previous_hash: Hash of the previous event
        expected_hash: Hash to verify against

    Returns:
        True if hash matches
    """
    computed = calculate_event_hash(
        timestamp, user, event_type, event_data, previous_hash
    )
    return computed == expected_hash
