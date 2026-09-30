#!/usr/bin/env python3
"""
Phase 5 Verification Script - File Carving Engine.

Validates:
1. Module imports (Signatures, Scanner, Validators, ConfidenceEngine, CarvingEngine, CarvingWidget)
2. Signature Database catalog (JSON definitions loaded)
3. Format structure validators (JPEG, PNG, PDF, ZIP)
4. Multi-pattern signature scanner
5. End-to-end disk image carving, DB persistence, and cryptographic audit hash chain
6. GUI integration (CarvingWidget offscreen instantiation and navigation)
"""

import io
import os
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 5 VERIFICATION (FILE CARVING ENGINE)")
print("=" * 80)
print()

# 1. Imports
print("[1/6] Testing Phase 5 module imports...")
try:
    from forensics_platform.carving import (
        FileSignature,
        SignatureDatabase,
        SignatureScanner,
        ConfidenceEngine,
        JPEGValidator,
        PNGValidator,
        PDFValidator,
        ZIPValidator,
        CarvingEngine,
    )
    from forensics_platform.gui.forensics.carving_widget import CarvingWidget
    from forensics_platform.core import ApplicationController
    from forensics_platform.core.config import Config
    from forensics_platform.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    print("✓ All Phase 5 carving components and GUI classes imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# 2. Signature Database
print("\n[2/6] Checking Signature Database and JSON definitions...")
try:
    sig_db = SignatureDatabase()
    sigs = sig_db.list_signatures()
    print(f"  Loaded {len(sigs)} signatures: {', '.join(s.file_type for s in sigs)}")
    assert sig_db.get_signature("jpeg") is not None
    assert sig_db.get_signature("png") is not None
    assert sig_db.get_signature("pdf") is not None
    assert sig_db.get_signature("zip") is not None
    print("✓ Signature database verified")
except Exception as e:
    print(f"✗ Signature database check failed: {e}")
    sys.exit(1)

# 3. Format Structure Validators
print("\n[3/6] Testing binary structure validators (JPEG, PNG, PDF, ZIP)...")
try:
    # JPEG test
    j_val = JPEGValidator()
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x11\x08\x00\x20\x00\x20\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    eoi = b"\xff\xd9"
    jpeg_synth = soi + app0 + sof0 + sos + b"\x12\x34" + eoi
    j_res = j_val.validate(jpeg_synth)
    assert j_res.is_valid and j_res.footer_found

    # PNG test
    p_val = PNGValidator()
    magic = b"\x89PNG\r\n\x1a\n"
    ihdr_d = struct.pack(">IIBBBBB", 32, 32, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", len(ihdr_d)) + b"IHDR" + ihdr_d + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_d) & 0xFFFFFFFF)
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    png_synth = magic + ihdr + iend
    p_res = p_val.validate(png_synth)
    assert p_res.is_valid and p_res.footer_found

    # PDF test
    pdf_val = PDFValidator()
    pdf_synth = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\nstartxref\n30\n%%EOF\n"
    pdf_res = pdf_val.validate(pdf_synth)
    assert pdf_res.is_valid and pdf_res.footer_found

    # ZIP test
    z_val = ZIPValidator()
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("test.txt", "Forensic carving content")
    zip_synth = bio.getvalue()
    z_res = z_val.validate(zip_synth)
    assert z_res.is_valid and z_res.footer_found

    print("✓ All 4 format validators verified on synthetic binary structures")
except Exception as e:
    print(f"✗ Validator check failed: {e}")
    sys.exit(1)

# 4. Confidence Engine
print("\n[4/6] Testing Confidence Engine & Entropy scoring...")
try:
    ce = ConfidenceEngine()
    ent_zero = ce.calculate_entropy(b"\x00" * 1024)
    assert ent_zero == 0.0

    ent_high = ce.calculate_entropy(bytes(range(256)) * 4)
    assert ent_high > 7.0

    score = ce.evaluate(sig_db.get_signature("jpeg"), j_res, jpeg_synth)
    assert score.total >= 80
    assert score.classification == "High"
    print(f"✓ Confidence engine verified (Sample score: {score.total}% {score.classification})")
except Exception as e:
    print(f"✗ Confidence engine failed: {e}")
    sys.exit(1)

# 5. End-to-End Carving & Database/Audit Integration
print("\n[5/6] Testing End-to-End Disk Image Carving & Audit Trail...")
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    cfg_file = tmp_path / "test_config.yaml"
    cfg = Config(
        data_dir=tmp_path,
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "phase5_test.db",
    )
    cfg.save(cfg_file)
    ctrl = ApplicationController(cfg_file)

    try:
        # Create a test case
        case = ctrl.case_manager.create_case(
            case_number="CASE-2026-CARVE",
            title="Carving Engine Test",
            investigator="Forensic Examiner",
        )

        # Build raw disk image with embedded artifacts
        disk_file = tmp_path / "evidence_disk.dd"
        disk = bytearray(2 * 1024 * 1024)  # 2MB image

        # Sector 0: JPEG
        disk[0 : len(jpeg_synth)] = jpeg_synth
        # Sector 1024 (512KB): PNG
        disk[512 * 1024 : 512 * 1024 + len(png_synth)] = png_synth
        # Sector 2048 (1MB): PDF
        disk[1024 * 1024 : 1024 * 1024 + len(pdf_synth)] = pdf_synth
        # Sector 3072 (1.5MB): ZIP
        disk[1536 * 1024 : 1536 * 1024 + len(zip_synth)] = zip_synth

        disk_file.write_bytes(disk)

        # Execute carving
        out_carved = tmp_path / "carved"
        results = ctrl.carving_engine.carve_image(
            image_path=disk_file,
            target_types=["jpeg", "png", "pdf", "zip"],
            min_confidence=50,
            output_dir=out_carved,
            case_id=case["id"],
            sector_aligned=True,
        )

        assert len(results) == 4
        carved_types = {r["file_type"] for r in results}
        assert carved_types == {"jpeg", "png", "pdf", "zip"}

        for r in results:
            assert Path(r["path"]).exists()
            assert len(r["sha256"]) == 64
            assert r["confidence_score"] >= 50

        # Verify audit chain integrity
        chain = ctrl.audit_logger.verify_integrity()
        assert chain["valid"] is True
        assert chain["total_events"] >= 6  # genesis, case created, carving started, 4 carved files, carving completed

        ctrl.shutdown()
        print(f"✓ Carved 4/4 artifacts with 100% SHA-256 integrity and verified audit chain ({chain['total_events']} events)")
    except Exception as e:
        print(f"✗ Carving engine integration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 6. GUI Integration
print("\n[6/6] Testing Carving GUI integration (offscreen)...")
try:
    app = QApplication.instance()
    if not app:
        app = QApplication(["verify_phase5", "-platform", "offscreen"])

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

        assert "carving" in main_window.pages
        assert hasattr(main_window, "carving_widget")

        # Navigate to carving
        main_window._navigate_to("carving")
        assert main_window.content_stack.currentIndex() == main_window.pages["carving"]

        controller.shutdown()
    app.quit()
    print("✓ CarvingWidget instantiated and navigated successfully in MainWindow")
except Exception as e:
    print(f"✗ GUI test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL PHASE 5 FILE CARVING ENGINE VERIFICATIONS PASSED!")
print("=" * 80)
print()
