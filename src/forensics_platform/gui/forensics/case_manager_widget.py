"""
Case Management GUI Widget.

Provides full case lifecycle management: listing, searching, filtering,
creating new cases, editing details, and viewing associated evidence.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QTextEdit, QMessageBox, QFrame,
    QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.themes import get_current_theme, get_theme_manager


class NewCaseDialog(QDialog):
    """Modal dialog for creating a new forensic case."""

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.case_data: Optional[Dict[str, Any]] = None
        self.setWindowTitle("Create New Forensic Case")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        theme = get_current_theme()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Header
        header = QLabel("New Investigation Case")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.accent};")
        layout.addWidget(header)

        # Case Number
        layout.addWidget(QLabel("Case Number *"))
        self.case_number_input = QLineEdit()
        suggested_num = self.controller.case_manager.generate_next_case_number()
        self.case_number_input.setText(suggested_num)
        layout.addWidget(self.case_number_input)

        # Title
        layout.addWidget(QLabel("Case Title *"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Unauthorized Data Exfiltration Investigation")
        layout.addWidget(self.title_input)

        # Investigator
        layout.addWidget(QLabel("Primary Investigator *"))
        self.investigator_input = QLineEdit()
        current_user = self.controller.get_system_status().get("platform", {}).get("username", "Investigator")
        self.investigator_input.setText(current_user)
        layout.addWidget(self.investigator_input)

        # Description
        layout.addWidget(QLabel("Case Description / Background"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Summary of incident, relevant scope, or initial notes...")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet(f"color: {theme.status_danger}; font-weight: bold;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create Case")
        create_btn.setStyleSheet(f"""
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
        create_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _on_submit(self):
        case_num = self.case_number_input.text().strip()
        title = self.title_input.text().strip()
        investigator = self.investigator_input.text().strip()
        desc = self.description_input.toPlainText().strip() or None

        if not case_num:
            self._show_error("Case number is required.")
            return
        if len(title) < 3:
            self._show_error("Case title must be at least 3 characters.")
            return
        if not investigator:
            self._show_error("Investigator name is required.")
            return

        try:
            self.case_data = self.controller.case_manager.create_case(
                case_number=case_num,
                title=title,
                investigator=investigator,
                description=desc
            )
            self.accept()
        except Exception as e:
            self._show_error(str(e))

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.setVisible(True)


