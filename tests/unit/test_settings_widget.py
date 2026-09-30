"""
Unit tests for SettingsWidget, simulation mode toggle, and demo data seeding.
"""

from pathlib import Path
import pytest
from PySide6.QtCore import Qt

from forensics_platform.core.config import Config
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.settings.settings_widget import SettingsWidget


@pytest.fixture
def settings_env(tmp_path, qapp):
    cfg_file = tmp_path / "settings_test_config.yaml"
    cfg = Config(
        app_name="Settings Test",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        case_dir=tmp_path / "cases",
        temp_dir=tmp_path / "temp",
        database_path=tmp_path / "settings_test.db",
        simulation_mode=True,
    )
    cfg.save(cfg_file)
    controller = ApplicationController(config_path=cfg_file)
    widget = SettingsWidget(controller)
    yield widget, controller, tmp_path
    controller.shutdown()


def test_settings_widget_init(settings_env, qtbot):
    widget, controller, _ = settings_env
    qtbot.addWidget(widget)

    assert "SIMULATION MODE: ACTIVE" in widget.mode_title.text()
    assert widget.conf_slider.value() == 50


def test_settings_demo_data_seeding(settings_env, qtbot):
    widget, controller, _ = settings_env
    qtbot.addWidget(widget)

    # Seed demo data without blocking modal
    widget._seed_demo_data(show_dialog=False)

    # Verify case was created
    cases = controller.case_manager.list_cases()
    assert any(c["case_number"] == "CASE-DEMO-2026" for c in cases)

    # Verify evidence was created
    case = next(c for c in cases if c["case_number"] == "CASE-DEMO-2026")
    evd = controller.evidence_manager.list_evidence(case_id=case["id"])
    assert len(evd) >= 1
    assert Path(evd[0]["image_path"]).exists()
    assert Path(evd[0]["image_path"]).stat().st_size > 0
