"""
Unit tests for CaseManager.
"""

import tempfile
from pathlib import Path
import pytest

from forensics_platform.core.config import Config
from forensics_platform.database.session import DatabaseManager
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.forensics.case_manager import CaseManager


@pytest.fixture
def test_setup():
    """Create test environment for CaseManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_cases.db"
        case_dir = tmp_path / "cases"
        case_dir.mkdir()

        config = Config(
            database_path=db_path,
            case_dir=case_dir,
            data_dir=tmp_path,
            log_dir=tmp_path / "logs",
            temp_dir=tmp_path / "temp",
        )

        db_manager = DatabaseManager(db_path)
        db_manager.initialize()
        audit_logger = AuditLogger(db_manager.get_session)

        case_manager = CaseManager(
            db_manager=db_manager,
            audit_logger=audit_logger,
            config=config,
        )

        yield case_manager, db_manager, audit_logger

        db_manager.close()


def test_create_case_success(test_setup):
    """Test successful case creation."""
    case_mgr, db_mgr, audit_mgr = test_setup

    case = case_mgr.create_case(
        case_number="CASE-2026-001",
        title="USB Drive Incident Investigation",
        investigator="Agent Fox Mulder",
        description="Investigation into unauthorized exfiltration",
    )

    assert case["id"] is not None
    assert case["case_number"] == "CASE-2026-001"
    assert case["title"] == "USB Drive Incident Investigation"
    assert case["status"] == "active"
    assert case["evidence_count"] == 0

    # Verify directory created
    case_path = case_mgr.config.case_dir / "CASE-2026-001"
    assert (case_path / "evidence").exists()
    assert (case_path / "reports").exists()


def test_create_case_validation_failures(test_setup):
    """Test validation rules when creating case."""
    case_mgr, _, _ = test_setup

    # Empty case number
    with pytest.raises(ValueError, match="Case number cannot be empty"):
        case_mgr.create_case(case_number="", title="Valid Title", investigator="Agent")

    # Short title
    with pytest.raises(ValueError, match="at least 3 characters"):
        case_mgr.create_case(case_number="CASE-01", title="No", investigator="Agent")

    # Empty investigator
    with pytest.raises(ValueError, match="Investigator name cannot be empty"):
        case_mgr.create_case(case_number="CASE-01", title="Valid Title", investigator="")


def test_create_case_duplicate_number(test_setup):
    """Test unique constraint on case number."""
    case_mgr, _, _ = test_setup

    case_mgr.create_case(
        case_number="CASE-2026-DUP",
        title="First Incident",
        investigator="Agent 1",
    )

    with pytest.raises(ValueError, match="already exists"):
        case_mgr.create_case(
            case_number="CASE-2026-DUP",
            title="Second Incident",
            investigator="Agent 2",
        )


def test_list_and_search_cases(test_setup):
    """Test listing, filtering by status, and searching."""
    case_mgr, _, _ = test_setup

    case_mgr.create_case(
        case_number="CASE-2026-101",
        title="Ransomware Analysis",
        investigator="Alice",
    )
    case_mgr.create_case(
        case_number="CASE-2026-102",
        title="Network Breach Intrusion",
        investigator="Bob",
    )

    # List all
    all_cases = case_mgr.list_cases()
    assert len(all_cases) == 2

    # Search
    search_res = case_mgr.list_cases(search="Ransomware")
    assert len(search_res) == 1
    assert search_res[0]["case_number"] == "CASE-2026-101"

    # Search by investigator
    inv_res = case_mgr.list_cases(investigator="Bob")
    assert len(inv_res) == 1
    assert inv_res[0]["case_number"] == "CASE-2026-102"


def test_update_and_lifecycle_cases(test_setup):
    """Test updating case details, closing, and archiving."""
    case_mgr, _, _ = test_setup

    created = case_mgr.create_case(
        case_number="CASE-2026-200",
        title="Mobile Phone Forensics",
        investigator="Charlie",
    )

    # Update title
    updated = case_mgr.update_case(
        case_id=created["id"],
        title="Updated Mobile Device Forensics",
    )
    assert updated["title"] == "Updated Mobile Device Forensics"

    # Close case
    closed = case_mgr.close_case(case_id=created["id"])
    assert closed["status"] == "closed"

    # Archive case
    archived = case_mgr.archive_case(case_id=created["id"])
    assert archived["status"] == "archived"


def test_delete_case(test_setup):
    """Test case deletion."""
    case_mgr, _, _ = test_setup

    case = case_mgr.create_case(
        case_number="CASE-2026-DEL",
        title="Temporary Incident",
        investigator="Dave",
    )

    success = case_mgr.delete_case(case["id"])
    assert success is True

    assert case_mgr.get_case(case["id"]) is None


def test_generate_next_case_number(test_setup):
    """Test auto-generation of next case number."""
    case_mgr, _, _ = test_setup

    num1 = case_mgr.generate_next_case_number()
    assert "CASE-" in num1

    case_mgr.create_case(case_number=num1, title="Test Case", investigator="Agent")
    num2 = case_mgr.generate_next_case_number()
    assert num2 != num1
