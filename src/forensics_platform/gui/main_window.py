"""
Main application window for the Forensics Platform.

Features:
- Sidebar navigation with light/dark theme support
- Theme toggle switch
- Integrated forensic case and evidence management
- Real-time audit log explorer
- Cohesive status reporting
"""

from typing import Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QStatusBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from forensics_platform.core import ApplicationController
from forensics_platform.gui.dashboard.dashboard_widget import DashboardWidget
from forensics_platform.gui.forensics.case_manager_widget import CaseManagerWidget
from forensics_platform.gui.forensics.evidence_manager_widget import EvidenceManagerWidget
from forensics_platform.gui.forensics.audit_viewer_widget import AuditViewerWidget
from forensics_platform.gui.forensics.recovery_widget import RecoveryWidget
from forensics_platform.gui.forensics.carving_widget import CarvingWidget
from forensics_platform.gui.sanitization.drive_eraser_widget import DriveEraserWidget
from forensics_platform.gui.sanitization.file_eraser_widget import FileEraserWidget
from forensics_platform.gui.reporting.reports_widget import ReportsWidget
from forensics_platform.gui.settings.settings_widget import SettingsWidget
from forensics_platform.gui.themes import (
    get_theme_manager, get_current_theme, Theme
)
from forensics_platform.utils.logging import get_logger


