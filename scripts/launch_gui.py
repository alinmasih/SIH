#!/usr/bin/env python3
"""
Launch the Forensics Platform GUI.

This script can be run directly to start the application.
"""

import sys
import os

# Add src to path if running from scripts directory
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_dir = os.path.join(project_root, "venv")
    venv_python = os.path.join(venv_dir, "bin", "python3")

    # If running with system python without activating venv, auto-switch to project venv
    if os.path.exists(venv_python) and sys.prefix != venv_dir:
        os.execv(venv_python, [venv_python] + sys.argv)

    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Import and run
    from forensics_platform.__main__ import main
    sys.exit(main())
