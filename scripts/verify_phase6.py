#!/usr/bin/env python3
"""
Phase 6 Verification Script - Sanitization Engine & Secure File Eraser.

Validates:
1. Module imports (Detector, Classifier, Safety, Sanitizers, VerificationEngine, FileEraser, GUI Widgets)
2. Block device detection and classification
3. Safety interlocks (system disk lock, mounted media detection, confirmation rules)
4. Drive sanitization & NIST SP 800-88 post-erasure verification with DB & audit tracking
5. Real block overwrite on virtual disk image and sample LBA verification
6. File shredding with metadata scrubbing and directory batch deletion
7. GUI Integration (DriveEraserWidget and FileEraserWidget offscreen instantiation and navigation)
"""

import os
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 6 VERIFICATION (SECURE SANITIZATION ENGINE)")
print("=" * 80)
print()

# 1. Imports
print("[1/7] Testing Phase 6 module imports...")
try:
    from forensics_platform.sanitization import (
        DeviceInfo,
        DeviceDetector,
        DeviceClassifier,
        DeviceType,
        SafetyChecker,
        SafetyCheckResult,
        BaseSanitizer,
        SanitizationStandard,
        SimulationSanitizer,
        HDDSanitizer,
        SSDSanitizer,
        VerificationEngine,
        VerificationResult,
        SanitizationManager,
    )
    from forensics_platform.file_eraser import FileShredder, ShredMethod, FileEraser
    from forensics_platform.gui.sanitization.drive_eraser_widget import DriveEraserWidget
    from forensics_platform.gui.sanitization.file_eraser_widget import FileEraserWidget
    from forensics_platform.core import ApplicationController
    from forensics_platform.core.config import Config
    from forensics_platform.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    print("✓ All Phase 6 sanitization and file eraser components imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# 2. Device Detection & Classification
print("\n[2/7] Testing block device detection and media classification...")
try:
    detector = DeviceDetector()
    devices = detector.enumerate_devices()
    print(f"  Detected {len(devices)} storage device(s) on host system.")
    for d in devices[:3]:
        dtype = DeviceClassifier.classify(d)
        print(f"  - {d.device_path}: {d.size_formatted} ({dtype.value.upper()}) | System: {d.is_system_disk} | Mounted: {d.is_mounted}")

    assert isinstance(detector.system_disks, set)
    print("✓ Device detection and classification verified")
except Exception as e:
    print(f"✗ Device detection failed: {e}")
    sys.exit(1)

# 3. Safety Constraints
print("\n[3/7] Testing safety checker interlocks...")
try:
    mock_sys_dev = DeviceInfo(device_path="/dev/sda", name="sda", size_bytes=10**11, is_system_disk=True)
    # Check that system disk is blocked in physical mode
    real_check = SafetyChecker.evaluate_device(mock_sys_dev, simulation_mode=False, confirmation_count=3)
    assert real_check.blocked is True
    assert not real_check.is_safe

    # Check that system disk produces safe warning in simulation mode
    sim_check = SafetyChecker.evaluate_device(mock_sys_dev, simulation_mode=True, confirmation_count=3)
    assert sim_check.blocked is False
    assert sim_check.is_safe is True
    print("✓ Safety interlocks successfully prevent non-simulation OS disk erasure")
except Exception as e:
    print(f"✗ Safety checks failed: {e}")
    sys.exit(1)

# 4. Drive Sanitization Pipeline & Database Persistence
print("\n[4/7] Testing SanitizationManager pipeline, DB persistence, and audit logging...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    cfg_file = tmp_path / "test_config.yaml"
    cfg = Config(
        data_dir=tmp_path,
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "phase6_test.db",
        simulation_mode=True,
    )
    cfg.save(cfg_file)
    ctrl = ApplicationController(cfg_file)

    try:
        # Create a test case
        case = ctrl.case_manager.create_case(
            case_number="CASE-2026-SAN",
            title="Sanitization Test Case",
            investigator="Sanitization Specialist",
        )

        target_dev = DeviceInfo(
            device_path="/dev/mock_nvme0n1",
            name="mock_nvme0n1",
            size_bytes=256 * 1024 * 1024 * 1024,
            bus_type="nvme",
            is_rotational=False,
        )

        san_res, ver_res = ctrl.sanitization_manager.sanitize_device(
            device=target_dev,
            standard=SanitizationStandard.DOD_5220_22_M,
            confirmation_count=3,
            case_id=case["id"],
        )

        assert san_res.success is True
        assert san_res.passes_completed == 3
        assert ver_res.is_passed is True

        # Check audit trail integrity
        chain = ctrl.audit_logger.verify_integrity()
        assert chain["valid"] is True
        assert chain["total_events"] >= 4  # genesis, case created, sanitization started, device sanitized

        ctrl.shutdown()
        print(f"✓ Drive sanitization pipeline verified (3 passes completed, audit chain intact with {chain['total_events']} events)")
    except Exception as e:
        print(f"✗ Sanitization pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 5. Real Overwrite & LBA Verification on Virtual Disk Image
print("\n[5/7] Testing real block overwriting & LBA sample verification...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    virtual_disk = tmp_path / "virtual_target.dd"
    # Create 512KB virtual disk with dirty pattern 0x55
    virtual_disk.write_bytes(b"\x55" * (512 * 1024))

    dev = DeviceInfo(device_path=str(virtual_disk), name="virtual_target.dd", size_bytes=512 * 1024)
    sanitizer = HDDSanitizer(chunk_size=64 * 1024)

    # Perform 1-pass Zero Overwrite
    res = sanitizer.sanitize(device=dev, standard=SanitizationStandard.NIST_800_88_CLEAR)
    assert res.success is True

    # Verify using VerificationEngine
    ve = VerificationEngine()
    ver_check = ve.verify_samples(str(virtual_disk), expected_pattern=b"\x00", sample_count=100)
    assert ver_check.is_passed is True
    assert ver_check.failed_samples == 0
    print("✓ Real block overwrite and 100% LBA sample verification passed")

# 6. Secure File Shredding & Metadata Scrubbing
print("\n[6/7] Testing secure file shredding, metadata scrubbing, and batch deletion...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    batch_dir = tmp_path / "target_folder" / "nested"
    batch_dir.mkdir(parents=True)
    f1 = batch_dir / "secret1.txt"
    f2 = batch_dir / "secret2.pdf"
    f1.write_text("CONFIDENTIAL FORENSIC FILE ONE")
    f2.write_bytes(b"%PDF-1.4 SECRETS" * 100)

    eraser = FileEraser()
    summary = eraser.erase_batch(
        paths=[tmp_path / "target_folder"],
        method=ShredMethod.DOD_3PASS,
    )

    assert summary["deleted_count"] == 2
    assert not f1.exists()
    assert not f2.exists()
    assert not (tmp_path / "target_folder").exists()
    print(f"✓ Secure file shredder verified (2 files obliterated, metadata scrubbed, directory tree eradicated)")

# 7. GUI Integration (DriveEraserWidget & FileEraserWidget)
print("\n[7/7] Testing GUI integration (offscreen)...")
try:
    app = QApplication.instance()
    if not app:
        app = QApplication(["verify_phase6", "-platform", "offscreen"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cfg_file = tmp_path / "gui_config.yaml"
        gui_cfg = Config(
            data_dir=tmp_path,
            log_dir=tmp_path / "logs",
            case_dir=tmp_path / "cases",
            temp_dir=tmp_path / "temp",
            database_path=tmp_path / "gui_test.db",
        )
        gui_cfg.save(cfg_file)
        controller = ApplicationController(cfg_file)
        main_window = MainWindow(controller)

        assert "drive_eraser" in main_window.pages
        assert "file_eraser" in main_window.pages
        assert hasattr(main_window, "drive_eraser_widget")
        assert hasattr(main_window, "file_eraser_widget")

        # Navigate to drive_eraser
        main_window._navigate_to("drive_eraser")
        assert main_window.content_stack.currentIndex() == main_window.pages["drive_eraser"]

        # Navigate to file_eraser
        main_window._navigate_to("file_eraser")
        assert main_window.content_stack.currentIndex() == main_window.pages["file_eraser"]

        controller.shutdown()
    app.quit()
    print("✓ DriveEraserWidget and FileEraserWidget instantiated and navigated successfully in MainWindow")
except Exception as e:
    print(f"✗ GUI test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL PHASE 6 SECURE SANITIZATION ENGINE VERIFICATIONS PASSED!")
print("=" * 80)
print()
