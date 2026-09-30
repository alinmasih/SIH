"""
Case management system for digital forensics investigations.

Handles case lifecycle, validation, storage, and tamper-evident audit logging.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from forensics_platform.database.models import Case, Evidence
from forensics_platform.database.session import DatabaseManager
from forensics_platform.audit.audit_logger import AuditLogger

if TYPE_CHECKING:
    from forensics_platform.core.config import Config


class CaseManager:
    """
    Manages forensic cases and their lifecycle.

    Coordinates database persistence, case directories, and audit logging.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        audit_logger: AuditLogger,
        config: Config
    ):
        """
        Initialize CaseManager.

        Args:
            db_manager: Database manager instance
            audit_logger: Audit logger instance
            config: Application configuration
        """
        self.db = db_manager
        self.audit = audit_logger
        self.config = config

    def create_case(
        self,
        case_number: str,
        title: str,
        investigator: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new forensic case.

        Args:
            case_number: Unique case identifier (e.g. 'CASE-2026-001')
            title: Descriptive case title (min 3 chars)
            investigator: Name or ID of primary investigator
            description: Optional detailed case summary

        Returns:
            Dictionary containing case details

        Raises:
            ValueError: If validation fails or case_number already exists
        """
        case_number = case_number.strip()
        title = title.strip()
        investigator = investigator.strip()

        if not case_number:
            raise ValueError("Case number cannot be empty")
        if len(title) < 3:
            raise ValueError("Case title must be at least 3 characters")
        if not investigator:
            raise ValueError("Investigator name cannot be empty")

        with self.db.session() as session:
            # Check unique constraint
            existing = session.query(Case).filter(Case.case_number == case_number).first()
            if existing:
                raise ValueError(f"Case with number '{case_number}' already exists")

            now = datetime.now(timezone.utc)
            case = Case(
                case_number=case_number,
                title=title,
                investigator=investigator,
                description=description,
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(case)
            session.commit()

            case_id = case.id
            case_dict = {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "investigator": case.investigator,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "evidence_count": 0,
            }

        # Create case directory structure on filesystem
        case_dir = self.config.case_dir / case_number
        for sub in ["evidence", "reports", "exports", "carved"]:
            (case_dir / sub).mkdir(parents=True, exist_ok=True)

        # Audit log event
        self.audit.log_event(
            event_type="case_created",
            event_data={
                "case_id": case_id,
                "case_number": case_number,
                "title": title,
                "investigator": investigator,
                "case_dir": str(case_dir),
            },
            event_category="case_management",
            case_id=case_id,
            user=investigator,
        )

        return case_dict

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve case by primary key ID."""
        with self.db.session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                return None
            evidence_count = session.query(Evidence).filter(Evidence.case_id == case_id).count()
            return {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "investigator": case.investigator,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "evidence_count": evidence_count,
            }

    def get_case_directory(self, case_id: int) -> Optional[Path]:
        """Get the filesystem directory Path for a case."""
        case = self.get_case(case_id)
        if not case:
            return None
        return self.config.case_dir / case["case_number"]

    def get_case_by_number(self, case_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve case by unique case number."""
        with self.db.session() as session:
            case = session.query(Case).filter(Case.case_number == case_number.strip()).first()
            if not case:
                return None
            evidence_count = session.query(Evidence).filter(Evidence.case_id == case.id).count()
            return {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "investigator": case.investigator,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "evidence_count": evidence_count,
            }

    def list_cases(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        investigator: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List cases with optional filters and evidence counts.

        Args:
            status: Optional status ('active', 'closed', 'archived')
            search: Optional search term matching number or title
            investigator: Optional filter by investigator

        Returns:
            List of case dictionaries
        """
        with self.db.session() as session:
            query = session.query(
                Case,
                func.count(Evidence.id).label("evidence_count")
            ).outerjoin(Evidence, Case.id == Evidence.case_id).group_by(Case.id)

            if status:
                query = query.filter(Case.status == status.lower())
            if investigator:
                query = query.filter(Case.investigator.ilike(f"%{investigator.strip()}%"))
            if search:
                term = f"%{search.strip()}%"
                query = query.filter(or_(Case.case_number.ilike(term), Case.title.ilike(term)))

            query = query.order_by(Case.created_at.desc())
            results = query.all()

            cases_list = []
            for case, ev_count in results:
                cases_list.append({
                    "id": case.id,
                    "case_number": case.case_number,
                    "title": case.title,
                    "investigator": case.investigator,
                    "description": case.description,
                    "status": case.status,
                    "created_at": case.created_at,
                    "updated_at": case.updated_at,
                    "evidence_count": ev_count,
                })
            return cases_list

    def update_case(
        self,
        case_id: int,
        title: Optional[str] = None,
        investigator: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing case.

        Args:
            case_id: Case ID
            title: Optional updated title
            investigator: Optional updated investigator
            description: Optional updated description
            status: Optional updated status ('active', 'closed', 'archived')

        Returns:
            Updated case details
        """
        valid_statuses = ("active", "closed", "archived")
        if status and status.lower() not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")
        if title is not None and len(title.strip()) < 3:
            raise ValueError("Case title must be at least 3 characters")

        with self.db.session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Case with ID {case_id} not found")

            updated_fields = {}
            if title is not None:
                case.title = title.strip()
                updated_fields["title"] = case.title
            if investigator is not None:
                case.investigator = investigator.strip()
                updated_fields["investigator"] = case.investigator
            if description is not None:
                case.description = description
                updated_fields["description"] = case.description
            if status is not None:
                case.status = status.lower()
                updated_fields["status"] = case.status

            case.updated_at = datetime.now(timezone.utc)
            session.commit()

            evidence_count = session.query(Evidence).filter(Evidence.case_id == case_id).count()
            case_dict = {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "investigator": case.investigator,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "evidence_count": evidence_count,
            }

        # Audit log event
        self.audit.log_event(
            event_type="case_updated",
            event_data={
                "case_id": case_id,
                "updated_fields": updated_fields,
            },
            event_category="case_management",
            case_id=case_id,
        )

        return case_dict

    def close_case(self, case_id: int) -> Dict[str, Any]:
        """Close an active case."""
        res = self.update_case(case_id, status="closed")
        self.audit.log_event(
            event_type="case_closed",
            event_data={"case_id": case_id, "status": "closed"},
            event_category="case_management",
            case_id=case_id,
        )
        return res

    def archive_case(self, case_id: int) -> Dict[str, Any]:
        """Archive a case."""
        res = self.update_case(case_id, status="archived")
        self.audit.log_event(
            event_type="case_archived",
            event_data={"case_id": case_id, "status": "archived"},
            event_category="case_management",
            case_id=case_id,
        )
        return res

    def delete_case(self, case_id: int) -> bool:
        """
        Delete a case and its related entities.

        Args:
            case_id: ID of case to delete

        Returns:
            True if deleted successfully
        """
        with self.db.session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                return False

            case_number = case.case_number
            session.delete(case)
            session.commit()

        self.audit.log_event(
            event_type="case_deleted",
            event_data={"case_id": case_id, "case_number": case_number},
            event_category="case_management",
            case_id=None,
        )
        return True

    def generate_next_case_number(self) -> str:
        """Generate the next suggested case number based on existing count for year."""
        current_year = datetime.now(timezone.utc).year
        prefix = f"CASE-{current_year}-"
        with self.db.session() as session:
            cases = session.query(Case.case_number).filter(
                Case.case_number.like(f"{prefix}%")
            ).all()

        max_seq = 0
        for (c_num,) in cases:
            try:
                seq = int(c_num.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                pass

        return f"{prefix}{max_seq + 1:03d}"