class NavigationButton(QPushButton):
    """Custom navigation sidebar button with reactive theme styling."""

    def __init__(self, text: str, page_id: str, parent=None):
        super().__init__(text, parent)
        self.page_id = page_id
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.apply_theme()

    def apply_theme(self):
        theme = get_current_theme()
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                margin: 2px 8px;
                background-color: transparent;
                font-size: 13px;
                font-weight: 500;
                color: {theme.text_primary};
            }}
            QPushButton:hover {{
                background-color: {theme.bg_hover};
            }}
            QPushButton:checked {{
                background-color: {theme.accent_subtle};
                color: {theme.accent};
                font-weight: bold;
                border-left: 3px solid {theme.accent};
            }}
        """)


class MainWindow(QMainWindow):
    """
    Main application window.

    Coordinates navigation, theme switching, status notifications,
    and the central stacked page container.
    """

    page_changed = Signal(str)

    def __init__(self, controller: ApplicationController):
        super().__init__()
        self.controller = controller
        self.logger = get_logger(__name__)

        # Ensure theme manager matches config
        theme_mgr = get_theme_manager()
        theme_mgr.set_theme(self.controller.config.theme)

        self._setup_window()
        self._create_ui()
        self._setup_connections()
        self._apply_theme()

        # Show dashboard by default
        self._show_dashboard()

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(f"Forensics Platform {self.controller.version}")
        self.setMinimumSize(1200, 800)

        if self.controller.config.remember_window_size:
            self.resize(1400, 900)

    def _create_ui(self):
        """Build main window layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar navigation
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area stack
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

        # Create pages
        self._create_pages()

        # Status bar
        self._create_status_bar()

    def _create_sidebar(self) -> QWidget:
        """Create navigation sidebar with header, items, and theme toggle."""
        sidebar = QFrame()
        sidebar.setFixedWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header area
        self.header_frame = QWidget()
        self.header_frame.setFixedHeight(85)
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(18, 14, 18, 10)

        self.title_label = QLabel("Forensics Platform")
        header_layout.addWidget(self.title_label)

        self.version_label = QLabel(f"v{self.controller.version} • Digital Forensics")
        header_layout.addWidget(self.version_label)

        layout.addWidget(self.header_frame)

        # Separator line
        self.header_separator = QFrame()
        self.header_separator.setFrameShape(QFrame.HLine)
        self.header_separator.setFixedHeight(1)
        layout.addWidget(self.header_separator)

        # Navigation buttons
        self.nav_buttons: Dict[str, NavigationButton] = {}
        nav_items = [
            ("Dashboard", "dashboard", "📊"),
            ("Cases", "cases", "📁"),
            ("Evidence", "evidence", "🗂️"),
            ("File Recovery", "recovery", "🔍"),
            ("File Carving", "carving", "🧩"),
            ("Drive Eraser", "drive_eraser", "💾"),
            ("File Eraser", "file_eraser", "🗑️"),
            ("Audit Logs", "audit", "📋"),
            ("Reports", "reports", "📄"),
            ("Settings", "settings", "⚙️"),
        ]

        for label, page_id, icon in nav_items:
            btn = NavigationButton(f"{icon}   {label}", page_id=page_id)
            btn.clicked.connect(lambda checked, pid=page_id: self._navigate_to(pid))
            self.nav_buttons[page_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Theme toggle button
        theme_mgr = get_theme_manager()
        toggle_label = "🌙 Dark Theme" if theme_mgr.is_light else "☀️ Light Theme"
        self.theme_toggle_btn = QPushButton(toggle_label)
        self.theme_toggle_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_toggle_btn)

        # Simulation mode warning badge
        if self.controller.is_simulation_mode:
            self.sim_label = QLabel("⚠️ SIMULATION MODE (ACTIVE)")
            self.sim_label.setAlignment(Qt.AlignCenter)
            self.sim_label.setStyleSheet("""
                QLabel {
                    background: #f59e0b;
                    color: #0f172a;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 11px;
                    margin: 8px;
                    border-radius: 6px;
                }
            """)
            layout.addWidget(self.sim_label)

        return sidebar

    def _create_pages(self):
        """Instantiate functional pages and placeholders into content stack."""
        self.pages = {}

        # 1. Dashboard
        self.dashboard_widget = DashboardWidget(self.controller)
        idx = self.content_stack.addWidget(self.dashboard_widget)
        self.pages["dashboard"] = idx

        # 2. Case Management (Phase 3 Complete)
        self.case_manager_widget = CaseManagerWidget(self.controller)
        idx = self.content_stack.addWidget(self.case_manager_widget)
        self.pages["cases"] = idx

        # 3. Evidence Management (Phase 3 Complete)
        self.evidence_manager_widget = EvidenceManagerWidget(self.controller)
        idx = self.content_stack.addWidget(self.evidence_manager_widget)
        self.pages["evidence"] = idx

        # 4. Audit Trail Viewer (Phase 3 Complete)
        self.audit_viewer_widget = AuditViewerWidget(self.controller)
        idx = self.content_stack.addWidget(self.audit_viewer_widget)
        self.pages["audit"] = idx

        # 5. File Recovery (Phase 4 Complete)
        self.recovery_widget = RecoveryWidget(self.controller)
        idx = self.content_stack.addWidget(self.recovery_widget)
        self.pages["recovery"] = idx

        # 6. File Carving (Phase 5 Complete)
        self.carving_widget = CarvingWidget(self.controller)
        idx = self.content_stack.addWidget(self.carving_widget)
        self.pages["carving"] = idx

        # 7. Drive Eraser (Phase 6 Complete)
        self.drive_eraser_widget = DriveEraserWidget(self.controller)
        idx = self.content_stack.addWidget(self.drive_eraser_widget)
        self.pages["drive_eraser"] = idx

        # 8. File Eraser (Phase 6 Complete)
        self.file_eraser_widget = FileEraserWidget(self.controller)
        idx = self.content_stack.addWidget(self.file_eraser_widget)
        self.pages["file_eraser"] = idx

        # 9. Forensic & Sanitization Reports (Phase 7 Complete)
        self.reports_widget = ReportsWidget(self.controller)
        idx = self.content_stack.addWidget(self.reports_widget)
        self.pages["reports"] = idx

        # 10. Platform Settings & Operational Controls
        self.settings_widget = SettingsWidget(self.controller)
        self.settings_widget.simulation_mode_toggled.connect(self._on_simulation_mode_toggled)
        self.settings_widget.demo_data_seeded.connect(self._on_demo_data_seeded)
        idx = self.content_stack.addWidget(self.settings_widget)
        self.pages["settings"] = idx

    def _create_placeholder(self, title: str, phase_info: str) -> QWidget:
        """Create a placeholder widget for upcoming phase components."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        theme = get_current_theme()

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet(f"color: {theme.text_primary}; font-size: 24px; font-weight: bold;")
        layout.addWidget(heading)

        sub = QLabel(f"Scheduled for development in {phase_info}.\nCore foundation and database schemas are already prepared.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {theme.text_secondary}; font-size: 14px;")
        layout.addWidget(sub)

        return widget

    def _create_status_bar(self):
        """Create informative application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        db_status = "✓ SQLite Connected" if self.controller.db_manager.is_initialized else "✗ Database Error"
        self.db_label = QLabel(db_status)
        self.db_label.setStyleSheet("padding: 0 12px; font-weight: 500;")
        self.status_bar.addPermanentWidget(self.db_label)

        if self.controller.is_simulation_mode:
            self.sim_status_label = QLabel("⚠️ SIMULATION MODE")
            self.sim_status_label.setStyleSheet("color: #d97706; font-weight: bold; padding: 0 10px;")
            self.status_bar.addPermanentWidget(self.sim_status_label)

    def _setup_connections(self):
        """Wire signals between components."""
        self.page_changed.connect(self._on_page_changed)

        # Connect Dashboard quick action buttons
        self.dashboard_widget.action_requested.connect(self._handle_dashboard_action)

    def _handle_dashboard_action(self, action: str):
        """React to action button clicks on the dashboard."""
        if action == "new_case":
            self._navigate_to("cases")
            self.case_manager_widget.open_new_case_dialog()
        elif action == "register_evidence":
            self._navigate_to("evidence")
            self.evidence_manager_widget.open_register_evidence_dialog()
        elif action == "recovery":
            self._navigate_to("recovery")
        elif action == "carving":
            self._navigate_to("carving")
        elif action == "audit":
            self._navigate_to("audit")
        elif action == "settings":
            self._navigate_to("settings")
        elif action == "load_demo":
            self.settings_widget._seed_demo_data()

    def _apply_theme(self):
        """Apply active theme stylesheets across the entire window hierarchy."""
        theme = get_current_theme()

        # Global application stylesheet
        self.setStyleSheet(theme.get_global_stylesheet())

        # Content stack background
        self.content_stack.setStyleSheet(f"background-color: {theme.bg_main};")

        # Sidebar styling
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_sidebar};
                border-right: 1px solid {theme.border};
            }}
        """)

        # Header typography
        self.title_label.setStyleSheet(f"color: {theme.text_primary}; font-size: 18px; font-weight: bold;")
        self.version_label.setStyleSheet(f"color: {theme.text_secondary}; font-size: 12px;")
        self.header_separator.setStyleSheet(f"background-color: {theme.border};")

        # Theme toggle button
        self.theme_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 16px;
                margin: 8px 12px;
                color: {theme.text_primary};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_subtle};
                border-color: {theme.accent};
                color: {theme.accent};
            }}
        """)
        theme_mgr = get_theme_manager()
        self.theme_toggle_btn.setText("🌙 Dark Theme" if theme_mgr.is_light else "☀️ Light Theme")

        # Navigation buttons
        for btn in self.nav_buttons.values():
            btn.apply_theme()

        # Status bar
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {theme.bg_surface};
                color: {theme.text_secondary};
                border-top: 1px solid {theme.border};
            }}
        """)

        # Propagate to dashboard
        if hasattr(self, "dashboard_widget"):
            self.dashboard_widget.apply_theme()

    def _toggle_theme(self):
        """Toggle between light and dark themes at runtime."""
        theme_mgr = get_theme_manager()
        theme_mgr.toggle_theme()
        self.controller.config_manager.set("theme", theme_mgr.current.name)
        self._apply_theme()
        self.logger.info(f"Theme switched to: {theme_mgr.current.name}")

    def _navigate_to(self, page_id: str):
        """Navigate to a given page ID."""
        if page_id in self.pages:
            for pid, btn in self.nav_buttons.items():
                btn.setChecked(pid == page_id)

            index = self.pages[page_id]
            self.content_stack.setCurrentIndex(index)
            self.page_changed.emit(page_id)

            page_names = {
                "dashboard": "Dashboard",
                "cases": "Cases Management",
                "evidence": "Evidence Management",
                "recovery": "File Recovery",
                "carving": "File Carving Engine",
                "drive_eraser": "Drive Eraser",
                "file_eraser": "File Eraser",
                "audit": "Audit Logs",
                "reports": "Reports",
                "settings": "Settings",
            }
            self.status_label.setText(f"Viewing: {page_names.get(page_id, page_id)}")
            self.logger.info(f"Navigated to page: {page_id}")

    def _show_dashboard(self):
        """Show dashboard page."""
        self._navigate_to("dashboard")

    def _on_page_changed(self, page_id: str):
        """Refresh page data when switching to it."""
        if page_id == "dashboard":
            self.dashboard_widget.refresh()
        elif page_id == "cases":
            self.case_manager_widget.refresh()
        elif page_id == "evidence":
            self.evidence_manager_widget.refresh()
        elif page_id == "audit":
            self.audit_viewer_widget.refresh()
        elif page_id == "recovery":
            self.recovery_widget.refresh()
        elif page_id == "carving":
            self.carving_widget.refresh_sources()
        elif page_id == "drive_eraser":
            self.drive_eraser_widget.refresh_devices()
        elif page_id == "settings":
            self.settings_widget.refresh()

    def _on_simulation_mode_toggled(self, is_sim: bool):
        """Update window badges and dependent views when simulation mode changes."""
        if hasattr(self, "sim_label"):
            self.sim_label.setVisible(is_sim)
        if hasattr(self, "sim_status_label"):
            self.sim_status_label.setVisible(is_sim)
        if hasattr(self, "dashboard_widget"):
            self.dashboard_widget.refresh()
        if hasattr(self, "drive_eraser_widget"):
            self.drive_eraser_widget.refresh_devices()
        self.show_status_message(f"Operational mode updated: {'SIMULATION' if is_sim else 'LIVE WRITE'}")

    def _on_demo_data_seeded(self):
        """Refresh all modules after demo data is created."""
        self.dashboard_widget.refresh()
        self.case_manager_widget.refresh()
        self.evidence_manager_widget.refresh()
        self.carving_widget.refresh_sources()
        self.recovery_widget.refresh()
        self.show_status_message("Demo case and synthetic evidence disk loaded successfully!")

    def show_status_message(self, message: str, timeout: int = 5000):
        """Show a temporary status message in the status bar."""
        self.status_bar.showMessage(message, timeout)

    def closeEvent(self, event):
        """Handle window close event."""
        self.logger.info("Main window closing")
        event.accept()
