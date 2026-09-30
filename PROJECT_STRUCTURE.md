# Complete Project Directory Structure

**Project:** Integrated Secure Data Sanitization & Digital Forensics Platform  
**Version:** 1.0  
**Date:** 2026-09-08  
**Purpose:** Complete directory layout with file descriptions

---

## 1. ROOT DIRECTORY STRUCTURE

```
forensics-platform/
├── README.md
├── ARCHITECTURE.md
├── OPEN_SOURCE_ANALYSIS.md
├── DATABASE_SCHEMA.md
├── PROJECT_STRUCTURE.md
├── DEVELOPMENT_PHASES.md
├── LICENSE
├── THIRD_PARTY.md
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pyproject.toml
├── .gitignore
├── .pylintrc
├── pytest.ini
│
├── docs/
│   ├── USER_MANUAL.md
│   ├── INSTALLATION.md
│   ├── DEVELOPER_GUIDE.md
│   ├── API_REFERENCE.md
│   ├── FORENSIC_WORKFLOW.md
│   ├── SANITIZATION_GUIDE.md
│   ├── SANITIZATION_LIMITATIONS.md
│   ├── TESTING_GUIDE.md
│   ├── SECURITY.md
│   └── images/
│       ├── architecture-diagram.png
│       ├── screenshots/
│       └── workflows/
│
├── src/
│   └── forensics_platform/
│       ├── __init__.py
│       ├── __main__.py
│       ├── version.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── app_controller.py
│       │   ├── config.py
│       │   ├── permissions.py
│       │   ├── job_manager.py
│       │   └── exceptions.py
│       │
│       ├── gui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── dashboard/
│       │   ├── sanitization/
│       │   ├── forensics/
│       │   ├── common/
│       │   └── themes/
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── schema.py
│       │   ├── session.py
│       │   └── migrations/
│       │
│       ├── sanitization/
│       │   ├── __init__.py
│       │   ├── device_detector.py
│       │   ├── device_classifier.py
│       │   ├── sanitizers/
│       │   ├── verification.py
│       │   └── safety_checks.py
│       │
│       ├── file_eraser/
│       │   ├── __init__.py
│       │   ├── file_selector.py
│       │   ├── batch_operations.py
│       │   ├── metadata_handler.py
│       │   ├── deletion_engine.py
│       │   └── verification.py
│       │
│       ├── forensics/
│       │   ├── __init__.py
│       │   ├── case_manager.py
│       │   ├── evidence_manager.py
│       │   ├── image_reader.py
│       │   ├── filesystem_analyzer.py
│       │   ├── deleted_file_analyzer.py
│       │   └── hash_manager.py
│       │
│       ├── carving/
│       │   ├── __init__.py
│       │   ├── signature_database.py
│       │   ├── signature_scanner.py
│       │   ├── structure_validator.py
│       │   ├── fragment_analyzer.py
│       │   ├── reconstruction_engine.py
│       │   ├── file_classifier.py
│       │   ├── confidence_engine.py
│       │   └── validators/
│       │
│       ├── audit/
│       │   ├── __init__.py
│       │   ├── audit_logger.py
│       │   ├── hash_chain.py
│       │   └── integrity_verifier.py
│       │
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── report_generator.py
│       │   ├── pdf_generator.py
│       │   ├── templates/
│       │   └── assets/
│       │
│       ├── external/
│       │   ├── __init__.py
│       │   ├── tool_manager.py
│       │   ├── sleuthkit_wrapper.py
│       │   └── adapters/
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           ├── hashing.py
│           ├── file_utils.py
│           ├── platform_utils.py
│           └── validators.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── data/
│   ├── signatures/
│   ├── config/
│   └── templates/
│
├── scripts/
│   ├── create_test_image.py
│   ├── verify_installation.py
│   └── generate_signature_db.py
│
└── build/
    └── (generated files)
```

---

## 2. FILE DESCRIPTIONS

### 2.1 Root Level Files

#### README.md
```markdown
# Integrated Secure Data Sanitization & Digital Forensics Platform

Academic/research prototype combining secure data sanitization and 
digital forensics capabilities.

## Features
- Secure drive sanitization
- File carving and recovery
- Case management
- Audit logging
- Forensic reporting

## Quick Start
See docs/INSTALLATION.md

## Documentation
- User Manual: docs/USER_MANUAL.md
- Architecture: ARCHITECTURE.md
- Developer Guide: docs/DEVELOPER_GUIDE.md
```

