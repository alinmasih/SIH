"""
Settings Widget for Platform Configuration, Operational Mode Toggle, and Demo Data Seeding.

Features:
- Live Simulation Mode toggle with safety confirmations
- Forensic acquisition & carving threshold configurations
- One-click Demonstration Sandbox generation with synthetic media
- Environment, database, and tool status inspection
"""

import os
import io
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QSlider, QSpinBox, QComboBox, QCheckBox,
    QMessageBox, QScrollArea, QSizePolicy
)

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme
from forensics_platform.utils.logging import get_logger


def _generate_synthetic_media(output_path: Path) -> Path:
    """
    Create a 32MB standard MBR forensic disk image containing:
    1. Standard MBR partition table with active FAT16 partition starting at sector 2048.
    2. Real allocated filesystem files (README.TXT).
    3. Real deleted files (_EAKED.PDF, _EMO.TXT) with directory entries pointing to intact clusters.
    4. Real carveable file signatures (JPEG, PNG, ZIP) in unallocated media space.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_sectors = 65536  # 32 MB total image
    part_start_sec = 2048  # 1MB offset (standard sector alignment)
    part_size_sec = 32768  # 16MB partition

    disk = bytearray(total_sectors * 512)

    # 1. Sector 0: MBR Partition Table
    struct.pack_into(
        "<B3sB3sII",
        disk, 446,
        0x80,            # Active / Bootable
        b"\x00\x01\x01", # Start CHS
        0x06,            # FAT16
        b"\x00\x01\x01", # End CHS
        part_start_sec,  # Start LBA sector
        part_size_sec    # Sector count
    )
    disk[510:512] = b"\x55\xaa"

    # 2. Sector 2048: FAT16 Boot Sector
    sec_bytes = 512
    sec_per_clus = 4     # 2KB cluster
    reserved_sec = 1
    num_fats = 2
    root_entries = 512
    sec_per_fat = 32

    boot_offset = part_start_sec * 512
    disk[boot_offset:boot_offset + 3] = b"\xeb\x3c\x90"
    disk[boot_offset + 3:boot_offset + 11] = b"MSDOS5.0"
    struct.pack_into("<H", disk, boot_offset + 11, sec_bytes)
    struct.pack_into("<B", disk, boot_offset + 13, sec_per_clus)
    struct.pack_into("<H", disk, boot_offset + 14, reserved_sec)
    struct.pack_into("<B", disk, boot_offset + 16, num_fats)
    struct.pack_into("<H", disk, boot_offset + 17, root_entries)
    struct.pack_into("<H", disk, boot_offset + 19, part_size_sec)
    disk[boot_offset + 21] = 0xF8  # Media descriptor
    struct.pack_into("<H", disk, boot_offset + 22, sec_per_fat)
    struct.pack_into("<H", disk, boot_offset + 24, 32)
    struct.pack_into("<H", disk, boot_offset + 26, 64)
    struct.pack_into("<I", disk, boot_offset + 28, part_start_sec)
    disk[boot_offset + 36] = 0x80
    disk[boot_offset + 38] = 0x29
    struct.pack_into("<I", disk, boot_offset + 39, 0x9988AABB)
    disk[boot_offset + 43:boot_offset + 54] = b"SEIZED_EVID"
    disk[boot_offset + 54:boot_offset + 62] = b"FAT16   "
    disk[boot_offset + 510:boot_offset + 512] = b"\x55\xaa"

    # 3. FAT Tables
    fat1_offset = boot_offset + (reserved_sec * sec_bytes)
    fat2_offset = fat1_offset + (sec_per_fat * sec_bytes)
    for fo in [fat1_offset, fat2_offset]:
        disk[fo:fo + 4] = b"\xf8\xff\xff\xff"
        # cluster 2 allocated (README.TXT) -> EOF marker
        struct.pack_into("<H", disk, fo + 4, 0xFFFF)
        # clusters 3 and 4 are marked free in FAT table (representing deleted files)

    # 4. Root Directory and Data Clusters
    root_sec_count = (root_entries * 32 + sec_bytes - 1) // sec_bytes
    root_offset = fat2_offset + (sec_per_fat * sec_bytes)
    data_offset = root_offset + (root_sec_count * sec_bytes)

    def cluster_byte_offset(c):
        return data_offset + (c - 2) * (sec_per_clus * sec_bytes)

    readme_data = b"FORENSIC EVIDENCE PRESERVATION NOTICE\nSeized storage media under chain of custody.\n"
    pdf_data = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\nxref\n0 4\n"
        b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n164\n%%EOF\n"
    )
    memo_data = b"CONFIDENTIAL AGENT ROSTER - SECURITY LEVEL 5\nOPERATIVE: John Doe\nSTATUS: ACTIVE\n"

    disk[cluster_byte_offset(2):cluster_byte_offset(2) + len(readme_data)] = readme_data
    disk[cluster_byte_offset(3):cluster_byte_offset(3) + len(pdf_data)] = pdf_data
    disk[cluster_byte_offset(4):cluster_byte_offset(4) + len(memo_data)] = memo_data

    # Directory entry 0: README.TXT (active)
    e0 = bytearray(32)
    e0[0:11] = b"README  TXT"
    e0[11] = 0x20
    struct.pack_into("<H", e0, 26, 2)
    struct.pack_into("<I", e0, 28, len(readme_data))
    disk[root_offset:root_offset + 32] = e0

    # Directory entry 1: _EAKED.PDF (deleted -> 0xE5)
    e1 = bytearray(32)
    e1[0:11] = b"\xE5EAKED  PDF"
    e1[11] = 0x20
    struct.pack_into("<H", e1, 26, 3)
    struct.pack_into("<I", e1, 28, len(pdf_data))
    disk[root_offset + 32:root_offset + 64] = e1

    # Directory entry 2: _EMO.TXT (deleted -> 0xE5)
    e2 = bytearray(32)
    e2[0:11] = b"\xE5EMO    TXT"
    e2[11] = 0x20
    struct.pack_into("<H", e2, 26, 4)
    struct.pack_into("<I", e2, 28, len(memo_data))
    disk[root_offset + 64:root_offset + 96] = e2

    # 5. Embedded Carveable Files in Unallocated Media Space
    # 5a. Synthetic JPEG
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x11\x08\x00\x40\x00\x40\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    scan = b"CONFIDENTIAL_EXECUTIVE_PHOTO_CARVED_EVIDENCE" * 30
    eoi = b"\xff\xd9"
    jpeg_data = soi + app0 + sof0 + sos + scan + eoi

    # 5b. Synthetic PNG
    magic = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    idat_data = bytes(range(120))
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    idat_chunk = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc
    png_data = magic + ihdr_chunk + idat_chunk + iend_chunk

    # 5c. Synthetic ZIP
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("network_credentials.txt", "Admin:Password123!\nDatabase:PostgresProdSecret\nAPI_KEY:sk_live_99218a00f2")
        zf.writestr("incident_summary.txt", "Incident investigation report for seized endpoint media.")
    zip_data = bio.getvalue()

    unalloc_sec = part_start_sec + part_size_sec + 100
    disk[512 * unalloc_sec : 512 * unalloc_sec + len(jpeg_data)] = jpeg_data
    disk[512 * (unalloc_sec + 100) : 512 * (unalloc_sec + 100) + len(png_data)] = png_data
    disk[512 * (unalloc_sec + 300) : 512 * (unalloc_sec + 300) + len(zip_data)] = zip_data

    output_path.write_bytes(disk)
    return output_path


class SettingsWidget(QWidget):
    """Configuration and Operational Mode Settings Page."""

    simulation_mode_toggled = Signal(bool)
    demo_data_seeded = Signal()

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = get_logger(__name__)

        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        theme = get_current_theme()

        # Header
        header_layout = QVBoxLayout()
        title = QLabel("⚙️ Platform Settings & Operational Controls")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {theme.text_primary};")
        subtitle = QLabel("Configure operational safety modes, forensic carving thresholds, and sandbox test data.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        # -------------------------------------------------------------
        # Section 1: Operational Mode (Simulation vs Live)
        # -------------------------------------------------------------
        self.mode_group = QGroupBox("Operational Safety Mode")
        self.mode_group.setStyleSheet(self._group_box_stylesheet(theme))
        mode_layout = QVBoxLayout(self.mode_group)
        mode_layout.setSpacing(12)

        self.mode_banner = QFrame()
        self.mb_layout = QVBoxLayout(self.mode_banner)
        self.mb_layout.setContentsMargins(16, 14, 16, 14)

        self.mode_title = QLabel()
        self.mode_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.mb_layout.addWidget(self.mode_title)

        self.mode_desc = QLabel()
        self.mode_desc.setWordWrap(True)
        self.mode_desc.setStyleSheet("font-size: 13px; line-height: 1.4;")
        self.mb_layout.addWidget(self.mode_desc)

        mode_layout.addWidget(self.mode_banner)

        btn_row = QHBoxLayout()
        self.toggle_mode_btn = QPushButton()
        self.toggle_mode_btn.setMinimumHeight(44)
        self.toggle_mode_btn.clicked.connect(self._toggle_simulation_mode)
        btn_row.addWidget(self.toggle_mode_btn)
        btn_row.addStretch()
        mode_layout.addLayout(btn_row)

        layout.addWidget(self.mode_group)

        # -------------------------------------------------------------
        # Section 2: 1-Click Demonstration Sandbox
        # -------------------------------------------------------------
        self.demo_group = QGroupBox("🚀 Demonstration Data Sandbox")
        self.demo_group.setStyleSheet(self._group_box_stylesheet(theme))
        demo_layout = QVBoxLayout(self.demo_group)
        demo_layout.setSpacing(12)

        demo_desc = QLabel(
            "If you do not have external raw forensic disk images (.dd) available, click below to automatically "
            "generate an authorized sample investigation case (<b>CASE-DEMO-2026</b>) with an embedded synthetic disk image "
            "containing real JPEG, PNG, and ZIP files. This enables immediate hands-on testing of File Carving, Recovery, and Reporting."
        )
        demo_desc.setTextFormat(Qt.RichText)
        demo_desc.setWordWrap(True)
        demo_desc.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        demo_layout.addWidget(demo_desc)

        demo_btn_row = QHBoxLayout()
        self.seed_demo_btn = QPushButton("⚡ Populate Demo Case & Synthetic Disk Image")
        self.seed_demo_btn.setMinimumHeight(44)
        self.seed_demo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: {theme.accent_text};
                font-weight: bold;
                padding: 8px 24px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.seed_demo_btn.clicked.connect(self._seed_demo_data)
        demo_btn_row.addWidget(self.seed_demo_btn)
        demo_btn_row.addStretch()
        demo_layout.addLayout(demo_btn_row)

        layout.addWidget(self.demo_group)

        # -------------------------------------------------------------
        # Section 3: Forensic Engine Settings
        # -------------------------------------------------------------
        self.forensic_group = QGroupBox("Forensic Analysis & Carving Parameters")
        self.forensic_group.setStyleSheet(self._group_box_stylesheet(theme))
        fg_layout = QVBoxLayout(self.forensic_group)
        fg_layout.setSpacing(14)

        # Confidence threshold
        th_layout = QHBoxLayout()
        th_lbl = QLabel("Default Minimum Carving Confidence:")
        th_lbl.setFixedWidth(260)
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(10, 95)
        self.conf_slider.setValue(self.controller.config.default_confidence_threshold)
        self.conf_val_lbl = QLabel(f"{self.conf_slider.value()}%")
        self.conf_val_lbl.setFixedWidth(50)
        self.conf_slider.valueChanged.connect(lambda v: self.conf_val_lbl.setText(f"{v}%"))
        th_layout.addWidget(th_lbl)
        th_layout.addWidget(self.conf_slider)
        th_layout.addWidget(self.conf_val_lbl)
        fg_layout.addLayout(th_layout)

        # Hash algorithm
        hash_row = QHBoxLayout()
        hash_lbl = QLabel("Primary Cryptographic Hash:")
        hash_lbl.setFixedWidth(260)
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["SHA-256 (NIST FIPS 180-4)", "MD5 (Legacy Compatibility)"])
        self.hash_combo.setCurrentIndex(0 if self.controller.config.hash_algorithm == "sha256" else 1)
        hash_row.addWidget(hash_lbl)
        hash_row.addWidget(self.hash_combo)
        hash_row.addStretch()
        fg_layout.addLayout(hash_row)

        # Save settings button
        save_btn_row = QHBoxLayout()
        self.save_settings_btn = QPushButton("Save Forensic Preferences")
        self.save_settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{
                border-color: {theme.accent};
                color: {theme.accent};
            }}
        """)
        self.save_settings_btn.clicked.connect(self._save_preferences)
        save_btn_row.addWidget(self.save_settings_btn)
        save_btn_row.addStretch()
        fg_layout.addLayout(save_btn_row)

        layout.addWidget(self.forensic_group)

        # -------------------------------------------------------------
        # Section 4: System & Storage Directories
        # -------------------------------------------------------------
        self.sys_group = QGroupBox("System Storage & Tool Integration")
        self.sys_group.setStyleSheet(self._group_box_stylesheet(theme))
        sg_layout = QVBoxLayout(self.sys_group)
        sg_layout.setSpacing(8)

        status = self.controller.get_system_status()
        ext_tools = status.get("external_tools", {})
        tsk_status = "✓ Installed & Verified" if ext_tools.get("sleuthkit") else "ℹ️ Optional (Using Native Stream Analyzers)"

        info_rows = [
            ("SQLite Database:", str(self.controller.config.database_path)),
            ("Case Working Directory:", str(self.controller.config.case_dir)),
            ("Application Logs:", str(self.controller.config.log_dir)),
            ("The Sleuth Kit (TSK):", tsk_status),
        ]

        for label, val in info_rows:
            r = QHBoxLayout()
            lbl = QLabel(f"<b>{label}</b>")
            lbl.setFixedWidth(220)
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-family: monospace;")
            r.addWidget(lbl)
            r.addWidget(v_lbl)
            r.addStretch()
            sg_layout.addLayout(r)

        layout.addWidget(self.sys_group)
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _group_box_stylesheet(self, theme) -> str:
        return f"""
            QGroupBox {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 14px;
                color: {theme.text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 6px;
            }}
        """

    def refresh(self):
        """Update widget displays to reflect current configuration state."""
        is_sim = self.controller.is_simulation_mode

        if is_sim:
            self.mode_banner.setStyleSheet("""
                QFrame {
                    background-color: #f0fdf4;
                    border: 2px solid #22c55e;
                    border-radius: 8px;
                }
            """)
            self.mode_title.setText("🛡️ SIMULATION MODE: ACTIVE (Safe Mode)")
            self.mode_title.setStyleSheet("color: #15803d; font-size: 16px; font-weight: bold;")
            self.mode_desc.setText(
                "All destructive drive erasure and wipe commands run in virtual memory loops with ZERO physical writes to disks. "
                "All file carving, evidence acquisition, case management, and court reporting operations function at 100% full capacity. "
                "Recommended for testing, training, and demonstrations."
            )
            self.mode_desc.setStyleSheet("color: #166534; font-size: 13px;")

            self.toggle_mode_btn.setText("⚠️ Switch to LIVE PHYSICAL WRITE MODE")
            self.toggle_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fee2e2;
                    border: 1px solid #ef4444;
                    color: #b91c1c;
                    font-weight: bold;
                    padding: 8px 20px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #ef4444;
                    color: white;
                }
            """)
        else:
            self.mode_banner.setStyleSheet("""
                QFrame {
                    background-color: #fef2f2;
                    border: 2px solid #ef4444;
                    border-radius: 8px;
                }
            """)
            self.mode_title.setText("⚠️ LIVE PHYSICAL WRITE MODE: ACTIVE (Caution)")
            self.mode_title.setStyleSheet("color: #b91c1c; font-size: 16px; font-weight: bold;")
            self.mode_desc.setText(
                "Physical drive sanitization will send raw block write commands (/dev/sdX, /dev/nvmeX). "
                "System disks (/, /boot, swap) remain permanently locked by safety interlocks. "
                "Requires running with root/sudo permissions for direct hardware access."
            )
            self.mode_desc.setStyleSheet("color: #991b1b; font-size: 13px;")

            self.toggle_mode_btn.setText("🛡️ Switch to SAFE SIMULATION MODE")
            self.toggle_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dcfce7;
                    border: 1px solid #22c55e;
                    color: #15803d;
                    font-weight: bold;
                    padding: 8px 20px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #22c55e;
                    color: white;
                }
            """)

    def _toggle_simulation_mode(self):
        """Toggle simulation mode with safety confirmation."""
        current_sim = self.controller.is_simulation_mode

        if current_sim:
            # Switching to LIVE mode - require explicit confirmation
            confirm = QMessageBox.warning(
                self,
                "Confirm Live Physical Mode",
                "Are you sure you want to switch to LIVE PHYSICAL WRITE MODE?\n\n"
                "• Drive sanitization operations will overwrite physical storage blocks.\n"
                "• Ensure you understand which target disks are connected.\n"
                "• Running as standard user will block raw block writes without sudo.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            new_mode = False
        else:
            new_mode = True

        self.controller.config_manager.set("simulation_mode", new_mode)
        self.controller.audit_logger.log_event(
            event_type="configuration_changed",
            event_data={"key": "simulation_mode", "old": current_sim, "new": new_mode},
            event_category="configuration"
        )
        self.refresh()
        self.simulation_mode_toggled.emit(new_mode)

    def _seed_demo_data(self, show_dialog: bool = True):
        """Create a complete demonstration case with synthetic raw image containing carveable files."""
        try:
            # 1. Create or retrieve demo case
            existing_cases = self.controller.case_manager.list_cases()
            demo_case = next((c for c in existing_cases if c["case_number"] == "CASE-DEMO-2026"), None)

            if not demo_case:
                demo_case = self.controller.case_manager.create_case(
                    case_number="CASE-DEMO-2026",
                    title="Project Cyber Citadel - Evidence Inspection",
                    investigator="Lead Forensic Examiner",
                    description="Automated demonstration investigation case containing synthetic flash media."
                )

            # 2. Generate synthetic disk image
            case_folder = self.controller.case_manager.get_case_directory(demo_case["id"])
            disk_path = case_folder / "evidence" / "seized_flash_media.dd"
            _generate_synthetic_media(disk_path)

            # 3. Register evidence item
            existing_evd = self.controller.evidence_manager.list_evidence(case_id=demo_case["id"])
            demo_evd = next((e for e in existing_evd if e["evidence_number"] == "EVD-DEMO-01"), None)

            if not demo_evd:
                demo_evd = self.controller.evidence_manager.register_evidence(
                    case_id=demo_case["id"],
                    evidence_number="EVD-DEMO-01",
                    source_type="disk_image",
                    image_path=str(disk_path),
                    device_model="SanDisk Ultra USB 3.0 (Demo)",
                    device_serial="DEMO-SN-9988-ABC",
                    notes="Synthetic 4MB disk image populated with embedded JPEG, PNG, and ZIP payload artifacts.",
                    calculate_hashes=True
                )

            self.demo_data_seeded.emit()

            if show_dialog:
                QMessageBox.information(
                    self,
                    "Demonstration Data Ready",
                    f"✅ Successfully seeded demonstration data!\n\n"
                    f"• Case: {demo_case['case_number']} - {demo_case['title']}\n"
                    f"• Evidence: {demo_evd['evidence_number']} ({disk_path.name})\n"
                    f"• Dual Baseline Hashes: SHA-256 and MD5 recorded.\n\n"
                    f"You can now test:\n"
                    f"1. 'File Carving' -> Select this image and click 'Start Carving Engine' to recover JPEG, PNG, and ZIP files.\n"
                    f"2. 'File Recovery' -> Inspect partition structures.\n"
                    f"3. 'Reports' -> Generate an official court-admissible PDF or HTML investigation report."
                )
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(self, "Error Seeding Demo Data", f"Failed to seed demo data: {e}")
            else:
                raise e

    def _save_preferences(self):
        """Save updated slider and combo box preferences to config."""
        threshold = self.conf_slider.value()
        algorithm = "sha256" if self.hash_combo.currentIndex() == 0 else "md5"

        self.controller.config_manager.set("default_confidence_threshold", threshold)
        self.controller.config_manager.set("hash_algorithm", algorithm)

        QMessageBox.information(self, "Settings Saved", "Forensic preferences updated and saved to config.yaml.")
