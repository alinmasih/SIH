"""
Evidence Management GUI Widget.

Provides forensic evidence registration, metadata extraction, cryptographic
SHA-256 hash calculation with background threading, and integrity verification.
"""

import os
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QTextEdit, QMessageBox, QFrame,
    QFileDialog, QProgressBar, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme
from forensics_platform.forensics.evidence_manager import VALID_SOURCE_TYPES


def format_bytes(size: Optional[int]) -> str:
    """Format byte count into human-readable representation."""
    if size is None or size < 0:
        return "Unknown"
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    s = float(size)
    while s >= 1024.0 and i < len(units) - 1:
        s /= 1024.0
        i += 1
    return f"{s:.2f} {units[i]}"


class HashWorker(QThread):
    """Background worker thread for calculating cryptographic hashes without blocking GUI."""

    progress = Signal(int, int)  # (bytes_read, total_bytes)
    finished_success = Signal(dict)
    finished_error = Signal(str)

    def __init__(self, evidence_manager, registration_kwargs: dict):
        super().__init__()
        self.evidence_manager = evidence_manager
        self.kwargs = registration_kwargs

    def run(self):
        try:
            def progress_cb(current, total):
                self.progress.emit(current, total)

            self.kwargs["progress_callback"] = progress_cb
            result = self.evidence_manager.register_evidence(**self.kwargs)
            self.finished_success.emit(result)
        except Exception as e:
            self.finished_error.emit(str(e))


