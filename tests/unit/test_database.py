"""
Unit tests for database models and session management.
"""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime

from forensics_platform.database.models import Case, Evidence, Operation
from forensics_platform.database.session import DatabaseManager


@pytest.fixture
def db_manager():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize()
        yield manager
        manager.close()


def test_database_initialization(db_manager):
    """Test database initialization"""
    assert db_manager.is_initialized == True
    assert db_manager.database_path.exists()


def test_create_case(db_manager):
    """Test creating a case"""
    with db_manager.session() as session:
        case = Case(
            case_number="CASE-2026-001",
            title="Test Case",
            investigator="Test Investigator",
            description="Test description",
            status="active"
        )
        session.add(case)
        session.commit()

        # Verify case was created
        assert case.id is not None
        assert case.case_number == "CASE-2026-001"
        assert case.created_at is not None


def test_case_unique_constraint(db_manager):
    """Test case number uniqueness constraint"""
    with db_manager.session() as session:
        case1 = Case(
            case_number="CASE-2026-002",
            title="First Case",
            investigator="Investigator"
        )
        session.add(case1)
        session.commit()

    # Try to create duplicate case number
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        with db_manager.session() as session:
            case2 = Case(
                case_number="CASE-2026-002",  # Duplicate
                title="Second Case",
                investigator="Investigator"
            )
            session.add(case2)
            session.commit()


def test_create_evidence(db_manager):
    """Test creating evidence"""
    with db_manager.session() as session:
        # Create case first
        case = Case(
            case_number="CASE-2026-003",
            title="Evidence Test",
            investigator="Investigator"
        )
        session.add(case)
        session.commit()

        # Create evidence
        evidence = Evidence(
            case_id=case.id,
            evidence_number="EVID-001",
            source_type="disk_image",
            sha256="a" * 64,
            image_path="/path/to/image.dd"
        )
        session.add(evidence)
        session.commit()

        assert evidence.id is not None
        assert evidence.case_id == case.id


def test_case_evidence_relationship(db_manager):
    """Test relationship between case and evidence"""
    with db_manager.session() as session:
        # Create case with evidence
        case = Case(
            case_number="CASE-2026-004",
            title="Relationship Test",
            investigator="Investigator"
        )
        evidence = Evidence(
            case=case,  # Use relationship
            evidence_number="EVID-002",
            source_type="disk_image",
            sha256="b" * 64
        )
        session.add(case)
        session.commit()

        # Retrieve case and check evidence
        retrieved_case = session.query(Case).filter_by(case_number="CASE-2026-004").first()
        assert len(retrieved_case.evidence) == 1
        assert retrieved_case.evidence[0].evidence_number == "EVID-002"


def test_cascade_delete(db_manager):
    """Test cascade deletion of evidence when case is deleted"""
    with db_manager.session() as session:
        case = Case(
            case_number="CASE-2026-005",
            title="Cascade Test",
            investigator="Investigator"
        )
        evidence = Evidence(
            case=case,
            evidence_number="EVID-003",
            source_type="disk_image",
            sha256="c" * 64
        )
        session.add(case)
        session.commit()

        case_id = case.id
        evidence_id = evidence.id

    # Delete case
    with db_manager.session() as session:
        case = session.get(Case, case_id)
        session.delete(case)
        session.commit()

    # Evidence should also be deleted (cascade)
    with db_manager.session() as session:
        evidence = session.get(Evidence, evidence_id)
        assert evidence is None


def test_create_operation(db_manager):
    """Test creating an operation"""
    with db_manager.session() as session:
        case = Case(
            case_number="CASE-2026-006",
            title="Operation Test",
            investigator="Investigator"
        )
        session.add(case)
        session.commit()

        operation = Operation(
            case_id=case.id,
            operation_type="file_carving",
            target="/path/to/image.dd",
            status="pending",
            tool_version="1.0.0"
        )
        session.add(operation)
        session.commit()

        assert operation.id is not None
        assert operation.status == "pending"


def test_genesis_audit_event(db_manager):
    """Test that genesis audit event is created"""
    from forensics_platform.database.models import AuditEvent

    with db_manager.session() as session:
        # Should have at least one audit event (genesis)
        count = session.query(AuditEvent).count()
        assert count >= 1

        # First event should be genesis
        first_event = session.query(AuditEvent).order_by(AuditEvent.id.asc()).first()
        assert first_event.event_type == "database_initialized"
        assert first_event.previous_hash is None
        assert first_event.event_hash is not None


def test_session_context_manager(db_manager):
    """Test session context manager"""
    # Should commit on success
    with db_manager.session() as session:
        case = Case(
            case_number="CASE-2026-007",
            title="Context Test",
            investigator="Investigator"
        )
        session.add(case)

    # Verify it was committed
    with db_manager.session() as session:
        case = session.query(Case).filter_by(case_number="CASE-2026-007").first()
        assert case is not None


def test_session_rollback_on_error(db_manager):
    """Test session rollback on exception"""
    try:
        with db_manager.session() as session:
            case = Case(
                case_number="CASE-2026-008",
                title="Rollback Test",
                investigator="Investigator"
            )
            session.add(case)
            # Force an error
            raise ValueError("Test error")
    except ValueError:
        pass

    # Case should not exist (rolled back)
    with db_manager.session() as session:
        case = session.query(Case).filter_by(case_number="CASE-2026-008").first()
        assert case is None