#### requirements.txt
```
PySide6>=6.6.0
SQLAlchemy>=2.0.0
python-magic>=0.4.27
Pillow>=10.0.0
pypdf>=3.17.0
cryptography>=41.0.0
psutil>=5.9.0
```

#### requirements-dev.txt
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-qt>=4.2.0
pylint>=3.0.0
black>=23.0.0
mypy>=1.5.0
sphinx>=7.0.0
```

#### setup.py
```python
from setuptools import setup, find_packages

setup(
    name="forensics-platform",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PySide6>=6.6.0",
        "SQLAlchemy>=2.0.0",
        # ... (from requirements.txt)
    ],
    entry_points={
        "console_scripts": [
            "forensics-platform=forensics_platform.__main__:main",
        ],
    },
)
```

#### .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
build/
dist/
*.egg-info/

# IDEs
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Evidence/Case Data
cases/
evidence/
recovered/

# OS
.DS_Store
Thumbs.db
```

---

### 2.2 Source Code Structure

#### src/forensics_platform/__init__.py
```python
"""
Integrated Secure Data Sanitization & Digital Forensics Platform

An academic/research prototype for secure data operations and forensic analysis.
"""

__version__ = "1.0.0"
__author__ = "Research Team"
__license__ = "MIT"

from .version import VERSION_INFO

__all__ = ['VERSION_INFO', '__version__']
```

#### src/forensics_platform/__main__.py
```python
"""
Main entry point for the application.
"""

import sys
from PySide6.QtWidgets import QApplication
from forensics_platform.core.app_controller import ApplicationController
from forensics_platform.gui.main_window import MainWindow

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Forensics Platform")
    app.setOrganizationName("Research")
    
    # Initialize application controller
    controller = ApplicationController()
    
    # Create and show main window
    window = MainWindow(controller)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

### 2.3 Core Module

```
core/
├── __init__.py
├── app_controller.py      # Central application coordinator
├── config.py              # Configuration management
├── permissions.py         # Permission and privilege handling
├── job_manager.py         # Background job management
└── exceptions.py          # Custom exception hierarchy
```

#### core/app_controller.py
**Purpose:** Central coordinator for all application components
**Key Classes:** `ApplicationController`
**Responsibilities:**
- Initialize all subsystems
- Coordinate between modules
- Manage application lifecycle
- Handle global configuration
- Coordinate shutdown

#### core/config.py
**Purpose:** Configuration management
**Key Classes:** `Config`, `ConfigManager`
**Responsibilities:**
- Load/save configuration
- Validate configuration values
- Provide default values
- Handle configuration updates

#### core/permissions.py
**Purpose:** Permission management and safety checks
**Key Classes:** `PermissionManager`, `PrivilegeLevel`
**Responsibilities:**
- Check user privileges
- Validate destructive operations
- Log permission checks
- Enforce safety policies

#### core/job_manager.py
**Purpose:** Manage background jobs and operations
**Key Classes:** `JobManager`, `Job`, `JobStatus`
**Responsibilities:**
- Queue management
- Progress tracking
- Job cancellation
- Result retrieval
- Thread pool management

#### core/exceptions.py
**Purpose:** Custom exception hierarchy
```python
class ForensicsPlatformException(Exception):
    """Base exception"""

class ConfigurationError(ForensicsPlatformException):
    """Configuration issues"""

class PermissionError(ForensicsPlatformException):
    """Permission/privilege issues"""

class ForensicsException(ForensicsPlatformException):
    """Forensic operation failures"""

class SanitizationException(ForensicsPlatformException):
    """Sanitization operation failures"""

class DatabaseException(ForensicsPlatformException):
    """Database operation failures"""
```

---

### 2.4 GUI Module

```
gui/
├── __init__.py
├── main_window.py          # Main application window
│
├── dashboard/
│   ├── __init__.py
│   ├── dashboard_widget.py
│   ├── case_summary.py
│   ├── operation_status.py
│   └── recent_activity.py
│
├── sanitization/
│   ├── __init__.py
│   ├── drive_eraser_widget.py
│   ├── file_eraser_widget.py
│   ├── device_selector.py
│   ├── confirmation_dialog.py
│   └── progress_widget.py
│
├── forensics/
│   ├── __init__.py
│   ├── case_manager_widget.py
│   ├── evidence_manager_widget.py
│   ├── recovery_widget.py
│   ├── recovered_files_widget.py
│   └── file_viewer.py
│
├── common/
│   ├── __init__.py
│   ├── widgets.py          # Reusable widgets
│   ├── dialogs.py          # Common dialogs
│   ├── tables.py           # Table components
│   ├── styles.py           # Style constants
│   └── icons.py            # Icon resources
│
└── themes/
    ├── __init__.py
    ├── dark_theme.qss
    └── light_theme.qss
