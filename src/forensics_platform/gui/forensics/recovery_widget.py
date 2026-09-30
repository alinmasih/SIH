"""
Forensic Recovery & Filesystem Analysis GUI Widget.

Provides interactive partition inspection, directory browsing, deleted file
filtering, and cryptographic file recovery into active investigation cases.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QGroupBox, QFileDialog, QMessageBox,
    QProgressBar, QFrame, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme


def format_bytes(size: Optional[int]) -> str:
    """Format byte size into readable unit string."""
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


class ScanFilesWorker(QThread):
    """Background worker for listing directory entries / deleted files."""

    finished_success = Signal(list)
    finished_error = Signal(str)

    def __init__(self, fs_analyzer, image_path: str, offset_sectors: int, deleted_only: bool):
        super().__init__()
        self.fs_analyzer = fs_analyzer
        self.image_path = image_path
        self.offset = offset_sectors
        self.deleted_only = deleted_only

    def run(self):
        try:
            files = self.fs_analyzer.list_files(
                self.image_path,
                offset_sectors=self.offset,
                deleted_only=self.deleted_only,
                recursive=True
            )
            self.finished_success.emit(files)
        except Exception as e:
            self.finished_error.emit(str(e))


class RecoverFileWorker(QThread):
    """Background worker for file extraction."""

    finished_success = Signal(dict)
    finished_error = Signal(str)

    def __init__(self, deleted_analyzer, image_path: str, offset_sectors: int, inode: str, filename: str, output_dir: str, case_id: Optional[int]):
        super().__init__()
        self.deleted_analyzer = deleted_analyzer
        self.image_path = image_path
        self.offset = offset_sectors
        self.inode = inode
        self.filename = filename
        self.output_dir = output_dir
        self.case_id = case_id

    def run(self):
        try:
            rec = self.deleted_analyzer.recover_file(
                image_path=self.image_path,
                offset_sectors=self.offset,
                inode=self.inode,
                filename=self.filename,
                output_dir=self.output_dir,
                case_id=self.case_id
            )
            if rec:
                self.finished_success.emit(rec)
            else:
                self.finished_error.emit("Failed to extract file bitstream from image.")
        except Exception as e:
            self.finished_error.emit(str(e))


class RecoveryWidget(QWidget):
    """Main view for Forensic Partition Analysis and Deleted File Recovery."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_image_path: Optional[str] = None
        self.current_case_id: Optional[int] = None
        self.partitions_cache: List[Dict[str, Any]] = []
        self.files_cache: List[Dict[str, Any]] = []
        self.recovered_cache: List[Dict[str, Any]] = []
        self.selected_partition_offset: int = 0

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
        title = QLabel("🔍 Forensic Analysis & Deleted File Recovery")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {theme.text_primary};")
        subtitle = QLabel("Analyze disk partitions, parse filesystem structures, and extract deleted files with The Sleuth Kit.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)
        main_layout.addLayout(top_bar)

        # Image / Evidence Selector Bar
        src_box = QFrame()
        src_box.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        src_layout = QHBoxLayout(src_box)
        src_layout.setContentsMargins(10, 4, 10, 4)

        src_layout.addWidget(QLabel("Target Evidence:"))
        self.evidence_combo = QComboBox()
        self.evidence_combo.currentIndexChanged.connect(self._on_evidence_selected)
        src_layout.addWidget(self.evidence_combo, stretch=2)

        browse_btn = QPushButton("Browse Image...")
        browse_btn.clicked.connect(self._browse_image)
        src_layout.addWidget(browse_btn)

        self.analyze_btn = QPushButton("⚡ Analyze Partitions")
        self.analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: {theme.accent_text};
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.analyze_btn.clicked.connect(self._analyze_current_image)
        src_layout.addWidget(self.analyze_btn)

        main_layout.addWidget(src_box)

        # Main splitter (Top: Partitions & Files, Bottom: Recovered Files Drawer)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # Top area: Horizontal splitter (Left: Partitions, Right: Files/Deleted)
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)

        # Partitions Table
        part_box = QGroupBox("Detected Partitions")
        part_layout = QVBoxLayout(part_box)
        self.part_table = QTableWidget()
        self.part_table.setColumnCount(4)
        self.part_table.setHorizontalHeaderLabels(["Slot", "Start Sector", "Size", "Type / Description"])
        self.part_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.part_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.part_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.part_table.setSelectionMode(QTableWidget.SingleSelection)
        self.part_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.part_table.itemSelectionChanged.connect(self._on_partition_selected)
        part_layout.addWidget(self.part_table)
        top_splitter.addWidget(part_box)

        # Filesystem Explorer & Recovery
        files_box = QGroupBox("Filesystem Browser & Deleted Items")
        files_layout = QVBoxLayout(files_box)

        # Filters and recovery action bar
        files_bar = QHBoxLayout()
        files_bar.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Files", "Deleted Files Only", "Allocated Files Only"])
        self.filter_combo.currentIndexChanged.connect(self._apply_file_filter)
        files_bar.addWidget(self.filter_combo)

        self.file_search = QLineEdit()
        self.file_search.setPlaceholderText("Search filename...")
        self.file_search.textChanged.connect(self._apply_file_filter)
        files_bar.addWidget(self.file_search, stretch=1)

        self.scan_files_btn = QPushButton("🔄 Scan Files")
        self.scan_files_btn.clicked.connect(self._scan_partition_files)
        files_bar.addWidget(self.scan_files_btn)

        self.recover_sel_btn = QPushButton("💾 Recover Selected")
        self.recover_sel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.status_success};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
        """)
        self.recover_sel_btn.clicked.connect(self._recover_selected_file)
        self.recover_sel_btn.setEnabled(False)
        files_bar.addWidget(self.recover_sel_btn)

        files_layout.addLayout(files_bar)

        # Status & Guidance Banner (useful when unformatted or raw space detected)
        self.status_banner = QFrame()
        self.status_banner.setVisible(False)
        sb_layout = QHBoxLayout(self.status_banner)
        sb_layout.setContentsMargins(10, 8, 10, 8)
        self.status_msg_label = QLabel()
        self.status_msg_label.setWordWrap(True)
        sb_layout.addWidget(self.status_msg_label, stretch=1)

        self.carve_hint_btn = QPushButton("🧩 Launch File Carving")
        self.carve_hint_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: {theme.accent_text};
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.carve_hint_btn.clicked.connect(self._jump_to_carving)
        self.carve_hint_btn.setVisible(False)
        sb_layout.addWidget(self.carve_hint_btn)
        files_layout.addWidget(self.status_banner)

        # Files Table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["Status", "Type", "Inode", "Name", "Action"])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.itemSelectionChanged.connect(self._on_file_selected)
        files_layout.addWidget(self.files_table)

        top_splitter.addWidget(files_box)
        top_splitter.setSizes([380, 700])
        splitter.addWidget(top_splitter)

        # Bottom area: Recovered Files Drawer
        rec_box = QGroupBox("Recovered Files (Session Artifacts)")
        rec_layout = QVBoxLayout(rec_box)
        self.rec_table = QTableWidget()
        self.rec_table.setColumnCount(5)
        self.rec_table.setHorizontalHeaderLabels(["ID", "Filename", "Size", "SHA-256 Hash", "Actions"])
        self.rec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rec_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rec_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.rec_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.rec_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rec_table.setEditTriggers(QTableWidget.NoEditTriggers)
        rec_layout.addWidget(self.rec_table)

        splitter.addWidget(rec_box)
        splitter.setSizes([500, 200])

        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        """Populate evidence dropdown with registered items."""
        self.evidence_combo.blockSignals(True)
        self.evidence_combo.clear()
        self.evidence_combo.addItem("-- Select Registered Evidence --", None)

        evidence_items = self.controller.evidence_manager.list_evidence()
        for ev in evidence_items:
            path = ev.get("image_path") or ev.get("source_path")
            display_name = f"{ev['case_number']} / {ev['evidence_number']} - {ev.get('device_model') or 'Image'} ({format_bytes(ev.get('capacity'))})"
            self.evidence_combo.addItem(display_name, (ev["id"], ev["case_id"], path))

        self.evidence_combo.blockSignals(False)
        self._load_recovered_files_from_db()

    def _load_recovered_files_from_db(self):
        """Load previously recovered files from database into session drawer."""
        try:
            with self.controller.db_manager.session() as session:
                from forensics_platform.database.models import RecoveredFile, Operation
                query = session.query(RecoveredFile)
                if self.current_case_id:
                    query = query.join(Operation).filter(Operation.case_id == self.current_case_id)
                records = query.order_by(RecoveredFile.id.desc()).limit(100).all()
                self.recovered_cache = [
                    {
                        "id": r.id,
                        "filename": r.filename,
                        "size": r.size,
                        "sha256": r.sha256 or "",
                        "path": r.path,
                    }
                    for r in records
                ]
                self._update_recovered_table()
        except Exception:
            pass

    def _on_evidence_selected(self):
        data = self.evidence_combo.currentData()
        if data:
            _, case_id, path = data
            self.current_case_id = case_id
            self.current_image_path = path
            self._load_recovered_files_from_db()
            if path and os.path.exists(path):
                self._analyze_current_image()
            elif path:
                QMessageBox.warning(self, "File Not Found", f"Evidence path does not exist on disk: {path}")

    def _browse_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Disk Image",
            "",
            "All Disk Images (*.dd *.raw *.img *.001 *.iso *.bin);;All Files (*)"
        )
        if filename:
            self.current_image_path = filename
            self.current_case_id = None
            self._analyze_current_image()

    def _analyze_current_image(self):
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "Select Image", "Please select a valid disk image first.")
            return

        try:
            self.partitions_cache = self.controller.filesystem_analyzer.analyze_partitions(self.current_image_path)
            self.part_table.setRowCount(len(self.partitions_cache))

            for row, p in enumerate(self.partitions_cache):
                self.part_table.setItem(row, 0, QTableWidgetItem(p["slot"]))
                self.part_table.setItem(row, 1, QTableWidgetItem(str(p["start_sector"])))
                size_str = format_bytes(p.get("size_bytes"))
                self.part_table.setItem(row, 2, QTableWidgetItem(size_str))
                self.part_table.setItem(row, 3, QTableWidgetItem(p.get("description", "")))

            if self.partitions_cache:
                self.part_table.selectRow(0)
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze partitions: {e}")

    def _on_partition_selected(self):
        rows = self.part_table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self.partitions_cache):
            p = self.partitions_cache[row]
            self.selected_partition_offset = p["start_sector"]
            self._scan_partition_files()

    def _scan_partition_files(self):
        if not self.current_image_path:
            return

        self.scan_files_btn.setEnabled(False)
        self.status_banner.setVisible(False)
        deleted_only = (self.filter_combo.currentText() == "Deleted Files Only")
        self.worker = ScanFilesWorker(
            self.controller.filesystem_analyzer,
            self.current_image_path,
            self.selected_partition_offset,
            deleted_only
        )
        self.worker.finished_success.connect(self._on_files_scanned)
        self.worker.finished_error.connect(self._on_scan_error)
        self.worker.start()

    def _on_files_scanned(self, files: list):
        self.scan_files_btn.setEnabled(True)
        self.files_cache = files
        self._apply_file_filter()
        theme = get_current_theme()

        if not files:
            self.status_banner.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.bg_surface};
                    border: 1px solid {theme.border};
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            self.status_msg_label.setStyleSheet(f"color: {theme.text_secondary};")
            self.status_msg_label.setText(
                "ℹ️ No files discovered in this partition directory structure. If this media has deleted partitions or unallocated raw data, use File Carving."
            )
            self.status_banner.setVisible(True)
            self.carve_hint_btn.setVisible(True)
        else:
            del_count = sum(1 for f in files if f.get("is_deleted"))
            self.status_banner.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.bg_surface};
                    border: 1px solid {theme.border};
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """)
            self.status_msg_label.setStyleSheet(f"color: {theme.status_success}; font-weight: 500;")
            self.status_msg_label.setText(
                f"✓ Scan completed: Discovered {len(files)} items ({del_count} deleted) in partition."
            )
            self.status_banner.setVisible(True)
            self.carve_hint_btn.setVisible(False)

    def _on_scan_error(self, err: str):
        self.scan_files_btn.setEnabled(True)
        self.files_cache = []
        self._apply_file_filter()
        theme = get_current_theme()

        self.status_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.status_danger};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        self.status_msg_label.setStyleSheet(f"color: {theme.status_danger};")
        self.status_msg_label.setText(
            f"⚠️ Filesystem Scan Notice: {err}\n"
            "The Sleuth Kit could not identify a valid filesystem at this sector offset.\n"
            "You can carve files directly from this raw media using signature-based File Carving."
        )
        self.status_banner.setVisible(True)
        self.carve_hint_btn.setVisible(True)

    def _jump_to_carving(self):
        w = self.window()
        if hasattr(w, "_navigate_to"):
            w._navigate_to("carving")
            if hasattr(w, "carving_widget") and self.current_image_path:
                w.carving_widget.evidence_combo.insertItem(
                    0,
                    f"Target: {Path(self.current_image_path).name}",
                    self.current_image_path
                )
                w.carving_widget.evidence_combo.setCurrentIndex(0)

    def _apply_file_filter(self):
        theme = get_current_theme()
        filter_mode = self.filter_combo.currentText()
        search = self.file_search.text().strip().lower()

        filtered = []
        for f in self.files_cache:
            if filter_mode == "Deleted Files Only" and not f.get("is_deleted"):
                continue
            if filter_mode == "Allocated Files Only" and f.get("is_deleted"):
                continue
            if search and search not in f["name"].lower():
                continue
            filtered.append(f)

        self.files_table.setRowCount(len(filtered))
        for row, f in enumerate(filtered):
            # Status badge
            is_del = f.get("is_deleted")
            status_item = QTableWidgetItem("DELETED" if is_del else "Allocated")
            if is_del:
                status_item.setForeground(QColor(theme.status_danger))
            else:
                status_item.setForeground(QColor(theme.status_success))
            self.files_table.setItem(row, 0, status_item)

            # Type
            type_item = QTableWidgetItem("📁 Dir" if f.get("is_directory") else "📄 File")
            self.files_table.setItem(row, 1, type_item)

            # Inode
            inode_item = QTableWidgetItem(str(f.get("inode", "")))
            inode_item.setData(Qt.UserRole, f)
            self.files_table.setItem(row, 2, inode_item)

            # Name
            self.files_table.setItem(row, 3, QTableWidgetItem(f["name"]))

            # Action
            rec_btn = QPushButton("💾 Recover")
            rec_btn.setEnabled(not f.get("is_directory"))
            rec_btn.clicked.connect(lambda _, item=f: self._recover_file_direct(item))
            self.files_table.setCellWidget(row, 4, rec_btn)

    def _on_file_selected(self):
        rows = self.files_table.selectedItems()
        self.recover_sel_btn.setEnabled(bool(rows))

    def _recover_selected_file(self):
        rows = self.files_table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        f = self.files_table.item(row, 2).data(Qt.UserRole)
        if f:
            self._recover_file_direct(f)

    def _recover_file_direct(self, file_entry: dict):
        # Choose destination directory
        case_info = None
        default_dir = str(self.controller.config.temp_dir)
        if self.current_case_id:
            case_info = self.controller.case_manager.get_case(self.current_case_id)
            if case_info:
                default_dir = str(self.controller.config.case_dir / case_info["case_number"] / "carved")

        dest_dir = QFileDialog.getExistingDirectory(
            self,
            f"Select Output Directory to Save '{file_entry['name']}'",
            default_dir
        )
        if not dest_dir:
            return

        self.rec_worker = RecoverFileWorker(
            deleted_analyzer=self.controller.deleted_file_analyzer,
            image_path=self.current_image_path,
            offset_sectors=self.selected_partition_offset,
            inode=file_entry["inode"],
            filename=file_entry["name"],
            output_dir=dest_dir,
            case_id=self.current_case_id
        )
        self.rec_worker.finished_success.connect(self._on_file_recovered)
        self.rec_worker.finished_error.connect(lambda err: QMessageBox.critical(self, "Recovery Error", err))
        self.rec_worker.start()

    def _on_file_recovered(self, rec: dict):
        self.recovered_cache.insert(0, rec)
        self._update_recovered_table()
        QMessageBox.information(
            self,
            "Recovery Successful",
            f"File '{rec['filename']}' recovered successfully!\n\n"
            f"Saved to: {rec['path']}\n"
            f"Size: {format_bytes(rec['size'])}\n"
            f"SHA-256: {rec['sha256']}"
        )

    def _update_recovered_table(self):
        self.rec_table.setRowCount(len(self.recovered_cache))
        for row, r in enumerate(self.recovered_cache):
            self.rec_table.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            self.rec_table.setItem(row, 1, QTableWidgetItem(r["filename"]))
            self.rec_table.setItem(row, 2, QTableWidgetItem(format_bytes(r["size"])))

            sha = r["sha256"]
            short_sha = f"{sha[:8]}...{sha[-8:]}" if len(sha) >= 16 else sha
            item_sha = QTableWidgetItem(short_sha)
            item_sha.setToolTip(f"Full SHA-256: {sha}")
            self.rec_table.setItem(row, 3, item_sha)

            open_btn = QPushButton("Open Folder")
            open_btn.clicked.connect(lambda _, path=r["path"]: self._open_folder(path))
            self.rec_table.setCellWidget(row, 4, open_btn)

    def _open_folder(self, file_path: str):
        folder = os.path.dirname(file_path)
        if os.path.exists(folder):
            try:
                subprocess.Popen(["xdg-open", folder])
            except Exception:
                pass
