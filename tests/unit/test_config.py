"""
Unit tests for configuration management.
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from forensics_platform.core.config import Config, ConfigManager


def test_config_default_values():
    """Test Config dataclass has correct defaults"""
    config = Config()

    assert config.app_name == "Forensics Platform"
    assert config.version == "1.0.0"
    assert config.simulation_mode == True  # SAFETY: Default to simulation
    assert config.require_explicit_confirmation == True
    assert config.hash_algorithm == "sha256"


def test_config_create_directories():
    """Test directory creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        config = Config()
        config.data_dir = temp_path / "test_data"
        config.log_dir = temp_path / "test_data/logs"
        config.case_dir = temp_path / "test_data/cases"
        config.temp_dir = temp_path / "test_data/temp"

        # Directories shouldn't exist yet
        assert not config.data_dir.exists()

        # Create directories
        config.create_directories()

        # Now they should exist
        assert config.data_dir.exists()
        assert config.log_dir.exists()
        assert config.case_dir.exists()
        assert config.temp_dir.exists()


def test_config_save_and_load():
    """Test saving and loading configuration"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Create and save config
        original = Config()
        original.simulation_mode = False
        original.log_level = "DEBUG"
        original.save(config_path)

        # Load config
        loaded = Config.load(config_path)

        assert loaded.simulation_mode == False
        assert loaded.log_level == "DEBUG"


def test_config_manager_initialization():
    """Test ConfigManager initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        manager = ConfigManager(config_path)

        assert manager.config is not None
        assert isinstance(manager.config, Config)


def test_config_manager_get_set():
    """Test ConfigManager get/set methods"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        manager = ConfigManager(config_path)

        # Test get
        assert manager.get("log_level") == "INFO"

        # Test set
        manager.set("log_level", "DEBUG")
        assert manager.get("log_level") == "DEBUG"


def test_config_manager_reset_to_defaults():
    """Test resetting configuration to defaults"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        manager = ConfigManager(config_path)

        # Change a value
        manager.set("log_level", "DEBUG")
        assert manager.get("log_level") == "DEBUG"

        # Reset to defaults
        manager.reset_to_defaults()
        assert manager.get("log_level") == "INFO"


def test_config_to_dict():
    """Test converting config to dictionary"""
    config = Config()
    config_dict = config.to_dict()

    assert isinstance(config_dict, dict)
    assert "app_name" in config_dict
    assert "version" in config_dict
    assert config_dict["app_name"] == "Forensics Platform"


def test_config_safety_defaults():
    """Test that safety-critical settings have safe defaults"""
    config = Config()

    # Destructive operations should default to safe mode
    assert config.simulation_mode == True
    assert config.require_explicit_confirmation == True
    assert config.confirmation_count >= 1