```

#### GUI Design Principles
- Non-blocking UI (all I/O in background threads)
- Consistent styling
- Clear visual hierarchy
- Responsive design
- Accessibility support

---

### 2.5 Database Module

```
database/
├── __init__.py
├── models.py              # SQLAlchemy ORM models
├── schema.py              # Raw SQL schema
├── session.py             # Session management
└── migrations/
    ├── __init__.py
    └── v1_initial.py
```

#### database/models.py
**Purpose:** SQLAlchemy ORM models
**Key Classes:** `Case`, `Evidence`, `Operation`, `RecoveredFile`, etc.
**Responsibilities:**
- Define database schema
- Provide ORM interface
- Implement relationships
- Define constraints

#### database/session.py
**Purpose:** Database session management
**Key Classes:** `DatabaseSession`, `SessionManager`
**Responsibilities:**
- Create/manage sessions
- Transaction handling
- Connection pooling
- Error handling

---

### 2.6 Sanitization Module

```
sanitization/
├── __init__.py
├── device_detector.py
├── device_classifier.py
├── sanitizers/
│   ├── __init__.py
│   ├── base_sanitizer.py
│   ├── hdd_sanitizer.py
│   ├── ssd_sanitizer.py
│   ├── nvme_sanitizer.py
│   └── usb_sanitizer.py
├── verification.py
└── safety_checks.py
```

#### sanitization/device_detector.py
**Purpose:** Detect and enumerate storage devices
**Key Classes:** `DeviceDetector`, `DeviceInfo`
**Key Methods:**
- `enumerate_devices()` - List all block devices
- `get_device_info(device_path)` - Detailed device info
- `detect_system_disk()` - Identify OS disk
**Platform Support:** Linux (sysfs, udev)

#### sanitization/device_classifier.py
**Purpose:** Classify device types
**Key Classes:** `DeviceClassifier`, `DeviceType`
**Key Methods:**
- `classify_device(device_info)` - Determine device type
- `check_capabilities(device_info)` - Check hardware features
- `recommend_method(device_type)` - Suggest sanitization method

#### sanitization/sanitizers/base_sanitizer.py
**Purpose:** Base class for all sanitizers
```python
class BaseSanitizer(ABC):
    @abstractmethod
    def sanitize(self, device: DeviceInfo, 
                 progress_callback: Callable) -> SanitizationResult:
        """Perform sanitization"""
    
    @abstractmethod
    def verify(self, device: DeviceInfo) -> VerificationResult:
        """Verify sanitization"""
    
    @abstractmethod
    def get_capabilities(self, device: DeviceInfo) -> Capabilities:
        """Check what this sanitizer can do with this device"""
