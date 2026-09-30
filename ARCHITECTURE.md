# Integrated Secure Data Sanitization & Digital Forensics Platform
## System Architecture Document

**Version:** 1.0  
**Date:** 2026-09-08  
**Status:** Design Phase

---

## 1. EXECUTIVE SUMMARY

This document describes the architecture of an academic/research prototype that integrates secure data sanitization and digital forensics capabilities into a unified desktop application. The platform is designed with modularity, safety, and extensibility as core principles.

### Key Capabilities

**Sanitization Domain:**
- Secure drive erasure with device-specific strategies
- File and folder secure deletion
- Verification and audit logging
- Sanitization reporting

**Forensic Domain:**
- Evidence and case management
- Disk image analysis
- Deleted file recovery
- Advanced signature-based file carving
- Structure validation and confidence scoring
- Forensic reporting

### Design Principles

1. **Safety First:** All destructive operations require explicit confirmation
2. **Modular Architecture:** Each component is independently testable
3. **Evidence Integrity:** Original evidence is never modified
4. **Transparency:** All limitations are clearly documented
5. **Auditability:** Tamper-evident logging of all operations
6. **Extensibility:** Plugin architecture for file signatures and validators

---

## 2. SYSTEM OVERVIEW

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │ Sanitization │  │  Forensics   │      │
│  │     GUI      │  │     GUI      │  │     GUI      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Application Controller & Core                │ │
│  │  • Configuration  • Permissions  • Job Manager         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                       Business Logic Layer                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Sanitization │  │  Forensics   │  │   Carving    │      │
│  │    Engine    │  │    Engine    │  │    Engine    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ File Eraser  │  │    Audit     │  │   Reporting  │      │
│  │    Engine    │  │    Engine    │  │    Engine    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │    SQLite      │  │  Signature DB  │  │  Audit Log   │  │
│  │   Database     │  │   (JSON/DB)    │  │   (Chain)    │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Filesystem  │  │ Block Devices│  │  External    │      │
│  │   Access     │  │    Access    │  │    Tools     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Architecture

```
src/
├── gui/                        # Presentation Layer
│   ├── main_window.py
│   ├── dashboard/
│   ├── sanitization/
│   ├── forensics/
│   ├── common/
│   └── themes/
│
├── core/                       # Application Core
│   ├── app_controller.py
│   ├── config.py
│   ├── permissions.py
│   ├── job_manager.py
│   └── exceptions.py
│
├── sanitization/               # Sanitization Domain
│   ├── device_detector.py
│   ├── device_classifier.py
│   ├── sanitizers/
│   │   ├── base_sanitizer.py
│   │   ├── hdd_sanitizer.py
│   │   ├── ssd_sanitizer.py
│   │   └── usb_sanitizer.py
│   ├── verification.py
│   └── safety_checks.py
│
├── file_eraser/                # File/Folder Deletion
│   ├── file_selector.py
│   ├── batch_operations.py
│   ├── metadata_handler.py
│   ├── deletion_engine.py
│   └── verification.py
│
├── forensics/                  # Forensics Domain
│   ├── case_manager.py
│   ├── evidence_manager.py
│   ├── image_reader.py
│   ├── filesystem_analyzer.py
│   ├── deleted_file_analyzer.py
│   └── hash_manager.py
│
├── carving/                    # File Carving Engine
│   ├── signature_database.py
│   ├── signature_scanner.py
│   ├── structure_validator.py
│   ├── fragment_analyzer.py
│   ├── reconstruction_engine.py
│   ├── file_classifier.py
│   ├── confidence_engine.py
│   └── validators/
│       ├── base_validator.py
│       ├── jpeg_validator.py
│       ├── png_validator.py
│       ├── pdf_validator.py
│       └── ... (extensible)
│
├── audit/                      # Audit & Integrity
│   ├── audit_logger.py
│   ├── hash_chain.py
│   └── integrity_verifier.py
│
├── reporting/                  # Report Generation
│   ├── report_generator.py
│   ├── templates/
│   │   ├── forensic_report.html
│   │   └── sanitization_report.html
│   └── pdf_generator.py
│
├── database/                   # Data Layer
│   ├── models.py
│   ├── schema.py
│   └── migrations/
│
├── external/                   # External Tool Integration
│   ├── sleuthkit_wrapper.py
│   ├── tool_manager.py
│   └── adapters/
│
└── utils/                      # Utilities
    ├── logging.py
    ├── hashing.py
    ├── file_utils.py
    └── platform_utils.py
```

