"""
Unit tests for DeletedFileAnalyzer.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from forensics_platform.core.config import Config
from forensics_platform.database.session import DatabaseManager
from forensics_platform.database.models import RecoveredFile, Operation
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.forensics.deleted_file_analyzer import DeletedFileAnalyzer
from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper


@pytest.fixture
def analyzer_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_deleted.db"
        config = Config(database_path=db_path, data_dir=tmp_path, temp_dir=tmp_path)

        db_mgr = DatabaseManager(db_path)
        db_mgr.initialize()
        audit = AuditLogger(db_mgr.get_session)

        # Mock TSK wrapper
        mock_tsk = MagicMock(spec=SleuthKitWrapper)
        mock_tsk.get_version.return_value = "The Sleuth Kit ver 4.12.1"

        analyzer = DeletedFileAnalyzer(
            db_manager=db_mgr,
            audit_logger=audit,
            config=config,
            tsk_wrapper=mock_tsk
        )

        yield analyzer, db_mgr, mock_tsk, tmp_path

        db_mgr.close()


def test_scan_deleted_files(analyzer_setup):
    """Test filtering deleted files from filesystem scan."""
    analyzer, _, mock_tsk, _ = analyzer_setup

    mock_tsk.list_files.return_value = [
        {"name": "allocated.doc", "inode": "10", "is_deleted": False, "is_directory": False},
        {"name": "deleted_confidential.pdf", "inode": "11", "is_deleted": True, "is_directory": False},
        {"name": "deleted_folder", "inode": "12", "is_deleted": True, "is_directory": True},
    ]

    deleted = analyzer.scan_deleted_files("fake_disk.raw", offset_sectors=2048)
    assert len(deleted) == 1
    assert deleted[0]["name"] == "deleted_confidential.pdf"
    assert deleted[0]["inode"] == "11"


def test_recover_file_success(analyzer_setup):
    """Test single file recovery, cryptographic hash generation, and DB insertion."""
    analyzer, db_mgr, mock_tsk, tmp_path = analyzer_setup

    def fake_extract(image_path, offset_sectors, inode, output_path):
        # Simulate icat writing extracted file bytes
        Path(output_path).write_bytes(b"RECOVERED_FORENSIC_EVIDENCE_PAYLOAD")
        return True

    mock_tsk.extract_file_by_inode.side_effect = fake_extract

    out_dir = tmp_path / "recovered_out"
    result = analyzer.recover_file(
        image_path="test_image.raw",
        offset_sectors=2048,
        inode="145",
        filename="financial_records.xlsx",
        output_dir=out_dir,
    )

    assert result is not None
    assert result["filename"] == "financial_records.xlsx"
    assert result["size"] == len(b"RECOVERED_FORENSIC_EVIDENCE_PAYLOAD")
    assert len(result["sha256"]) == 64
    assert result["detected_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Verify DB record
    with db_mgr.session() as session:
        rec = session.query(RecoveredFile).filter(RecoveredFile.id == result["id"]).first()
        assert rec is not None
        assert rec.filename == "financial_records.xlsx"
        assert rec.sha256 == result["sha256"]
        assert rec.validation_status == "valid"
