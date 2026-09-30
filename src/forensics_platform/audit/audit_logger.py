"""
Tamper-evident audit logger.

Logs all forensic operations with hash chaining for integrity verification.
Every event is linked to the previous via SHA-256, making any modification detectable.
"""

import json
import os
import platform
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from forensics_platform.database.models import AuditEvent
from forensics_platform.audit.hash_chain import calculate_event_hash


class AuditLogger:
    """
    Tamper-evident audit logging system.

    Maintains a hash chain across all audit events. Each event includes
    the hash of the previous event, so any modification breaks the chain.
    """

    def __init__(self, session_factory):
        """
        Initialize audit logger.

        Args:
            session_factory: Callable returning a SQLAlchemy Session
        """
        self._session_factory = session_factory
        self._user = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        self._hostname = platform.node()

    def log_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        event_category: Optional[str] = None,
        case_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        user: Optional[str] = None
    ) -> int:
        """
        Log an audit event with hash chaining.

        Args:
            event_type: Type of event (e.g., 'case_created', 'evidence_registered')
            event_data: Event details as dictionary
            event_category: Optional category
            case_id: Optional associated case ID
            operation_id: Optional associated operation ID
            evidence_id: Optional associated evidence ID
            user: Optional override for current user

        Returns:
            ID of the created audit event
        """
        session = self._session_factory()
        try:
            timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            timestamp_str = timestamp.isoformat()
            actual_user = user or self._user
            event_data_json = json.dumps(event_data, default=str, sort_keys=True)

            # Get the hash of the most recent event (previous_hash)
            previous_event = (
                session.query(AuditEvent)
                .order_by(AuditEvent.id.desc())
                .first()
            )
            previous_hash = previous_event.event_hash if previous_event else None

            # Calculate event hash
            event_hash = calculate_event_hash(
                timestamp_str, actual_user, event_type,
                event_data_json, previous_hash
            )

            # Create audit event
            audit_event = AuditEvent(
                timestamp=timestamp,
                user=actual_user,
                event_type=event_type,
                event_category=event_category,
                case_id=case_id,
                operation_id=operation_id,
                evidence_id=evidence_id,
                event_data=event_data_json,
                previous_hash=previous_hash,
                event_hash=event_hash,
                hostname=self._hostname,
            )

            session.add(audit_event)
            session.commit()

            return audit_event.id

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_audit_trail(
        self,
        case_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with optional filters.

        Args:
            case_id: Filter by case ID
            operation_id: Filter by operation ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return

        Returns:
            List of audit event dictionaries
        """
        session = self._session_factory()
        try:
            query = session.query(AuditEvent)

            if case_id is not None:
                query = query.filter(AuditEvent.case_id == case_id)
            if operation_id is not None:
                query = query.filter(AuditEvent.operation_id == operation_id)
            if event_type is not None:
                query = query.filter(AuditEvent.event_type == event_type)
            if start_time is not None:
                query = query.filter(AuditEvent.timestamp >= start_time)
            if end_time is not None:
                query = query.filter(AuditEvent.timestamp <= end_time)

            events = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()

            return [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "user": e.user,
                    "event_type": e.event_type,
                    "event_category": e.event_category,
                    "case_id": e.case_id,
                    "operation_id": e.operation_id,
                    "event_data": json.loads(e.event_data),
                    "previous_hash": e.previous_hash,
                    "event_hash": e.event_hash,
                }
                for e in events
            ]
        finally:
            session.close()

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire audit chain.

        Recomputes each hash and verifies it matches the stored value.

        Returns:
            Dictionary with verification results:
            {
                "valid": True/False,
                "total_events": int,
                "verified_events": int,
                "first_broken_event_id": int or None,
                "error_message": str or None
            }
        """
        session = self._session_factory()
        try:
            events = (
                session.query(AuditEvent)
                .order_by(AuditEvent.id.asc())
                .all()
            )

            if not events:
                return {
                    "valid": True,
                    "total_events": 0,
                    "verified_events": 0,
                    "first_broken_event_id": None,
                    "error_message": None
                }

            total = len(events)
            verified = 0
            previous_hash = None

            for event in events:
                # Verify that previous_hash matches what we expect
                if event.previous_hash != previous_hash:
                    return {
                        "valid": False,
                        "total_events": total,
                        "verified_events": verified,
                        "first_broken_event_id": event.id,
                        "error_message": (
                            f"Event {event.id}: previous_hash mismatch. "
                            f"Expected '{previous_hash}', got '{event.previous_hash}'"
                        )
                    }

                # Recalculate and verify the event hash
                ts = event.timestamp
                ts_str = ts.replace(tzinfo=None).isoformat() if getattr(ts, "tzinfo", None) else ts.isoformat()
                computed_hash = calculate_event_hash(
                    ts_str,
                    event.user,
                    event.event_type,
                    event.event_data,
                    event.previous_hash
                )

                if computed_hash != event.event_hash:
                    return {
                        "valid": False,
                        "total_events": total,
                        "verified_events": verified,
                        "first_broken_event_id": event.id,
                        "error_message": (
                            f"Event {event.id}: event_hash mismatch. "
                            f"Data may have been tampered with."
                        )
                    }

                previous_hash = event.event_hash
                verified += 1

            return {
                "valid": True,
                "total_events": total,
                "verified_events": verified,
                "first_broken_event_id": None,
                "error_message": None
            }
        finally:
            session.close()

    # ---- Convenience methods for common events ----

    def log_case_created(self, case_id: int, case_number: str, title: str):
        """Log case creation"""
        self.log_event(
            event_type="case_created",
            event_category="case_management",
            case_id=case_id,
            event_data={"case_number": case_number, "title": title}
        )

    def log_case_closed(self, case_id: int, case_number: str):
        """Log case closure"""
        self.log_event(
            event_type="case_closed",
            event_category="case_management",
            case_id=case_id,
            event_data={"case_number": case_number}
        )

    def log_evidence_registered(
        self, case_id: int, evidence_id: int, evidence_number: str, sha256: str
    ):
        """Log evidence registration"""
        self.log_event(
            event_type="evidence_registered",
            event_category="evidence_management",
            case_id=case_id,
            evidence_id=evidence_id,
            event_data={
                "evidence_number": evidence_number,
                "sha256": sha256
            }
        )

    def log_operation_started(
        self, operation_id: int, operation_type: str, target: str,
        case_id: Optional[int] = None
    ):
        """Log operation start"""
        self.log_event(
            event_type="operation_started",
            event_category="forensic_operation" if "sanitization" not in operation_type
                          else "sanitization_operation",
            case_id=case_id,
            operation_id=operation_id,
            event_data={"operation_type": operation_type, "target": target}
        )

    def log_operation_completed(
        self, operation_id: int, operation_type: str, result_summary: Dict[str, Any],
        case_id: Optional[int] = None
    ):
        """Log operation completion"""
        self.log_event(
            event_type="operation_completed",
            event_category="forensic_operation" if "sanitization" not in operation_type
                          else "sanitization_operation",
            case_id=case_id,
            operation_id=operation_id,
            event_data={
                "operation_type": operation_type,
                "result_summary": result_summary
            }
        )

    def log_sanitization_requested(
        self, device: str, method: str, case_id: Optional[int] = None
    ):
        """Log sanitization request (before execution)"""
        self.log_event(
            event_type="sanitization_requested",
            event_category="sanitization_operation",
            case_id=case_id,
            event_data={"device": device, "method": method}
        )