---

## 3. DETAILED COMPONENT DESIGN

### 3.1 Presentation Layer (GUI)

**Technology:** PySide6 (Qt for Python)

**Components:**

#### Main Window
- Central application window
- Navigation sidebar
- Status bar with operation progress
- Dark/light theme support

#### Dashboard
- Active cases overview
- Recent operations summary
- Quick access to common tasks
- System status indicators

#### Sanitization GUI
- Device selection and information display
- Sanitization method configuration
- Safety warnings and confirmations
- Progress monitoring
- Verification results

#### Forensics GUI
- Case management interface
- Evidence registration
- Analysis configuration
- Recovery results browser
- File preview capabilities

#### Common Components
- Progress dialogs with cancellation
- Confirmation dialogs for destructive operations
- Log viewer
- Report viewer
- Settings dialog

**Key Design Decisions:**

1. **Non-blocking Operations:** All long-running tasks use QThread or QThreadPool
2. **Responsive UI:** Progress updates every 100ms minimum
3. **Safety Confirmations:** Multi-step confirmation for destructive operations
4. **Accessibility:** Full keyboard navigation, screen reader compatible
5. **Theming:** Material-inspired design with professional forensic aesthetic

---

### 3.2 Application Core

#### Application Controller
- Application lifecycle management
- Module initialization and dependency injection
- Global exception handling
- Shutdown coordination

#### Configuration Manager
- YAML/JSON configuration files
- User preferences
- System capabilities detection
- Per-case configuration

#### Permissions System
- Privilege validation
- Safety checks before destructive operations
- Audit logging of permission checks

#### Job Manager
- Asynchronous job execution
- Progress tracking
- Job cancellation
- Job history and recovery

---

### 3.3 Sanitization Engine

#### Device Detector
```python
class DeviceInfo:
    path: str
    model: str
    serial: str
    capacity: int
    device_type: DeviceType  # HDD, SSD, USB, NVMe, etc.
    connection_type: ConnectionType  # SATA, USB, NVMe, etc.
    removable: bool
    system_disk: bool
    partitions: List[PartitionInfo]
```

**Responsibilities:**
- Enumerate block devices
- Query device information via sysfs/udev
- Detect system disk status
- Identify removable media

#### Device Classifier
- Classify device type (HDD/SSD/NVMe/USB)
- Determine appropriate sanitization strategies
- Check for hardware security features (ATA Secure Erase, NVMe Format)

#### Sanitizers

**Base Sanitizer Interface:**
```python
class BaseSanitizer(ABC):
    @abstractmethod
    def sanitize(self, device: DeviceInfo, 
                 progress_callback: Callable) -> SanitizationResult
    
    @abstractmethod
    def verify(self, device: DeviceInfo) -> VerificationResult
    
    @abstractmethod
    def get_capabilities(self, device: DeviceInfo) -> SanitizerCapabilities
```

**HDD Sanitizer:**
- Multiple overwrite passes (configurable)
- Pattern-based overwriting
- Random data overwriting
- NIST SP 800-88 compliant methods

**SSD Sanitizer:**
- ATA Secure Erase detection and execution
- NVMe Format/Sanitize commands
- Cryptographic erase where supported
- Clear limitation documentation when hardware features unavailable

**USB Sanitizer:**
- Device-appropriate strategies
- Removable media handling

#### Verification Engine
- Post-sanitization verification
- Random sampling verification
- Full device verification (time-intensive)
- Verification report generation

#### Safety Checks
- System disk detection and warning
- Mounted filesystem detection
- Active partition detection
- User confirmation requirements

---

