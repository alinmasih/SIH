"""
Tamper-evident audit logging package.
"""

from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.audit.hash_chain import calculate_event_hash, verify_event_hash

__all__ = [
    "AuditLogger",
    "calculate_event_hash",
    "verify_event_hash",
]
