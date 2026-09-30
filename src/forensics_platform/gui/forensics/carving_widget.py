"""
Carving GUI Widget - interactive file carving, signature configuration, and preview.

Provides non-blocking multi-signature carving, live progress tracking, confidence visualization,
and artifact inspection/preview for digital forensics.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
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
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme


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


class CarvingWorker(QThread):
    """Background thread to perform non-blocking file carving."""

    progress_updated = Signal(dict)
    finished_success = Signal(list)
    finished_error = Signal(str)

    def __init__(
        self,
        carving_engine,
        image_path: str,
        target_types: List[str],
        min_confidence: int,
        output_dir: Path,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        sector_aligned: bool = True,
    ):
        super().__init__()
        self.carving_engine = carving_engine
        self.image_path = image_path
        self.target_types = target_types
        self.min_confidence = min_confidence
        self.output_dir = output_dir
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.sector_aligned = sector_aligned
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            results = self.carving_engine.carve_image(
                image_path=self.image_path,
                target_types=self.target_types,
                min_confidence=self.min_confidence,
                output_dir=self.output_dir,
                case_id=self.case_id,
                evidence_id=self.evidence_id,
                sector_aligned=self.sector_aligned,
                progress_callback=self._on_progress,
                cancel_token=lambda: self._cancelled,
            )
            self.finished_success.emit(results)
        except Exception as e:
            self.finished_error.emit(str(e))

    def _on_progress(self, progress_dict: Dict[str, Any]):
        self.progress_updated.emit(progress_dict)


class CarvedFilePreviewDialog(QDialog):
    """Modal dialog displaying visual preview, metadata, and hex inspection of a carved file."""

    def __init__(self, file_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.setWindowTitle(f"Preview Carved File - {file_info.get('filename', 'Unknown')}")
        self.setMinimumSize(700, 520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header Info Card
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #f1f5f9; border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)

        fn = self.file_info.get("filename", "")
        ftype = self.file_info.get("file_type", "").upper()
        size_str = format_bytes(self.file_info.get("size", 0))
        offset_hex = f"0x{self.file_info.get('offset', 0):08X}"
        conf = self.file_info.get("confidence_score", 0)
        conf_level = self.file_info.get("confidence_classification", "Unknown")
        sha256 = self.file_info.get("sha256", "N/A")

        title_lbl = QLabel(f"<b>{fn}</b> ({ftype})")
        title_lbl.setStyleSheet("font-size: 15px; color: #0f172a;")
        info_layout.addWidget(title_lbl)

        meta_text = (
            f"<b>Offset:</b> {offset_hex} &nbsp;|&nbsp; "
            f"<b>Size:</b> {size_str} &nbsp;|&nbsp; "
            f"<b>Confidence:</b> {conf}% ({conf_level})<br>"
            f"<b>SHA-256:</b> <span style='font-family: monospace; font-size: 11px;'>{sha256}</span>"
        )
        meta_lbl = QLabel(meta_text)
        meta_lbl.setTextFormat(Qt.RichText)
        info_layout.addWidget(meta_lbl)
        layout.addWidget(info_frame)

        # Body: Preview or Hex View
        file_path = Path(self.file_info.get("path", ""))
        ftype_lower = self.file_info.get("file_type", "").lower()

        if file_path.exists() and ftype_lower in ("jpeg", "jpg", "png", "gif"):
            preview_box = QGroupBox("Visual Preview")
            prev_layout = QVBoxLayout(preview_box)
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            img_lbl.setStyleSheet("background-color: #0f172a; border-radius: 4px; padding: 8px;")

            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(550, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl.setPixmap(scaled_pixmap)
            else:
                img_lbl.setText("Image preview unavailable or corrupt")
                img_lbl.setStyleSheet("color: #94a3b8;")

            prev_layout.addWidget(img_lbl)
            layout.addWidget(preview_box)

        # Hex / Header Inspector
        hex_box = QGroupBox("Header & Content Inspection (First 512 bytes)")
        hex_layout = QVBoxLayout(hex_box)
        hex_text = QTextEdit()
        hex_text.setReadOnly(True)
        hex_text.setFont(QFont("Monospace", 10))

        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    chunk = f.read(512)
                lines = []
                for i in range(0, len(chunk), 16):
                    sub = chunk[i : i + 16]
                    hex_part = " ".join(f"{b:02X}" for b in sub).ljust(48)
                    ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in sub)
                    lines.append(f"{i:04X}  {hex_part}  |{ascii_part}|")
                hex_text.setPlainText("\n".join(lines))
            except Exception as e:
                hex_text.setPlainText(f"Error reading file: {e}")

        hex_layout.addWidget(hex_text)
        layout.addWidget(hex_box)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 6px 16px; background-color: #2563eb; color: white; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class CarvingWidget(QWidget):
    """Interactive File Carving view."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.worker: Optional[CarvingWorker] = None
        self.carved_items: List[Dict[str, Any]] = []

        self._init_ui()
        self.refresh_sources()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        theme = get_current_theme()

        # 1. Page Header Card
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

        title_lbl = QLabel("🧩 File Carving Engine")
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.text_primary};")
        header_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Extract files directly from raw disk images and unallocated sectors using multi-pattern "
            "binary signatures, deep format validation, and mathematical confidence scoring."
        )
        sub_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-size: 13px;")
        sub_lbl.setWordWrap(True)
        header_layout.addWidget(sub_lbl)

        main_layout.addWidget(header_card)

        # 2. Configuration & Scope Card
        config_card = QFrame()
        config_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        config_layout = QVBoxLayout(config_card)
        config_layout.setSpacing(14)

        # Row 1: Target Image & Case Selection
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        # Target Evidence Selector
        src_lbl = QLabel("Target Evidence:")
        src_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        row1_layout.addWidget(src_lbl)

        self.evidence_combo = QComboBox()
        self.evidence_combo.setMinimumWidth(260)
        self.evidence_combo.setStyleSheet("padding: 6px;")
        row1_layout.addWidget(self.evidence_combo)

        browse_btn = QPushButton("📁 Browse Image...")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_main};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 12px;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{
                background-color: {theme.accent_subtle};
            }}
        """)
        browse_btn.clicked.connect(self._browse_custom_image)
        row1_layout.addWidget(browse_btn)

        row1_layout.addSpacing(16)

        # Case Selector
        case_lbl = QLabel("Target Case:")
        case_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        row1_layout.addWidget(case_lbl)

        self.case_combo = QComboBox()
        self.case_combo.setMinimumWidth(200)
        self.case_combo.setStyleSheet("padding: 6px;")
        row1_layout.addWidget(self.case_combo)

        row1_layout.addStretch()
        config_layout.addLayout(row1_layout)

        # Row 2: Target Signatures
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(16)

        sig_title = QLabel("Signatures:")
        sig_title.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        row2_layout.addWidget(sig_title)

        self.check_jpeg = QCheckBox("JPEG (.jpg)")
        self.check_jpeg.setChecked(True)
        row2_layout.addWidget(self.check_jpeg)

        self.check_png = QCheckBox("PNG (.png)")
        self.check_png.setChecked(True)
        row2_layout.addWidget(self.check_png)

        self.check_pdf = QCheckBox("PDF (.pdf)")
        self.check_pdf.setChecked(True)
        row2_layout.addWidget(self.check_pdf)

        self.check_zip = QCheckBox("ZIP Archive (.zip)")
        self.check_zip.setChecked(True)
        row2_layout.addWidget(self.check_zip)

        self.check_gif = QCheckBox("GIF (.gif)")
        self.check_gif.setChecked(True)
        row2_layout.addWidget(self.check_gif)

        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        sel_all_btn.clicked.connect(self._select_all_signatures)
        row2_layout.addWidget(sel_all_btn)

        row2_layout.addStretch()
        config_layout.addLayout(row2_layout)

        # Row 3: Confidence Slider & Options
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(16)

        self.conf_label = QLabel("Confidence Threshold: 50%")
        self.conf_label.setStyleSheet(f"font-weight: 600; color: {theme.text_primary}; min-width: 170px;")
        row3_layout.addWidget(self.conf_label)

        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(50)
        self.conf_slider.setMaximumWidth(200)
        self.conf_slider.valueChanged.connect(self._on_slider_changed)
        row3_layout.addWidget(self.conf_slider)

        self.sector_align_check = QCheckBox("Sector Aligned (512-byte fast search)")
        self.sector_align_check.setChecked(True)
        row3_layout.addWidget(self.sector_align_check)

        row3_layout.addStretch()

        # Action Buttons
        self.start_btn = QPushButton("⚡ Start File Carving")
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background-color: #1d4ed8;
            }}
            QPushButton:disabled {{
                background-color: #94a3b8;
            }}
        """)
        self.start_btn.clicked.connect(self.start_carving)
        row3_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_carving)
        row3_layout.addWidget(self.stop_btn)

        config_layout.addLayout(row3_layout)
        main_layout.addWidget(config_card)

        # 3. Live Progress & Status Card
        self.progress_card = QFrame()
        self.progress_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        prog_layout = QVBoxLayout(self.progress_card)
        prog_layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.status_lbl = QLabel("Ready to scan media.")
        self.status_lbl.setStyleSheet(f"font-weight: 600; color: {theme.text_primary};")
        status_row.addWidget(self.status_lbl)

        status_row.addStretch()
        self.stats_lbl = QLabel("Candidates: 0 | Carved: 0")
        self.stats_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-size: 12px;")
        status_row.addWidget(self.stats_lbl)
        prog_layout.addLayout(status_row)

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
                background-color: #2563eb;
                border-radius: 6px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.progress_card)

        # 4. Results Card
        results_card = QFrame()
        results_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        res_layout = QVBoxLayout(results_card)
        res_layout.setSpacing(12)

        res_header = QHBoxLayout()
        self.res_count_lbl = QLabel("Carved Artifacts (0)")
        self.res_count_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.text_primary};")
        res_header.addWidget(self.res_count_lbl)

        res_header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter carved files...")
        self.search_edit.setMaximumWidth(220)
        self.search_edit.setStyleSheet("padding: 4px 8px;")
        self.search_edit.textChanged.connect(self._filter_results)
        res_header.addWidget(self.search_edit)

        res_layout.addLayout(res_header)

        # Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Filename", "Type", "Size", "Offset", "Confidence", "SHA-256", "Actions"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setStyleSheet(f"""
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
        res_layout.addWidget(self.results_table)

        main_layout.addWidget(results_card)

    def _on_slider_changed(self, value: int):
        self.conf_label.setText(f"Confidence Threshold: {value}%")

    def _select_all_signatures(self):
        state = not self.check_jpeg.isChecked()
        self.check_jpeg.setChecked(state)
        self.check_png.setChecked(state)
        self.check_pdf.setChecked(state)
        self.check_zip.setChecked(state)
        self.check_gif.setChecked(state)

    def refresh_sources(self):
        """Populate evidence and case dropdowns."""
        self.evidence_combo.clear()
        self.case_combo.clear()

        # Add cases
        try:
            cases = self.controller.case_manager.list_cases()
            for c in cases:
                self.case_combo.addItem(f"{c['case_number']} - {c['title']}", c["id"])
        except Exception:
            pass

        # Add evidence items
        try:
            evidences = self.controller.evidence_manager.list_evidence()
            for ev in evidences:
                path = ev.get("image_path") or ev.get("source_path")
                if not path:
                    continue
                label = ev.get("device_model") or Path(path).name or "Image"
                st = ev.get("source_type", "disk_image").replace("_", " ").title()
                display = f"#{ev['evidence_number']} - {label} ({st})"
                self.evidence_combo.addItem(display, path)
        except Exception:
            pass

    def _browse_custom_image(self):
        fn, _ = QFileDialog.getOpenFileName(
            self,
            "Select Target Disk Image or File",
            str(Path.home()),
            "Raw Disk Images (*.dd *.raw *.img *.001 *.iso *.bin);;All Files (*.*)",
        )
        if fn:
            self.evidence_combo.insertItem(0, f"Custom: {Path(fn).name}", fn)
            self.evidence_combo.setCurrentIndex(0)

    def _get_target_types(self) -> List[str]:
        types = []
        if self.check_jpeg.isChecked():
            types.append("jpeg")
        if self.check_png.isChecked():
            types.append("png")
        if self.check_pdf.isChecked():
            types.append("pdf")
        if self.check_zip.isChecked():
            types.append("zip")
        if self.check_gif.isChecked():
            types.append("gif")
        return types

    def start_carving(self):
        """Initiate non-blocking carving workflow."""
        image_path = self.evidence_combo.currentData()
        if not image_path or not Path(image_path).exists():
            QMessageBox.warning(self, "Invalid Image", "Please select a valid target image or file.")
            return

        target_types = self._get_target_types()
        if not target_types:
            QMessageBox.warning(self, "No Signatures Selected", "Please select at least one signature format.")
            return

        case_id = self.case_combo.currentData()
        min_conf = self.conf_slider.value()
        sector_align = self.sector_align_check.isChecked()

        # Resolve output dir
        if case_id:
            try:
                case = self.controller.case_manager.get_case(case_id)
                case_dir = Path(self.controller.config.case_dir) / case["case_number"] / "carved"
            except Exception:
                case_dir = Path(image_path).parent / "carved"
        else:
            case_dir = Path(image_path).parent / "carved"

        case_dir.mkdir(parents=True, exist_ok=True)

        self.carved_items.clear()
        self.results_table.setRowCount(0)
        self.res_count_lbl.setText("Carved Artifacts (0)")
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Initializing scanner...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.worker = CarvingWorker(
            carving_engine=self.controller.carving_engine,
            image_path=str(image_path),
            target_types=target_types,
            min_confidence=min_conf,
            output_dir=case_dir,
            case_id=case_id,
            sector_aligned=sector_align,
        )
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.finished_success.connect(self._on_carving_finished)
        self.worker.finished_error.connect(self._on_carving_error)
        self.worker.start()

    def stop_carving(self):
        """Request cancellation of running worker."""
        if self.worker and self.worker.isRunning():
            self.status_lbl.setText("Cancelling carving run...")
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def _on_progress_update(self, data: Dict[str, Any]):
        percent = int(data.get("percent", 0))
        self.progress_bar.setValue(percent)

        scanned_str = format_bytes(data.get("bytes_scanned", 0))
        total_str = format_bytes(data.get("total_bytes", 0))
        cands = data.get("candidates_found", 0)
        carved = data.get("files_carved", 0)

        self.status_lbl.setText(f"Scanning media: {scanned_str} / {total_str} ({percent}%)")
        self.stats_lbl.setText(f"Candidates: {cands} | Carved: {carved}")

        # If a file was carved in this step, add it dynamically
        latest = data.get("latest_carved")
        if latest and latest not in self.carved_items:
            self.carved_items.append(latest)
            self._add_row_to_table(latest)
            self.res_count_lbl.setText(f"Carved Artifacts ({len(self.carved_items)})")

    def _on_carving_finished(self, results: List[Dict[str, Any]]):
        self.carved_items = results
        self._populate_results_table(results)
        self.progress_bar.setValue(100)
        self.status_lbl.setText(f"✓ Carving complete. Recovered {len(results)} validated artifacts.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_carving_error(self, err_msg: str):
        self.status_lbl.setText(f"✗ Carving error: {err_msg}")
        QMessageBox.critical(self, "Carving Failure", f"An error occurred during carving:\n{err_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _add_row_to_table(self, item: Dict[str, Any]):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        fn_item = QTableWidgetItem(item.get("filename", ""))
        type_item = QTableWidgetItem(item.get("file_type", "").upper())
        size_item = QTableWidgetItem(format_bytes(item.get("size", 0)))
        offset_item = QTableWidgetItem(f"0x{item.get('offset', 0):08X}")

        # Confidence pill
        conf = item.get("confidence_score", 0)
        conf_level = item.get("confidence_classification", "Unknown")
        conf_item = QTableWidgetItem(f"{conf}% ({conf_level})")

        if conf >= 80:
            conf_item.setBackground(QColor("#dcfce7"))
            conf_item.setForeground(QColor("#166534"))
        elif conf >= 50:
            conf_item.setBackground(QColor("#fef3c7"))
            conf_item.setForeground(QColor("#92400e"))
        else:
            conf_item.setBackground(QColor("#fee2e2"))
            conf_item.setForeground(QColor("#991b1b"))

        sha_short = item.get("sha256", "")[:16] + "..." if item.get("sha256") else "N/A"
        sha_item = QTableWidgetItem(sha_short)
        sha_item.setToolTip(item.get("sha256", ""))

        # Action Buttons
        actions_widget = QWidget()
        act_layout = QHBoxLayout(actions_widget)
        act_layout.setContentsMargins(4, 2, 4, 2)
        act_layout.setSpacing(6)

        prev_btn = QPushButton("👁️ Preview")
        prev_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        prev_btn.clicked.connect(lambda _, it=item: self._show_preview(it))
        act_layout.addWidget(prev_btn)

        open_btn = QPushButton("📂 Open")
        open_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        open_btn.clicked.connect(lambda _, it=item: self._open_file_folder(it))
        act_layout.addWidget(open_btn)

        self.results_table.setItem(row, 0, fn_item)
        self.results_table.setItem(row, 1, type_item)
        self.results_table.setItem(row, 2, size_item)
        self.results_table.setItem(row, 3, offset_item)
        self.results_table.setItem(row, 4, conf_item)
        self.results_table.setItem(row, 5, sha_item)
        self.results_table.setCellWidget(row, 6, actions_widget)

    def _populate_results_table(self, items: List[Dict[str, Any]]):
        self.results_table.setRowCount(0)
        for item in items:
            self._add_row_to_table(item)
        self.res_count_lbl.setText(f"Carved Artifacts ({len(items)})")

    def _filter_results(self, query: str):
        query = query.lower().strip()
        for row in range(self.results_table.rowCount()):
            fn_item = self.results_table.item(row, 0)
            type_item = self.results_table.item(row, 1)
            matches = (query in fn_item.text().lower()) or (query in type_item.text().lower())
            self.results_table.setRowHidden(row, not matches)

    def _show_preview(self, item: Dict[str, Any]):
        dialog = CarvedFilePreviewDialog(item, self)
        dialog.exec()

    def _open_file_folder(self, item: Dict[str, Any]):
        path = Path(item.get("path", ""))
        if path.exists():
            folder = path.parent
            try:
                subprocess.run(["xdg-open", str(folder)], check=False)
            except Exception as e:
                QMessageBox.information(self, "Folder Path", f"File located at:\n{path}")