### 3.4 File Eraser Engine

#### File Selector
- Single file selection
- Directory tree selection
- Batch file selection
- Size and impact preview

#### Batch Operations
- Parallel processing
- Progress tracking
- Error handling per-file
- Rollback on critical errors

#### Metadata Handler
- Filename obfuscation
- Timestamp manipulation where supported
- Extended attribute handling
- Filesystem-specific metadata

#### Deletion Engine
- Secure overwrite (with limitations documented)
- Multiple pass overwrite
- Filesystem API-based deletion
- Verification

---

### 3.5 Forensics Engine

#### Case Manager
```python
class Case:
    id: int
    case_number: str
    title: str
    investigator: str
    description: str
    created_at: datetime
    updated_at: datetime
    status: CaseStatus
```

**Responsibilities:**
- Create/open/close cases
- Case metadata management
- Case-evidence relationships
- Case audit trail

#### Evidence Manager
```python
class Evidence:
    id: int
    case_id: int
    evidence_number: str
    source_type: SourceType
    device_model: str
    device_serial: str
    capacity: int
    source_path: str
    image_path: str
    acquisition_time: datetime
    sha256: str
    notes: str
```

**Responsibilities:**
- Evidence registration
- Hash calculation and verification
- Evidence metadata storage
- Chain of custody tracking

#### Image Reader
- Raw image format support
- E01 format support (via external tools)
- AFF format support (via external tools)
- Split image handling
- Read-only access enforcement

#### Filesystem Analyzer
- Partition table parsing
- Filesystem metadata extraction
- Directory structure recovery
- Deleted entry identification

#### Deleted File Analyzer
- Unallocated space identification
- Deleted inode recovery
- File metadata reconstruction
- Timestamp preservation

---

### 3.6 Carving Engine

This is the most complex subsystem, designed for extensibility and accuracy.

#### Architecture

```
Raw Image → Block Reader → Signature Scanner → Candidate Detection
                                                        ↓
Recovered File ← Classification ← Validation ← Structure Analysis
                        ↓
                 Confidence Score
```

#### Signature Database

**Storage Format:** JSON-based registry

```json
{
  "file_type": "JPEG",
  "mime_type": "image/jpeg",
  "extensions": [".jpg", ".jpeg"],
  "signatures": [
    {
      "type": "header",
      "offset": 0,
      "bytes": "FFD8FF",
      "mask": "FFFFFF"
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
    "structural_markers": ["FFD8", "FFDB", "FFD9"]
  }
}
```

**Initial Support:**
- JPEG
- PNG
- PDF
- ZIP
- DOCX/XLSX (as ZIP variants)
- MP3
- GIF
- BMP
- MP4

**Extensibility:**
- New signatures via JSON configuration
- Custom validators via plugin system

#### Signature Scanner
- Sliding window search
- Multi-pattern matching (Aho-Corasick algorithm)
- Efficient binary searching
- Offset tracking

#### Structure Validator

**Per-format validators:**

```python
class FileValidator(ABC):
    @abstractmethod
    def validate_structure(self, data: bytes) -> ValidationResult
    
    @abstractmethod
    def estimate_actual_size(self, data: bytes) -> Optional[int]
    
    @abstractmethod
    def check_integrity(self, data: bytes) -> IntegrityResult
```

**JPEG Validator Example:**
- Verify JPEG markers (SOI, SOF, SOS, EOI)
- Check segment structure
- Validate quantization tables
- Verify scan data

**PNG Validator Example:**
- Verify PNG signature
- Check chunk CRCs
- Validate IHDR chunk
- Verify chunk sequence

#### Fragment Analyzer
- Detect fragmentation indicators
- Identify fragment boundaries
- Match fragment patterns
- Estimate missing data

#### Reconstruction Engine
- Ordered fragment assembly
- Gap detection and reporting
- Partial file reconstruction
- Reconstruction validation

#### File Classifier
- Signature-based classification
- Magic number detection
- MIME type determination
- Extension inference (secondary)

#### Confidence Engine

**Scoring Model:**

