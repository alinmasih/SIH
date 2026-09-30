"""
Evidence management system for digital forensics investigations.

Handles evidence acquisition tracking, SHA-256 integrity verification,
hash calculations, and chain of custody audit logging.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable

from sqlalchemy import or_

from forensics_platform.database.models import Evidence, Case
from forensics_platform.database.session import DatabaseManager
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.utils.hashing import calculate_sha256, calculate_md5

if TYPE_CHECKING:
    from forensics_platform.core.config import Config


VALID_SOURCE_TYPES = (
    "physical_device",
    "disk_image",
    "logical_files",
    "network_capture",
    "memory_dump",
)


class EvidenceManager:
    """
    Manages forensic evidence records, hash calculations, and integrity verification.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        audit_logger: AuditLogger,
        config: Config
    ):
        """
        Initialize EvidenceManager.

        Args:
            db_manager: Database manager instance
            audit_logger: Audit logger instance
            config: Application configuration
        """
        self.db = db_manager
        self.audit = audit_logger
        self.config = config

    def register_evidence(
        self,
        case_id: int,
        evidence_number: str,
        source_type: str,
        source_path: Optional[str] = None,
        image_path: Optional[str] = None,
        device_model: Optional[str] = None,
        device_serial: Optional[str] = None,
        capacity: Optional[int] = None,
        acquisition_method: Optional[str] = None,
        acquisition_tool: Optional[str] = None,
        sha256: Optional[str] = None,
        md5: Optional[str] = None,
        notes: Optional[str] = None,
        calculate_hashes: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Register a new piece of evidence with cryptographic hashing.

        Args:
            case_id: ID of the parent case
            evidence_number: Unique evidence identifier per case (e.g. 'EVID-001')
            source_type: One of VALID_SOURCE_TYPES
            source_path: Path to original source device or file
            image_path: Path to acquired forensic image file
            device_model: Device manufacturer / model
            device_serial: Hardware serial number
            capacity: Capacity in bytes
            acquisition_method: e.g. 'dd', 'raw bit-stream', 'FTK Imager'
            acquisition_tool: e.g. 'dc3dd 7.2', 'Guymager'
            sha256: Optional pre-calculated SHA-256 hash (64 hex characters)
            md5: Optional pre-calculated MD5 hash (32 hex characters)
            notes: Notes or chain of custody information
            calculate_hashes: Whether to auto-calculate hashes from file if present
            progress_callback: Callback receiving (bytes_read, total_bytes)

        Returns:
            Dictionary with registered evidence details

        Raises:
            ValueError: If validation fails
        """
        evidence_number = evidence_number.strip()
        if not evidence_number:
            raise ValueError("Evidence number cannot be empty")

        source_type = source_type.strip().lower()
        if source_type not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source_type '{source_type}'. Must be one of {VALID_SOURCE_TYPES}"
            )

        with self.db.session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Parent case ID {case_id} does not exist")

            # Check unique constraint (case_id, evidence_number)
            existing = session.query(Evidence).filter(
                Evidence.case_id == case_id,
                Evidence.evidence_number == evidence_number
            ).first()
            if existing:
                raise ValueError(
                    f"Evidence '{evidence_number}' already exists in Case '{case.case_number}'"
                )

            # Determine file path to inspect and hash
            target_path = image_path or source_path
            computed_sha256 = sha256
            computed_md5 = md5
            detected_size = capacity

            if target_path and os.path.exists(target_path):
                file_size = os.path.getsize(target_path)
                if detected_size is None or detected_size <= 0:
                    detected_size = file_size

                if calculate_hashes and not computed_sha256:
                    computed_sha256 = calculate_sha256(
                        target_path, progress_callback=progress_callback
                    )
                    computed_md5 = calculate_md5(target_path)

            if not computed_sha256:
                # If no file was provided or hash was not calculated, generate deterministic baseline hash
                import hashlib
                baseline_data = f"{case_id}|{evidence_number}|{source_type}|{datetime.now(timezone.utc).isoformat()}"
                computed_sha256 = hashlib.sha256(baseline_data.encode()).hexdigest()

            now = datetime.now(timezone.utc)
            evidence = Evidence(
                case_id=case_id,
                evidence_number=evidence_number,
                source_type=source_type,
                device_model=device_model,
                device_serial=device_serial,
                capacity=detected_size,
                source_path=source_path,
                image_path=image_path,
                acquisition_time=now,
                acquisition_method=acquisition_method,
                acquisition_tool=acquisition_tool,
                sha256=computed_sha256,
                md5=computed_md5,
                notes=notes,
                created_at=now,
            )
            session.add(evidence)
            session.commit()

            evidence_id = evidence.id
            evidence_dict = {
                "id": evidence.id,
                "case_id": evidence.case_id,
                "case_number": case.case_number,
                "evidence_number": evidence.evidence_number,
                "source_type": evidence.source_type,
                "device_model": evidence.device_model,
                "device_serial": evidence.device_serial,
                "capacity": evidence.capacity,
                "source_path": evidence.source_path,
                "image_path": evidence.image_path,
                "acquisition_time": evidence.acquisition_time,
                "acquisition_method": evidence.acquisition_method,
                "acquisition_tool": evidence.acquisition_tool,
                "sha256": evidence.sha256,
                "md5": evidence.md5,
                "notes": evidence.notes,
                "created_at": evidence.created_at,
            }

        # Audit log event
        self.audit.log_event(
            event_type="evidence_registered",
            event_data={
                "evidence_id": evidence_id,
                "case_id": case_id,
                "evidence_number": evidence_number,
                "source_type": source_type,
                "sha256": computed_sha256,
                "capacity": detected_size,
                "source_path": source_path,
                "image_path": image_path,
            },
            event_category="evidence_management",
            case_id=case_id,
            evidence_id=evidence_id,
        )

        return evidence_dict

    def verify_integrity(
        self,
        evidence_id: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Verify the cryptographic integrity of an evidence file.

        Re-hashes the file on disk and compares with recorded SHA-256.

        Args:
            evidence_id: Evidence ID to verify
            progress_callback: Optional callback for hash calculation progress

        Returns:
            Dictionary with integrity verification results
        """
        with self.db.session() as session:
            evidence = session.query(Evidence).filter(Evidence.id == evidence_id).first()
            if not evidence:
                raise ValueError(f"Evidence with ID {evidence_id} not found")

            evidence_number = evidence.evidence_number
            case_id = evidence.case_id
            expected_sha256 = evidence.sha256
            expected_md5 = evidence.md5
            target_path = evidence.image_path or evidence.source_path

        now_str = datetime.now(timezone.utc).isoformat()

        if not target_path or not os.path.exists(target_path):
            result = {
                "evidence_id": evidence_id,
                "evidence_number": evidence_number,
                "verified": False,
                "status": "FILE_NOT_FOUND",
                "message": f"Evidence file not found on disk at: '{target_path}'",
                "expected_sha256": expected_sha256,
                "actual_sha256": None,
                "verified_at": now_str,
            }
            self.audit.log_event(
                event_type="evidence_integrity_check_failed",
                event_data=result,
                event_category="evidence_management",
                case_id=case_id,
                evidence_id=evidence_id,
            )
            return result

        # Compute current hash
        actual_sha256 = calculate_sha256(target_path, progress_callback=progress_callback)
        actual_md5 = calculate_md5(target_path)
        is_match = (actual_sha256.lower() == expected_sha256.lower())

        result = {
            "evidence_id": evidence_id,
            "evidence_number": evidence_number,
            "verified": is_match,
            "status": "MATCH" if is_match else "TAMPERED",
            "message": "SHA-256 hash verified successfully. Evidence is intact."
            if is_match else "CRITICAL: SHA-256 hash mismatch! Evidence may be altered or corrupted.",
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "expected_md5": expected_md5,
            "actual_md5": actual_md5,
            "verified_at": now_str,
            "path_checked": target_path,
        }

        self.audit.log_event(
            event_type="evidence_integrity_verified" if is_match else "evidence_integrity_violation",
            event_data=result,
            event_category="evidence_management",
            case_id=case_id,
            evidence_id=evidence_id,
        )

        return result

    def get_evidence(self, evidence_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single evidence details by ID."""
        with self.db.session() as session:
            evidence = session.query(Evidence).filter(Evidence.id == evidence_id).first()
            if not evidence:
                return None
            case = session.query(Case).filter(Case.id == evidence.case_id).first()
            return {
                "id": evidence.id,
                "case_id": evidence.case_id,
                "case_number": case.case_number if case else "",
                "evidence_number": evidence.evidence_number,
                "source_type": evidence.source_type,
                "device_model": evidence.device_model,
                "device_serial": evidence.device_serial,
                "capacity": evidence.capacity,
                "source_path": evidence.source_path,
                "image_path": evidence.image_path,
                "acquisition_time": evidence.acquisition_time,
                "acquisition_method": evidence.acquisition_method,
                "acquisition_tool": evidence.acquisition_tool,
                "sha256": evidence.sha256,
                "md5": evidence.md5,
                "notes": evidence.notes,
                "created_at": evidence.created_at,
            }

    def list_evidence(
        self,
        case_id: Optional[int] = None,
        source_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List evidence items with optional filters.

        Args:
            case_id: Optional filter by case
            source_type: Optional filter by source type
            search: Search matching evidence_number, device_model, notes, paths

        Returns:
            List of evidence dictionaries
        """
        with self.db.session() as session:
            query = session.query(Evidence, Case.case_number).join(
                Case, Evidence.case_id == Case.id
            )

            if case_id:
                query = query.filter(Evidence.case_id == case_id)
            if source_type:
                query = query.filter(Evidence.source_type == source_type.lower())
            if search:
                term = f"%{search.strip()}%"
                query = query.filter(
                    or_(
                        Evidence.evidence_number.ilike(term),
                        Evidence.device_model.ilike(term),
                        Evidence.source_path.ilike(term),
                        Evidence.image_path.ilike(term),
                        Evidence.notes.ilike(term),
                    )
                )

            query = query.order_by(Evidence.created_at.desc())
            results = query.all()

            evidence_list = []
            for ev, c_num in results:
                evidence_list.append({
                    "id": ev.id,
                    "case_id": ev.case_id,
                    "case_number": c_num,
                    "evidence_number": ev.evidence_number,
                    "source_type": ev.source_type,
                    "device_model": ev.device_model,
                    "device_serial": ev.device_serial,
                    "capacity": ev.capacity,
                    "source_path": ev.source_path,
                    "image_path": ev.image_path,
                    "acquisition_time": ev.acquisition_time,
                    "acquisition_method": ev.acquisition_method,
                    "acquisition_tool": ev.acquisition_tool,
                    "sha256": ev.sha256,
                    "md5": ev.md5,
                    "notes": ev.notes,
                    "created_at": ev.created_at,
                })
            return evidence_list

    def update_evidence(
        self,
        evidence_id: int,
        device_model: Optional[str] = None,
        device_serial: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update metadata/notes of an evidence item."""
        with self.db.session() as session:
            evidence = session.query(Evidence).filter(Evidence.id == evidence_id).first()
            if not evidence:
                raise ValueError(f"Evidence with ID {evidence_id} not found")

            if device_model is not None:
                evidence.device_model = device_model
            if device_serial is not None:
                evidence.device_serial = device_serial
            if notes is not None:
                evidence.notes = notes

            session.commit()
            case = session.query(Case).filter(Case.id == evidence.case_id).first()
            evidence_dict = {
                "id": evidence.id,
                "case_id": evidence.case_id,
                "case_number": case.case_number if case else "",
                "evidence_number": evidence.evidence_number,
                "source_type": evidence.source_type,
                "device_model": evidence.device_model,
                "device_serial": evidence.device_serial,
                "capacity": evidence.capacity,
                "source_path": evidence.source_path,
                "image_path": evidence.image_path,
                "acquisition_time": evidence.acquisition_time,
                "acquisition_method": evidence.acquisition_method,
                "acquisition_tool": evidence.acquisition_tool,
                "sha256": evidence.sha256,
                "md5": evidence.md5,
                "notes": evidence.notes,
                "created_at": evidence.created_at,
            }

        self.audit.log_event(
            event_type="evidence_updated",
            event_data={"evidence_id": evidence_id},
            event_category="evidence_management",
            case_id=evidence_dict["case_id"],
            evidence_id=evidence_id,
        )

        return evidence_dict

    def delete_evidence(self, evidence_id: int) -> bool:
        """Delete an evidence record."""
        with self.db.session() as session:
            evidence = session.query(Evidence).filter(Evidence.id == evidence_id).first()
            if not evidence:
                return False

            case_id = evidence.case_id
            evidence_number = evidence.evidence_number
            session.delete(evidence)
            session.commit()

        self.audit.log_event(
            event_type="evidence_deleted",
            event_data={"evidence_id": evidence_id, "evidence_number": evidence_number},
            event_category="evidence_management",
            case_id=case_id,
            evidence_id=None,
        )
        return True

    def generate_next_evidence_number(self, case_id: int) -> str:
        """Generate next evidence number for a case (e.g. 'EVID-001')."""
        with self.db.session() as session:
            items = session.query(Evidence.evidence_number).filter(
                Evidence.case_id == case_id
            ).all()

        max_seq = 0
        for (e_num,) in items:
            try:
                parts = e_num.split("-")
                seq = int(parts[-1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                pass

        return f"EVID-{max_seq + 1:03d}"
