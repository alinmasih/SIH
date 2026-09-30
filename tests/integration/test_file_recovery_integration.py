"""
Integration tests for End-to-End File Recovery & Carving.

Validates:
1. Generation of synthetic MBR forensic media.
2. Partition table analysis detecting FAT16 volume.
3. Discovery and extraction of deleted files via Sleuth Kit.
4. Raw signature carving of unallocated media space.
5. Database persistence and audit trail logging.
"""

from pathlib import Path
import pytest

from forensics_platform.core.config import Config
from forensics_platform.database.session import DatabaseManager
from forensics_platform.database.models import Case, Evidence, RecoveredFile, Operation, AuditEvent
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.forensics.case_manager import CaseManager
from forensics_platform.forensics.evidence_manager import EvidenceManager
from forensics_platform.forensics.filesystem_analyzer import FilesystemAnalyzer
from forensics_platform.forensics.deleted_file_analyzer import DeletedFileAnalyzer
from forensics_platform.carving.carving_engine import CarvingEngine
from forensics_platform.gui.settings.settings_widget import _generate_synthetic_media


@pytest.fixture
def recovery_env(tmp_path):
    db_path = tmp_path / "integration_forensics.db"
    config = Config(
        database_path=db_path,
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
    )
    db_mgr = DatabaseManager(db_path)
    db_mgr.initialize()
    audit = AuditLogger(db_mgr.get_session)

    case_mgr = CaseManager(db_mgr, audit, config)
    evidence_mgr = EvidenceManager(db_mgr, audit, config)
    fs_analyzer = FilesystemAnalyzer()
    deleted_analyzer = DeletedFileAnalyzer(db_mgr, audit, config)
    carving_engine = CarvingEngine(db_manager=db_mgr, audit_logger=audit)

    # Generate synthetic disk
    disk_path = tmp_path / "seized_media.dd"
    _generate_synthetic_media(disk_path)

    yield {
        "config": config,
        "db": db_mgr,
        "audit": audit,
        "case_mgr": case_mgr,
        "evidence_mgr": evidence_mgr,
        "fs_analyzer": fs_analyzer,
        "deleted_analyzer": deleted_analyzer,
        "carving_engine": carving_engine,
        "disk_path": disk_path,
        "tmp_path": tmp_path,
    }

    db_mgr.close()


def test_end_to_end_file_recovery_and_carving(recovery_env):
    """Verify full end-to-end recovery pipeline on forensic disk image."""
    disk_path = recovery_env["disk_path"]
    case_mgr = recovery_env["case_mgr"]
    evidence_mgr = recovery_env["evidence_mgr"]
    fs_analyzer = recovery_env["fs_analyzer"]
    deleted_analyzer = recovery_env["deleted_analyzer"]
    carving_engine = recovery_env["carving_engine"]
    db_mgr = recovery_env["db"]
    tmp_path = recovery_env["tmp_path"]

    # 1. Create Case
    case = case_mgr.create_case(
        case_number="CASE-INTEG-001",
        title="Integration Test Case",
        investigator="Test Agent",
    )
    assert case["id"] is not None

    # 2. Register Evidence
    evd = evidence_mgr.register_evidence(
        case_id=case["id"],
        evidence_number="EVD-001",
        source_type="disk_image",
        image_path=str(disk_path),
        calculate_hashes=True,
    )
    assert evd["sha256"] is not None
    assert len(evd["sha256"]) == 64

    # 3. Analyze Partitions
    partitions = fs_analyzer.analyze_partitions(disk_path)
    assert len(partitions) >= 1
    # Locate FAT16 partition (usually starting at sector 2048)
    fat_part = next((p for p in partitions if p.get("start_sector") == 2048), partitions[0])
    offset_sec = fat_part["start_sector"]
    assert offset_sec == 2048

    # 4. Scan for Deleted Files on Partition
    deleted_files = deleted_analyzer.scan_deleted_files(disk_path, offset_sectors=offset_sec)
    assert len(deleted_files) >= 1
    pdf_candidate = next((f for f in deleted_files if "pdf" in f["name"].lower()), deleted_files[0])
    assert pdf_candidate["is_deleted"] is True

    # 5. Recover Deleted File via Sleuth Kit icat
    recovered_out = tmp_path / "recovered_artifacts"
    rec_result = deleted_analyzer.recover_file(
        image_path=disk_path,
        offset_sectors=offset_sec,
        inode=pdf_candidate["inode"],
        filename=pdf_candidate["name"],
        output_dir=recovered_out,
        case_id=case["id"],
    )
    assert rec_result is not None
    assert Path(rec_result["path"]).exists()
    assert rec_result["size"] > 0
    assert len(rec_result["sha256"]) == 64

    # 6. Carve Embedded Signatures in Unallocated Media Space
    carved_out = tmp_path / "carved_artifacts"
    carved_results = carving_engine.carve_image(
        image_path=disk_path,
        target_types=["jpeg", "png", "zip"],
        min_confidence=50,
        output_dir=carved_out,
        case_id=case["id"],
        sector_aligned=True,
    )
    assert len(carved_results) == 3
    for c in carved_results:
        assert Path(c["path"]).exists()
        assert c["confidence_score"] >= 50
        assert c["file_type"] in ["jpeg", "png", "zip"]

    # 7. Validate Database Records and Integrity
    with db_mgr.session() as session:
        # Check RecoveredFile records (1 deleted recovery + 3 carved)
        all_recs = session.query(RecoveredFile).all()
        assert len(all_recs) == 4

        # Check Operations recorded
        ops = session.query(Operation).filter(Operation.case_id == case["id"]).all()
        assert len(ops) >= 2
        op_types = [o.operation_type for o in ops]
        assert "deleted_file_recovery" in op_types
        assert "file_carving" in op_types

        # Check Audit Log events
        audit_events = session.query(AuditEvent).filter(AuditEvent.case_id == case["id"]).all()
        assert len(audit_events) >= 5
        event_types = [e.event_type for e in audit_events]
        assert "case_created" in event_types
        assert "evidence_registered" in event_types
        assert "file_recovered" in event_types
        assert "carving_started" in event_types
        assert "file_carved" in event_types
