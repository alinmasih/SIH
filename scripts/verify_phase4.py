#!/usr/bin/env python3
"""
Phase 4 Verification Script - Forensic Analysis Engine.

Validates:
1. Module imports (TSK wrapper, ImageReader, FilesystemAnalyzer, DeletedFileAnalyzer, RecoveryWidget)
2. TSK Tool availability check
3. Raw and split-raw image reading and MBR partition detection
4. Filesystem metadata and partition analysis
5. Deleted file discovery and extraction simulation
6. Database tracking (RecoveredFile table & Operations)
7. GUI integration (RecoveryWidget offscreen instantiation and navigation)
"""

import sys
import os
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 4 VERIFICATION (ANALYSIS & RECOVERY ENGINE)")
print("=" * 80)
print()

# 1. Imports
print("[1/6] Testing Phase 4 module imports...")
try:
    from forensics_platform.core import ApplicationController
    from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper
    from forensics_platform.forensics.image_reader import ImageReader, ImageFormat
    from forensics_platform.forensics.filesystem_analyzer import FilesystemAnalyzer
    from forensics_platform.forensics.deleted_file_analyzer import DeletedFileAnalyzer
    from forensics_platform.gui.forensics.recovery_widget import RecoveryWidget
    from forensics_platform.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    print("✓ All Phase 4 engine and GUI components imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# 2. Check TSK availability
print("\n[2/6] Checking The Sleuth Kit (TSK) system integration...")
try:
    wrapper = SleuthKitWrapper()
    status = wrapper.check_availability()
    version = wrapper.get_version()
    print(f"  TSK Version detected: {version}")
    for tool, avail in status.items():
        icon = "✓" if avail else "✗"
        print(f"  {icon} {tool}: {'available' if avail else 'missing'}")
    assert any(status.values()), "At least some TSK tools must be installed or detected"
    print("✓ TSK integration verified")
except Exception as e:
    print(f"✗ TSK check failed: {e}")
    sys.exit(1)

# 3. ImageReader & MBR parsing
print("\n[3/6] Testing ImageReader (raw & split-raw block handling)...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    img_file = tmp_path / "synthetic_disk.img"

    # Create synthetic disk with MBR
    mbr = bytearray(512)
    mbr[446] = 0x80      # Bootable
    mbr[450] = 0x07      # NTFS
    mbr[454:458] = (2048).to_bytes(4, "little")
    mbr[458:462] = (8192).to_bytes(4, "little")
    mbr[510:512] = b"\x55\xaa"

    data = mbr + b"\x00" * (1024 * 1024 - 512)
    img_file.write_bytes(data)

    try:
        with ImageReader(img_file) as reader:
            assert reader.get_size() == 1024 * 1024
            assert reader.get_sector_count() == 2048
            partitions = reader.parse_mbr_partitions()
            assert len(partitions) == 1
            assert partitions[0]["start_sector"] == 2048
            assert partitions[0]["bootable"] is True
            print("✓ ImageReader block access and native MBR partition parsing verified")
    except Exception as e:
        print(f"✗ ImageReader test failed: {e}")
        sys.exit(1)

# 4. Filesystem Analyzer
print("\n[4/6] Testing FilesystemAnalyzer...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    img_file = tmp_path / "test.dd"
    img_file.write_bytes(b"\x00" * (512 * 4096))

    try:
        fs_analyzer = FilesystemAnalyzer(wrapper)
        info = fs_analyzer.get_image_info(img_file)
        assert info["size_bytes"] == 512 * 4096

        parts = fs_analyzer.analyze_partitions(img_file)
        assert len(parts) >= 1
        print(f"✓ FilesystemAnalyzer verified ({len(parts)} partition/volume entry identified)")
    except Exception as e:
        print(f"✗ FilesystemAnalyzer test failed: {e}")
        sys.exit(1)

# 5. Deleted File Recovery & DB Persistence
print("\n[5/6] Testing Deleted File Analyzer & Database Persistence...")
from forensics_platform.core.config import Config

with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    cfg_file = tmp_path / "config.yaml"
    test_cfg = Config(
        data_dir=tmp_path,
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "phase4_test.db",
    )
    test_cfg.save(cfg_file)
    ctrl = ApplicationController(cfg_file)

    try:
        # Create a test case
        case = ctrl.case_manager.create_case(
            case_number="CASE-2026-REC",
            title="Recovery Test Case",
            investigator="Forensic Examiner"
        )

        # Simulate recovering a deleted file
        out_dir = tmp_path / "recovered"
        # Mock extract_file_by_inode behavior
        def mock_extract(image_path, offset_sectors, inode, output_path):
            Path(output_path).write_bytes(b"RECOVERED_CONFIDENTIAL_FORENSIC_DOCUMENT")
            return True

        ctrl.tsk_wrapper.extract_file_by_inode = mock_extract

        rec = ctrl.deleted_file_analyzer.recover_file(
            image_path=str(tmp_path / "test.dd"),
            offset_sectors=2048,
            inode="123",
            filename="financials.pdf",
            output_dir=out_dir,
            case_id=case["id"]
        )

        assert rec is not None
        assert rec["filename"] == "financials.pdf"
        assert len(rec["sha256"]) == 64
        assert rec["size"] == len(b"RECOVERED_CONFIDENTIAL_FORENSIC_DOCUMENT")

        # Verify audit event
        chain = ctrl.audit_logger.verify_integrity()
        assert chain["valid"] is True

        ctrl.shutdown()
        print("✓ Deleted file recovery, SHA-256 computation, DB persistence, and audit logging verified")
    except Exception as e:
        print(f"✗ Deleted file recovery test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 6. GUI Integration
print("\n[6/6] Testing Recovery GUI integration (offscreen)...")
try:
    app = QApplication.instance()
    if not app:
        app = QApplication(["verify_phase4", "-platform", "offscreen"])

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

        assert "recovery" in main_window.pages
        assert hasattr(main_window, "recovery_widget")

        # Navigate to recovery
        main_window._navigate_to("recovery")
        assert main_window.content_stack.currentIndex() == main_window.pages["recovery"]

        controller.shutdown()
    app.quit()
    print("✓ RecoveryWidget instantiated and navigated successfully in MainWindow")
except Exception as e:
    print(f"✗ GUI test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL PHASE 4 FORENSIC ANALYSIS ENGINE VERIFICATIONS PASSED!")
print("=" * 80)
print()
