"""
Integration test for the complete end-to-end digital forensics pipeline.

Validates the full lifecycle:
1. Case creation & directory provisioning
2. Evidence image registration & cryptographic baseline hashing (SHA-256 & MD5)
3. Cryptographic integrity re-verification and chain of custody tracking
4. Partition structure analysis
5. Deleted file recovery and signature carving
6. Multi-format court report compilation (HTML, PDF, JSON, CSV) with cryptographic seals
7. End-to-end tamper-evident audit log chain verification
"""

import json
from pathlib import Path
import tempfile
import pytest

from forensics_platform.core.config import Config
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.reporting.report_generator import ReportFormat, ReportType


@pytest.fixture
def forensic_pipeline_env(tmp_path):
    """Sets up a complete isolated forensic environment with temporary database and folders."""
    cfg_file = tmp_path / "test_config.yaml"
    cfg = Config(
        app_name="Forensics Platform Pipeline Test",
        version="1.0.0",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "pipeline_test.db",
        simulation_mode=True,
    )
    cfg.save(cfg_file)
    controller = ApplicationController(config_path=cfg_file)
    yield controller, tmp_path
    controller.shutdown()


def test_full_forensic_pipeline_lifecycle(forensic_pipeline_env):
    controller, root_path = forensic_pipeline_env

    # -------------------------------------------------------------
    # Step 1: Create Case
    # -------------------------------------------------------------
    case = controller.case_manager.create_case(
        case_number="CASE-2026-INT-001",
        title="Operation Cyber Fortress Investigation",
        investigator="Special Agent Jane Doe",
        description="Forensic examination of seized media image.",
    )
    assert case["id"] is not None
    assert case["case_number"] == "CASE-2026-INT-001"
    assert case["status"] == "active"

    case_folder = controller.case_manager.get_case_directory(case["id"])
    assert case_folder.exists()

    # -------------------------------------------------------------
    # Step 2: Construct Synthetic Disk Image with Target Evidence
    # -------------------------------------------------------------
    disk_path = root_path / "evidence_suspect_drive.dd"

    # Synthetic JPEG image header & EOF trailer
    jpeg_data = (
        b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        b"\xFF\xDB\x00C\x00" + b"\x01" * 64 +
        b"\xFF\xDA\x00\x0C\x03\x01\x00\x02\x11\x03\x11\x00?\x00" +
        b"ENCRYPTED_FINANCIAL_SPREADSHEET_DATA_STREAM" +
        b"\xFF\xD9"
    )

    # Synthetic PDF document
    pdf_data = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"xref\n0 2\n0000000000 65535 f \n0000000010 00000 n \n"
        b"trailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n70\n%%EOF\n"
    )

    # Build 2MB disk image with structured sector placement
    disk_buffer = bytearray(2 * 1024 * 1024)
    # Put JPEG at sector 100 (51,200 bytes offset)
    disk_buffer[51200 : 51200 + len(jpeg_data)] = jpeg_data
    # Put PDF at sector 2000 (1,024,000 bytes offset)
    disk_buffer[1024000 : 1024000 + len(pdf_data)] = pdf_data

    disk_path.write_bytes(disk_buffer)
    assert disk_path.exists()

    # -------------------------------------------------------------
    # Step 3: Evidence Ingestion & Cryptographic Verification
    # -------------------------------------------------------------
    evidence = controller.evidence_manager.register_evidence(
        case_id=case["id"],
        evidence_number="EVID-001-SUSPECT-DRIVE",
        source_type="disk_image",
        source_path=str(disk_path),
        image_path=str(disk_path),
        device_model="Seagate Barracuda 2MB Virtual LUN",
        device_serial="SN-9988776655",
        notes="Bit-stream raw forensic image acquired from suspect workstation.",
    )
    assert evidence["id"] is not None
    assert len(evidence["sha256"]) == 64
    assert len(evidence["md5"]) == 32

    # Verify cryptographic integrity initially
    initial_verify = controller.evidence_manager.verify_integrity(evidence["id"])
    assert initial_verify["verified"] is True
    assert initial_verify["status"] == "MATCH"

    # -------------------------------------------------------------
    # Step 4: Filesystem & Partition Analysis
    # -------------------------------------------------------------
    info = controller.filesystem_analyzer.get_image_info(disk_path)
    assert info["size_bytes"] == 2 * 1024 * 1024

    partitions = controller.filesystem_analyzer.analyze_partitions(disk_path)
    assert len(partitions) >= 1

    # -------------------------------------------------------------
    # Step 5: Advanced File Carving Pipeline
    # -------------------------------------------------------------
    carve_out_dir = root_path / "carved_artifacts"
    carved_files = controller.carving_engine.carve_image(
        image_path=disk_path,
        target_types=["jpeg", "pdf"],
        min_confidence=40,
        output_dir=carve_out_dir,
        case_id=case["id"],
        evidence_id=evidence["id"],
        sector_aligned=False,
    )

    assert len(carved_files) >= 2
    carved_types = {cf["file_type"] for cf in carved_files}
    assert "jpeg" in carved_types
    assert "pdf" in carved_types

    for cf in carved_files:
        p = Path(cf["path"])
        assert p.exists()
        assert p.stat().st_size > 0
        assert len(cf["sha256"]) == 64
        assert cf["confidence_score"] >= 40

    # -------------------------------------------------------------
    # Step 6: Multi-Format Court Report Generation
    # -------------------------------------------------------------
    reports = {}
    for fmt in [ReportFormat.HTML, ReportFormat.PDF, ReportFormat.JSON, ReportFormat.CSV]:
        rep = controller.report_generator.generate_forensic_report(
            case_id=case["id"],
            format=fmt,
            generated_by="Special Agent Jane Doe",
        )
        assert rep.id is not None
        assert Path(rep.file_path).exists()
        assert Path(rep.file_path).stat().st_size > 0
        assert len(rep.report_hash) == 64
        reports[fmt] = rep

    # Verify JSON structure
    json_path = Path(reports[ReportFormat.JSON].file_path)
    with open(json_path, "r", encoding="utf-8") as jf:
        json_content = json.load(jf)
        assert json_content["report_type"] == ReportType.FORENSIC_RECOVERY
        assert json_content["case"]["case_number"] == "CASE-2026-INT-001"
        assert json_content["statistics"]["total_files"] >= 2

    # -------------------------------------------------------------
    # Step 7: Cryptographic Audit Hash Chain Integrity Verification
    # -------------------------------------------------------------
    chain_check = controller.audit_logger.verify_integrity()
    assert chain_check["valid"] is True
    assert chain_check["total_events"] >= 8  # genesis + case + evidence + carve start/events + reports
    assert chain_check["verified_events"] == chain_check["total_events"]
    assert chain_check["first_broken_event_id"] is None
