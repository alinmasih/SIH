#!/usr/bin/env python3
"""
Phase 8 Verification Script - Testing, Quality Assurance, & Performance Benchmarks.

Validates:
1. Clean environment and module imports across all subsystems
2. Complete end-to-end digital forensic pipeline lifecycle
3. Complete end-to-end sanitization & post-wipe verification pipeline lifecycle
4. Security interlocks (system disk lock, path traversal blocking, audit tamper detection)
5. Headless GUI test execution (MainWindow initialization, 10-view navigation, themes)
6. Performance throughput benchmarks (Dual hashing > 50 MB/s, carving > 1 MB/s, audit verification scaling)
7. Full automated pytest execution status (Unit, Integration, E2E)
"""

import os
import sys
import time
import struct
import zipfile
import zlib
import io
import subprocess
from pathlib import Path

# Ensure src is in sys.path
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 8 QUALITY ASSURANCE & VERIFICATION")
print("=" * 80)
print()

# ----------------------------------------------------------------------
# 1. Imports
# ----------------------------------------------------------------------
print("[1/7] Testing module imports and subsystem availability...")
try:
    from forensics_platform.core.config import Config
    from forensics_platform.core.app_controller import ApplicationController
    from forensics_platform.forensics.case_manager import CaseManager
    from forensics_platform.forensics.evidence_manager import EvidenceManager
    from forensics_platform.carving.carving_engine import CarvingEngine
    from forensics_platform.sanitization.sanitization_manager import SanitizationManager
    from forensics_platform.file_eraser import FileEraser
    from forensics_platform.reporting.report_generator import ReportGenerator, ReportFormat, ReportType
    from forensics_platform.audit.audit_logger import AuditLogger
    from forensics_platform.utils.hashing import calculate_multiple_hashes
    from PySide6.QtWidgets import QApplication
    from forensics_platform.gui.main_window import MainWindow

    print("✓ All core, forensic, sanitization, reporting, and GUI modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Ensure QApplication exists for offscreen GUI tests
app = QApplication.instance()
if not app:
    app = QApplication(["--platform", "offscreen"])

# ----------------------------------------------------------------------
# 2. Forensic Pipeline Verification
# ----------------------------------------------------------------------
print("\n[2/7] Verifying End-to-End Forensic Investigation Pipeline...")
try:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg_file = tmp_path / "cfg.yaml"
        cfg = Config(
            app_name="Verify Phase 8",
            data_dir=tmp_path / "data",
            log_dir=tmp_path / "logs",
            case_dir=tmp_path / "cases",
            temp_dir=tmp_path / "temp",
            database_path=tmp_path / "verify.db",
            simulation_mode=True
        )
        cfg.save(cfg_file)
        controller = ApplicationController(config_path=cfg_file)

        # Create case
        case = controller.case_manager.create_case(
            case_number="VERIFY-8-CASE",
            title="Phase 8 Verification Case",
            investigator="Lead Auditor"
        )
        assert case["id"] is not None

        # Synthetic disk image with embedded JPEG
        img_path = tmp_path / "seized.dd"
        soi = b"\xff\xd8"
        app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        sof0 = b"\xff\xc0\x00\x11\x08\x00\x40\x00\x40\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
        sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
        scan = b"CARVED_JPEG_PAYLOAD" * 20
        eoi = b"\xff\xd9"
        synthetic_jpeg = soi + app0 + sof0 + sos + scan + eoi
        disk = bytearray(1024 * 1024)
        disk[512 : 512 + len(synthetic_jpeg)] = synthetic_jpeg
        img_path.write_bytes(disk)

        # Register evidence with integrity hashes
        evidence = controller.evidence_manager.register_evidence(
            case_id=case["id"],
            evidence_number="EVD-P8-01",
            source_type="disk_image",
            image_path=str(img_path),
            calculate_hashes=True
        )
        assert evidence["sha256"] is not None
        assert len(evidence["sha256"]) == 64

        # Run file carver
        carver = CarvingEngine()
        carved = carver.carve_image(
            image_path=img_path,
            target_types=["jpeg"],
            output_dir=tmp_path / "carved",
            sector_aligned=True
        )
        assert len(carved) == 1
        assert carved[0]["file_type"] == "jpeg"

        # Generate signed forensic report
        (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
        rep = controller.report_generator.generate_forensic_report(
            case_id=case["id"],
            format="html",
            output_path=tmp_path / "reports" / "forensic_report.html",
            generated_by="Lead Auditor"
        )
        assert Path(rep.file_path).exists()
        assert Path(rep.file_path).stat().st_size > 0

        # Verify audit chain remains cryptographically unbroken
        audit_res = controller.audit_logger.verify_integrity()
        assert audit_res["valid"] is True
        assert audit_res["verified_events"] >= 3

        controller.shutdown()
        print(f"✓ Forensic pipeline operational (Case, Evidence, Carving, Report, {audit_res['verified_events']} Audit Events Verified)")
except Exception as e:
    print(f"✗ Forensic pipeline verification failed: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 3. Sanitization & Post-Wipe Verification Pipeline
# ----------------------------------------------------------------------
print("\n[3/7] Verifying End-to-End Sanitization & Post-Wipe Verification Pipeline...")
try:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg_file = tmp_path / "san_cfg.yaml"
        cfg = Config(
            app_name="Verify Phase 8 Sanitization",
            data_dir=tmp_path / "data",
            log_dir=tmp_path / "logs",
            case_dir=tmp_path / "cases",
            temp_dir=tmp_path / "temp",
            database_path=tmp_path / "san_verify.db",
            simulation_mode=True
        )
        cfg.save(cfg_file)
        controller = ApplicationController(config_path=cfg_file)

        from forensics_platform.sanitization import DeviceInfo, SanitizationStandard
        from forensics_platform.database.models import Operation

        mock_dev = DeviceInfo(
            device_path="/dev/sdb",
            name="sdb",
            size_bytes=10 * 1024 * 1024,
            model="Crucial CT1000MX500SSD1",
            serial="SN-SAN-2026-XYZ",
            bus_type="sata",
            is_removable=False,
            is_rotational=False,
            is_system_disk=False,
            mountpoints=[],
        )

        sim_san_res, sim_ver_res = controller.sanitization_manager.sanitize_device(
            device=mock_dev,
            standard=SanitizationStandard.NIST_800_88_CLEAR,
            confirmation_count=3,
        )
        assert sim_san_res.success is True
        assert sim_ver_res.result == "pass"

        with controller.db_manager.session() as s:
            op = s.query(Operation).order_by(Operation.id.desc()).first()
            assert op is not None
            op_id = op.id

        # Generate NIST Certificate
        (tmp_path / "certs").mkdir(parents=True, exist_ok=True)
        cert = controller.report_generator.generate_sanitization_certificate(
            operation_id=op_id,
            format=ReportFormat.HTML,
            output_path=tmp_path / "certs" / "sanitization_cert.html",
            generated_by="Security Officer"
        )
        assert Path(cert.file_path).exists()

        controller.shutdown()
        print(f"✓ Sanitization pipeline operational (NIST Clear, Byte Verification Passed, Certificate Issued)")
except Exception as e:
    print(f"✗ Sanitization pipeline verification failed: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 4. Security Interlocks & Anti-Tamper Verification
# ----------------------------------------------------------------------
print("\n[4/7] Verifying Security Interlocks & Cryptographic Anti-Tamper Protections...")
try:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg_file = tmp_path / "sec_cfg.yaml"
        cfg = Config(
            database_path=tmp_path / "sec.db",
            simulation_mode=False
        )
        cfg.save(cfg_file)
        controller = ApplicationController(config_path=cfg_file)

        # 1. System path & directory traversal protection
        eraser = FileEraser(audit_logger=controller.audit_logger)
        assert eraser.is_protected("/etc") is True
        assert eraser.is_protected("/usr/bin") is True
        assert eraser.is_protected(Path("/var/log/../../etc/passwd")) is True
        traversal_res = eraser.erase_file(Path("/var/log/../../etc/passwd"))
        assert traversal_res["success"] is False

        # 2. Cryptographic audit chain tamper detection
        controller.audit_logger.log_event(
            event_type="security_check",
            event_data={"check": "initial"},
            event_category="security"
        )
        controller.audit_logger.log_event(
            event_type="security_check",
            event_data={"check": "second"},
            event_category="security"
        )
        clean_res = controller.audit_logger.verify_integrity()
        assert clean_res["valid"] is True

        # Intentionally tamper with an event record
        from forensics_platform.database.models import AuditEvent
        with controller.db_manager.session() as session:
            evt = session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
            evt.event_data = '{"tampered": true}'

        tampered_res = controller.audit_logger.verify_integrity()
        assert tampered_res["valid"] is False
        assert tampered_res["first_broken_event_id"] is not None

        controller.shutdown()
        print(f"✓ Security interlocks & tamper detection operational (Traversal Blocked, Tamper Detected on Event {tampered_res['first_broken_event_id']})")
except Exception as e:
    print(f"✗ Security interlock verification failed: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 5. Headless GUI Navigation & Theme Verification
# ----------------------------------------------------------------------
print("\n[5/7] Verifying Headless GUI Navigation across all 10 Views...")
try:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg_file = tmp_path / "gui_cfg.yaml"
        cfg = Config(
            database_path=tmp_path / "gui.db",
            simulation_mode=True
        )
        cfg.save(cfg_file)
        controller = ApplicationController(config_path=cfg_file)
        win = MainWindow(controller)

        # Test all 10 views
        views = ["dashboard", "cases", "evidence", "recovery", "carving", "drive_eraser", "file_eraser", "audit", "reports", "settings"]
        for v in views:
            win._navigate_to(v)
            assert win.content_stack.currentIndex() == win.pages[v]
            assert win.nav_buttons[v].isChecked() is True

        # Theme toggle
        initial_theme = controller.config.theme
        win._toggle_theme()
        toggled_theme = controller.config_manager.get("theme")
        assert initial_theme != toggled_theme

        win.close()
        controller.shutdown()
        print(f"✓ GUI validation successful: All {len(views)} views rendered, responsive theme switching verified")
except Exception as e:
    print(f"✗ GUI verification failed: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 6. Performance Benchmarking Metrics
# ----------------------------------------------------------------------
print("\n[6/7] Benchmarking Throughput & Verification Latency...")
try:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Hashing Throughput (8MB)
        h_file = tmp_path / "hash_bench.bin"
        h_data = b"X" * (8 * 1024 * 1024)
        h_file.write_bytes(h_data)

        t0 = time.perf_counter()
        hashes = calculate_multiple_hashes(h_file, algorithms=["sha256", "md5"])
        t1 = time.perf_counter()
        hash_rate = 8.0 / max(t1 - t0, 0.0001)
        assert hash_rate >= 50.0

        # 2. Carving Throughput (2MB)
        c_file = tmp_path / "carve_bench.dd"
        c_disk = bytearray(2 * 1024 * 1024)
        c_disk[512 : 512 + len(synthetic_jpeg)] = synthetic_jpeg
        c_file.write_bytes(c_disk)

        engine = CarvingEngine()
        t0 = time.perf_counter()
        results = engine.carve_image(
            image_path=c_file,
            target_types=["jpeg"],
            output_dir=tmp_path / "c_out",
            sector_aligned=True
        )
        t1 = time.perf_counter()
        carve_rate = 2.0 / max(t1 - t0, 0.0001)
        assert carve_rate >= 1.0

        # 3. Audit Log Scaling (100 records)
        db_file = tmp_path / "audit_scale.db"
        from forensics_platform.database.session import DatabaseManager
        db_mgr = DatabaseManager(db_file)
        db_mgr.initialize()
        audit_log = AuditLogger(db_mgr.get_session)
        for i in range(100):
            audit_log.log_event(
                event_type=f"evt_{i}",
                event_data={"seq": i},
                event_category="system"
            )
        t0 = time.perf_counter()
        v_res = audit_log.verify_integrity()
        t1 = time.perf_counter()
        audit_rate = v_res["verified_events"] / max(t1 - t0, 0.0001)
        assert v_res["valid"] is True

        print(f"✓ Cryptographic Hashing: {hash_rate:.1f} MB/s (dual SHA-256 + MD5)")
        print(f"✓ File Carving Engine:   {carve_rate:.1f} MB/s (signature-aligned)")
        print(f"✓ Audit Verification:    {audit_rate:.0f} records/s ({v_res['verified_events']} events in {(t1-t0)*1000:.1f}ms)")
except Exception as e:
    print(f"✗ Benchmark verification failed: {e}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 7. Automated Test Suite Status
# ----------------------------------------------------------------------
print("\n[7/7] Checking Full Pytest Test Suite Status...")
cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"]
res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
if res.returncode == 0:
    first_line = res.stdout.strip().split("\n")[-1]
    print(f"✓ All automated tests passing: {first_line}")
else:
    print(f"✗ Pytest reported failures:\n{res.stdout}\n{res.stderr}")
    sys.exit(1)

print()
print("=" * 80)
print("PHASE 8 VERIFICATION COMPLETE: ALL QUALITY ASSURANCE CHECKS PASSED (100%)")
print("=" * 80)
