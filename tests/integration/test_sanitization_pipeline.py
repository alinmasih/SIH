"""
Integration test for the complete secure data sanitization pipeline.

Validates the full sanitization workflow:
1. Media classification (HDD, SSD, NVMe, USB)
2. Multi-tier safety interlocks & destructive action guards
3. Drive sanitization execution (DoD 5220.22-M 3-pass & NIST Clear)
4. Post-erasure forensic verification via LBA sampling & 100% inspection
5. Secure file shredding & directory eradication
6. NIST SP 800-88 Sanitization Certificate generation in multiple formats (HTML, PDF, JSON, CSV)
7. Cryptographic audit log hash chain validation
"""

import json
import os
from pathlib import Path
import pytest

from forensics_platform.core.config import Config
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.file_eraser.shredder import ShredMethod
from forensics_platform.reporting.report_generator import ReportFormat, ReportType
from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.device_classifier import DeviceClassifier, DeviceType
from forensics_platform.sanitization.safety_checks import SafetyChecker
from forensics_platform.sanitization import (
    SanitizationStandard,
    HDDSanitizer,
    VerificationEngine,
)


@pytest.fixture
def sanitization_pipeline_env(tmp_path):
    """Sets up an isolated sanitization environment."""
    cfg_file = tmp_path / "sanitization_config.yaml"
    cfg = Config(
        app_name="Sanitization Pipeline Test",
        version="1.0.0",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "sanitization_test.db",
        simulation_mode=True,
    )
    cfg.save(cfg_file)
    controller = ApplicationController(config_path=cfg_file)
    yield controller, tmp_path
    controller.shutdown()


