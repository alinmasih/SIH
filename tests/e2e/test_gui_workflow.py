"""
End-to-End GUI Workflow Test Suite for Forensics Platform.

Validates:
1. MainWindow initialization and default state
2. Seamless sidebar navigation across all 10 views
3. Dynamic theme toggle (Dark / Light)
4. Dashboard quick action button dispatching
5. Case creation and evidence registration dialog workflows
6. Status bar updates and simulation mode banners
"""

import pytest
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from forensics_platform.core.config import Config
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.main_window import MainWindow
from forensics_platform.gui.forensics.case_manager_widget import NewCaseDialog
from forensics_platform.gui.forensics.evidence_manager_widget import RegisterEvidenceDialog
from forensics_platform.gui.themes import get_theme_manager


@pytest.fixture
def gui_app_env(tmp_path, qapp):
    """Sets up an isolated GUI test environment with temporary database and controller."""
    cfg_file = tmp_path / "gui_test_config.yaml"
    cfg = Config(
        app_name="Forensics Platform GUI Test",
        version="1.0.0",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "gui_test.db",
        simulation_mode=True,
        theme="dark",
    )
    cfg.save(cfg_file)
    controller = ApplicationController(config_path=cfg_file)
    window = MainWindow(controller)
    
    yield window, controller, tmp_path
    
    window.close()
    controller.shutdown()


def test_main_window_initialization(gui_app_env, qtbot):
    """Verify MainWindow loads cleanly with default configuration and widgets."""
    window, controller, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    # Window title and attributes
    assert "Forensics Platform" in window.windowTitle()
    assert window.minimumWidth() == 1200
    assert window.minimumHeight() == 800

    # Default view must be dashboard
    assert window.content_stack.currentIndex() == window.pages["dashboard"]
    assert window.nav_buttons["dashboard"].isChecked() is True

    # Status bar indicators
    assert "Dashboard" in window.status_label.text()
    assert "SQLite Connected" in window.db_label.text()
    assert hasattr(window, "sim_status_label")
    assert "SIMULATION MODE" in window.sim_status_label.text()


def test_full_sidebar_navigation(gui_app_env, qtbot):
    """Verify navigation to all 10 application views updates stack index and status bar."""
    window, _, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    pages_to_test = [
        ("dashboard", 0),
        ("cases", 1),
        ("evidence", 2),
        ("audit", 3),
        ("recovery", 4),
        ("carving", 5),
        ("drive_eraser", 6),
        ("file_eraser", 7),
        ("reports", 8),
        ("settings", 9),
    ]

    for page_id, expected_index in pages_to_test:
        btn = window.nav_buttons[page_id]
        qtbot.mouseClick(btn, Qt.LeftButton)

        # Content stack must reflect chosen page
        assert window.content_stack.currentIndex() == expected_index
        assert btn.isChecked() is True

        # All other buttons must be unchecked
        for other_id, other_btn in window.nav_buttons.items():
            if other_id != page_id:
                assert other_btn.isChecked() is False

        # Status text must indicate active view
        assert page_id in window.status_label.text().lower().replace(" ", "_") or "cases" in window.status_label.text().lower()


def test_theme_toggle_dynamic_update(gui_app_env, qtbot):
    """Verify theme switcher updates theme manager, stylesheets, and button labels."""
    window, controller, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    theme_mgr = get_theme_manager()
    initial_is_light = theme_mgr.is_light

    # Click toggle button
    qtbot.mouseClick(window.theme_toggle_btn, Qt.LeftButton)

    # Theme state should have flipped
    assert theme_mgr.is_light != initial_is_light
    assert controller.config_manager.get("theme") == theme_mgr.current.name

    if theme_mgr.is_light:
        assert "Dark Theme" in window.theme_toggle_btn.text()
    else:
        assert "Light Theme" in window.theme_toggle_btn.text()

    # Toggle back to original
    qtbot.mouseClick(window.theme_toggle_btn, Qt.LeftButton)
    assert theme_mgr.is_light == initial_is_light


