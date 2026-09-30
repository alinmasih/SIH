"""
Unit tests for FileShredder and FileEraser.
"""

from pathlib import Path

from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.core.config import Config
from forensics_platform.database.models import Operation
from forensics_platform.database.session import DatabaseManager
from forensics_platform.file_eraser import FileEraser, FileShredder, ShredMethod


def test_file_shredder_dod(tmp_path):
    """Verify FileShredder overwrites and removes file."""
    f = tmp_path / "sensitive.txt"
    f.write_text("SUPER_CONFIDENTIAL_FORENSIC_EVIDENCE_PAYLOAD")

    success = FileShredder.shred_file(f, method=ShredMethod.DOD_3PASS, wipe_metadata=True)
    assert success is True
    assert not f.exists()


def test_file_eraser_protected_path():
    """Verify FileEraser prevents deleting protected system paths."""
    eraser = FileEraser()
    assert eraser.is_protected("/") is True
    assert eraser.is_protected("/etc") is True
    assert eraser.is_protected("/usr") is True

    res = eraser.erase_file("/etc/passwd")
    assert res["success"] is False
    assert "Protected system path" in res["error"]


def test_file_eraser_batch_with_db_and_audit(tmp_path):
    """Verify batch erasure recurses into subdirectories, deletes files, and records DB/audit logs."""
    db_file = tmp_path / "erase_test.db"
    db_manager = DatabaseManager(db_file)
    db_manager.initialize()
    audit_logger = AuditLogger(db_manager.get_session)

    eraser = FileEraser(db_manager=db_manager, audit_logger=audit_logger)

    # Create directory tree with files
    sub_dir = tmp_path / "project_to_delete" / "sub"
    sub_dir.mkdir(parents=True)
    f1 = sub_dir / "file1.doc"
    f2 = sub_dir / "file2.pdf"
    f1.write_bytes(b"A" * 1024)
    f2.write_bytes(b"B" * 2048)

    summary = eraser.erase_batch(
        paths=[tmp_path / "project_to_delete"],
        method=ShredMethod.ZERO,
        case_id=None,
    )

    assert summary["deleted_count"] == 2
    assert summary["total_bytes"] == 3072
    assert not f1.exists()
    assert not f2.exists()
    assert not sub_dir.exists()

    # Check DB operation
    with db_manager.session() as session:
        op = session.query(Operation).filter_by(operation_type="file_deletion").first()
        assert op is not None
        assert op.status == "completed"
        assert op.items_processed == 2

    # Check audit events
    chain = audit_logger.verify_integrity()
    assert chain["valid"] is True
    assert chain["total_events"] >= 3  # genesis + 2 file_deleted events