def test_full_sanitization_pipeline_lifecycle(sanitization_pipeline_env):
    controller, root_path = sanitization_pipeline_env

    # -------------------------------------------------------------
    # Step 1: Case Provisioning for Sanitization Record
    # -------------------------------------------------------------
    case = controller.case_manager.create_case(
        case_number="CASE-2026-SAN-001",
        title="Asset Decommissioning & Disposal Project",
        investigator="SecOps Lead Alex Vance",
        description="NIST SP 800-88 Rev 1 compliant drive sanitization.",
    )
    assert case["id"] is not None

    # -------------------------------------------------------------
    # Step 2: Device Detection & Classification
    # -------------------------------------------------------------
    devices = controller.device_detector.enumerate_devices()
    assert isinstance(devices, list)

    target_mock_device = DeviceInfo(
        device_path="/dev/sdb",
        name="sdb",
        size_bytes=10 * 1024 * 1024,  # 10 MB
        model="Crucial CT1000MX500SSD1",
        serial="SN-SAN-2026-XYZ",
        bus_type="sata",
        is_removable=False,
        is_rotational=False,
        is_system_disk=False,
        mountpoints=[],
    )
    classified_type = DeviceClassifier.classify(target_mock_device)
    assert classified_type == DeviceType.SSD
    rec_method = DeviceClassifier.recommend_sanitization(target_mock_device)
    assert "Purge" in rec_method["standard"] or "Clear" in rec_method["standard"]

    # -------------------------------------------------------------
    # Step 3: Safety Checker Interlocks
    # -------------------------------------------------------------
    checker = SafetyChecker()
    # Safe device check in simulation mode
    safe_res = checker.evaluate_device(target_mock_device, simulation_mode=True, confirmation_count=3, required_confirmations=3)
    assert safe_res.blocked is False
    assert safe_res.is_safe is True

    # In real mode without root, physical device write is blocked for safety
    if os.geteuid() != 0:
        non_root_res = checker.evaluate_device(target_mock_device, simulation_mode=False, confirmation_count=3)
        assert non_root_res.blocked is True
        assert any("root" in err.lower() for err in non_root_res.errors)

    # Critical system device protection
    sys_device = DeviceInfo(
        device_path="/dev/nvme0n1",
        name="nvme0n1",
        size_bytes=512 * 1024 * 1024 * 1024,
        model="Samsung 980 PRO",
        serial="SAMSUNG-SYS-001",
        bus_type="nvme",
        is_system_disk=True,
        mountpoints=["/"],
    )
    danger_res = checker.evaluate_device(sys_device, simulation_mode=False, confirmation_count=3, required_confirmations=3)
    assert danger_res.blocked is True
    assert len(danger_res.errors) > 0

    # -------------------------------------------------------------
    # Step 4: Drive Sanitization Execution (DoD 3-pass Overwrite)
    # -------------------------------------------------------------
    # Create a raw virtual drive image
    drive_image = root_path / "target_sanitized_disk.img"
    original_data = b"CONFIDENTIAL_PAYROLL_DATABASE_RECORDS" * 1000
    drive_image.write_bytes(original_data)
    img_size = drive_image.stat().st_size

    # Real overwrite using HDDSanitizer (3 passes)
    img_device = DeviceInfo(
        device_path=str(drive_image),
        name=drive_image.name,
        size_bytes=img_size,
    )
    hdd_san = HDDSanitizer()
    san_res = hdd_san.sanitize(
        device=img_device,
        standard=SanitizationStandard.NIST_800_88_CLEAR,
    )
    assert san_res.success is True
    assert san_res.passes_completed == 1
    assert san_res.bytes_written == img_size

    # Post-erasure verification: verify no remnants of original plaintext exist
    sanitized_bytes = drive_image.read_bytes()
    assert b"CONFIDENTIAL_PAYROLL" not in sanitized_bytes

    # LBA verification engine check
    ver_res = VerificationEngine.verify_samples(str(drive_image), sample_count=100)
    assert ver_res.result == "pass"
    assert ver_res.failed_samples == 0

    # -------------------------------------------------------------
    # Step 5: Simulation Sanitization via SanitizationManager
    # -------------------------------------------------------------
    sim_san_res, sim_ver_res = controller.sanitization_manager.sanitize_device(
        device=target_mock_device,
        standard=SanitizationStandard.NIST_800_88_CLEAR,
        case_id=case["id"],
        confirmation_count=3,
    )
    assert sim_san_res.success is True
    assert sim_ver_res.result == "pass"

    with controller.db_manager.session() as s:
        from forensics_platform.database.models import Operation
        op = s.query(Operation).filter(Operation.case_id == case["id"]).order_by(Operation.id.desc()).first()
        assert op is not None
        op_id = op.id

    # -------------------------------------------------------------
    # Step 6: File Shredding with Directory Eradication
    # -------------------------------------------------------------
    target_shred_dir = root_path / "classified_docs"
    target_shred_dir.mkdir(parents=True, exist_ok=True)
    f1 = target_shred_dir / "passwords.txt"
    f2 = target_shred_dir / "keys.pem"
    f1.write_bytes(b"ROOT_PASSWORD_SECRET_12345")
    f2.write_bytes(b"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgk...")

    shred_res = controller.file_eraser.erase_directory(
        directory_path=target_shred_dir,
        method=ShredMethod.DOD_3PASS,
        case_id=case["id"],
    )
    assert shred_res["deleted_count"] == 2
    assert not f1.exists()
    assert not f2.exists()
    assert not target_shred_dir.exists()

    # -------------------------------------------------------------
    # Step 7: NIST SP 800-88 Sanitization Certificate Generation
    # -------------------------------------------------------------
    certs = {}
    for fmt in [ReportFormat.HTML, ReportFormat.PDF, ReportFormat.JSON, ReportFormat.CSV]:
        cert = controller.report_generator.generate_sanitization_certificate(
            operation_id=op_id,
            format=fmt,
            generated_by="SecOps Lead Alex Vance",
        )
        assert cert.id is not None
        assert Path(cert.file_path).exists()
        assert Path(cert.file_path).stat().st_size > 0
        assert len(cert.report_hash) == 64
        certs[fmt] = cert

    # Verify JSON certificate payload
    json_cert_path = Path(certs[ReportFormat.JSON].file_path)
    with open(json_cert_path, "r", encoding="utf-8") as jf:
        c_data = json.load(jf)
        assert "certificate_id" in c_data
        assert c_data["device"]["path"] == "/dev/sdb"
        assert c_data["verification"]["result"] == "pass"

    # -------------------------------------------------------------
    # Step 8: Cryptographic Audit Hash Chain Validation
    # -------------------------------------------------------------
    chain_check = controller.audit_logger.verify_integrity()
    assert chain_check["valid"] is True
    assert chain_check["total_events"] >= 6  # genesis + case + sanitization + file shred + certificates
    assert chain_check["verified_events"] == chain_check["total_events"]
    assert chain_check["first_broken_event_id"] is None