```

#### sanitization/verification.py
**Purpose:** Post-sanitization verification
**Key Classes:** `VerificationEngine`, `VerificationMethod`
**Key Methods:**
- `verify_full(device)` - Full device verification
- `verify_sampled(device, sample_count)` - Sample-based verification
- `verify_hash(device)` - Hash-based verification

---

### 2.7 File Eraser Module

```
file_eraser/
├── __init__.py
├── file_selector.py
├── batch_operations.py
├── metadata_handler.py
├── deletion_engine.py
└── verification.py
```

#### file_eraser/deletion_engine.py
**Purpose:** Secure file deletion
**Key Classes:** `DeletionEngine`, `DeletionMethod`
**Key Methods:**
- `delete_file(path, method)` - Delete single file
- `delete_directory(path, recursive, method)` - Delete directory
- `overwrite_file(path, passes)` - Overwrite file data

---

### 2.8 Forensics Module

```
forensics/
├── __init__.py
├── case_manager.py
├── evidence_manager.py
├── image_reader.py
├── filesystem_analyzer.py
├── deleted_file_analyzer.py
└── hash_manager.py
```

#### forensics/case_manager.py
**Purpose:** Case lifecycle management
**Key Classes:** `CaseManager`, `Case`
**Key Methods:**
- `create_case(case_info)` - Create new case
- `open_case(case_id)` - Open existing case
- `close_case(case_id)` - Close case
- `add_evidence(case_id, evidence_info)` - Add evidence

#### forensics/evidence_manager.py
**Purpose:** Evidence tracking and integrity
**Key Classes:** `EvidenceManager`, `Evidence`
**Key Methods:**
- `register_evidence(evidence_info)` - Register new evidence
- `calculate_hash(evidence_path)` - Calculate evidence hash
- `verify_integrity(evidence_id)` - Verify evidence integrity
- `get_evidence_info(evidence_id)` - Retrieve evidence metadata

#### forensics/image_reader.py
**Purpose:** Read forensic disk images
**Key Classes:** `ImageReader`, `ImageFormat`
**Supported Formats:**
- Raw (dd)
- Split raw (dd.001, dd.002, ...)
- E01 (via external tool)
**Key Methods:**
- `open_image(path)` - Open disk image
- `read_block(offset, size)` - Read block of data
- `get_image_info()` - Get image metadata

#### forensics/filesystem_analyzer.py
**Purpose:** Filesystem structure analysis
**Key Classes:** `FilesystemAnalyzer`
**Integration:** The Sleuth Kit wrapper
**Key Methods:**
- `analyze_partitions(image)` - Detect partitions
- `analyze_filesystem(image, offset)` - Analyze filesystem
- `list_files(image, path)` - List files
- `get_file_metadata(image, inode)` - Get file metadata

---

### 2.9 Carving Module

```
carving/
├── __init__.py
├── signature_database.py
├── signature_scanner.py
├── structure_validator.py
├── fragment_analyzer.py
├── reconstruction_engine.py
├── file_classifier.py
├── confidence_engine.py
└── validators/
    ├── __init__.py
    ├── base_validator.py
    ├── jpeg_validator.py
    ├── png_validator.py
    ├── pdf_validator.py
    ├── zip_validator.py
    ├── mp3_validator.py
    └── office_validator.py
```

#### carving/signature_database.py
**Purpose:** Manage file signatures
**Key Classes:** `SignatureDatabase`, `FileSignature`
**Key Methods:**
- `load_signatures(directory)` - Load signature definitions
- `get_signature(file_type)` - Get signature for file type
- `register_signature(signature)` - Add new signature
**Storage:** JSON files in `data/signatures/`

#### carving/signature_scanner.py
**Purpose:** Scan for file signatures
**Key Classes:** `SignatureScanner`, `ScanResult`
**Key Methods:**
- `scan_image(image_path, signatures)` - Scan for signatures
- `scan_region(data, signatures)` - Scan data region
**Algorithm:** Aho-Corasick multi-pattern matching

#### carving/structure_validator.py
**Purpose:** Validate file structure
**Key Classes:** `StructureValidator`
**Key Methods:**
- `validate_file(data, file_type)` - Validate structure
- `get_validator(file_type)` - Get appropriate validator

#### carving/confidence_engine.py
**Purpose:** Calculate recovery confidence
**Key Classes:** `ConfidenceEngine`, `ConfidenceScore`
**Scoring Model:**
```python
class ConfidenceScore:
    signature_match: int        # 20 points
    structure_valid: int        # 25 points
    parser_valid: int          # 25 points
    size_consistent: int       # 10 points
    fragment_consistent: int   # 10 points
    additional_checks: int     # 10 points
    total: int                 # Sum (0-100)
    factors: Dict[str, Any]    # Detailed breakdown
```

#### carving/validators/jpeg_validator.py
**Purpose:** JPEG-specific validation
**Key Classes:** `JPEGValidator(BaseValidator)`
**Key Methods:**
- `validate_structure(data)` - Check JPEG structure
- `find_markers(data)` - Find JPEG markers
- `validate_segments(data)` - Validate segment structure
- `estimate_size(data)` - Estimate actual file size

---

### 2.10 Audit Module

```
audit/
├── __init__.py
├── audit_logger.py
├── hash_chain.py
└── integrity_verifier.py
```

#### audit/audit_logger.py
**Purpose:** Tamper-evident audit logging
**Key Classes:** `AuditLogger`, `AuditEvent`
**Key Methods:**
- `log_event(event_type, event_data)` - Log event
- `get_audit_trail(case_id)` - Retrieve audit trail
**Hash Chain:** Each event includes previous event hash

#### audit/hash_chain.py
**Purpose:** Hash chain management
**Key Classes:** `HashChain`
**Key Methods:**
- `add_event(event)` - Add event to chain
- `calculate_hash(event, previous_hash)` - Calculate event hash
- `verify_chain()` - Verify chain integrity

#### audit/integrity_verifier.py
**Purpose:** Verify audit log integrity
**Key Classes:** `IntegrityVerifier`
**Key Methods:**
- `verify_audit_log()` - Verify entire log
- `verify_chain_segment(start_id, end_id)` - Verify segment
- `detect_tampering()` - Detect tampering attempts

---

### 2.11 Reporting Module

```
reporting/
├── __init__.py
├── report_generator.py
├── pdf_generator.py
├── templates/
│   ├── forensic_report.html
│   ├── sanitization_report.html
│   ├── case_summary.html
│   └── audit_report.html
└── assets/
    ├── logo.png
    ├── styles.css
    └── report.css
