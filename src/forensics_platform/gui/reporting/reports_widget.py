"""
Reports GUI Widget - interactive management, generation, and inspection of forensic reports.

Provides:
- Generation of Forensic Recovery Reports, NIST SP 800-88 Sanitization Certificates, Case Summaries, and Audit Ledgers
- Multi-format export (PDF, HTML, JSON, CSV)
- Interactive In-App Document Preview (HTML / Raw)
- Cryptographic SHA-256 seal verification with one-click tamper detection
- External viewer integration and search filtering
"""

from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme
from forensics_platform.reporting.report_generator import (
    ReportFormat,
    ReportGenerator,
    ReportType,
)


def format_bytes(size: Optional[int]) -> str:
    """Format byte count into human-readable unit."""
    if size is None or size < 0:
        return "Unknown"
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    s = float(size)
    while s >= 1024.0 and i < len(units) - 1:
        s /= 1024.0
        i += 1
    return f"{s:.2f} {units[i]}"


class GenerateReportDialog(QDialog):
    """Modal dialog for configuring and generating new forensic and sanitization reports."""

    def __init__(self, controller: ApplicationController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.theme = get_current_theme()
        self.setWindowTitle("Generate Forensic Report or Certificate")
        self.setMinimumSize(560, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title_label = QLabel("Generate Forensic Report / Certificate")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.theme.text_primary};")
        layout.addWidget(title_label)

        sub_label = QLabel("Select report type, case target, and output format for court-admissible export.")
        sub_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")
        layout.addWidget(sub_label)

        # Form Container
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_surface};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)

        # 1. Report Type
        type_box = QHBoxLayout()
        type_lbl = QLabel("Report Type:")
        type_lbl.setFixedWidth(140)
        type_lbl.setStyleSheet("font-weight: 600;")
        self.type_combo = QComboBox()
        self.type_combo.addItem("Forensic Recovery Report", ReportType.FORENSIC_RECOVERY)
        self.type_combo.addItem("NIST SP 800-88 Sanitization Certificate", ReportType.SANITIZATION)
        self.type_combo.addItem("Case Summary Dossier", ReportType.CASE_SUMMARY)
        self.type_combo.addItem("Audit Trail & Chain of Custody", ReportType.AUDIT_TRAIL)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_box.addWidget(type_lbl)
        type_box.addWidget(self.type_combo)
        form_layout.addLayout(type_box)

        # 2. Case Selection
        self.case_box = QHBoxLayout()
        case_lbl = QLabel("Associated Case:")
        case_lbl.setFixedWidth(140)
        case_lbl.setStyleSheet("font-weight: 600;")
        self.case_combo = QComboBox()
        self._populate_cases()
        self.case_combo.currentIndexChanged.connect(self._on_case_changed)
        self.case_box.addWidget(case_lbl)
        self.case_box.addWidget(self.case_combo)
        form_layout.addLayout(self.case_box)

        # 3. Operation Selection (for Forensic & Sanitization)
        self.op_box = QHBoxLayout()
        self.op_lbl = QLabel("Target Operation:")
        self.op_lbl.setFixedWidth(140)
        self.op_lbl.setStyleSheet("font-weight: 600;")
        self.op_combo = QComboBox()
        self._populate_operations()
        self.op_box.addWidget(self.op_lbl)
        self.op_box.addWidget(self.op_combo)
        form_layout.addLayout(self.op_box)

        # 4. Output Format
        fmt_box = QHBoxLayout()
        fmt_lbl = QLabel("Export Format:")
        fmt_lbl.setFixedWidth(140)
        fmt_lbl.setStyleSheet("font-weight: 600;")
        self.format_combo = QComboBox()
        self.format_combo.addItem("PDF Document (.pdf)", ReportFormat.PDF)
        self.format_combo.addItem("Standalone HTML (.html)", ReportFormat.HTML)
        self.format_combo.addItem("Structured JSON (.json)", ReportFormat.JSON)
        self.format_combo.addItem("CSV Data Table (.csv)", ReportFormat.CSV)
        fmt_box.addWidget(fmt_lbl)
        fmt_box.addWidget(self.format_combo)
        form_layout.addLayout(fmt_box)

        # 5. Investigator / Technician Name
        inv_box = QHBoxLayout()
        inv_lbl = QLabel("Examiner Name:")
        inv_lbl.setFixedWidth(140)
        inv_lbl.setStyleSheet("font-weight: 600;")
        self.inv_input = QLineEdit()
        self.inv_input.setText(os.getenv("USER", "Forensic Analyst"))
        inv_box.addWidget(inv_lbl)
        inv_box.addWidget(self.inv_input)
        form_layout.addLayout(inv_box)

        # 6. Watermark (Optional)
        wm_box = QHBoxLayout()
        wm_lbl = QLabel("Watermark (PDF):")
        wm_lbl.setFixedWidth(140)
        wm_lbl.setStyleSheet("font-weight: 600;")
        self.wm_input = QLineEdit()
        self.wm_input.setPlaceholderText("e.g. CONFIDENTIAL, DRAFT, COURT EXHIBIT (Optional)")
        wm_box.addWidget(wm_lbl)
        wm_box.addWidget(self.wm_input)
        form_layout.addLayout(wm_box)

        layout.addWidget(form_frame)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)

        self.generate_btn = QPushButton("✨ Generate & Seal Report")
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent};
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #1d4ed8;
            }}
        """)
        self.generate_btn.clicked.connect(self._generate_report)
        btn_box.addWidget(self.generate_btn)

        layout.addLayout(btn_box)

        # Trigger initial visibility adjustment
        self._on_type_changed()

    def _populate_cases(self):
        """Populate case selector from database."""
        self.case_combo.clear()
        cases = self.controller.case_manager.list_cases()
        if not cases:
            self.case_combo.addItem("No cases available (Create a Case first)", None)
            return

        for c in cases:
            self.case_combo.addItem(f"{c['case_number']} - {c['title']}", c["id"])

    def _populate_operations(self):
        """Populate operations based on selected case and report type."""
        self.op_combo.clear()
        selected_type = self.type_combo.currentData()
        case_id = self.case_combo.currentData()

        session = self.controller.db_manager.get_session()
        try:
            from forensics_platform.database.models import Operation, SanitizationOperation

            if selected_type == ReportType.SANITIZATION:
                # Query sanitization operations
                sanit_ops = (
                    session.query(SanitizationOperation)
                    .join(Operation, SanitizationOperation.operation_id == Operation.id)
                    .order_by(Operation.id.desc())
                    .all()
                )
                if not sanit_ops:
                    self.op_combo.addItem("No sanitization operations available", None)
                    return
                for s in sanit_ops:
                    self.op_combo.addItem(
                        f"Op #{s.operation_id} ({s.device} - {s.sanitization_method} - {s.verification_result.upper()})",
                        s.operation_id,
                    )
            else:
                # General or forensic operations
                if not case_id:
                    self.op_combo.addItem("Select a case first", None)
                    return
                ops = (
                    session.query(Operation)
                    .filter(Operation.case_id == case_id)
                    .order_by(Operation.id.desc())
                    .all()
                )
                if not ops:
                    self.op_combo.addItem("All Case Operations / Default", None)
                    return

                self.op_combo.addItem("Latest / All Operations in Case", None)
                for op in ops:
                    self.op_combo.addItem(
                        f"Op #{op.id} ({op.operation_type} - {op.status})",
                        op.id,
                    )
        finally:
            session.close()

    def _on_type_changed(self):
        """Toggle field visibility based on report type."""
        selected_type = self.type_combo.currentData()

        if selected_type == ReportType.AUDIT_TRAIL:
            self.case_box.setEnabled(True)
            self.op_combo.setEnabled(False)
            self.op_lbl.setText("Operation:")
        elif selected_type == ReportType.SANITIZATION:
            self.op_lbl.setText("Sanitization Op:")
            self.op_combo.setEnabled(True)
            self._populate_operations()
        elif selected_type == ReportType.CASE_SUMMARY:
            self.op_combo.setEnabled(False)
            self.op_lbl.setText("Operation (N/A):")
        else:
            self.op_lbl.setText("Target Operation:")
            self.op_combo.setEnabled(True)
            self._populate_operations()

    def _on_case_changed(self):
        """Update operations when case changes."""
        if self.type_combo.currentData() != ReportType.SANITIZATION:
            self._populate_operations()

    def _generate_report(self):
        """Execute report generation."""
        report_type = self.type_combo.currentData()
        case_id = self.case_combo.currentData()
        op_id = self.op_combo.currentData()
        fmt = self.format_combo.currentData()
        inv_name = self.inv_input.text().strip() or "Forensic Examiner"
        watermark = self.wm_input.text().strip() or None

        if report_type in (ReportType.FORENSIC_RECOVERY, ReportType.CASE_SUMMARY) and not case_id:
            QMessageBox.warning(self, "Missing Case", "Please select a valid case to generate this report.")
            return

        if report_type == ReportType.SANITIZATION and not op_id:
            QMessageBox.warning(
                self, "Missing Operation", "Please perform or select a Sanitization Operation first."
            )
            return

        try:
            generator: ReportGenerator = self.controller.report_generator
            report = generator.generate_report(
                report_type=report_type,
                case_id=case_id,
                operation_id=op_id,
                format=fmt,
                watermark=watermark,
                generated_by=inv_name,
            )
            QMessageBox.information(
                self,
                "Report Generated",
                f"Report #{report.id} ({report.report_type}) generated successfully!\n\n"
                f"Format: {report.report_format.upper()}\n"
                f"SHA-256 Seal: {report.report_hash[:20]}...\n"
                f"Saved to: {report.file_path}",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"Failed to generate report:\n{str(e)}")


class ReportsWidget(QWidget):
    """
    Main interactive Reports GUI component.
    """

    def __init__(self, controller: ApplicationController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.theme = get_current_theme()
        self._selected_report_id: Optional[int] = None
        self._init_ui()
        self.refresh_reports()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("📄 Forensic Reports & Sanitization Certificates")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.theme.text_primary};")
        subtitle = QLabel("Generate court-admissible dossiers, NIST SP 800-88 certificates, and verify SHA-256 integrity.")
        subtitle.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Action Buttons
        self.gen_btn = QPushButton("✨ Generate Report")
        self.gen_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent};
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #1d4ed8;
            }}
        """)
        self.gen_btn.clicked.connect(self._open_generate_dialog)
        header_layout.addWidget(self.gen_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_reports)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # 2. Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_surface};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(12)

        # Case Filter
        filter_layout.addWidget(QLabel("Case:"))
        self.case_filter = QComboBox()
        self.case_filter.addItem("All Cases", None)
        self.case_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.case_filter)

        # Type Filter
        filter_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Report Types", None)
        self.type_filter.addItem("Forensic Recovery", ReportType.FORENSIC_RECOVERY)
        self.type_filter.addItem("Sanitization Certificate", ReportType.SANITIZATION)
        self.type_filter.addItem("Case Summary", ReportType.CASE_SUMMARY)
        self.type_filter.addItem("Audit Trail", ReportType.AUDIT_TRAIL)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.type_filter)

        # Format Filter
        filter_layout.addWidget(QLabel("Format:"))
        self.format_filter = QComboBox()
        self.format_filter.addItem("All Formats", None)
        self.format_filter.addItem("PDF", ReportFormat.PDF)
        self.format_filter.addItem("HTML", ReportFormat.HTML)
        self.format_filter.addItem("JSON", ReportFormat.JSON)
        self.format_filter.addItem("CSV", ReportFormat.CSV)
        self.format_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.format_filter)

        filter_layout.addStretch()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search reports...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input)

        main_layout.addWidget(filter_frame)

        # 3. Main Splitter: Table (Left) + Preview Panel (Right)
        splitter = QSplitter(Qt.Horizontal)

        # Left Container: Reports Table
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Type", "Case", "Format", "Size", "Generated At", "Integrity"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        table_layout.addWidget(self.table)

        # Table Action Toolbar
        action_bar = QHBoxLayout()
        self.verify_btn = QPushButton("🛡️ Verify Integrity")
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self._verify_selected_integrity)
        action_bar.addWidget(self.verify_btn)

        self.open_ext_btn = QPushButton("🌐 Open in System Viewer")
        self.open_ext_btn.setEnabled(False)
        self.open_ext_btn.clicked.connect(self._open_in_external_viewer)
        action_bar.addWidget(self.open_ext_btn)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("color: #dc2626;")
        self.delete_btn.clicked.connect(self._delete_selected_report)
        action_bar.addWidget(self.delete_btn)

        action_bar.addStretch()
        table_layout.addLayout(action_bar)
        splitter.addWidget(table_container)

        # Right Container: In-App Preview & Inspection Pane
        preview_container = QFrame()
        preview_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_surface};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(10)

        # Preview Header
        self.prev_title = QLabel("Report Preview & Cryptographic Verification")
        self.prev_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self.theme.text_primary};")
        preview_layout.addWidget(self.prev_title)

        # Verification Status Card
        self.seal_card = QFrame()
        self.seal_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_main};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        seal_layout = QVBoxLayout(self.seal_card)
        seal_layout.setSpacing(4)
        self.seal_status_lbl = QLabel("🛡️ SHA-256 Digest: Select a report")
        self.seal_status_lbl.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.seal_verdict_lbl = QLabel("Status: Awaiting selection")
        self.seal_verdict_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
        seal_layout.addWidget(self.seal_status_lbl)
        seal_layout.addWidget(self.seal_verdict_lbl)
        preview_layout.addWidget(self.seal_card)

        # In-App Browser Preview
        self.preview_browser = QTextBrowser()
        self.preview_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: white;
                color: #0f172a;
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        self.preview_browser.setHtml(
            "<div style='text-align: center; color: #64748b; margin-top: 150px; font-size: 14px;'>"
            "Select any report from the ledger on the left to preview its content and inspect the cryptographic audit seal."
            "</div>"
        )
        preview_layout.addWidget(self.preview_browser)

        splitter.addWidget(preview_container)
        splitter.setSizes([520, 580])
        main_layout.addWidget(splitter)

    # -------------------------------------------------------------------------
    # Data Population & Filtering
    # -------------------------------------------------------------------------

    def refresh_reports(self):
        """Refresh reports list and case filters."""
        # Refresh case filter options
        current_case_id = self.case_filter.currentData()
        self.case_filter.blockSignals(True)
        self.case_filter.clear()
        self.case_filter.addItem("All Cases", None)
        cases = self.controller.case_manager.list_cases()
        for c in cases:
            self.case_filter.addItem(f"{c['case_number']} - {c['title']}", c["id"])

        # Restore selection if still exists
        idx = self.case_filter.findData(current_case_id)
        if idx >= 0:
            self.case_filter.setCurrentIndex(idx)
        self.case_filter.blockSignals(False)

        self._load_reports_data()

    def _load_reports_data(self):
        """Fetch reports from database and apply active filters."""
        generator: ReportGenerator = self.controller.report_generator
        all_reports = generator.list_reports(limit=200)

        case_filter = self.case_filter.currentData()
        type_filter = self.type_filter.currentData()
        fmt_filter = self.format_filter.currentData()
        search_query = self.search_input.text().strip().lower()

        filtered = []
        for r in all_reports:
            if case_filter is not None and r["case_id"] != case_filter:
                continue
            if type_filter and r["report_type"] != type_filter:
                continue
            if fmt_filter and r["report_format"] != fmt_filter:
                continue
            if search_query:
                term = f"{r['id']} {r['report_type']} {r['file_path']} {r['generated_by']}".lower()
                if search_query not in term:
                    continue
            filtered.append(r)

        self._populate_table(filtered)

    def _populate_table(self, reports: List[Dict[str, Any]]):
        """Populate QTableWidget with filtered report items."""
        self.table.setRowCount(0)
        self.table.setRowCount(len(reports))

        for row, r in enumerate(reports):
            # ID
            id_item = QTableWidgetItem(f"#{r['id']}")
            id_item.setData(Qt.UserRole, r["id"])
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)

            # Type
            type_label = r["report_type"].replace("_", " ").title()
            type_item = QTableWidgetItem(type_label)
            self.table.setItem(row, 1, type_item)

            # Case
            case_item = QTableWidgetItem(f"Case #{r['case_id']}")
            case_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, case_item)

            # Format
            fmt_item = QTableWidgetItem(r["report_format"].upper())
            fmt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, fmt_item)

            # Size
            size_item = QTableWidgetItem(format_bytes(r["file_size"]))
            self.table.setItem(row, 4, size_item)

            # Date
            dt_str = r["generated_at"][:19].replace("T", " ") if r["generated_at"] else "N/A"
            date_item = QTableWidgetItem(dt_str)
            self.table.setItem(row, 5, date_item)

            # Integrity Quick Check
            exists = r.get("file_exists", False)
            if not exists:
                integ_item = QTableWidgetItem("⚠️ MISSING")
                integ_item.setForeground(QColor("#94a3b8"))
            else:
                integ_item = QTableWidgetItem("🛡️ SEALED")
                integ_item.setForeground(QColor("#16a34a"))
            integ_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, integ_item)

        # Reselect previous item if applicable
        if self._selected_report_id:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.data(Qt.UserRole) == self._selected_report_id:
                    self.table.selectRow(row)
                    break

    def _apply_filters(self):
        """Trigger reload upon filter change."""
        self._load_reports_data()

    # -------------------------------------------------------------------------
    # Preview & Actions
    # -------------------------------------------------------------------------

    def _on_table_selection_changed(self):
        """Handle selection of a report in the table."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            self._selected_report_id = None
            self.verify_btn.setEnabled(False)
            self.open_ext_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        row = selected_items[0].row()
        report_id = self.table.item(row, 0).data(Qt.UserRole)
        self._selected_report_id = report_id

        self.verify_btn.setEnabled(True)
        self.open_ext_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        self._load_report_preview(report_id)

    def _load_report_preview(self, report_id: int):
        """Display report details and render preview in the preview browser."""
        generator: ReportGenerator = self.controller.report_generator
        report = generator.get_report(report_id)
        if not report:
            return

        self.prev_title.setText(f"Report #{report['id']}: {report['report_type'].replace('_', ' ').title()}")
        self.seal_status_lbl.setText(f"SHA-256 Digest: {report['report_hash']}")

        file_path = Path(report["file_path"])
        if not file_path.exists():
            self.seal_verdict_lbl.setText("Status: ❌ File does not exist on disk")
            self.seal_verdict_lbl.setStyleSheet("color: #dc2626; font-weight: bold;")
            self.preview_browser.setHtml(
                f"<div style='color: #dc2626; padding: 20px; font-weight: bold;'>"
                f"File not found at: {file_path}"
                f"</div>"
            )
            return

        # Perform fast verification
        is_valid, current_hash, stored_hash = generator.verify_report_integrity(report_id)
        if is_valid:
            self.seal_verdict_lbl.setText("Status: ✓ CRYPTOGRAPHIC INTEGRITY VERIFIED (UNBROKEN SEAL)")
            self.seal_verdict_lbl.setStyleSheet("color: #16a34a; font-weight: bold;")
        else:
            self.seal_verdict_lbl.setText(f"Status: ⚠️ TAMPERING DETECTED (Current hash: {current_hash[:16]}...)")
            self.seal_verdict_lbl.setStyleSheet("color: #dc2626; font-weight: bold;")

        # Render preview based on format
        fmt = report["report_format"].lower()
        if fmt == ReportFormat.HTML:
            try:
                content = file_path.read_text(encoding="utf-8")
                self.preview_browser.setHtml(content)
            except Exception as e:
                self.preview_browser.setPlainText(f"Error loading HTML preview: {str(e)}")
        elif fmt in (ReportFormat.JSON, ReportFormat.CSV):
            try:
                content = file_path.read_text(encoding="utf-8")
                self.preview_browser.setPlainText(content)
            except Exception as e:
                self.preview_browser.setPlainText(f"Error loading text: {str(e)}")
        elif fmt == ReportFormat.PDF:
            self.preview_browser.setHtml(
                f"<div style='padding: 24px; text-align: center;'>"
                f"<h2 style='color: #1e3a8a;'>PDF Document Sealed</h2>"
                f"<p style='color: #475569;'>This is a compiled binary PDF document ({format_bytes(report['file_size'])}).</p>"
                f"<p>Click <strong>'Open in System Viewer'</strong> below to view in your PDF reader.</p>"
                f"<p class='mono' style='font-size: 11px; background: #f1f5f9; padding: 8px; border-radius: 4px; word-break: break-all;'>"
                f"Path: {file_path}<br>SHA-256: {report['report_hash']}"
                f"</p>"
                f"</div>"
            )

    def _verify_selected_integrity(self):
        """Explicitly re-check and display verification dialog for selected report."""
        if not self._selected_report_id:
            return

        generator: ReportGenerator = self.controller.report_generator
        is_valid, current_hash, stored_hash = generator.verify_report_integrity(self._selected_report_id)

        if is_valid:
            QMessageBox.information(
                self,
                "Integrity Verified",
                f"✓ Report #{self._selected_report_id} Integrity Verified!\n\n"
                f"File SHA-256 matches database hash:\n{stored_hash}\n\n"
                f"The report has not been modified or corrupted since generation.",
            )
        else:
            QMessageBox.critical(
                self,
                "Integrity Check Failed",
                f"⚠️ Tampering / Discrepancy Detected for Report #{self._selected_report_id}!\n\n"
                f"Stored Database Hash:\n{stored_hash}\n\n"
                f"Computed File Hash:\n{current_hash}\n\n"
                f"WARNING: The report file on disk does not match the immutable cryptographic record.",
            )
        self._load_report_preview(self._selected_report_id)

    def _open_in_external_viewer(self):
        """Open the selected report file in the system default application."""
        if not self._selected_report_id:
            return

        generator: ReportGenerator = self.controller.report_generator
        report = generator.get_report(self._selected_report_id)
        if not report:
            return

        path = Path(report["file_path"])
        if not path.exists():
            QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{path}")
            return

        # Attempt to open via Qt DesktopServices
        url = QUrl.fromLocalFile(str(path))
        success = QDesktopServices.openUrl(url)
        if not success:
            # Fallback to xdg-open on Linux
            try:
                subprocess.Popen(["xdg-open", str(path)])
            except Exception as e:
                QMessageBox.critical(self, "Open Error", f"Could not launch viewer:\n{str(e)}")

    def _delete_selected_report(self):
        """Delete selected report with confirmation."""
        if not self._selected_report_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete Report #{self._selected_report_id}?\n"
            "This will remove the file from disk and record an audit log event.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            generator: ReportGenerator = self.controller.report_generator
            generator.delete_report(self._selected_report_id)
            self._selected_report_id = None
            self.refresh_reports()
            self.preview_browser.setHtml(
                "<div style='text-align: center; color: #64748b; margin-top: 150px; font-size: 14px;'>"
                "Report deleted. Select another report from the ledger."
                "</div>"
            )

    def _open_generate_dialog(self):
        """Open the Generate Report modal dialog."""
        dialog = GenerateReportDialog(self.controller, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_reports()
