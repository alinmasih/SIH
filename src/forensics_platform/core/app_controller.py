"""
Application controller - central coordinator for all platform components.

Initializes and coordinates all subsystems.
"""

import sys
from pathlib import Path
from typing import Optional

from forensics_platform.core.config import Config, ConfigManager
from forensics_platform.database.session import DatabaseManager
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper
from forensics_platform.forensics.case_manager import CaseManager
from forensics_platform.forensics.evidence_manager import EvidenceManager
from forensics_platform.forensics.filesystem_analyzer import FilesystemAnalyzer
from forensics_platform.forensics.deleted_file_analyzer import DeletedFileAnalyzer
from forensics_platform.carving.carving_engine import CarvingEngine
from forensics_platform.sanitization.sanitization_manager import SanitizationManager
from forensics_platform.file_eraser.file_eraser import FileEraser
from forensics_platform.reporting.report_generator import ReportGenerator
from forensics_platform.version import VERSION, get_version_string


class ApplicationController:
    """
    Central application coordinator.

    Manages lifecycle of all subsystems:
    - Configuration
    - Database
    - Audit logging
    - Forensic Case & Evidence Managers
    - Filesystem & Deleted File Analyzers
    - Module initialization
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize application controller.

        Args:
            config_path: Optional path to configuration file
        """
        self._initialized = False

        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config

        # Initialize database
        self.db_manager = DatabaseManager(self.config.database_path)
        self.db_manager.initialize()

        # Initialize audit logger
        self.audit_logger = AuditLogger(self.db_manager.get_session)

        # External Tool Wrappers
        self.tsk_wrapper = SleuthKitWrapper(self.config.sleuthkit_path)

        # Initialize Case and Evidence managers
        self.case_manager = CaseManager(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config
        )
        self.evidence_manager = EvidenceManager(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config
        )

        # Initialize Filesystem and Deleted File Analyzers
        self.filesystem_analyzer = FilesystemAnalyzer(self.tsk_wrapper)
        self.deleted_file_analyzer = DeletedFileAnalyzer(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config,
            tsk_wrapper=self.tsk_wrapper
        )

        # Initialize Carving Engine
        self.carving_engine = CarvingEngine(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
        )

        # Initialize Sanitization and File Eraser
        self.sanitization_manager = SanitizationManager(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config,
        )
        self.device_detector = self.sanitization_manager.detector
        self.file_eraser = FileEraser(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config,
        )

        # Initialize Reporting Engine
        self.report_generator = ReportGenerator(
            db_manager=self.db_manager,
            audit_logger=self.audit_logger,
            config=self.config,
        )

        self._initialized = True

    @property
    def version(self) -> str:
        """Get application version"""
        return VERSION

    @property
    def version_string(self) -> str:
        """Get human-readable version string"""
        return get_version_string()

    @property
    def is_simulation_mode(self) -> bool:
        """Check if running in simulation mode (safe for development)"""
        return self.config.simulation_mode

    def shutdown(self):
        """Clean shutdown of all subsystems"""
        if self.db_manager:
            self.db_manager.close()

    def get_system_status(self) -> dict:
        """
        Get current system status summary.

        Returns:
            Dictionary with status of all subsystems
        """
        from forensics_platform.utils.platform_utils import (
            get_platform_info, check_external_tools
        )

        platform_info = get_platform_info()
        tools = check_external_tools()

        return {
            "version": self.version,
            "simulation_mode": self.config.simulation_mode,
            "database_initialized": self.db_manager.is_initialized,
            "platform": {
                "os": platform_info.os_name,
                "version": platform_info.os_version,
                "hostname": platform_info.hostname,
                "is_root": platform_info.is_root,
                "username": platform_info.username,
            },
            "external_tools": tools,
            "config_path": str(self.config_manager.config_path),
            "database_path": str(self.config.database_path),
        }