class RegisterEvidenceDialog(QDialog):
    """Modal dialog for registering forensic evidence."""

    def __init__(self, controller: ApplicationController, preselected_case_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.preselected_case_id = preselected_case_id
        self.registered_evidence: Optional[Dict[str, Any]] = None
        self.setWindowTitle("Register Forensic Evidence")
        self.setMinimumWidth(550)
        self._init_ui()

    def _init_ui(self):
        theme = get_current_theme()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Evidence Acquisition Registration")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.accent};")
        layout.addWidget(header)

        # Case selection
        layout.addWidget(QLabel("Associated Case *"))
        self.case_combo = QComboBox()
        cases = self.controller.case_manager.list_cases(status="active")
        if not cases:
            cases = self.controller.case_manager.list_cases()  # Fallback to all cases

        for c in cases:
            self.case_combo.addItem(f"{c['case_number']} - {c['title']}", c["id"])

        if self.preselected_case_id:
            idx = self.case_combo.findData(self.preselected_case_id)
            if idx >= 0:
                self.case_combo.setCurrentIndex(idx)

        self.case_combo.currentIndexChanged.connect(self._on_case_changed)
        layout.addWidget(self.case_combo)

        # Evidence Number
        layout.addWidget(QLabel("Evidence Identifier *"))
        self.evidence_num_input = QLineEdit()
        layout.addWidget(self.evidence_num_input)
        self._update_suggested_evidence_num()

        # Source Type
        layout.addWidget(QLabel("Evidence Source Type *"))
        self.source_type_combo = QComboBox()
        for st in VALID_SOURCE_TYPES:
            display_name = st.replace("_", " ").title()
            self.source_type_combo.addItem(display_name, st)
        layout.addWidget(self.source_type_combo)

        # File picker for Image / Source path
        layout.addWidget(QLabel("Forensic Image / File Path (optional)"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("/path/to/disk_image.dd or evidence file...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Device details
        dev_layout = QHBoxLayout()
        dev_col1 = QVBoxLayout()
        dev_col1.addWidget(QLabel("Device Model"))
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g. Kingston DataTraveler 32GB")
        dev_col1.addWidget(self.model_input)
        dev_layout.addLayout(dev_col1)

        dev_col2 = QVBoxLayout()
        dev_col2.addWidget(QLabel("Serial Number"))
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("e.g. 0014D12345ABC")
        dev_col2.addWidget(self.serial_input)
        dev_layout.addLayout(dev_col2)
        layout.addLayout(dev_layout)

        # Notes
        layout.addWidget(QLabel("Chain of Custody / Acquisition Notes"))
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Acquisition tool, physical condition, seizure location...")
        self.notes_input.setMaximumHeight(80)
        layout.addWidget(self.notes_input)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status text
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.register_btn = QPushButton("Register Evidence")
        self.register_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: {theme.accent_text};
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.register_btn.clicked.connect(self._on_register)
        btn_layout.addWidget(self.register_btn)

        layout.addLayout(btn_layout)

    def _on_case_changed(self):
        self._update_suggested_evidence_num()

    def _update_suggested_evidence_num(self):
        case_id = self.case_combo.currentData()
        if case_id:
            suggested = self.controller.evidence_manager.generate_next_evidence_number(case_id)
            self.evidence_num_input.setText(suggested)

    def _browse_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Forensic Evidence File or Image",
            "",
            "All Files (*);;Raw Images (*.dd *.raw *.img *.001);;E01 Images (*.e01);;Packet Captures (*.pcap *.pcapng)"
        )
        if filename:
            self.path_input.setText(filename)
            # Auto-fill model if empty
            if not self.model_input.text():
                self.model_input.setText(os.path.basename(filename))

    def _on_register(self):
        case_id = self.case_combo.currentData()
        if not case_id:
            QMessageBox.warning(self, "Validation Error", "Please select or create an active case first.")
            return

        ev_num = self.evidence_num_input.text().strip()
        if not ev_num:
            QMessageBox.warning(self, "Validation Error", "Evidence number cannot be empty.")
            return

        source_type = self.source_type_combo.currentData()
        path = self.path_input.text().strip() or None
        model = self.model_input.text().strip() or None
        serial = self.serial_input.text().strip() or None
        notes = self.notes_input.toPlainText().strip() or None

        # Disable buttons while registering
        self.register_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText("Computing SHA-256 and MD5 cryptographic integrity hashes...")

        reg_kwargs = {
            "case_id": case_id,
            "evidence_number": ev_num,
            "source_type": source_type,
            "image_path": path,
            "device_model": model,
            "device_serial": serial,
            "notes": notes,
            "calculate_hashes": True,
        }

        self.worker = HashWorker(self.controller.evidence_manager, reg_kwargs)
        self.worker.progress.connect(self._on_hash_progress)
        self.worker.finished_success.connect(self._on_registration_complete)
        self.worker.finished_error.connect(self._on_registration_error)
        self.worker.start()

    def _on_hash_progress(self, current: int, total: int):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
            self.status_label.setText(f"Hashing: {format_bytes(current)} / {format_bytes(total)} ({pct}%)")

    def _on_registration_complete(self, result: dict):
        self.registered_evidence = result
        self.accept()

    def _on_registration_error(self, error_msg: str):
        theme = get_current_theme()
        self.register_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet(f"color: {theme.status_danger}; font-weight: bold;")


class EvidenceDetailDialog(QDialog):
    """Detailed view for single evidence item including integrity re-verification."""

    def __init__(self, controller: ApplicationController, evidence_dict: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.controller = controller
        self.evidence = evidence_dict
        self.setWindowTitle(f"Evidence Details: {evidence_dict['evidence_number']}")
        self.setMinimumWidth(600)
        self._init_ui()

    def _init_ui(self):
        theme = get_current_theme()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header = QLabel(f"Evidence: {self.evidence['evidence_number']}")
        header.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.accent};")
        layout.addWidget(header)

        # Meta grid
        info_box = QGroupBox("Cryptographic & Hardware Metadata")
        info_layout = QVBoxLayout(info_box)

        rows = [
            ("Case Number:", self.evidence.get("case_number", "N/A")),
            ("Source Type:", self.evidence["source_type"].replace("_", " ").title()),
            ("Device Model:", self.evidence.get("device_model") or "Not Specified"),
            ("Serial Number:", self.evidence.get("device_serial") or "Not Specified"),
            ("Capacity / Size:", format_bytes(self.evidence.get("capacity"))),
            ("Acquisition Path:", self.evidence.get("image_path") or self.evidence.get("source_path") or "N/A"),
            ("Acquisition Tool:", self.evidence.get("acquisition_tool") or "N/A"),
            ("SHA-256 Hash:", self.evidence.get("sha256", "N/A")),
            ("MD5 Hash:", self.evidence.get("md5") or "N/A"),
            ("Acquisition Time:", str(self.evidence.get("acquisition_time"))),
            ("Notes:", self.evidence.get("notes") or "None recorded"),
        ]

        for label_text, val in rows:
            row_layout = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-weight: bold; width: 140px; color: {theme.text_secondary};")
            lbl.setFixedWidth(140)
            val_lbl = QLabel(str(val))
            val_lbl.setWordWrap(True)
            val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row_layout.addWidget(lbl)
            row_layout.addWidget(val_lbl)
            info_layout.addLayout(row_layout)

        layout.addWidget(info_box)

        # Integrity check result label
        self.verify_result_label = QLabel("")
        self.verify_result_label.setStyleSheet("padding: 8px; border-radius: 6px; font-weight: bold;")
        self.verify_result_label.setVisible(False)
        layout.addWidget(self.verify_result_label)

        # Buttons
        btn_layout = QHBoxLayout()
        verify_btn = QPushButton("🛡️ Re-Verify SHA-256 Integrity")
        verify_btn.clicked.connect(self._run_integrity_check)
        btn_layout.addWidget(verify_btn)

        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _run_integrity_check(self):
        theme = get_current_theme()
        try:
            res = self.controller.evidence_manager.verify_integrity(self.evidence["id"])
            self.verify_result_label.setVisible(True)
            if res["verified"]:
                self.verify_result_label.setText("✓ Cryptographic Integrity PASSED: File hash matches recorded SHA-256.")
                self.verify_result_label.setStyleSheet(
                    f"background-color: {theme.accent_subtle}; color: {theme.status_success}; border: 1px solid {theme.status_success}; padding: 8px;"
                )
            else:
                self.verify_result_label.setText(f"✗ INTEGRITY FAILURE: {res['message']}")
                self.verify_result_label.setStyleSheet(
                    f"background-color: #fee2e2; color: {theme.status_danger}; border: 1px solid {theme.status_danger}; padding: 8px;"
                )
        except Exception as e:
            QMessageBox.critical(self, "Verification Error", str(e))


class EvidenceManagerWidget(QWidget):
    """Main view for Evidence Management."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.evidence_cache: List[Dict[str, Any]] = []
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        theme = get_current_theme()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🗂️ Forensic Evidence Management")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {theme.text_primary};")
        subtitle = QLabel("Track digital evidence acquisitions, extract hardware metadata, and verify hash integrity.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        self.reg_btn = QPushButton("+ Register Evidence")
        self.reg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: {theme.accent_text};
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.reg_btn.clicked.connect(self.open_register_evidence_dialog)
        top_bar.addWidget(self.reg_btn)

        main_layout.addLayout(top_bar)

        # Filters Toolbar
        filter_box = QFrame()
        filter_box.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(8, 4, 8, 4)

        filter_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search evidence #, model, path, or notes...")
        self.search_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.search_input, stretch=2)

        filter_layout.addWidget(QLabel("Filter Case:"))
        self.case_filter = QComboBox()
        self.case_filter.addItem("All Cases", None)
        self.case_filter.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.case_filter, stretch=1)

        filter_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", "")
        for st in VALID_SOURCE_TYPES:
            self.type_filter.addItem(st.replace("_", " ").title(), st)
        self.type_filter.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.type_filter, stretch=1)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        main_layout.addWidget(filter_box)

        # Evidence Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Evidence #", "Case", "Source Type", "Device / Filename", "Capacity", "SHA-256 Hash", "Acquired", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        main_layout.addWidget(self.table, stretch=1)

    def refresh(self):
        """Reload cases in filter and evidence in table."""
        # Refresh case filter dropdown
        current_case_id = self.case_filter.currentData()
        self.case_filter.blockSignals(True)
        self.case_filter.clear()
        self.case_filter.addItem("All Cases", None)
        cases = self.controller.case_manager.list_cases()
        for c in cases:
            self.case_filter.addItem(f"{c['case_number']}", c["id"])
        idx = self.case_filter.findData(current_case_id)
        if idx >= 0:
            self.case_filter.setCurrentIndex(idx)
        self.case_filter.blockSignals(False)

        self.evidence_cache = self.controller.evidence_manager.list_evidence()
        self._apply_filter()

    def _apply_filter(self):
        theme = get_current_theme()
        search = self.search_input.text().strip().lower()
        case_id = self.case_filter.currentData()
        source_type = self.type_filter.currentData()

        filtered = []
        for ev in self.evidence_cache:
            if case_id is not None and ev["case_id"] != case_id:
                continue
            if source_type and ev["source_type"] != source_type:
                continue
            if search:
                haystack = f"{ev['evidence_number']} {ev['case_number']} {ev.get('device_model') or ''} {ev.get('image_path') or ''} {ev.get('notes') or ''}".lower()
                if search not in haystack:
                    continue
            filtered.append(ev)

        self.table.setRowCount(len(filtered))
        for row, ev in enumerate(filtered):
            # Evidence #
            item_num = QTableWidgetItem(ev["evidence_number"])
            item_num.setData(Qt.UserRole, ev["id"])
            item_num.setFont(item_num.font())
            self.table.setItem(row, 0, item_num)

            # Case
            self.table.setItem(row, 1, QTableWidgetItem(ev["case_number"]))

            # Source Type
            st_clean = ev["source_type"].replace("_", " ").title()
            self.table.setItem(row, 2, QTableWidgetItem(st_clean))

            # Device / Filename
            label_dev = ev.get("device_model")
            if not label_dev and ev.get("image_path"):
                label_dev = os.path.basename(ev["image_path"])
            self.table.setItem(row, 3, QTableWidgetItem(label_dev or "N/A"))

            # Capacity
            size_str = format_bytes(ev.get("capacity"))
            self.table.setItem(row, 4, QTableWidgetItem(size_str))

            # SHA-256 (abbreviated)
            sha = ev.get("sha256", "")
            short_sha = f"{sha[:8]}...{sha[-8:]}" if len(sha) >= 16 else sha
            item_sha = QTableWidgetItem(short_sha)
            item_sha.setToolTip(f"Full SHA-256: {sha}")
            self.table.setItem(row, 5, item_sha)

            # Acquired
            acq_str = ev["acquisition_time"].strftime("%Y-%m-%d %H:%M") if ev.get("acquisition_time") else ""
            self.table.setItem(row, 6, QTableWidgetItem(acq_str))

            # Actions
            btn_cell = QWidget()
            btn_cell_layout = QHBoxLayout(btn_cell)
            btn_cell_layout.setContentsMargins(4, 2, 4, 2)
            btn_cell_layout.setSpacing(4)

            verify_btn = QPushButton("🛡️ Verify")
            verify_btn.clicked.connect(lambda _, eid=ev["id"]: self._verify_integrity_quick(eid))
            btn_cell_layout.addWidget(verify_btn)

            details_btn = QPushButton("Details")
            details_btn.clicked.connect(lambda _, eid=ev["id"]: self._show_evidence_details(eid))
            btn_cell_layout.addWidget(details_btn)

            self.table.setCellWidget(row, 7, btn_cell)

    def _on_row_double_clicked(self, index):
        row = index.row()
        evidence_id = self.table.item(row, 0).data(Qt.UserRole)
        self._show_evidence_details(evidence_id)

    def _show_evidence_details(self, evidence_id: int):
        ev = self.controller.evidence_manager.get_evidence(evidence_id)
        if ev:
            dialog = EvidenceDetailDialog(self.controller, ev, parent=self)
            dialog.exec()

    def _verify_integrity_quick(self, evidence_id: int):
        try:
            res = self.controller.evidence_manager.verify_integrity(evidence_id)
            if res["verified"]:
                QMessageBox.information(
                    self,
                    "Integrity Verified",
                    f"✓ Evidence '{res['evidence_number']}' matches recorded SHA-256 hash!\n\n"
                    f"Hash: {res['expected_sha256']}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Integrity Violation",
                    f"✗ WARNING: Evidence '{res['evidence_number']}' FAILED integrity verification!\n\n"
                    f"Reason: {res['message']}\n"
                    f"Expected: {res['expected_sha256']}\n"
                    f"Actual:   {res['actual_sha256']}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Verification Error", str(e))

    def open_register_evidence_dialog(self, case_id: Optional[int] = None):
        """Open modal to register evidence."""
        dialog = RegisterEvidenceDialog(self.controller, preselected_case_id=case_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
            QMessageBox.information(
                self,
                "Evidence Registered",
                f"Evidence '{dialog.registered_evidence['evidence_number']}' registered successfully with SHA-256."
            )
