"""
Drive Eraser GUI Widget - interactive NIST SP 800-88 compliant storage sanitization.

Provides hardware device detection, safety constraint checks, multi-step confirmation gates,
multi-pass overwrite tracking, and post-sanitization sample verification reports.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme
from forensics_platform.sanitization import (
    DeviceInfo,
    SanitizationResult,
    SanitizationStandard,
    VerificationResult,
)


class DriveSanitizationWorker(QThread):
    """Background thread to perform non-blocking drive sanitization and verification."""

    progress_updated = Signal(dict)
    finished_success = Signal(object, object)  # (SanitizationResult, VerificationResult)
    finished_error = Signal(str)

    def __init__(
        self,
        sanitization_manager,
        device: DeviceInfo,
        standard: SanitizationStandard,
        confirmation_count: int,
        case_id: Optional[int] = None,
    ):
        super().__init__()
        self.mgr = sanitization_manager
        self.device = device
        self.standard = standard
        self.confirmation_count = confirmation_count
        self.case_id = case_id
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            san_res, ver_res = self.mgr.sanitize_device(
                device=self.device,
                standard=self.standard,
                confirmation_count=self.confirmation_count,
                case_id=self.case_id,
                progress_callback=self._on_progress,
                cancel_token=lambda: self._cancelled,
            )
            self.finished_success.emit(san_res, ver_res)
        except Exception as e:
            self.finished_error.emit(str(e))

    def _on_progress(self, progress_dict: Dict[str, Any]):
        self.progress_updated.emit(progress_dict)


class SanitizationConfirmDialog(QDialog):
    """Triple-confirmation modal dialog before physical or simulated drive sanitization."""

    def __init__(self, device: DeviceInfo, standard: SanitizationStandard, is_simulation: bool, parent=None):
        super().__init__(parent)
        self.device = device
        self.standard = standard
        self.is_simulation = is_simulation
        self.setWindowTitle("CRITICAL CONFIRMATION - Drive Sanitization")
        self.setMinimumWidth(560)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Warning banner
        banner = QFrame()
        banner_bg = "#fef3c7" if self.is_simulation else "#fee2e2"
        banner_border = "#f59e0b" if self.is_simulation else "#ef4444"
        banner_text = "#92400e" if self.is_simulation else "#991b1b"
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {banner_bg};
                border: 2px solid {banner_border};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        ban_layout = QVBoxLayout(banner)

        headline = "🛡️ SIMULATION SANITIZATION" if self.is_simulation else "⚠️ PERMANENT DATA DESTRUCTION"
        head_lbl = QLabel(f"<b>{headline}</b>")
        head_lbl.setStyleSheet(f"color: {banner_text}; font-size: 16px;")
        ban_layout.addWidget(head_lbl)

        desc = (
            f"Target Device: <b>{self.device.device_path}</b> ({self.device.size_formatted})<br>"
            f"Model: {self.device.model or 'Generic'} &nbsp;|&nbsp; Serial: {self.device.serial or 'N/A'}<br>"
            f"Selected Standard: <b>{self.standard.value}</b>"
        )
        desc_lbl = QLabel(desc)
        desc_lbl.setTextFormat(Qt.RichText)
        desc_lbl.setStyleSheet(f"color: {banner_text};")
        ban_layout.addWidget(desc_lbl)
        layout.addWidget(banner)

        # Confirmations
        self.chk_understand = QCheckBox("I understand that ALL data on this drive will be overwritten and unrecoverable.")
        self.chk_not_os = QCheckBox(f"I verify that {self.device.device_path} is NOT my operating system or backup disk.")
        self.chk_understand.toggled.connect(self._validate)
        self.chk_not_os.toggled.connect(self._validate)
        layout.addWidget(self.chk_understand)
        layout.addWidget(self.chk_not_os)

        # Typed phrase verification
        self.required_phrase = f"ERASE {self.device.device_path}"
        prompt_lbl = QLabel(f"Type <b>{self.required_phrase}</b> below to enable sanitization:")
        prompt_lbl.setTextFormat(Qt.RichText)
        layout.addWidget(prompt_lbl)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText(self.required_phrase)
        self.confirm_edit.textChanged.connect(self._validate)
        self.confirm_edit.setStyleSheet("padding: 8px; font-family: monospace; font-size: 14px;")
        layout.addWidget(self.confirm_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.erase_btn = QPushButton("Permanently Erase Device")
        self.erase_btn.setEnabled(False)
        self.erase_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:disabled { background-color: #cbd5e1; color: #64748b; }
        """)
        self.erase_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.erase_btn)
        layout.addLayout(btn_layout)

    def _validate(self):
        phrase_ok = (self.confirm_edit.text().strip() == self.required_phrase)
        checks_ok = self.chk_understand.isChecked() and self.chk_not_os.isChecked()
        self.erase_btn.setEnabled(phrase_ok and checks_ok)