```python
class ConfidenceScore:
    signature_match: int        # 0-20 points
    structure_valid: int        # 0-25 points
    parser_valid: int          # 0-25 points
    size_consistent: int       # 0-10 points
    fragment_consistent: int   # 0-10 points
    additional_checks: int     # 0-10 points
    total: int                 # 0-100
    
    factors: Dict[str, Any]    # Detailed breakdown
```

**Scoring Rules:**
- Signature match: Binary (20 or 0)
- Structure validation: Graduated based on validation depth
- Parser validation: Binary per parser
- Size consistency: Graduated based on expected vs actual
- Fragment consistency: Based on reconstruction quality

**Confidence Levels:**
- 90-100: High confidence
- 70-89: Medium confidence
- 50-69: Low confidence
- 0-49: Very low confidence / likely corrupt

---

### 3.7 Audit Engine

#### Hash Chain Architecture

```python
class AuditEvent:
    id: int
    timestamp: datetime
    user: str
    event_type: EventType
    case_id: Optional[int]
    operation_id: Optional[int]
    event_data: Dict[str, Any]
    previous_hash: str
    event_hash: str
```

**Hash Calculation:**
```
event_hash = SHA256(
    timestamp +
    user +
    event_type +
    event_data_json +
    previous_hash
)
```

**Chain Verification:**
- Start from genesis event
- Recompute each hash
- Verify chain integrity
- Detect tampering

#### Audit Logger
- Synchronous logging (cannot be skipped)
- Automatic chain maintenance
- Periodic integrity verification
- Export capability

---

### 3.8 Reporting Engine

#### Report Types

**Forensic Recovery Report:**
- Executive summary
- Case information
- Evidence details
- Acquisition metadata
- Analysis methodology
- Results summary
- Recovered file catalog
- Individual file details
- Confidence scores
- Validation results
- Tool versions
- Limitations statement
- Audit hash
- Signature

**Sanitization Report:**
- Executive summary
- Device information
- Sanitization method
- Verification method
- Verification results
- Timeline
- Tool versions
- Limitations statement
- Audit hash
- Signature

#### Report Generator
- Template-based generation
- HTML primary format
- PDF export capability
- Embedded evidence hashes
- Embedded audit chain proof

---

## 4. DATA LAYER

### 4.1 Database Schema

**Entity Relationship Diagram:**

```
Cases (1) ──< (N) Evidence
  │
  └──< (N) Operations
           │
           ├──< (N) RecoveredFiles
           │
           └──< (N) SanitizationOperations

Cases (1) ──< (N) Reports

Operations (1) ──< (N) AuditEvents
```

### 4.2 Complete Schema

