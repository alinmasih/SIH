"""
Main application entry point.

Launches the GUI application.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from forensics_platform.core import ApplicationController
from forensics_platform.gui.main_window import MainWindow
from forensics_platform.utils.logging import setup_logging, get_logger
from forensics_platform.version import get_version_string


def main():
    """Main entry point for the application"""

    # Initialize application
    app = QApplication(sys.argv)
    app.setApplicationName("Forensics Platform")
    app.setOrganizationName("Research")
    app.setApplicationVersion(get_version_string())

    # High DPI scaling is enabled by default in Qt 6

    try:
        # Initialize application controller
        controller = ApplicationController()

        # Setup logging
        setup_logging(
            log_dir=controller.config.log_dir,
            log_level=controller.config.log_level
        )

        logger = get_logger(__name__)
        logger.info("=" * 80)
        logger.info(f"Starting Forensics Platform {controller.version}")
        logger.info(f"Simulation Mode: {controller.is_simulation_mode}")
        logger.info("=" * 80)

        # Create and show main window
        window = MainWindow(controller)
        window.show()

        # Run application
        exit_code = app.exec()

        # Cleanup
        logger.info("Application shutting down")
        controller.shutdown()

        return exit_code

    except Exception as e:
        print(f"Fatal error starting application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
