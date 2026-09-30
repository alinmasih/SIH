"""
Dashboard widget - main overview page.

Displays:
- System status
- Case and Evidence statistics
- Operations summary
- Quick action triggers
- Recent tamper-evident activity feed
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal

from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.database.models import Case, Evidence, Operation, RecoveredFile
from forensics_platform.utils.logging import get_logger
from forensics_platform.gui.themes import get_current_theme


class StatCard(QFrame):
    """Statistics card widget with adaptive theme styling."""

    def __init__(self, title: str, value: str, icon: str = "", color: str = "#2563eb"):
        super().__init__()
        self.color = color
        self.setFrameStyle(QFrame.Box)
        self.apply_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Icon and title
        header_layout = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 26px; color: {color};")
            header_layout.addWidget(icon_label)

        self.title_label = QLabel(title)
        header_layout.addWidget(self.title_label, stretch=1)
        layout.addLayout(header_layout)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
        layout.addWidget(self.value_label)

    def apply_theme(self):
        theme = get_current_theme()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border: 1px solid {self.color};
                background-color: {theme.bg_hover};
            }}
        """)
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(f"color: {theme.text_secondary}; font-size: 13px; font-weight: 600;")

    def update_value(self, value: str):
        """Update the displayed count."""
        self.value_label.setText(value)