```sql
-- Cases table
CREATE TABLE cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    investigator TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('active', 'closed', 'archived')) DEFAULT 'active'
);

-- Evidence table
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    evidence_number TEXT NOT NULL,
    source_type TEXT CHECK(source_type IN ('physical_device', 'disk_image', 'logical_files', 'network_capture')),
    device_model TEXT,
    device_serial TEXT,
    capacity INTEGER,
    source_path TEXT,
    image_path TEXT,
    acquisition_time TIMESTAMP,
    sha256 TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    UNIQUE(case_id, evidence_number)
);

-- Operations table
CREATE TABLE operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    operation_type TEXT CHECK(operation_type IN (
        'forensic_analysis', 
        'file_carving', 
        'drive_sanitization', 
        'file_deletion'
    )) NOT NULL,
    target TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT CHECK(status IN ('running', 'completed', 'failed', 'cancelled')) DEFAULT 'running',
    tool_version TEXT NOT NULL,
    parameters TEXT,  -- JSON
    result TEXT,      -- JSON
    error_message TEXT,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
);

-- Recovered files table
CREATE TABLE recovered_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    detected_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    offset INTEGER NOT NULL,
    validation_status TEXT CHECK(validation_status IN (
        'valid', 'partial', 'invalid', 'unknown'
    )) DEFAULT 'unknown',
    confidence_score INTEGER CHECK(confidence_score >= 0 AND confidence_score <= 100),
    confidence_details TEXT,  -- JSON
    sha256 TEXT,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

-- Sanitization operations table
CREATE TABLE sanitization_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL,
    device TEXT NOT NULL,
    device_type TEXT CHECK(device_type IN ('hdd', 'ssd', 'nvme', 'usb', 'other')),
    device_model TEXT,
    device_serial TEXT,
    capacity INTEGER,
    sanitization_method TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    verification_result TEXT CHECK(verification_result IN ('pass', 'fail', 'partial', 'skipped')),
    verification_details TEXT,  -- JSON
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE,
    UNIQUE(operation_id)
);

-- Audit events table
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user TEXT NOT NULL,
    event_type TEXT NOT NULL,
    case_id INTEGER,
    operation_id INTEGER,
    event_data TEXT NOT NULL,  -- JSON
    previous_hash TEXT,
    event_hash TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE SET NULL
);

-- Reports table
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    operation_id INTEGER,
    report_type TEXT CHECK(report_type IN ('forensic', 'sanitization', 'audit')) NOT NULL,
    file_path TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_hash TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_evidence_case ON evidence(case_id);
CREATE INDEX idx_operations_case ON operations(case_id);
CREATE INDEX idx_operations_type ON operations(operation_type);
CREATE INDEX idx_recovered_files_operation ON recovered_files(operation_id);
CREATE INDEX idx_recovered_files_type ON recovered_files(detected_type);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_events_case ON audit_events(case_id);
CREATE INDEX idx_reports_case ON reports(case_id);
```

---

## 5. EXTERNAL INTEGRATIONS

### 5.1 Integration Strategy

We use a **wrapper pattern** to isolate external dependencies:

```python
class ExternalTool(ABC):
    @abstractmethod
    def check_availability(self) -> bool
    
    @abstractmethod
    def get_version(self) -> str
    
    @abstractmethod
    def execute(self, args: List[str]) -> ToolResult
```

### 5.2 The Sleuth Kit Integration

**Purpose:** Filesystem analysis, deleted file recovery

**Integration Method:** Command-line wrapper

**Key Commands:**
- `mmls` - Partition analysis
- `fsstat` - Filesystem information
- `fls` - File listing including deleted files
- `icat` - File content extraction
- `tsk_recover` - Bulk file recovery

**Wrapper Class:**
```python
class SleuthKitWrapper(ExternalTool):
    def analyze_filesystem(self, image_path: str, offset: int) -> FilesystemInfo
    def list_files(self, image_path: str, recursive: bool) -> List[FileEntry]
    def extract_file(self, image_path: str, inode: int, output_path: str)
    def recover_deleted(self, image_path: str, output_dir: str)
```

### 5.3 PhotoRec/Scalpel Integration (Optional)

**Purpose:** Benchmark against established carving tools

**Integration Method:** Command-line execution

**Usage:** Comparison and validation of our carving engine

### 5.4 libmagic Integration

**Purpose:** File type identification

**Integration Method:** Python binding (python-magic)

**Usage:**
- Secondary file type verification
- MIME type detection
- File classification

---

## 6. CROSS-CUTTING CONCERNS

### 6.1 Error Handling

**Strategy:**
- Custom exception hierarchy
- Exception logging with context
- User-friendly error messages
- Technical details in logs
- Graceful degradation where possible

```python
class ForensicsException(Exception): pass
class EvidenceIntegrityError(ForensicsException): pass
class CarvingError(ForensicsException): pass
class SanitizationError(ForensicsException): pass
class DeviceAccessError(SanitizationError): pass
```

### 6.2 Logging

**Multi-level logging:**
1. **Application Log** - Standard Python logging
2. **Audit Log** - Hash-chained tamper-evident log
3. **Operation Log** - Per-operation detailed log
4. **Debug Log** - Verbose debugging information

### 6.3 Security Considerations

1. **Privilege Management:**
   - Minimum necessary privileges
   - Explicit privilege escalation for device access
   - Privilege audit logging