class EditCaseDialog(QDialog):
    """Modal dialog for editing case details."""

    def __init__(self, controller: ApplicationController, case_dict: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.controller = controller
        self.case_dict = case_dict
        self.updated_case: Optional[Dict[str, Any]] = None
        self.setWindowTitle(f"Edit Case: {case_dict['case_number']}")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        theme = get_current_theme()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header = QLabel(f"Edit Case: {self.case_dict['case_number']}")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.accent};")
        layout.addWidget(header)

        # Title
        layout.addWidget(QLabel("Case Title *"))
        self.title_input = QLineEdit()
        self.title_input.setText(self.case_dict["title"])
        layout.addWidget(self.title_input)

        # Investigator
        layout.addWidget(QLabel("Primary Investigator *"))
        self.investigator_input = QLineEdit()
        self.investigator_input.setText(self.case_dict["investigator"])
        layout.addWidget(self.investigator_input)

        # Status
        layout.addWidget(QLabel("Status"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "closed", "archived"])
        self.status_combo.setCurrentText(self.case_dict["status"])
        layout.addWidget(self.status_combo)

        # Description
        layout.addWidget(QLabel("Description"))
        self.description_input = QTextEdit()
        self.description_input.setText(self.case_dict.get("description") or "")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"""
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
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        title = self.title_input.text().strip()
        investigator = self.investigator_input.text().strip()
        status = self.status_combo.currentText()
        desc = self.description_input.toPlainText().strip() or None

        if len(title) < 3:
            QMessageBox.warning(self, "Invalid Title", "Title must be at least 3 characters.")
            return

        try:
            self.updated_case = self.controller.case_manager.update_case(
                case_id=self.case_dict["id"],
                title=title,
                investigator=investigator,
                description=desc,
                status=status
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Update Error", str(e))


class CaseManagerWidget(QWidget):
    """Main view for Case Management."""

    case_selected = Signal(int)

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cases_cache: List[Dict[str, Any]] = []
        self.selected_case: Optional[Dict[str, Any]] = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        theme = get_current_theme()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Top Bar
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("📁 Forensic Case Management")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {theme.text_primary};")
        subtitle = QLabel("Create and manage investigation cases, scopes, and chain of custody tracking.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        self.new_case_btn = QPushButton("+ New Case")
        self.new_case_btn.setStyleSheet(f"""
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
        self.new_case_btn.clicked.connect(self.open_new_case_dialog)
        top_bar.addWidget(self.new_case_btn)

        main_layout.addLayout(top_bar)

        # Filter & Search Toolbar
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
        self.search_input.setPlaceholderText("Filter by case #, title, or investigator...")
        self.search_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.search_input, stretch=2)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Active", "Closed", "Archived"])
        self.status_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.status_filter, stretch=1)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        main_layout.addWidget(filter_box)

        # Splitter with Cases Table on top and Details Panel on bottom
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # Cases Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Case #", "Title", "Investigator", "Status", "Evidence Items", "Created Date", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        splitter.addWidget(self.table)

        # Details Panel
        self.detail_panel = QGroupBox("Selected Case Details")
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setSpacing(10)

        self.detail_header = QLabel("Select a case to inspect details and linked evidence.")
        self.detail_header.setStyleSheet(f"color: {theme.text_secondary}; font-style: italic;")
        detail_layout.addWidget(self.detail_header)

        self.detail_desc = QLabel("")
        self.detail_desc.setWordWrap(True)
        detail_layout.addWidget(self.detail_desc)

        detail_actions = QHBoxLayout()
        self.edit_case_btn = QPushButton("✏️ Edit Case")
        self.edit_case_btn.setEnabled(False)
        self.edit_case_btn.clicked.connect(self._edit_selected_case)
        detail_actions.addWidget(self.edit_case_btn)

        self.toggle_status_btn = QPushButton("Toggle Status")
        self.toggle_status_btn.setEnabled(False)
        self.toggle_status_btn.clicked.connect(self._toggle_case_status)
        detail_actions.addWidget(self.toggle_status_btn)

        self.delete_case_btn = QPushButton("🗑️ Delete Case")
        self.delete_case_btn.setEnabled(False)
        self.delete_case_btn.setStyleSheet(f"color: {theme.status_danger};")
        self.delete_case_btn.clicked.connect(self._delete_selected_case)
        detail_actions.addWidget(self.delete_case_btn)

        detail_actions.addStretch()
        detail_layout.addLayout(detail_actions)

        splitter.addWidget(self.detail_panel)
        splitter.setSizes([450, 180])

        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        """Fetch cases from database and populate table."""
        self.cases_cache = self.controller.case_manager.list_cases()
        self._apply_filter()

    def _apply_filter(self):
        """Filter table items based on search and status dropdown."""
        theme = get_current_theme()
        search = self.search_input.text().strip().lower()
        status = self.status_filter.currentText().lower()
        if status == "all statuses":
            status = ""

        filtered = []
        for c in self.cases_cache:
            if status and c["status"] != status:
                continue
            if search:
                haystack = f"{c['case_number']} {c['title']} {c['investigator']}".lower()
                if search not in haystack:
                    continue
            filtered.append(c)

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            # Case #
            item_num = QTableWidgetItem(c["case_number"])
            item_num.setData(Qt.UserRole, c["id"])
            item_num.setFont(item_num.font())
            self.table.setItem(row, 0, item_num)

            # Title
            item_title = QTableWidgetItem(c["title"])
            self.table.setItem(row, 1, item_title)

            # Investigator
            item_inv = QTableWidgetItem(c["investigator"])
            self.table.setItem(row, 2, item_inv)

            # Status pill
            status_str = c["status"].capitalize()
            item_status = QTableWidgetItem(status_str)
            if c["status"] == "active":
                item_status.setForeground(QColor(theme.status_success))
            elif c["status"] == "closed":
                item_status.setForeground(QColor(theme.text_muted))
            else:
                item_status.setForeground(QColor(theme.status_warning))
            self.table.setItem(row, 3, item_status)

            # Evidence Items
            ev_count = str(c.get("evidence_count", 0))
            item_ev = QTableWidgetItem(f"{ev_count} item(s)")
            item_ev.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_ev)

            # Created Date
            created_str = c["created_at"].strftime("%Y-%m-%d %H:%M") if c["created_at"] else ""
            self.table.setItem(row, 5, QTableWidgetItem(created_str))

            # Action button
            view_btn = QPushButton("View")
            view_btn.setProperty("case_id", c["id"])
            view_btn.clicked.connect(lambda _, cid=c["id"]: self._select_case_by_id(cid))
            self.table.setCellWidget(row, 6, view_btn)

    def _on_row_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self._clear_detail_panel()
            return

        row = selected_rows[0].row()
        case_id = self.table.item(row, 0).data(Qt.UserRole)
        self._select_case_by_id(case_id)

    def _select_case_by_id(self, case_id: int):
        case = self.controller.case_manager.get_case(case_id)
        if not case:
            return

        self.selected_case = case
        theme = get_current_theme()

        self.detail_header.setText(
            f"Case: {case['case_number']} | Title: {case['title']} | Investigator: {case['investigator']} | Status: {case['status'].upper()}"
        )
        self.detail_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.accent};")

        desc_text = case.get("description") or "No description provided."
        self.detail_desc.setText(
            f"Description: {desc_text}\n"
            f"Associated Evidence: {case.get('evidence_count', 0)} item(s) registered.\n"
            f"Created: {case['created_at'].strftime('%Y-%m-%d %H:%M:%S')} | Last Updated: {case['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self.edit_case_btn.setEnabled(True)
        self.toggle_status_btn.setEnabled(True)
        self.toggle_status_btn.setText("Close Case" if case["status"] == "active" else "Re-Open Case")
        self.delete_case_btn.setEnabled(True)

        self.case_selected.emit(case["id"])

    def _clear_detail_panel(self):
        self.selected_case = None
        self.detail_header.setText("Select a case to inspect details and linked evidence.")
        self.detail_header.setStyleSheet(f"color: {get_current_theme().text_secondary}; font-style: italic;")
        self.detail_desc.setText("")
        self.edit_case_btn.setEnabled(False)
        self.toggle_status_btn.setEnabled(False)
        self.delete_case_btn.setEnabled(False)

    def _on_row_double_clicked(self, index):
        row = index.row()
        case_id = self.table.item(row, 0).data(Qt.UserRole)
        self._select_case_by_id(case_id)
        self._edit_selected_case()

    def open_new_case_dialog(self):
        """Open modal to create a new case."""
        dialog = NewCaseDialog(self.controller, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.case_data:
            self.refresh()
            self._select_case_by_id(dialog.case_data["id"])

    def _edit_selected_case(self):
        if not self.selected_case:
            return
        dialog = EditCaseDialog(self.controller, self.selected_case, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.updated_case:
            self.refresh()
            self._select_case_by_id(dialog.updated_case["id"])

    def _toggle_case_status(self):
        if not self.selected_case:
            return
        new_status = "closed" if self.selected_case["status"] == "active" else "active"
        self.controller.case_manager.update_case(self.selected_case["id"], status=new_status)
        self.refresh()
        self._select_case_by_id(self.selected_case["id"])

    def _delete_selected_case(self):
        if not self.selected_case:
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Delete Case",
            f"Are you sure you want to permanently delete case '{self.selected_case['case_number']}'?\n"
            f"All associated evidence and operation history will be unlinked or deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.controller.case_manager.delete_case(self.selected_case["id"])
            self._clear_detail_panel()
            self.refresh()
