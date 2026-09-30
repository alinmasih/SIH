"""
Tamper-Evident Audit Trail GUI Viewer.

Visualizes the cryptographic hash chain of all system events and enables
real-time chain integrity verification to detect any database tampering.
"""

import json
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTextEdit, QFrame, QMessageBox,
    QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme


class AuditViewerWidget(QWidget):
    """View for inspecting tamper-evident audit logs and verifying hash chain integrity."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.events_cache: List[Dict[str, Any]] = []
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
        title = QLabel("📋 Tamper-Evident Audit Log")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {theme.text_primary};")
        subtitle = QLabel("Cryptographic SHA-256 hash chain providing non-repudiation for all forensic actions.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        self.verify_chain_btn = QPushButton("🛡️ Verify Chain Integrity")
        self.verify_chain_btn.setStyleSheet(f"""
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
        self.verify_chain_btn.clicked.connect(self.verify_integrity)
        top_bar.addWidget(self.verify_chain_btn)

        main_layout.addLayout(top_bar)

        # Verification Status Banner
        self.status_banner = QLabel()
        self.status_banner.setStyleSheet(f"""
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
        """)
        self.status_banner.setVisible(False)
        main_layout.addWidget(self.status_banner)

        # Filter toolbar
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
        self.search_input.setPlaceholderText("Filter events by type, user, payload...")
        self.search_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.search_input, stretch=2)

        filter_layout.addWidget(QLabel("Limit:"))
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["50", "100", "250", "500"])
        self.limit_combo.setCurrentText("100")
        self.limit_combo.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.limit_combo)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        main_layout.addWidget(filter_box)

        # Splitter: Table on top, Event Details JSON viewer on bottom
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Event ID", "Timestamp", "User", "Event Type", "Category", "Event Hash (SHA-256)", "Previous Hash"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Details Panel
        detail_box = QGroupBox("Selected Audit Event Payload")
        detail_layout = QVBoxLayout(detail_box)

        self.json_viewer = QTextEdit()
        self.json_viewer.setReadOnly(True)
        self.json_viewer.setPlaceholderText("Select an event row above to inspect the signed event payload.")
        detail_layout.addWidget(self.json_viewer)

        splitter.addWidget(detail_box)
        splitter.setSizes([420, 200])

        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        """Fetch audit trail events."""
        limit = int(self.limit_combo.currentText())
        self.events_cache = self.controller.audit_logger.get_audit_trail(limit=limit)
        self._apply_filter()

    def _apply_filter(self):
        search = self.search_input.text().strip().lower()
        filtered = []
        for ev in self.events_cache:
            if search:
                haystack = f"{ev['id']} {ev['user']} {ev['event_type']} {ev.get('event_category') or ''} {ev.get('event_data') or ''}".lower()
                if search not in haystack:
                    continue
            filtered.append(ev)

        self.table.setRowCount(len(filtered))
        for row, ev in enumerate(filtered):
            # Event ID
            item_id = QTableWidgetItem(str(ev["id"]))
            item_id.setData(Qt.UserRole, ev)
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            # Timestamp
            ts = ev.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)
            self.table.setItem(row, 1, QTableWidgetItem(ts_str))

            # User
            self.table.setItem(row, 2, QTableWidgetItem(ev.get("user", "")))

            # Event Type
            item_type = QTableWidgetItem(ev.get("event_type", ""))
            item_type.setFont(item_type.font())
            self.table.setItem(row, 3, item_type)

            # Category
            self.table.setItem(row, 4, QTableWidgetItem(ev.get("event_category") or "-"))

            # Event Hash
            ehash = ev.get("event_hash", "")
            short_ehash = f"{ehash[:8]}...{ehash[-8:]}" if len(ehash) >= 16 else ehash
            item_ehash = QTableWidgetItem(short_ehash)
            item_ehash.setToolTip(f"Full Hash: {ehash}")
            self.table.setItem(row, 5, item_ehash)

            # Previous Hash
            phash = ev.get("previous_hash") or "GENESIS"
            short_phash = f"{phash[:8]}...{phash[-8:]}" if len(phash) >= 16 else phash
            item_phash = QTableWidgetItem(short_phash)
            item_phash.setToolTip(f"Previous: {phash}")
            self.table.setItem(row, 6, item_phash)

    def _on_row_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.json_viewer.clear()
            return

        row = selected_rows[0].row()
        ev = self.table.item(row, 0).data(Qt.UserRole)
        if not ev:
            return

        try:
            data_raw = ev.get("event_data")
            if isinstance(data_raw, str):
                parsed = json.loads(data_raw)
            else:
                parsed = data_raw
            pretty = json.dumps(parsed, indent=2)
        except Exception:
            pretty = str(ev.get("event_data"))

        summary = (
            f"// Event #{ev['id']} - {ev['event_type']} by {ev['user']}\n"
            f"// Hash: {ev['event_hash']}\n"
            f"// Prev: {ev.get('previous_hash') or 'GENESIS'}\n\n"
            f"{pretty}"
        )
        self.json_viewer.setText(summary)

    def verify_integrity(self):
        """Run cryptographic hash chain verification."""
        theme = get_current_theme()
        result = self.controller.audit_logger.verify_integrity()
        self.status_banner.setVisible(True)

        if result["valid"]:
            self.status_banner.setText(
                f"✓ AUDIT HASH CHAIN INTACT: Verified {result['total_events']} events sequentially from genesis. Zero tampering detected."
            )
            self.status_banner.setStyleSheet(f"""
                background-color: {theme.accent_subtle};
                color: {theme.status_success};
                border: 1px solid {theme.status_success};
                padding: 12px 16px;
                border-radius: 8px;
                font-weight: bold;
            """)
        else:
            self.status_banner.setText(
                f"✗ AUDIT HASH CHAIN COMPROMISED: Verification failed at Event #{result.get('first_broken_event_id')}! {result.get('error_message')}"
            )
            self.status_banner.setStyleSheet(f"""
                background-color: #fee2e2;
                color: {theme.status_danger};
                border: 1px solid {theme.status_danger};
                padding: 12px 16px;
                border-radius: 8px;
                font-weight: bold;
            """)