```

#### reporting/report_generator.py
**Purpose:** Generate forensic reports
**Key Classes:** `ReportGenerator`, `ReportType`
**Key Methods:**
- `generate_forensic_report(case_id, operation_id)` - Forensic report
- `generate_sanitization_report(operation_id)` - Sanitization report
- `generate_case_summary(case_id)` - Case summary
**Output Formats:** HTML, PDF

#### reporting/pdf_generator.py
**Purpose:** Convert HTML reports to PDF
**Key Classes:** `PDFGenerator`
**Technology:** WeasyPrint or ReportLab
**Key Methods:**
- `html_to_pdf(html_path, pdf_path)` - Convert HTML to PDF
- `add_watermark(pdf_path, text)` - Add watermark

---

### 2.12 External Tools Module

```
external/
├── __init__.py
├── tool_manager.py
├── sleuthkit_wrapper.py
└── adapters/
    ├── __init__.py
    └── photorec_adapter.py
```

#### external/tool_manager.py
**Purpose:** Manage external tool availability
**Key Classes:** `ToolManager`, `ExternalTool`
**Key Methods:**
- `check_tool_availability(tool_name)` - Check if tool exists
- `get_tool_version(tool_name)` - Get tool version
- `list_available_tools()` - List all available tools

#### external/sleuthkit_wrapper.py
**Purpose:** The Sleuth Kit integration
**Key Classes:** `SleuthKitWrapper`
**Key Methods:**
- `mmls(image_path)` - Analyze partitions
- `fsstat(image_path, offset)` - Filesystem info
- `fls(image_path, offset, recursive)` - List files
- `icat(image_path, offset, inode, output)` - Extract file
- `tsk_recover(image_path, offset, output_dir)` - Recover files

---

### 2.13 Utils Module

```
utils/
├── __init__.py
├── logging.py
├── hashing.py
├── file_utils.py
├── platform_utils.py
└── validators.py
```

#### utils/hashing.py
**Purpose:** Cryptographic hashing utilities
**Key Functions:**
- `calculate_sha256(file_path)` - SHA-256 hash
- `calculate_md5(file_path)` - MD5 hash
- `calculate_hash_stream(stream, algorithm)` - Hash from stream
- `verify_hash(file_path, expected_hash)` - Verify hash

#### utils/platform_utils.py
**Purpose:** Platform-specific utilities
**Key Functions:**
- `get_platform_info()` - OS information
- `check_privileges()` - Check if running as root/admin
- `get_block_devices()` - List block devices (Linux-specific)

---

## 3. DATA DIRECTORY

```
data/
├── signatures/
│   ├── jpeg.json
│   ├── png.json
│   ├── pdf.json
│   ├── zip.json
│   ├── mp3.json
│   ├── office.json
│   └── README.md
│
├── config/
│   ├── default_config.yaml
│   └── config_schema.json
│
└── templates/
    └── (report templates)
