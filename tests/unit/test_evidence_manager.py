"""
Unit tests for EvidenceManager.
"""

import tempfile
from pathlib import Path
import pytest

from forensics_platform.core.config import Config
from forensics_platform.database.session import DatabaseManager
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.forensics.case_manager import CaseManager
from forensics_platform.forensics.evidence_manager import EvidenceManager
from forensics_platform.utils.hashing import calculate_sha256


@pytest.fixture
def test_setup():
    """Create test environment for EvidenceManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_evidence.db"
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

        evidence_manager = EvidenceManager(
            db_manager=db_manager,
            audit_logger=audit_logger,
            config=config,
        )

        # Create baseline test case
        case = case_manager.create_case(
            case_number="CASE-2026-EVID-TEST",
            title="Evidence Testing Case",
            investigator="Forensic Analyst",
        )

        yield evidence_manager, case_manager, case["id"], tmp_path

        db_manager.close()


def test_register_evidence_with_file(test_setup):
    """Test registering evidence from a real file on disk."""
    ev_mgr, _, case_id, tmp_path = test_setup

    # Create dummy evidence disk image
    image_file = tmp_path / "usb_image.dd"
    image_data = b"FORENSIC_RAW_DISK_IMAGE_CONTENT_SAMPLE_12345"
    image_file.write_bytes(image_data)

    expected_sha256 = calculate_sha256(str(image_file))

    ev = ev_mgr.register_evidence(
        case_id=case_id,
        evidence_number="EVID-001",
        source_type="disk_image",
        image_path=str(image_file),
        device_model="SanDisk Ultra USB 3.0",
        device_serial="SD123456789",
        notes="Seized from suspect workstation",
    )

    assert ev["id"] is not None
    assert ev["evidence_number"] == "EVID-001"
    assert ev["sha256"] == expected_sha256
    assert ev["capacity"] == len(image_data)


def test_register_evidence_validation_errors(test_setup):
    """Test evidence validation rules."""
    ev_mgr, _, case_id, _ = test_setup

    # Invalid source type
    with pytest.raises(ValueError, match="Invalid source_type"):
        ev_mgr.register_evidence(
            case_id=case_id,
            evidence_number="EVID-001",
            source_type="unsupported_source_type",
        )

    # Empty evidence number
    with pytest.raises(ValueError, match="Evidence number cannot be empty"):
        ev_mgr.register_evidence(
            case_id=case_id,
            evidence_number="",
            source_type="disk_image",
        )

    # Non-existent parent case
    with pytest.raises(ValueError, match="Parent case ID 999999 does not exist"):
        ev_mgr.register_evidence(
            case_id=999999,
            evidence_number="EVID-001",
            source_type="disk_image",
        )


def test_verify_integrity_pass(test_setup):
    """Test cryptographic integrity check when file is untampered."""
    ev_mgr, _, case_id, tmp_path = test_setup

    image_file = tmp_path / "valid_image.raw"
    image_file.write_bytes(b"AUTHENTIC_DATA_PAYLOAD_FOR_FORENSIC_EXAMINATION")

    ev = ev_mgr.register_evidence(
        case_id=case_id,
        evidence_number="EVID-PASS",
        source_type="disk_image",
        image_path=str(image_file),
    )

    result = ev_mgr.verify_integrity(ev["id"])
    assert result["verified"] is True
    assert result["status"] == "MATCH"
    assert result["expected_sha256"] == result["actual_sha256"]


def test_verify_integrity_tampered_fail(test_setup):
    """Test cryptographic integrity check detects tampered data."""
    ev_mgr, _, case_id, tmp_path = test_setup

    image_file = tmp_path / "tamper_test.raw"
    image_file.write_bytes(b"ORIGINAL_UNTOUCHED_CONTENT")

    ev = ev_mgr.register_evidence(
        case_id=case_id,
        evidence_number="EVID-TAMPER",
        source_type="disk_image",
        image_path=str(image_file),
    )

    # Simulate tampering: modify one byte of the file
    image_file.write_bytes(b"TAMPERED_MODIFIED_CONTENT!")

    result = ev_mgr.verify_integrity(ev["id"])
    assert result["verified"] is False
    assert result["status"] == "TAMPERED"
    assert result["expected_sha256"] != result["actual_sha256"]


def test_list_and_delete_evidence(test_setup):
    """Test listing and deleting evidence."""
    ev_mgr, _, case_id, _ = test_setup

    ev1 = ev_mgr.register_evidence(
        case_id=case_id,
        evidence_number="EVID-LIST-1",
        source_type="logical_files",
    )
    ev2 = ev_mgr.register_evidence(
        case_id=case_id,
        evidence_number="EVID-LIST-2",
        source_type="memory_dump",
    )

    items = ev_mgr.list_evidence(case_id=case_id)
    assert len(items) == 2

    # Filter by source_type
    mem_items = ev_mgr.list_evidence(source_type="memory_dump")
    assert len(mem_items) == 1
    assert mem_items[0]["evidence_number"] == "EVID-LIST-2"

    # Delete
    deleted = ev_mgr.delete_evidence(ev1["id"])
    assert deleted is True
    assert len(ev_mgr.list_evidence(case_id=case_id)) == 1
