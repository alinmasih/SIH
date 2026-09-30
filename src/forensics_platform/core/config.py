"""
Configuration management system for the forensics platform.

Handles loading, saving, and validating configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class Config:
    """Application configuration"""

    # Application
    app_name: str = "Forensics Platform"
    version: str = "1.0.0"

    # Directories
    data_dir: Path = field(default_factory=lambda: Path.home() / ".local/share/forensics-platform")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".local/share/forensics-platform/logs")
    case_dir: Path = field(default_factory=lambda: Path.home() / ".local/share/forensics-platform/cases")
    temp_dir: Path = field(default_factory=lambda: Path.home() / ".local/share/forensics-platform/temp")

    # Database
    database_path: Path = field(default_factory=lambda: Path.home() / ".local/share/forensics-platform/forensics.db")

    # Sanitization - SAFETY DEFAULTS
    simulation_mode: bool = True  # SAFETY: Default to simulation
    require_explicit_confirmation: bool = True
    confirmation_count: int = 3  # Number of confirmations required

    # Carving
    carving_chunk_size: int = 1024 * 1024  # 1MB chunks
    max_file_size: int = 100 * 1024 * 1024  # 100MB max recovered file
    default_confidence_threshold: int = 50  # 0-100
    parallel_validation: bool = True

    # Forensics
    calculate_hashes: bool = True
    hash_algorithm: str = "sha256"
    verify_evidence_on_open: bool = True

    # Logging
    log_level: str = "INFO"
    max_log_size_mb: int = 100
    log_backup_count: int = 5
    enable_audit_log: bool = True

    # GUI
    theme: str = "light"  # 'light' or 'dark'
    remember_window_size: bool = True
    confirm_destructive_operations: bool = True

    # External Tools
    sleuthkit_path: str = "/usr/bin"  # Auto-detect if empty

    def __post_init__(self):
        """Convert string paths to Path objects"""
        # Convert any string paths to Path objects
        for field_name in ['data_dir', 'log_dir', 'case_dir', 'temp_dir', 'database_path']:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, Path(value))

        # Expand ~ in paths
        for field_name in ['data_dir', 'log_dir', 'case_dir', 'temp_dir', 'database_path']:
            path = getattr(self, field_name)
            if isinstance(path, Path):
                setattr(self, field_name, path.expanduser())

    def create_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.data_dir, self.log_dir, self.case_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create database directory
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (for serialization)"""
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, Path):
                data[key] = str(value)
            else:
                data[key] = value
        return data

    def save(self, path: Path):
        """Save configuration to YAML file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> 'Config':
        """Load configuration from YAML file"""
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f)

        if data is None:
            return cls()

        # Filter out None values and unknown keys
        valid_data = {k: v for k, v in data.items() if v is not None and k in cls.__dataclass_fields__}

        return cls(**valid_data)


class ConfigManager:
    """Manage application configuration"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_path = Path.home() / ".config/forensics-platform/config.yaml"

        self.config_path = config_path
        self.config = self._load_or_create()

    def _load_or_create(self) -> Config:
        """Load existing config or create default"""
        if self.config_path.exists():
            try:
                config = Config.load(self.config_path)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                print("Using default configuration.")
                config = Config()
        else:
            config = Config()
            # Save default config
            try:
                config.save(self.config_path)
            except Exception as e:
                print(f"Warning: Could not save default config: {e}")

        # Create necessary directories
        config.create_directories()

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        """Set configuration value and save"""
        if not hasattr(self.config, key):
            raise ValueError(f"Unknown configuration key: {key}")

        setattr(self.config, key, value)
        self.save()

    def save(self):
        """Save configuration to file"""
        try:
            self.config.save(self.config_path)
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_or_create()

    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = Config()
        self.config.create_directories()
        self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return self.config.to_dict()


# Singleton instance for global access
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    """Get current configuration"""
    return get_config_manager().config