```

### Signature File Example (data/signatures/jpeg.json)

```json
{
  "file_type": "JPEG",
  "mime_type": "image/jpeg",
  "extensions": [".jpg", ".jpeg", ".jpe"],
  "category": "image",
  "description": "JPEG image format",
  
  "signatures": [
    {
      "type": "header",
      "offset": 0,
      "bytes": "FFD8FFE0",
      "mask": "FFFFFFFF",
      "description": "JPEG/JFIF"
    },
    {
      "type": "header",
      "offset": 0,
      "bytes": "FFD8FFE1",
      "mask": "FFFFFFFF",
      "description": "JPEG/EXIF"
    },
    {
      "type": "footer",
      "bytes": "FFD9",
      "match_strategy": "last_occurrence"
    }
  ],
  
  "validation": {
    "validator_class": "JPEGValidator",
    "min_size": 100,
    "max_size": 104857600,
    "required_markers": ["FFD8", "FFD9"],
    "structural_check": true
  },
  
  "metadata": {
    "specification": "ITU-T T.81, ISO/IEC 10918-1",
    "reference_url": "https://www.w3.org/Graphics/JPEG/",
    "added_date": "2026-09-08",
    "tested": true
  }
}
```

---

## 4. TEST DIRECTORY

```
tests/
├── __init__.py
├── conftest.py            # Pytest configuration
│
├── fixtures/
│   ├── __init__.py
│   ├── disk_images/
│   │   ├── small_test.dd
│   │   ├── ntfs_test.dd
│   │   └── README.md
│   ├── files/
│   │   ├── valid/
│   │   │   ├── test.jpg
│   │   │   ├── test.png
│   │   │   └── test.pdf
│   │   ├── corrupted/
│   │   └── fragments/
│   └── databases/
│       └── test_db.sqlite
│
├── unit/
│   ├── __init__.py
│   ├── test_hashing.py
│   ├── test_signature_scanner.py
│   ├── test_validators.py
│   ├── test_confidence_engine.py
│   ├── test_hash_chain.py
│   └── test_database_models.py
│
├── integration/
│   ├── __init__.py
│   ├── test_case_workflow.py
│   ├── test_carving_workflow.py
│   ├── test_sanitization_workflow.py
│   └── test_reporting.py
│
└── e2e/
    ├── __init__.py
    ├── test_forensic_analysis.py
    └── test_complete_workflow.py
```

---

## 5. SCRIPTS DIRECTORY

```
scripts/
├── create_test_image.py      # Create test disk images
├── verify_installation.py    # Verify all dependencies
├── generate_signature_db.py  # Generate signature database
├── benchmark_carving.py      # Benchmark carving performance
└── setup_dev_environment.sh  # Setup development environment
```

---

## 6. BUILD ARTIFACTS

```
build/
├── lib/
├── bdist/
└── exe/               # PyInstaller output

dist/
└── forensics-platform-1.0.0.tar.gz
```

---

## 7. USER DATA DIRECTORIES

**Not in repository - created at runtime:**

```
~/.local/share/forensics-platform/
├── config.yaml
├── forensics.db
├── logs/
│   ├── application.log
│   ├── audit.log
│   └── operations/
├── cases/
│   ├── CASE-2026-001/
│   │   ├── evidence/
│   │   ├── recovered/
│   │   ├── reports/
│   │   └── metadata.json
│   └── CASE-2026-002/
└── temp/
```

---

## 8. CONFIGURATION FILES

### pyproject.toml
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "forensics-platform"
version = "1.0.0"
description = "Integrated Secure Data Sanitization & Digital Forensics Platform"
authors = [{name = "Research Team"}]
license = {text = "MIT"}
requires-python = ">=3.12"

[tool.black]
line-length = 100
target-version = ['py312']

[tool.pylint]
max-line-length = 100
disable = ["C0111"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

---

## 9. FILE COUNT SUMMARY

| Directory | Purpose | Estimated Files |
|-----------|---------|-----------------|
| src/core | Application core | 6 files |
| src/gui | User interface | 30+ files |
| src/database | Data layer | 5 files |
| src/sanitization | Sanitization engine | 10 files |
| src/file_eraser | File deletion | 6 files |
| src/forensics | Forensic engine | 7 files |
| src/carving | File carving | 15 files |
| src/audit | Audit logging | 4 files |
| src/reporting | Report generation | 6 files |
| src/external | External tools | 5 files |
| src/utils | Utilities | 6 files |
| tests | Test suite | 30+ files |
| data | Configuration/data | 15+ files |
| docs | Documentation | 10+ files |
| **Total** | | **150-200 files** |

---

## 10. IMPLEMENTATION PRIORITY

### Phase 1: Foundation
1. Project structure
2. Core module
3. Database module
4. Utils module

### Phase 2: GUI Shell
5. Main window
6. Dashboard
7. Common widgets

### Phase 3: Forensics
8. Case/evidence management
9. Filesystem analysis
10. Carving engine

### Phase 4: Sanitization
11. Device detection
12. Sanitizers
13. Verification

### Phase 5: Completion
14. Reporting
15. Audit system
16. Testing
17. Documentation

---

**END OF PROJECT STRUCTURE DOCUMENT**
