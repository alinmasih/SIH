"""
File Eraser GUI Widget - interactive multi-pass file and directory shredding.

Provides file and folder queue management, algorithm selection (Zero, DoD 3-Pass, Gutmann),
metadata scrubbing, non-blocking asynchronous erasure, and audit logging.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.file_eraser.shredder import ShredMethod
from forensics_platform.gui.themes import get_current_theme


def format_bytes(size: int) -> str:
    if size < 0:
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


class FileEraserWorker(QThread):
    """Background thread to perform batch file shredding without UI freezing."""

    progress_updated = Signal(dict)
    finished_success = Signal(dict)
    finished_error = Signal(str)

    def __init__(
        self,
        file_eraser,
        paths: List[Path],
        method: ShredMethod,
        case_id: Optional[int] = None,
    ):
        super().__init__()
        self.eraser = file_eraser
        self.paths = paths
        self.method = method
        self.case_id = case_id
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            summary = self.eraser.erase_batch(
                paths=self.paths,
                method=self.method,
                case_id=self.case_id,
                progress_callback=self._on_progress,
                cancel_token=lambda: self._cancelled,
            )
            self.finished_success.emit(summary)
        except Exception as e:
            self.finished_error.emit(str(e))

    def _on_progress(self, progress_dict: Dict[str, Any]):
        self.progress_updated.emit(progress_dict)


class FileEraserWidget(QWidget):
    """Secure File and Directory Eraser view."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.worker: Optional[FileEraserWorker] = None
        self.queue_paths: List[Path] = []

        self._init_ui()

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

        title_lbl = QLabel("🗑️ Secure File & Directory Eraser")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.text_primary};")
        header_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Permanently shred individual files and directory trees using multi-pass overwrites, "
            "filename obfuscation, timestamp zeroing, and sector truncation."
        )
        sub_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-size: 13px;")
        sub_lbl.setWordWrap(True)
        header_layout.addWidget(sub_lbl)

        main_layout.addWidget(header_card)

        # 2. Queue & Controls Card
        queue_card = QFrame()
        queue_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        q_layout = QVBoxLayout(queue_card)
        q_layout.setSpacing(12)

        # Toolbar
        tb_layout = QHBoxLayout()
        tb_layout.setSpacing(10)

        self.add_files_btn = QPushButton("📄 Add Files...")
        self.add_files_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_main};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 12px;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{ background-color: {theme.accent_subtle}; }}
        """)
        self.add_files_btn.clicked.connect(self._add_files)
        tb_layout.addWidget(self.add_files_btn)

        self.add_dir_btn = QPushButton("📁 Add Folder...")
        self.add_dir_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_main};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 12px;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{ background-color: {theme.accent_subtle}; }}
        """)
        self.add_dir_btn.clicked.connect(self._add_directory)
        tb_layout.addWidget(self.add_dir_btn)

        self.clear_btn = QPushButton("❌ Clear Queue")
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_main};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 12px;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{ background-color: {theme.accent_subtle}; }}
        """)
        self.clear_btn.clicked.connect(self._clear_queue)
        tb_layout.addWidget(self.clear_btn)

        tb_layout.addStretch()

        self.queue_info_lbl = QLabel("Queue: 0 items (0 B)")
        self.queue_info_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-weight: 600;")
        tb_layout.addWidget(self.queue_info_lbl)

        q_layout.addLayout(tb_layout)

        # Queue Table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Path", "Type", "Size", "Status"])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setStyleSheet(f"""
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
        q_layout.addWidget(self.queue_table)

        main_layout.addWidget(queue_card)

        # 3. Shred Settings & Actions Card
        act_card = QFrame()
        act_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        act_layout = QVBoxLayout(act_card)
        act_layout.setSpacing(14)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(16)

        m_lbl = QLabel("Shredding Method:")
        m_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        opt_row.addWidget(m_lbl)

        self.method_combo = QComboBox()
        self.method_combo.setMinimumWidth(260)
        self.method_combo.addItem("Single-Pass Zero Overwrite (Fast)", ShredMethod.ZERO)
        self.method_combo.addItem("DoD 5220.22-M - 3 Passes (0x00, 0xFF, Random)", ShredMethod.DOD_3PASS)
        self.method_combo.addItem("Gutmann 7-Pass Patterned Overwrite", ShredMethod.GUTMANN_7)
        self.method_combo.addItem("Cryptographically Secure Random (1 Pass)", ShredMethod.RANDOM)
        opt_row.addWidget(self.method_combo)

        opt_row.addStretch()

        self.shred_btn = QPushButton("🔥 Securely Shred All Queued Items")
        self.shred_btn.setEnabled(False)
        self.shred_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:disabled { background-color: #cbd5e1; color: #64748b; }
        """)
        self.shred_btn.clicked.connect(self._confirm_and_shred)
        opt_row.addWidget(self.shred_btn)

        self.stop_btn = QPushButton("⏹ Cancel")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #64748b;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover { background-color: #475569; }
            QPushButton:disabled { background-color: #cbd5e1; }
        """)
        self.stop_btn.clicked.connect(self._cancel_shred)
        opt_row.addWidget(self.stop_btn)

        act_layout.addLayout(opt_row)

        # Progress elements
        self.status_lbl = QLabel("Ready to shred queued files.")
        self.status_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        act_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                height: 12px;
                border-radius: 6px;
                background-color: #e2e8f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #ef4444;
                border-radius: 6px;
            }
        """)
        act_layout.addWidget(self.progress_bar)

        main_layout.addWidget(act_card)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Shred",
            str(Path.home()),
            "All Files (*.*)",
        )
        for f in files:
            p = Path(f).resolve()
            if p not in self.queue_paths:
                self.queue_paths.append(p)
        self._refresh_queue_table()

    def _add_directory(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Shred Recursively",
            str(Path.home()),
        )
        if folder:
            p = Path(folder).resolve()
            if p not in self.queue_paths:
                self.queue_paths.append(p)
        self._refresh_queue_table()

    def _clear_queue(self):
        self.queue_paths.clear()
        self._refresh_queue_table()

    def _refresh_queue_table(self):
        self.queue_table.setRowCount(0)
        total_bytes = 0

        for p in self.queue_paths:
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)

            is_dir = p.is_dir()
            type_str = "Directory" if is_dir else "File"
            size = 0
            if p.exists():
                try:
                    if not is_dir:
                        size = p.stat().st_size
                    else:
                        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                except OSError:
                    pass
            total_bytes += size

            is_prot = self.controller.file_eraser.is_protected(p)
            status_str = "BLOCKED (System)" if is_prot else "Ready"
            status_color = QColor("#ef4444") if is_prot else QColor("#10b981")

            self.queue_table.setItem(row, 0, QTableWidgetItem(str(p)))
            self.queue_table.setItem(row, 1, QTableWidgetItem(type_str))
            self.queue_table.setItem(row, 2, QTableWidgetItem(format_bytes(size)))

            st_item = QTableWidgetItem(status_str)
            st_item.setForeground(status_color)
            self.queue_table.setItem(row, 3, st_item)

        valid_count = sum(1 for p in self.queue_paths if not self.controller.file_eraser.is_protected(p))
        self.queue_info_lbl.setText(f"Queue: {len(self.queue_paths)} items ({format_bytes(total_bytes)})")
        self.shred_btn.setEnabled(valid_count > 0)

    def _confirm_and_shred(self):
        valid_paths = [p for p in self.queue_paths if not self.controller.file_eraser.is_protected(p)]
        if not valid_paths:
            return

        reply = QMessageBox.warning(
            self,
            "Permanent Data Shredding Confirmation",
            f"Are you absolutely sure you want to permanently shred {len(valid_paths)} item(s)?\n\n"
            "This operation cannot be undone. All file contents and metadata will be permanently overwritten.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        method: ShredMethod = self.method_combo.currentData()

        self.progress_bar.setValue(0)
        self.shred_btn.setEnabled(False)
        self.add_files_btn.setEnabled(False)
        self.add_dir_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_lbl.setText("Starting secure shredder...")

        self.worker = FileEraserWorker(
            file_eraser=self.controller.file_eraser,
            paths=valid_paths,
            method=method,
        )
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.finished_success.connect(self._on_shred_finished)
        self.worker.finished_error.connect(self._on_shred_error)
        self.worker.start()

    def _cancel_shred(self):
        if self.worker and self.worker.isRunning():
            self.status_lbl.setText("Cancelling shredder...")
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def _on_progress_update(self, data: Dict[str, Any]):
        pct = int(data.get("percent", 0))
        self.progress_bar.setValue(pct)
        cur_file = data.get("current_file", "")
        cur = data.get("current", 0)
        tot = data.get("total", 0)
        self.status_lbl.setText(f"Shredding ({cur}/{tot}): {Path(cur_file).name}")

    def _on_shred_finished(self, summary: Dict[str, Any]):
        self.progress_bar.setValue(100)
        self.shred_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_dir_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        deleted = summary.get("deleted_count", 0)
        total_b = summary.get("total_bytes", 0)
        self.status_lbl.setText(f"✓ Successfully shredded {deleted} files ({format_bytes(total_b)}).")
        self.queue_paths.clear()
        self._refresh_queue_table()

        QMessageBox.information(
            self,
            "Shredding Complete",
            f"Successfully and permanently shredded {deleted} file(s).\n"
            f"Total bytes overwritten: {format_bytes(total_b)}\n"
            "All operations logged in cryptographic audit trail.",
        )

    def _on_shred_error(self, err_msg: str):
        self.status_lbl.setText(f"✗ Error: {err_msg}")
        self.shred_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_dir_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Shredding Error", f"An error occurred:\n{err_msg}")