2. **Input Validation:**
   - Device path validation
   - File path validation
   - SQL injection prevention (parameterized queries)
   - Command injection prevention (no shell=True)

3. **Data Protection:**
   - Sensitive data clearing from memory
   - Secure temporary file handling
   - Evidence data access controls

### 6.4 Performance Optimization

1. **Carving Engine:**
   - Chunked reading (1MB chunks)
   - Multi-threaded scanning where safe
   - Efficient pattern matching algorithms
   - Progress checkpointing for resume

2. **Database:**
   - Proper indexing
   - Batch operations for bulk inserts
   - Connection pooling

3. **GUI:**
   - Lazy loading for large result sets
   - Virtual scrolling for tables
   - Background processing for all I/O

---

## 7. TECHNOLOGY JUSTIFICATION

### Python 3.12+
- **Pros:** Rich ecosystem, rapid development, excellent forensics libraries
- **Cons:** Performance compared to C/C++ (mitigated by native extensions)
- **Verdict:** Appropriate for prototype, extensible, maintainable

### PySide6 (Qt)
- **Pros:** Professional desktop UI, cross-platform, mature, excellent documentation
- **Cons:** Large dependency, learning curve
- **Verdict:** Industry standard for forensics applications (Autopsy uses similar)

### SQLite
- **Pros:** Zero configuration, file-based, ACID compliant, widely supported
- **Cons:** Not suitable for multi-user (not required for this application)
- **Verdict:** Perfect for single-user forensic workstation

### SQLAlchemy (Optional)
- **Pros:** ORM abstraction, migration support, database independence
- **Cons:** Additional complexity, slight performance overhead
- **Verdict:** Recommended for cleaner code and maintainability

---

## 8. DEPLOYMENT ARCHITECTURE

### Development Environment
```
Linux (Ubuntu 22.04+ / Debian 12+)
Python 3.12+
PySide6 6.x
Virtual environment (venv)
Development tools: pytest, pylint, black
```

### Production Package
```
PyInstaller single executable (future)
Configuration directory: ~/.local/share/forensics-platform/
Database location: ~/.local/share/forensics-platform/data/
Log directory: ~/.local/share/forensics-platform/logs/
Signature database: ~/.local/share/forensics-platform/signatures/
```

### System Requirements
```
Minimum:
- Linux kernel 5.x+
- 4GB RAM
- 100GB free disk space
- Root/sudo access for device operations

Recommended:
- 8GB+ RAM
- SSD for application
- Separate storage for evidence
- Dedicated forensic workstation
```

---

## 9. SAFETY ARCHITECTURE

### Destructive Operation Safety

**Multi-layer protection:**

```
User Intent
    ↓
Safety Check #1: Operation Classification
    ↓
Safety Check #2: Target Validation
    ↓
Safety Check #3: System Disk Detection
    ↓
Safety Check #4: Mount Status Check
    ↓
Confirmation Dialog #1: Information Display
    ↓
Confirmation Dialog #2: Explicit Device Entry
    ↓
Confirmation Dialog #3: Final Warning
    ↓
Audit Log Entry
    ↓
Operation Execution
    ↓
Verification
    ↓
Audit Log Entry
```

### Development Safety

**Simulation Mode:**
- All destructive operations default to DRY_RUN = True
- Explicit configuration flag to enable real operations
- Simulation mode logs all operations without execution
- Testing against virtual devices

---

## 10. EXTENSIBILITY POINTS

### Plugin Architecture

1. **File Type Plugins:**
   - New signature definitions (JSON)
   - Custom validators (Python classes)
   - Registration via plugin directory

2. **Sanitization Method Plugins:**
   - Custom sanitization strategies
   - Device-specific handlers

3. **Report Templates:**
   - Custom HTML templates
   - Additional report formats

4. **External Tool Adapters:**
   - New forensic tool integrations
   - Custom analysis scripts

---

## 11. LIMITATIONS AND CONSTRAINTS

### Documented Limitations

1. **SSD Sanitization:**
   - Overwrite methods are insufficient for SSD flash
   - Requires hardware-specific secure erase
   - Depends on firmware implementation
   - Some SSDs may not support secure erase