class DriveEraserWidget(QWidget):
    """Modern Drive Sanitization view."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.worker: Optional[DriveSanitizationWorker] = None
        self.selected_device: Optional[DeviceInfo] = None
        self.devices: List[DeviceInfo] = []

        self._init_ui()
        self.refresh_devices()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        theme = get_current_theme()

        # 1. Header Card
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        header_layout = QVBoxLayout(header_card)
        header_layout.setSpacing(6)

        title_lbl = QLabel("💾 Secure Drive Eraser (NIST SP 800-88)")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.text_primary};")
        header_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Hardware-level and multi-pass block sanitization for magnetic hard drives, solid-state drives, "
            "and removable flash media with post-erasure LBA sample verification."
        )
        sub_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-size: 13px;")
        sub_lbl.setWordWrap(True)
        header_layout.addWidget(sub_lbl)

        # Simulation mode banner
        sim_banner = QFrame()
        is_sim = self.controller.is_simulation_mode
        sim_bg = "#eff6ff" if is_sim else "#fef2f2"
        sim_color = "#1d4ed8" if is_sim else "#b91c1c"
        sim_border = "#bfdbfe" if is_sim else "#fecaca"
        sim_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {sim_bg};
                border: 1px solid {sim_border};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        sb_layout = QHBoxLayout(sim_banner)
        sb_layout.setContentsMargins(4, 2, 4, 2)
        sim_txt = (
            "🛡️ <b>SAFETY MODE: SIMULATION ACTIVE</b> — Device operations will run virtualized with 0 real writes to media."
            if is_sim else
            "⚠️ <b>WARNING: PHYSICAL WRITE MODE ACTIVE</b> — Drive sanitization will permanently overwrite physical blocks!"
        )
        sim_lbl = QLabel(sim_txt)
        sim_lbl.setTextFormat(Qt.RichText)
        sim_lbl.setStyleSheet(f"color: {sim_color}; font-size: 12px;")
        sb_layout.addWidget(sim_lbl)
        header_layout.addWidget(sim_banner)

        main_layout.addWidget(header_card)

        # 2. Devices Table Card
        dev_card = QFrame()
        dev_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setSpacing(12)

        dh_layout = QHBoxLayout()
        dh_title = QLabel("Detected Storage Devices")
        dh_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.text_primary};")
        dh_layout.addWidget(dh_title)
        dh_layout.addStretch()

        ref_btn = QPushButton("🔄 Refresh Devices")
        ref_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_main};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 12px;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{ background-color: {theme.accent_subtle}; }}
        """)
        ref_btn.clicked.connect(self.refresh_devices)
        dh_layout.addWidget(ref_btn)
        dev_layout.addLayout(dh_layout)

        self.dev_table = QTableWidget()
        self.dev_table.setColumnCount(8)
        self.dev_table.setHorizontalHeaderLabels([
            "Device", "Type", "Capacity", "Model", "Serial", "Mount Status", "System Disk", "Safety State"
        ])
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.dev_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.dev_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dev_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dev_table.itemSelectionChanged.connect(self._on_device_selected)
        self.dev_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.bg_surface};
                color: {theme.text_primary};
                gridline-color: {theme.border};
                border: 1px solid {theme.border};
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {theme.bg_main};
                color: {theme.text_primary};
                font-weight: 600;
                padding: 6px;
                border: 1px solid {theme.border};
            }}
        """)
        dev_layout.addWidget(self.dev_table)

        main_layout.addWidget(dev_card)

        # 3. Sanitization Execution Card
        exec_card = QFrame()
        exec_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        exec_layout = QVBoxLayout(exec_card)
        exec_layout.setSpacing(14)

        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(16)

        std_lbl = QLabel("Sanitization Standard:")
        std_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        cfg_row.addWidget(std_lbl)

        self.std_combo = QComboBox()
        self.std_combo.setMinimumWidth(320)
        self.std_combo.setStyleSheet("padding: 6px;")
        for std in SanitizationStandard:
            self.std_combo.addItem(std.value, std)
        cfg_row.addWidget(self.std_combo)

        cfg_row.addStretch()

        self.start_btn = QPushButton("🚀 Sanitize Target Device")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{ background-color: #1d4ed8; }}
            QPushButton:disabled {{ background-color: #94a3b8; }}
        """)
        self.start_btn.clicked.connect(self._confirm_and_start)
        cfg_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Cancel")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:disabled { background-color: #cbd5e1; }
        """)
        self.stop_btn.clicked.connect(self._cancel_sanitization)
        cfg_row.addWidget(self.stop_btn)

        exec_layout.addLayout(cfg_row)

        # Progress elements
        self.status_lbl = QLabel("Select a storage device from the inventory table above.")
        self.status_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        exec_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                height: 14px;
                border-radius: 7px;
                background-color: #e2e8f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 7px;
            }
        """)
        exec_layout.addWidget(self.progress_bar)

        # Verification report box
        self.ver_box = QGroupBox("Post-Sanitization Verification Certificate")
        self.ver_box.setVisible(False)
        vb_layout = QVBoxLayout(self.ver_box)
        self.ver_report_lbl = QLabel()
        self.ver_report_lbl.setTextFormat(Qt.RichText)
        vb_layout.addWidget(self.ver_report_lbl)
        exec_layout.addWidget(self.ver_box)

        main_layout.addWidget(exec_card)

    def refresh_devices(self):
        """Enumerate block devices and populate table."""
        try:
            self.devices = self.controller.sanitization_manager.list_devices()
        except Exception as e:
            self.devices = []

        self.dev_table.setRowCount(0)
        for d in self.devices:
            row = self.dev_table.rowCount()
            self.dev_table.insertRow(row)

            # Device Type
            dtype = self.controller.sanitization_manager.classifier.classify(d).value.upper()

            # Mount status
            mnt_str = "Mounted (" + ", ".join(d.mountpoints[:2]) + ")" if d.is_mounted else "Unmounted"
            # System disk
            sys_str = "YES (Host OS)" if d.is_system_disk else "No"

            # Safety state
            safety = self.controller.sanitization_manager.check_safety(d, confirmation_count=3)
            if safety.blocked and not self.controller.is_simulation_mode:
                safe_str = "BLOCKED"
                safe_color = QColor("#ef4444")
            elif d.is_system_disk or d.is_mounted:
                safe_str = "WARNING"
                safe_color = QColor("#f59e0b")
            else:
                safe_str = "SAFE"
                safe_color = QColor("#10b981")

            self.dev_table.setItem(row, 0, QTableWidgetItem(d.device_path))
            self.dev_table.setItem(row, 1, QTableWidgetItem(dtype))
            self.dev_table.setItem(row, 2, QTableWidgetItem(d.size_formatted))
            self.dev_table.setItem(row, 3, QTableWidgetItem(d.model or "Generic"))
            self.dev_table.setItem(row, 4, QTableWidgetItem(d.serial or "N/A"))
            self.dev_table.setItem(row, 5, QTableWidgetItem(mnt_str))
            self.dev_table.setItem(row, 6, QTableWidgetItem(sys_str))

            safe_item = QTableWidgetItem(safe_str)
            safe_item.setForeground(safe_color)
            safe_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.dev_table.setItem(row, 7, safe_item)

    def _on_device_selected(self):
        selected_rows = self.dev_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_device = None
            self.start_btn.setEnabled(False)
            return

        idx = selected_rows[0].row()
        if 0 <= idx < len(self.devices):
            self.selected_device = self.devices[idx]
            self.start_btn.setEnabled(True)
            self.status_lbl.setText(f"Ready to sanitize: {self.selected_device.device_path} ({self.selected_device.size_formatted})")

            # Recommend standard
            rec = self.controller.sanitization_manager.classifier.recommend_sanitization(self.selected_device)
            # Match standard in combo
            for i in range(self.std_combo.count()):
                if self.std_combo.itemData(i).value == rec["standard"]:
                    self.std_combo.setCurrentIndex(i)
                    break

    def _confirm_and_start(self):
        if not self.selected_device:
            return

        std: SanitizationStandard = self.std_combo.currentData()
        is_sim = self.controller.is_simulation_mode

        dialog = SanitizationConfirmDialog(
            device=self.selected_device,
            standard=std,
            is_simulation=is_sim,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        # Start sanitization thread
        self.ver_box.setVisible(False)
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_lbl.setText("Starting sanitization engine...")

        self.worker = DriveSanitizationWorker(
            sanitization_manager=self.controller.sanitization_manager,
            device=self.selected_device,
            standard=std,
            confirmation_count=3,
        )
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.finished_success.connect(self._on_sanitization_finished)
        self.worker.finished_error.connect(self._on_sanitization_error)
        self.worker.start()

    def _cancel_sanitization(self):
        if self.worker and self.worker.isRunning():
            self.status_lbl.setText("Cancelling sanitization run...")
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def _on_progress_update(self, data: Dict[str, Any]):
        pct = int(data.get("overall_percent", 0))
        self.progress_bar.setValue(pct)
        status = data.get("status", "")
        self.status_lbl.setText(f"{status} ({pct}%)")

    def _on_sanitization_finished(self, san_res: SanitizationResult, ver_res: VerificationResult):
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if san_res.success:
            self.status_lbl.setText(f"✓ Sanitization and Verification Complete ({san_res.duration_seconds}s)")
            self.ver_box.setVisible(True)

            ver_color = "#166534" if ver_res.is_passed else "#991b1b"
            ver_badge = "✓ PASSED" if ver_res.is_passed else "✗ FAILED"
            report_text = (
                f"<b>Standard Applied:</b> {san_res.standard_applied}<br>"
                f"<b>Passes Completed:</b> {san_res.passes_completed} &nbsp;|&nbsp; "
                f"<b>Throughput:</b> {san_res.throughput_mb_s} MB/s &nbsp;|&nbsp; "
                f"<b>Duration:</b> {san_res.duration_seconds}s<br>"
                f"<b>Verification Result:</b> <span style='color: {ver_color}; font-weight: bold;'>{ver_badge}</span> "
                f"({ver_res.total_samples} sectors sampled, {ver_res.failed_samples} failed)<br>"
                f"<b>Expected Pattern:</b> <span style='font-family: monospace;'>0x{ver_res.expected_pattern_hex}</span>"
            )
            self.ver_report_lbl.setText(report_text)
            QMessageBox.information(self, "Sanitization Complete", f"Successfully sanitized {self.selected_device.device_path}!\nVerification: {ver_res.result.upper()}")
        else:
            self.status_lbl.setText(f"✗ Sanitization Failed: {'; '.join(san_res.errors)}")
            QMessageBox.critical(self, "Sanitization Failed", f"Operation failed:\n{'; '.join(san_res.errors)}")

    def _on_sanitization_error(self, err_msg: str):
        self.status_lbl.setText(f"✗ Error: {err_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{err_msg}")