class DashboardWidget(QWidget):
    """Dashboard widget showing system overview and fast actions."""

    # Signal emitted when a quick action is triggered: ('new_case', 'register_evidence', 'recovery', 'report')
    action_requested = Signal(str)

    def __init__(self, controller: ApplicationController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = get_logger(__name__)

        self._create_ui()
        self._setup_auto_refresh()
        self.refresh()

    def _create_ui(self):
        """Build responsive dashboard UI."""
        theme = get_current_theme()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Top Header
        self.header_label = QLabel("📊 Platform Dashboard")
        self.header_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {theme.text_primary};")
        main_layout.addWidget(self.header_label)

        # Scroll area for clean overflow handling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)

        # 1. Statistics Cards Grid
        self.stats_group = QGroupBox("Key Investigation Metrics")
        self.stats_group.setStyleSheet(self._group_box_stylesheet(theme))
        stats_layout = QGridLayout(self.stats_group)
        stats_layout.setSpacing(16)

        self.cases_card = StatCard("Total Cases", "0", "📁", theme.accent)
        self.evidence_card = StatCard("Evidence Items", "0", "🗂️", theme.status_success)
        self.operations_card = StatCard("Operations Run", "0", "⚙️", theme.status_warning)
        self.recovered_card = StatCard("Recovered Files", "0", "🔍", "#8b5cf6")

        stats_layout.addWidget(self.cases_card, 0, 0)
        stats_layout.addWidget(self.evidence_card, 0, 1)
        stats_layout.addWidget(self.operations_card, 1, 0)
        stats_layout.addWidget(self.recovered_card, 1, 1)

        scroll_layout.addWidget(self.stats_group)

        # 2. Quick Actions
        self.actions_group = QGroupBox("Quick Actions")
        self.actions_group.setStyleSheet(self._group_box_stylesheet(theme))
        actions_layout = QGridLayout(self.actions_group)
        actions_layout.setSpacing(12)

        actions = [
            ("📁 New Case", lambda: self.action_requested.emit("new_case"), 0, 0),
            ("🗂️ Register Evidence", lambda: self.action_requested.emit("register_evidence"), 0, 1),
            ("🔍 File Recovery", lambda: self.action_requested.emit("recovery"), 1, 0),
            ("📋 Audit Trail", lambda: self.action_requested.emit("audit"), 1, 1),
            ("⚡ Load Demo Data", lambda: self.action_requested.emit("load_demo"), 2, 0),
            ("⚙️ Operational Settings", lambda: self.action_requested.emit("settings"), 2, 1),
        ]

        for text, handler, row, col in actions:
            btn = QPushButton(text)
            btn.setMinimumHeight(52)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.bg_surface};
                    border: 1px solid {theme.border};
                    border-radius: 8px;
                    color: {theme.text_primary};
                    font-size: 14px;
                    font-weight: 600;
                    text-align: left;
                    padding-left: 20px;
                }}
                QPushButton:hover {{
                    background-color: {theme.accent_subtle};
                    border-color: {theme.accent};
                    color: {theme.accent};
                }}
            """)
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn, row, col)

        scroll_layout.addWidget(self.actions_group)

        # 3. System Status
        self.system_group = QGroupBox("Platform & Engine Status")
        self.system_group.setStyleSheet(self._group_box_stylesheet(theme))
        system_layout = QVBoxLayout(self.system_group)

        self.system_status_label = QLabel()
        self.system_status_label.setStyleSheet(f"color: {theme.text_primary}; padding: 6px; line-height: 1.5;")
        self.system_status_label.setWordWrap(True)
        system_layout.addWidget(self.system_status_label)

        scroll_layout.addWidget(self.system_group)

        # 4. Recent Tamper-Evident Activity
        self.activity_group = QGroupBox("Recent Audit Activity")
        self.activity_group.setStyleSheet(self._group_box_stylesheet(theme))
        activity_layout = QVBoxLayout(self.activity_group)

        self.activity_label = QLabel("Loading activity...")
        self.activity_label.setStyleSheet(f"color: {theme.text_secondary}; padding: 6px;")
        self.activity_label.setWordWrap(True)
        activity_layout.addWidget(self.activity_label)

        scroll_layout.addWidget(self.activity_group)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _group_box_stylesheet(self, theme) -> str:
        return f"""
            QGroupBox {{
                font-size: 15px;
                font-weight: bold;
                color: {theme.text_primary};
                background-color: {theme.bg_surface};
                border: 1px solid {theme.border};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 6px;
                color: {theme.text_primary};
            }}
        """

    def apply_theme(self):
        """Re-apply dynamic theme tokens."""
        theme = get_current_theme()
        self.header_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {theme.text_primary};")
        for card in [self.cases_card, self.evidence_card, self.operations_card, self.recovered_card]:
            card.apply_theme()

        for grp in [self.stats_group, self.actions_group, self.system_group, self.activity_group]:
            grp.setStyleSheet(self._group_box_stylesheet(theme))

        self.system_status_label.setStyleSheet(f"color: {theme.text_primary}; padding: 6px;")
        self.activity_label.setStyleSheet(f"color: {theme.text_secondary}; padding: 6px;")

    def _setup_auto_refresh(self):
        """Setup auto refresh timer (every 30 seconds)."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(30000)

    def refresh(self):
        """Reload all metrics and activity."""
        try:
            self._load_statistics()
            self._load_system_status()
            self._load_recent_activity()
        except Exception as e:
            self.logger.error(f"Error refreshing dashboard: {e}")

    def _load_statistics(self):
        """Load live metrics from database."""
        with self.controller.db_manager.session() as session:
            cases_count = session.query(Case).count()
            evidence_count = session.query(Evidence).count()
            op_count = session.query(Operation).count()
            rec_count = session.query(RecoveredFile).count()

        self.cases_card.update_value(str(cases_count))
        self.evidence_card.update_value(str(evidence_count))
        self.operations_card.update_value(str(op_count))
        self.recovered_card.update_value(str(rec_count))

    def _load_system_status(self):
        """Render system status report."""
        status = self.controller.get_system_status()
        platform_info = status.get("platform", {})
        ext_tools = status.get("external_tools", {})

        sim_text = "⚠️ SIMULATION MODE (Destructive calls simulated)" if status["simulation_mode"] else "LIVE MODE"
        db_text = "✓ Connected (SQLite WAL)" if status["database_initialized"] else "✗ Not Connected"

        tools_status = []
        for tool, detected in ext_tools.items():
            icon = "✓" if detected else "✗"
            tools_status.append(f"{icon} {tool}")
        tools_str = ", ".join(tools_status) if tools_status else "Scanning..."

        html = f"""
        <b>Core Platform:</b> v{status['version']} &nbsp;|&nbsp; <b>Database:</b> {db_text} &nbsp;|&nbsp; <b>Operational Mode:</b> {sim_text}<br>
        <b>Host Environment:</b> {platform_info.get('os', 'Unknown')} ({platform_info.get('version', '')}) &nbsp;|&nbsp; <b>User:</b> {platform_info.get('username', '')}<br>
        <b>External Tool Integrations:</b> {tools_str}
        """
        self.system_status_label.setText(html)

    def _load_recent_activity(self):
        """Load recent audit events from hash-chained audit logger."""
        theme = get_current_theme()
        audit_trail = self.controller.audit_logger.get_audit_trail(limit=5)
        if not audit_trail:
            self.activity_label.setText("No activity recorded yet.")
            return

        items = []
        for ev in audit_trail:
            ts = ev.get("timestamp")
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)[:19]
            items.append(
                f"<li style='margin-bottom: 6px;'><b>{ev['event_type']}</b> - {ts_str} &nbsp;"
                f"<span style='color: {theme.text_secondary};'>(User: {ev['user']}, Hash: <code>{ev['event_hash'][:8]}...</code>)</span></li>"
            )

        html = f"<ul style='margin: 0; padding-left: 18px;'>{''.join(items)}</ul>"
        self.activity_label.setText(html)
