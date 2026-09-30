"""
Security and Defensive Interlocks Integration Tests.

Validates defensive posture, safety gates, and integrity protections:
1. Root / OS partition protection against destructive overwriting
2. Multi-tier confirmation gates enforcement
3. System protected paths and path traversal protection in file shredder
4. Cryptographic tamper detection in audit hash chain
5. Database relational integrity and rollback isolation
"""

import os
from pathlib import Path
import pytest

from forensics_platform.core.config import Config
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.database.models import AuditEvent, Case, Evidence
from forensics_platform.file_eraser.file_eraser import FileEraser
from forensics_platform.sanitization.device_detector import DeviceInfo
from forensics_platform.sanitization.safety_checks import SafetyChecker


@pytest.fixture
def security_env(tmp_path):
    cfg_file = tmp_path / "security_config.yaml"
    cfg = Config(
        app_name="Security Interlocks Test",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "security_test.db",
        simulation_mode=True,
    )
    cfg.save(cfg_file)
    controller = ApplicationController(config_path=cfg_file)
    yield controller, tmp_path
    controller.shutdown()


def test_system_disk_and_confirmation_interlocks():
    """Verify that OS disks and insufficient confirmations are strictly blocked."""
    checker = SafetyChecker()

    # 1. Host Root / Boot Drive
    root_drive = DeviceInfo(
        device_path="/dev/nvme0n1",
        name="nvme0n1",
        size_bytes=1000 * 1024 * 1024 * 1024,
        is_system_disk=True,
        mountpoints=["/"],
    )
    # Real mode must block unconditionally
    res_real = checker.evaluate_device(root_drive, simulation_mode=False, confirmation_count=10)
    assert res_real.blocked is True
    assert any("destroy the host OS" in err for err in res_real.errors)

    # Simulation mode permits with prominent warning
    res_sim = checker.evaluate_device(root_drive, simulation_mode=True, confirmation_count=3, required_confirmations=3)
    assert res_sim.blocked is False
    assert any("[SIMULATION ONLY]" in w for w in res_sim.warnings)

    # 2. Insufficient Confirmations
    external_drive = DeviceInfo(
        device_path="/dev/sdc",
        name="sdc",
        size_bytes=32 * 1024 * 1024 * 1024,
        is_system_disk=False,
        mountpoints=[],
    )
    # Required = 3, Provided = 1 -> BLOCKED
    res_conf = checker.evaluate_device(external_drive, simulation_mode=True, confirmation_count=1, required_confirmations=3)
    assert res_conf.is_safe is False
    assert any("confirmation" in err.lower() for err in res_conf.errors)

    # Required = 3, Provided = 3 -> PERMITTED
    res_conf_ok = checker.evaluate_device(external_drive, simulation_mode=True, confirmation_count=3, required_confirmations=3)
    assert res_conf_ok.blocked is False


def test_file_eraser_system_path_and_traversal_protection(tmp_path):
    """Verify that protected Linux system folders and directory traversal tricks are blocked."""
    eraser = FileEraser()

    # Direct protected system directories
    for protected in ["/", "/etc", "/bin", "/sbin", "/usr", "/boot", "/lib", "/dev", "/sys", "/proc"]:
        assert eraser.is_protected(protected) is True
        res = eraser.erase_file(protected)
        assert res["success"] is False
        assert "protected" in res["error"].lower()

    # Nested subpaths within protected directories
    assert eraser.is_protected("/etc/shadow") is True
    assert eraser.is_protected("/etc/passwd") is True
    assert eraser.is_protected("/usr/bin/bash") is True

    # Path traversal attack representation (e.g. /var/log/../../etc/passwd)
    traversal_path = Path("/var/log/../../etc/passwd")
    assert eraser.is_protected(traversal_path) is True

    # Safe test file inside workspace is permitted
    safe_file = tmp_path / "removable_test.txt"
    safe_file.write_bytes(b"SAFE_TO_DELETE")
    assert eraser.is_protected(safe_file) is False
    del_res = eraser.erase_file(safe_file)
    assert del_res["success"] is True
    assert not safe_file.exists()


def test_cryptographic_audit_tamper_detection(security_env):
    """Verify that tampering with any audit record breaks the cryptographic hash chain."""
    controller, _ = security_env

    # Generate legitimate audit events
    case1 = controller.case_manager.create_case("CASE-SEC-01", "Security Case 1", "Analyst Alpha")
    case2 = controller.case_manager.create_case("CASE-SEC-02", "Security Case 2", "Analyst Beta")

    # Verify initial chain is valid
    chain_init = controller.audit_logger.verify_integrity()
    assert chain_init["valid"] is True
    assert chain_init["total_events"] >= 3  # genesis + 2 cases

    # Tamper with the event data in the database
    with controller.db_manager.session() as session:
        event_to_tamper = session.query(AuditEvent).filter(AuditEvent.id == 2).first()
        assert event_to_tamper is not None
        # Maliciously alter the investigator name inside the encrypted payload
        event_to_tamper.event_data = '{"action": "malicious_unauthorized_override"}'
        session.commit()

    # Re-verify integrity -> MUST FAIL
    chain_tampered = controller.audit_logger.verify_integrity()
    assert chain_tampered["valid"] is False
    assert chain_tampered["first_broken_event_id"] == 2
    assert "event_hash mismatch" in chain_tampered["error_message"]


def test_database_cascade_and_isolation(security_env):
    """Verify relational cascade deletion and rollback isolation under failure conditions."""
    controller, _ = security_env

    # Create Case and Evidence
    case = controller.case_manager.create_case("CASE-ISO-01", "Isolation Test", "Admin")
    ev = controller.evidence_manager.register_evidence(
        case_id=case["id"],
        evidence_number="EV-ISO-01",
        source_type="logical_files",
        notes="Relational test",
    )

    with controller.db_manager.session() as s:
        assert s.query(Case).filter(Case.id == case["id"]).count() == 1
        assert s.query(Evidence).filter(Evidence.case_id == case["id"]).count() == 1

    # Delete Case -> Evidence must be cleanly cascaded
    deleted = controller.case_manager.delete_case(case["id"])
    assert deleted is True

    with controller.db_manager.session() as s:
        assert s.query(Case).filter(Case.id == case["id"]).count() == 0
        assert s.query(Evidence).filter(Evidence.case_id == case["id"]).count() == 0

    # Test Rollback isolation: Duplicate unique case_number
    with pytest.raises(ValueError, match="already exists"):
        controller.case_manager.create_case("CASE-DUP-01", "Dup 1", "User")
        controller.case_manager.create_case("CASE-DUP-01", "Dup 2", "User")