2. **File Recovery:**
   - No recovery is guaranteed
   - Fragmented files may be incomplete
   - Overwritten data cannot be recovered
   - TRIM/discard operations prevent recovery on SSDs

3. **File Carving:**
   - Signature-based only (no AI/ML classification)
   - Limited format support initially
   - Fragmentation reduces success rate
   - Corrupted files may not be recoverable

4. **Filesystem Support:**
   - Depends on The Sleuth Kit capabilities
   - Some filesystems better supported than others

5. **Platform Support:**
   - Linux primary, Windows future
   - Block device access requires privileges

---

## 12. TESTING STRATEGY

### Test Pyramid

```
                 E2E Tests
              (10 tests, slow)
           ────────────────
          Integration Tests
         (100 tests, medium)
       ────────────────────
      Unit Tests
   (1000 tests, fast)
 ────────────────────
```

### Test Coverage Goals

- Unit tests: 80%+ coverage
- Integration tests: Critical paths
- E2E tests: Main workflows

### Test Data

```
tests/
├── fixtures/
│   ├── disk_images/
│   │   ├── small_image.dd       (10MB)
│   │   ├── medium_image.dd      (100MB)
│   │   ├── fragmented_image.dd
│   │   └── corrupted_image.dd
│   ├── files/
│   │   ├── valid/
│   │   ├── corrupted/
│   │   └── fragments/
│   └── databases/
└── mocks/
```

---

## 13. DEVELOPMENT PHASES

Detailed in separate PROJECT_PHASES document.

**Summary:**
1. Foundation (Weeks 1-2)
2. Database & Core (Week 3)
3. GUI Shell (Week 4)
4. Forensics Engine (Weeks 5-7)
5. Carving Engine (Weeks 8-10)
6. Sanitization Engine (Weeks 11-13)
7. Reporting & Audit (Week 14)
8. Testing & Documentation (Week 15)
9. Integration & Polish (Week 16)

---

## 14. SUCCESS CRITERIA

### Functional Requirements
✓ Create and manage forensic cases
✓ Register and hash evidence
✓ Analyze disk images
✓ Recover deleted files
✓ Carve files using signatures
✓ Validate recovered files
✓ Score recovery confidence
✓ Sanitize drives safely
✓ Delete files securely
✓ Generate reports
✓ Maintain audit trail
✓ Verify audit integrity

### Non-Functional Requirements
✓ Professional GUI
✓ Responsive performance
✓ Safety mechanisms working
✓ Comprehensive documentation
✓ Test coverage >80%
✓ All limitations documented

---

## 15. RISK ANALYSIS

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data loss due to bugs | Medium | Critical | Extensive testing, simulation mode, explicit confirmations |
| Poor carving accuracy | Medium | Medium | Benchmark against established tools, validation engine |
| Performance issues | Low | Medium | Profiling, optimization, chunked processing |
| External tool dependency failures | Low | Medium | Graceful degradation, error handling |
| Platform compatibility issues | Low | Low | Test on multiple distributions |

### Project Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope creep | High | High | Clear phase boundaries, MVP focus |
| Over-engineering | Medium | Medium | Iterative development, regular reviews |
| Documentation lag | Medium | Low | Documentation as development proceeds |

---

## APPENDICES

### A. Glossary

**Carving:** Recovery of files from raw data without filesystem metadata
**Sanitization:** Secure deletion preventing data recovery
**Evidence Integrity:** Ensuring evidence has not been modified
**Chain of Custody:** Documentation of evidence handling
**Signature:** Unique byte pattern identifying file type
**Confidence Score:** Metric indicating recovery quality
**Audit Chain:** Tamper-evident log using hash linking

### B. References

- NIST SP 800-88 Rev. 1
- The Sleuth Kit documentation
- Autopsy documentation
- PhotoRec documentation
- Digital Forensics Wikipedia
- Linux kernel block device documentation

### C. Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-08 | System | Initial architecture document |

---

**END OF ARCHITECTURE DOCUMENT**
