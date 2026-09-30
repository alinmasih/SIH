#!/usr/bin/env python3
"""
Phase 3 Verification Script - Case & Evidence Management + Light Theme.

Validates:
1. Light Theme initialization & dynamic theme switcher
2. CaseManager lifecycle operations
3. EvidenceManager registration & cryptographic hashing
4. Integrity verification & tamper detection
5. Tamper-evident hash chain audit logging
6. Qt GUI widgets (CaseManagerWidget, EvidenceManagerWidget, AuditViewerWidget)
"""

import sys
import os
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 3 & LIGHT THEME VERIFICATION")
print("=" * 80)
print()

# Step 1: Import modules
print("[1/6] Testing Phase 3 module imports...")
try:
    from forensics_platform.core import ApplicationController, Config
    from forensics_platform.forensics.case_manager import CaseManager
    from forensics_platform.forensics.evidence_manager import EvidenceManager
    from forensics_platform.gui.themes import get_theme_manager, get_current_theme, LIGHT_THEME
    from forensics_platform.gui.forensics import CaseManagerWidget, EvidenceManagerWidget, AuditViewerWidget
    from forensics_platform.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    print("✓ All Phase 3 backend and GUI components imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test Light Theme
print("\n[2/6] Testing Light Theme system...")
try:
    theme_mgr = get_theme_manager()
    theme_mgr.set_theme("light")
    current = get_current_theme()
    assert current.name == "light", f"Expected light, got {current.name}"
    assert current.bg_main == "#f8fafc"
    assert current.text_primary == "#0f172a"
    assert current.accent == "#2563eb"

    # Test toggle
    toggled = theme_mgr.toggle_theme()
    assert toggled.name == "dark"
    restored = theme_mgr.toggle_theme()
    assert restored.name == "light"

    print("✓ Light Theme verified (default active, high contrast palette, toggle operational)")
except Exception as e:
    print(f"✗ Theme test failed: {e}")
    sys.exit(1)

# Step 3: Test CaseManager
print("\n[3/6] Testing CaseManager backend...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    config = Config(
        database_path=tmp_path / "test.db",
        case_dir=tmp_path / "cases",
        data_dir=tmp_path,
        log_dir=tmp_path / "logs",
        temp_dir=tmp_path / "temp",
        theme="light",
    )
    from forensics_platform.database.session import DatabaseManager
    from forensics_platform.audit.audit_logger import AuditLogger

    db = DatabaseManager(config.database_path)
    db.initialize()
    audit = AuditLogger(db.get_session)

    case_mgr = CaseManager(db, audit, config)
    ev_mgr = EvidenceManager(db, audit, config)

    try:
        # Create case
        c = case_mgr.create_case(
            case_number="CASE-2026-V3",
            title="Phase 3 Verification Incident",
            investigator="Lead Examiner",
            description="End to end test case"
        )
        assert c["id"] is not None
        assert c["status"] == "active"
        assert (config.case_dir / "CASE-2026-V3" / "evidence").exists()

        # Update case
        up = case_mgr.update_case(c["id"], title="Updated Phase 3 Incident")
        assert up["title"] == "Updated Phase 3 Incident"

        # List cases
        cases = case_mgr.list_cases(search="V3")
        assert len(cases) == 1

        print("✓ CaseManager working (creation, directory setup, update, listing)")
    except Exception as e:
        print(f"✗ CaseManager failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 4: Test EvidenceManager
    print("\n[4/6] Testing EvidenceManager & Cryptographic Hashing...")
    try:
        test_file = tmp_path / "disk.img"
        test_file.write_bytes(b"DIGITAL_FORENSICS_EVIDENCE_PAYLOAD_PHASE_3_VERIFY")

        ev = ev_mgr.register_evidence(
            case_id=c["id"],
            evidence_number="EVID-001",
            source_type="disk_image",
            image_path=str(test_file),
            device_model="Virtual USB Block Device",
            notes="Sample image for validation"
        )

        assert ev["id"] is not None
        assert len(ev["sha256"]) == 64
        assert ev["capacity"] == 49

        # Test integrity check PASS
        res_pass = ev_mgr.verify_integrity(ev["id"])
        assert res_pass["verified"] is True
        assert res_pass["status"] == "MATCH"

        # Simulate tamper
        test_file.write_bytes(b"TAMPERED_MODIFIED_DATA")
        res_fail = ev_mgr.verify_integrity(ev["id"])
        assert res_fail["verified"] is False
        assert res_fail["status"] == "TAMPERED"

        print("✓ EvidenceManager working (registration, auto SHA-256, integrity verification, tamper detection)")
    except Exception as e:
        print(f"✗ EvidenceManager failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 5: Test Audit Chain
    print("\n[5/6] Testing Tamper-Evident Audit Chain...")
    try:
        chain_res = audit.verify_integrity()
        assert chain_res["valid"] is True
        assert chain_res["total_events"] >= 4  # genesis + case_created + case_updated + evidence_registered + verify

        print(f"✓ Audit hash chain intact ({chain_res['total_events']} events verified from genesis)")
    except Exception as e:
        print(f"✗ Audit chain verification failed: {e}")
        sys.exit(1)

    db.close()

# Step 6: Test GUI Widgets (Offscreen)
print("\n[6/6] Testing GUI integration (MainWindow, CaseManagerWidget, EvidenceManagerWidget, AuditViewerWidget)...")
try:
    app = QApplication.instance()
    if not app:
        app = QApplication(["verify_phase3", "-platform", "offscreen"])

    controller = ApplicationController()
    main_window = MainWindow(controller)

    assert "cases" in main_window.pages
    assert "evidence" in main_window.pages
    assert "audit" in main_window.pages

    # Switch pages
    main_window._navigate_to("cases")
    assert main_window.content_stack.currentIndex() == main_window.pages["cases"]

    main_window._navigate_to("evidence")
    assert main_window.content_stack.currentIndex() == main_window.pages["evidence"]

    main_window._navigate_to("audit")
    assert main_window.content_stack.currentIndex() == main_window.pages["audit"]

    # Verify theme toggle in GUI
    assert main_window.controller.config.theme == "light"

    controller.shutdown()
    app.quit()
    print("✓ GUI shell and Phase 3 widgets initialized and navigated cleanly in Light Theme")
except Exception as e:
    print(f"✗ GUI widget test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL PHASE 3 & LIGHT THEME VERIFICATIONS PASSED!")
print("=" * 80)
print()