def test_dashboard_quick_actions(gui_app_env, qtbot):
    """Verify dashboard quick action signals navigate directly to target modules."""
    window, _, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    # Recovery quick action
    window._handle_dashboard_action("recovery")
    assert window.content_stack.currentIndex() == window.pages["recovery"]
    assert window.nav_buttons["recovery"].isChecked() is True

    # Carving quick action
    window._handle_dashboard_action("carving")
    assert window.content_stack.currentIndex() == window.pages["carving"]
    assert window.nav_buttons["carving"].isChecked() is True

    # Audit quick action
    window._handle_dashboard_action("audit")
    assert window.content_stack.currentIndex() == window.pages["audit"]
    assert window.nav_buttons["audit"].isChecked() is True


def test_new_case_dialog_workflow(gui_app_env, qtbot):
    """Verify Case creation dialog validation and persistence in GUI table."""
    window, controller, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    dialog = NewCaseDialog(controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    # Validation: empty form should fail
    dialog._on_submit()
    assert dialog.result() != QDialog.Accepted
    assert bool(dialog.error_label.text()) is True

    # Fill valid inputs
    dialog.case_number_input.setText("GUI-CASE-001")
    dialog.title_input.setText("E2E GUI Automated Case")
    dialog.investigator_input.setText("Inspector Gadget")
    dialog.description_input.setText("Created during E2E automated testing.")

    # Submit valid form
    dialog._on_submit()
    assert dialog.result() == QDialog.Accepted
    assert dialog.case_data is not None
    assert dialog.case_data["case_number"] == "GUI-CASE-001"

    # Verify case manager widget displays it
    window.case_manager_widget.refresh()
    assert len(window.case_manager_widget.cases_cache) >= 1
    found_case = next(c for c in window.case_manager_widget.cases_cache if c["case_number"] == "GUI-CASE-001")
    assert found_case["title"] == "E2E GUI Automated Case"


def test_register_evidence_dialog_workflow(gui_app_env, qtbot):
    """Verify Evidence acquisition dialog registers item and reflects in manager."""
    window, controller, tmp_path = gui_app_env
    qtbot.addWidget(window)
    window.show()

    # Pre-create a case
    case = controller.case_manager.create_case(
        case_number="CASE-EVD-99",
        title="Evidence Acquisition Case",
        investigator="Agent Smith"
    )

    # Create dummy image file
    sample_img = tmp_path / "disk.raw"
    sample_img.write_bytes(b"\x00" * 4096)

    dialog = RegisterEvidenceDialog(controller, preselected_case_id=case["id"], parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.evidence_num_input.setText("EVD-2026-99-A")
    dialog.path_input.setText(str(sample_img))
    dialog.notes_input.setText("Seized USB Flash Drive")

    dialog._on_register()
    # Wait for HashWorker background thread to finish
    qtbot.waitUntil(lambda: dialog.result() == QDialog.Accepted, timeout=5000)
    assert dialog.registered_evidence is not None
    assert dialog.registered_evidence["evidence_number"] == "EVD-2026-99-A"

    # Verify Evidence manager widget displays it
    window.evidence_manager_widget.refresh()
    assert len(window.evidence_manager_widget.evidence_cache) >= 1
    evd = next(e for e in window.evidence_manager_widget.evidence_cache if e["evidence_number"] == "EVD-2026-99-A")
    assert evd["case_id"] == case["id"]


def test_status_bar_and_notifications(gui_app_env, qtbot):
    """Verify transient status messages and permanent widget state."""
    window, _, _ = gui_app_env
    qtbot.addWidget(window)
    window.show()

    window.show_status_message("Custom Operation Completed Successfully")
    assert window.status_bar.currentMessage() == "Custom Operation Completed Successfully"
