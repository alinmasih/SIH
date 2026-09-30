"""
Theme system for Forensics Platform.

Provides cohesive, modern light and dark themes with full Qt stylesheet generators.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Theme:
    """Color palette and styling tokens for application themes."""

    name: str
    bg_main: str
    bg_surface: str
    bg_sidebar: str
    bg_header: str
    bg_hover: str
    border: str
    border_subtle: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_subtle: str
    accent_text: str
    input_bg: str
    input_border: str
    table_header_bg: str
    table_row_alt: str
    status_success: str
    status_warning: str
    status_danger: str
    status_info: str

    def get_global_stylesheet(self) -> str:
        """Generate comprehensive application Qt stylesheet."""
        return f"""
        QMainWindow {{
            background-color: {self.bg_main};
            color: {self.text_primary};
        }}
        QWidget {{
            color: {self.text_primary};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 13px;
        }}
        QDialog {{
            background-color: {self.bg_surface};
            color: {self.text_primary};
        }}
        QLabel {{
            color: {self.text_primary};
        }}
        QGroupBox {{
            background-color: {self.bg_surface};
            border: 1px solid {self.border};
            border-radius: 8px;
            margin-top: 14px;
            padding: 16px;
            font-weight: bold;
            color: {self.text_primary};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            color: {self.text_primary};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
            background-color: {self.input_bg};
            border: 1px solid {self.input_border};
            border-radius: 6px;
            padding: 8px 12px;
            color: {self.text_primary};
            selection-background-color: {self.accent};
            selection-color: {self.accent_text};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
            border: 1px solid {self.accent};
        }}
        QComboBox {{
            background-color: {self.input_bg};
            border: 1px solid {self.input_border};
            border-radius: 6px;
            padding: 6px 12px;
            color: {self.text_primary};
            min-height: 24px;
        }}
        QComboBox:focus {{
            border: 1px solid {self.accent};
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.bg_surface};
            border: 1px solid {self.border};
            selection-background-color: {self.accent_subtle};
            selection-color: {self.accent};
            color: {self.text_primary};
            padding: 4px;
        }}
        QPushButton {{
            background-color: {self.bg_surface};
            border: 1px solid {self.border};
            border-radius: 6px;
            padding: 8px 16px;
            color: {self.text_primary};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {self.bg_hover};
            border-color: {self.accent};
        }}
        QPushButton:pressed {{
            background-color: {self.accent_subtle};
        }}
        QPushButton:disabled {{
            background-color: {self.border_subtle};
            color: {self.text_muted};
            border-color: {self.border};
        }}
        QTableWidget, QTableView {{
            background-color: {self.bg_surface};
            border: 1px solid {self.border};
            border-radius: 8px;
            gridline-color: {self.border_subtle};
            color: {self.text_primary};
            selection-background-color: {self.accent_subtle};
            selection-color: {self.text_primary};
            alternate-background-color: {self.table_row_alt};
        }}
        QHeaderView::section {{
            background-color: {self.table_header_bg};
            color: {self.text_secondary};
            padding: 8px 12px;
            border: none;
            border-bottom: 2px solid {self.border};
            font-weight: 600;
            font-size: 12px;
            text-align: left;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {self.border};
            min-height: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {self.text_muted};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {self.border};
            min-width: 24px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QProgressBar {{
            background-color: {self.border_subtle};
            border: 1px solid {self.border};
            border-radius: 6px;
            text-align: center;
            color: {self.text_primary};
            height: 16px;
            font-size: 11px;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {self.accent};
            border-radius: 5px;
        }}
        QStatusBar {{
            background-color: {self.bg_surface};
            color: {self.text_secondary};
            border-top: 1px solid {self.border};
        }}
        """


LIGHT_THEME = Theme(
    name="light",
    bg_main="#f8fafc",
    bg_surface="#ffffff",
    bg_sidebar="#ffffff",
    bg_header="#ffffff",
    bg_hover="#f1f5f9",
    border="#e2e8f0",
    border_subtle="#f1f5f9",
    text_primary="#0f172a",
    text_secondary="#475569",
    text_muted="#94a3b8",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_subtle="#eff6ff",
    accent_text="#ffffff",
    input_bg="#ffffff",
    input_border="#cbd5e1",
    table_header_bg="#f8fafc",
    table_row_alt="#fbfcfe",
    status_success="#16a34a",
    status_warning="#d97706",
    status_danger="#dc2626",
    status_info="#0284c7",
)

DARK_THEME = Theme(
    name="dark",
    bg_main="#18181b",
    bg_surface="#27272a",
    bg_sidebar="#1f1f23",
    bg_header="#27272a",
    bg_hover="#3f3f46",
    border="#3f3f46",
    border_subtle="#2d2d30",
    text_primary="#f4f4f5",
    text_secondary="#a1a1aa",
    text_muted="#71717a",
    accent="#3b82f6",
    accent_hover="#60a5fa",
    accent_subtle="rgba(59, 130, 246, 0.15)",
    accent_text="#ffffff",
    input_bg="#18181b",
    input_border="#3f3f46",
    table_header_bg="#202024",
    table_row_alt="#222226",
    status_success="#22c55e",
    status_warning="#f59e0b",
    status_danger="#ef4444",
    status_info="#38bdf8",
)


class ThemeManager:
    """Manages application themes and active state."""

    def __init__(self, initial_theme: str = "light"):
        self._current_theme_name = initial_theme.lower()
        self._theme = LIGHT_THEME if self._current_theme_name == "light" else DARK_THEME

    @property
    def current(self) -> Theme:
        """Get the currently active theme."""
        return self._theme

    @property
    def is_light(self) -> bool:
        """Check if currently active theme is light."""
        return self._theme.name == "light"

    def set_theme(self, theme_name: str) -> Theme:
        """Set active theme by name ('light' or 'dark')."""
        self._current_theme_name = theme_name.lower()
        self._theme = LIGHT_THEME if self._current_theme_name == "light" else DARK_THEME
        return self._theme

    def toggle_theme(self) -> Theme:
        """Toggle between light and dark themes."""
        new_theme = "dark" if self.is_light else "light"
        return self.set_theme(new_theme)


# Global singleton theme manager
_theme_manager = ThemeManager(initial_theme="light")


def get_theme_manager() -> ThemeManager:
    """Get global theme manager instance."""
    return _theme_manager


def get_current_theme() -> Theme:
    """Get current active theme."""
    return _theme_manager.current
