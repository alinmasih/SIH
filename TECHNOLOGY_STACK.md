# Technology Stack & API Design

**Project:** Integrated Secure Data Sanitization & Digital Forensics Platform  
**Version:** 1.0  
**Date:** 2026-09-08  
**Purpose:** Technology decisions, API design, and interface specifications

---

## 1. TECHNOLOGY STACK JUSTIFICATION

### 1.1 Python 3.12+

**Selected:** ✓  
**Rationale:**

**Strengths:**
- Rich forensics ecosystem (pytsk3, python-magic, Pillow)
- Rapid development and prototyping
- Excellent for academic/research projects
- Strong support for data processing
- Cross-platform compatibility
- Large community and documentation
- Easy integration with external tools

**Weaknesses:**
- Performance vs. C/C++ (mitigated by native extensions)
- GIL for CPU-bound tasks (mitigated by multiprocessing)
- Packaging complexity (mitigated by PyInstaller)

**Performance Mitigation:**
- Use native libraries where available (pytsk3, Pillow)
- Chunked processing for large files
- Multiprocessing for parallel operations
- Efficient algorithms (Aho-Corasick for pattern matching)

**Verdict:** ✓ **APPROVED** - Ideal for academic prototype

---

### 1.2 PySide6 (Qt for Python)

**Selected:** ✓  
**Rationale:**

**Strengths:**
- Professional desktop UI framework
- Native look and feel
- Excellent widget library
- Mature and stable
- Cross-platform (Linux, Windows, macOS)
- Strong threading support (QThread)
- Used by professional forensic tools
- LGPL license compatible with commercial use

**Alternatives Considered:**
- **Tkinter:** Too basic for professional application
- **PyQt6:** GPL license more restrictive
- **Kivy:** Better for mobile, less professional on desktop
- **Web-based (Electron):** Overhead, not suitable for forensics

**Verdict:** ✓ **APPROVED** - Industry standard for forensic apps

---

### 1.3 SQLite

**Selected:** ✓  
**Rationale:**

**Strengths:**
- Zero configuration
- File-based (portable)
- ACID compliant
- Fast for single-user
- Excellent Python support
- No server required
- Backup = file copy
- Suitable for forensic case files

**Weaknesses:**
- Not suitable for concurrent writes (not needed for our use case)
- No network access (not needed)

**Alternatives Considered:**
- **PostgreSQL:** Overkill, requires server
- **MySQL:** Overkill, requires server
- **JSON files:** No ACID, no querying

**Verdict:** ✓ **APPROVED** - Perfect for single-user forensic workstation

---

### 1.4 SQLAlchemy

**Selected:** ✓  
**Rationale:**

**Strengths:**
- ORM abstraction
- Database independence
- Migration support
- Query building
- Relationship management
- Type safety with Python type hints

**Weaknesses:**
- Learning curve
- Slight performance overhead (negligible for our use case)

**Alternatives Considered:**
- **Raw SQL:** More verbose, error-prone
- **Peewee:** Smaller, but less mature

**Verdict:** ✓ **APPROVED** - Cleaner code, better maintainability

---

### 1.5 Additional Libraries

| Library | Purpose | License | Justification |
|---------|---------|---------|---------------|
| python-magic | File type detection | MIT | Standard for file identification |
| Pillow | Image validation | HPND | Industry standard for Python |
| pypdf | PDF validation | BSD-3 | Best PDF library for Python |
| cryptography | Cryptographic operations | Apache 2.0/BSD | Security operations |
| psutil | System information | BSD-3 | Cross-platform system info |
| pytest | Testing | MIT | Standard Python testing |
| black | Code formatting | MIT | Python code formatter |
| pylint | Linting | GPL | Code quality (dev only) |
| WeasyPrint | PDF generation | BSD | HTML to PDF conversion |

---

## 2. API DESIGN PRINCIPLES

### 2.1 Design Principles

1. **Consistency:** Similar operations have similar APIs
2. **Clarity:** Function names clearly indicate purpose
3. **Type Safety:** Use type hints throughout
4. **Error Handling:** Explicit error types and messages
5. **Logging:** All operations logged
6. **Progress Callbacks:** Long operations provide progress
7. **Cancellation:** Long operations can be cancelled
8. **Immutability:** Input data never modified
9. **Validation:** Input validated at boundaries
10. **Documentation:** All public APIs documented

---

### 2.2 Core API Patterns

#### Result Pattern

```python
from dataclasses import dataclass
from typing import Optional, Generic, TypeVar

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    """Result of an operation"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    @classmethod
    def ok(cls, data: T) -> 'Result[T]':
        """Create successful result"""
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str, error_type: str = "Error") -> 'Result[T]':
        """Create failure result"""
        return cls(success=False, error=error, error_type=error_type)
```

#### Progress Callback Pattern

```python
from typing import Callable, Optional

ProgressCallback = Callable[[int, int], None]  # (current, total)

def process_file(path: Path, 
                 progress_callback: Optional[ProgressCallback] = None) -> Result:
    """
    Process file with progress reporting.
    
    Args:
        path: File to process
        progress_callback: Optional callback(bytes_processed, total_bytes)
    
    Returns:
        Result object
    """
    total_size = path.stat().st_size
    processed = 0
    
    # ... processing
    
    if progress_callback:
        progress_callback(processed, total_size)
```

#### Operation Info Pattern

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OperationInfo:
    """Information about an operation"""
    operation_id: int
    operation_type: str
    start_time: datetime
    status: str
    progress: float  # 0.0 to 1.0
    current_step: str
    cancellable: bool
```

---

## 3. MODULE APIS

### 3.1 Case Manager API

```python
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CaseInfo:
    """Case information"""
    case_number: str
    title: str
    investigator: str
    description: str
    status: str = "active"

@dataclass
class Case:
    """Case with full details"""
    id: int
    case_number: str
    title: str
    investigator: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    evidence_count: int
    operation_count: int

class CaseManager:
    """Manage forensic cases"""
    
    def create_case(self, case_info: CaseInfo) -> Result[Case]:
        """
        Create a new case.
        
        Args:
            case_info: Case information
        
        Returns:
            Result containing created Case
        
        Raises:
            ValidationError: Invalid case information
        """
        pass
    
    def get_case(self, case_id: int) -> Result[Case]:
        """Get case by ID"""
        pass
    
    def list_cases(self, 
                   status: Optional[str] = None,
                   investigator: Optional[str] = None) -> Result[List[Case]]:
        """List cases with optional filters"""
        pass
    
    def update_case(self, case_id: int, **updates) -> Result[Case]:
        """Update case information"""
        pass
    
    def close_case(self, case_id: int) -> Result[Case]:
        """Close a case"""
        pass
```

---

### 3.2 Evidence Manager API

```python
@dataclass
class EvidenceInfo:
    """Evidence registration information"""
    case_id: int
    evidence_number: str
    source_type: str
    image_path: Path
    device_model: Optional[str] = None
    device_serial: Optional[str] = None
    capacity: Optional[int] = None
    notes: Optional[str] = None

@dataclass
class Evidence:
    """Evidence with full details"""
    id: int
    case_id: int
    evidence_number: str
    source_type: str
    image_path: Path
    sha256: str
    acquisition_time: datetime
    # ... additional fields

class EvidenceManager:
    """Manage forensic evidence"""
    
    def register_evidence(self, 
                          evidence_info: EvidenceInfo,
                          calculate_hash: bool = True,
                          progress_callback: Optional[ProgressCallback] = None
                          ) -> Result[Evidence]:
        """
        Register new evidence.
        
        Args:
            evidence_info: Evidence information
            calculate_hash: Whether to calculate SHA-256
            progress_callback: Progress updates during hashing
        
        Returns:
            Result containing registered Evidence
        """
        pass
    
    def verify_evidence_integrity(self, 
                                  evidence_id: int,
                                  progress_callback: Optional[ProgressCallback] = None
                                  ) -> Result[bool]:
        """
        Verify evidence integrity by recalculating hash.
        
        Returns:
            Result containing True if hash matches
        """
        pass
    
    def get_evidence(self, evidence_id: int) -> Result[Evidence]:
        """Get evidence by ID"""
        pass
    
    def list_evidence(self, case_id: int) -> Result[List[Evidence]]:
        """List all evidence for a case"""
        pass
```

---

### 3.3 File Carving API

```python
@dataclass
class CarvingConfig:
    """File carving configuration"""
    image_path: Path
    output_dir: Path
    file_types: List[str]  # e.g., ['jpeg', 'png', 'pdf']
    validate_files: bool = True
    calculate_confidence: bool = True
    min_confidence: int = 0  # 0-100
    max_file_size: int = 100 * 1024 * 1024  # 100MB

@dataclass
class RecoveredFile:
    """Information about a recovered file"""
    filename: str
    file_type: str
    offset: int
    size: int
    validation_status: str
    confidence_score: int
    sha256: str
    is_fragmented: bool

@dataclass
class CarvingResult:
    """Result of carving operation"""
    total_candidates: int
    validated_files: int
    invalid_files: int
    recovered_files: List[RecoveredFile]
    duration_seconds: float

class CarvingEngine:
    """File carving engine"""
    
    def carve_files(self,
                    config: CarvingConfig,
                    progress_callback: Optional[ProgressCallback] = None
                    ) -> Result[CarvingResult]:
        """
        Carve files from disk image.
        
        Args:
            config: Carving configuration
            progress_callback: Progress updates
        
        Returns:
            Result containing CarvingResult
        """
        pass
    
    def validate_file(self, file_path: Path, file_type: str) -> Result[ValidationResult]:
        """Validate a recovered file"""
        pass
    
    def calculate_confidence(self, file_path: Path, file_type: str) -> Result[int]:
        """Calculate confidence score for recovered file"""
        pass
```

---

### 3.4 Sanitization API

```python
@dataclass
class DeviceInfo:
    """Storage device information"""
    path: str
    model: str
    serial: str
    capacity: int
    device_type: str  # 'hdd', 'ssd', 'nvme', 'usb'
    removable: bool
    system_disk: bool
    mounted: bool
    partitions: List[str]

@dataclass
class SanitizationConfig:
    """Sanitization configuration"""
    device: str
    method: str
    verify: bool = True
    simulation: bool = True  # SAFETY: Default simulation
    force: bool = False  # Override safety checks (use with extreme caution)

@dataclass
class SanitizationResult:
    """Result of sanitization operation"""
    device: str
    method: str
    duration_seconds: float
    verification_result: str  # 'pass', 'fail', 'skipped'
    verification_details: dict

class DeviceDetector:
    """Detect storage devices"""
    
    def enumerate_devices(self) -> Result[List[DeviceInfo]]:
        """Enumerate all block devices"""
        pass
    
    def get_device_info(self, device_path: str) -> Result[DeviceInfo]:
        """Get detailed device information"""
        pass
    
    def is_system_disk(self, device_path: str) -> Result[bool]:
        """Check if device is system disk"""
        pass

class SanitizationEngine:
    """Drive sanitization engine"""
    
    def sanitize_device(self,
                       config: SanitizationConfig,
                       progress_callback: Optional[ProgressCallback] = None
                       ) -> Result[SanitizationResult]:
        """
        Sanitize storage device.
        
        SAFETY: Performs multiple safety checks before proceeding.
        Requires explicit user confirmation.
        
        Args:
            config: Sanitization configuration
            progress_callback: Progress updates
        
        Returns:
            Result containing SanitizationResult
        
        Raises:
            PermissionError: Insufficient privileges
            SafetyError: Safety check failed
        """
        pass
    
    def verify_sanitization(self, device: str) -> Result[VerificationResult]:
        """Verify sanitization was successful"""
        pass
```

---

### 3.5 Audit API

```python
@dataclass
class AuditEvent:
    """Audit event"""
    timestamp: datetime
    user: str
    event_type: str
    event_data: dict
    case_id: Optional[int] = None
    operation_id: Optional[int] = None

class AuditLogger:
    """Tamper-evident audit logging"""
    
    def log_event(self, 
                  event_type: str,
                  event_data: dict,
                  case_id: Optional[int] = None,
                  operation_id: Optional[int] = None) -> Result[int]:
        """
        Log an audit event.
        
        Automatically maintains hash chain for tamper detection.
        
        Returns:
            Result containing event ID
        """
        pass
    
    def get_audit_trail(self, 
                       case_id: Optional[int] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> Result[List[AuditEvent]]:
        """Get audit trail with optional filters"""
        pass
    
    def verify_integrity(self) -> Result[bool]:
        """
        Verify audit log integrity.
        
        Checks hash chain for tampering.
        
        Returns:
            Result containing True if integrity verified
        """
        pass
```

---

### 3.6 Reporting API

```python
@dataclass
class ReportConfig:
    """Report configuration"""
    case_id: int
    operation_id: Optional[int] = None
    report_type: str  # 'forensic', 'sanitization', 'case_summary'
    format: str = 'html'  # 'html', 'pdf'
    include_audit_chain: bool = True

class ReportGenerator:
    """Generate forensic reports"""
    
    def generate_report(self, config: ReportConfig) -> Result[Path]:
        """
        Generate report.
        
        Args:
            config: Report configuration
        
        Returns:
            Result containing path to generated report
        """
        pass
    
    def generate_forensic_report(self, 
                                 case_id: int, 
                                 operation_id: int,
                                 format: str = 'html') -> Result[Path]:
        """Generate forensic recovery report"""
        pass
    
    def generate_sanitization_report(self,
                                    operation_id: int,
                                    format: str = 'html') -> Result[Path]:
        """Generate sanitization report"""
        pass
```

---

## 4. GUI SIGNAL/SLOT ARCHITECTURE

### 4.1 Qt Signals Pattern

```python
from PySide6.QtCore import QObject, Signal

class OperationSignals(QObject):
    """Signals for operation progress"""
    started = Signal(int)  # operation_id
    progress = Signal(int, int, int)  # operation_id, current, total
    status_update = Signal(int, str)  # operation_id, message
    completed = Signal(int, object)  # operation_id, result
    failed = Signal(int, str)  # operation_id, error_message
    cancelled = Signal(int)  # operation_id

class CaseSignals(QObject):
    """Signals for case management"""
    case_created = Signal(int)  # case_id
    case_updated = Signal(int)  # case_id
    case_closed = Signal(int)  # case_id
    evidence_added = Signal(int, int)  # case_id, evidence_id
```

---

## 5. THREADING ARCHITECTURE

### 5.1 Background Operations

```python
from PySide6.QtCore import QRunnable, QThreadPool

class OperationRunner(QRunnable):
    """Run operation in background thread"""
    
    def __init__(self, operation_func, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.signals = OperationSignals()
    
    def run(self):
        """Execute operation"""
        try:
            self.signals.started.emit(self.operation_id)
            
            result = self.operation_func(*self.args, **self.kwargs)
            
            self.signals.completed.emit(self.operation_id, result)
        except Exception as e:
            self.signals.failed.emit(self.operation_id, str(e))

class JobManager:
    """Manage background jobs"""
    
    def __init__(self):
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
    
    def submit_job(self, operation_func, *args, **kwargs) -> int:
        """Submit job to thread pool"""
        runner = OperationRunner(operation_func, *args, **kwargs)
        self.thread_pool.start(runner)
        return runner.operation_id
```

---

## 6. ERROR HANDLING STRATEGY

### 6.1 Exception Hierarchy

```python
class ForensicsPlatformException(Exception):
    """Base exception for all platform errors"""
    pass

class ConfigurationError(ForensicsPlatformException):
    """Configuration-related errors"""
    pass

class ValidationError(ForensicsPlatformException):
    """Input validation errors"""
    pass

class PermissionError(ForensicsPlatformException):
    """Permission/privilege errors"""
    pass

class SafetyError(ForensicsPlatformException):
    """Safety check failures"""
    pass

class ForensicsError(ForensicsPlatformException):
    """Forensic operation failures"""
    pass

class SanitizationError(ForensicsPlatformException):
    """Sanitization operation failures"""
    pass

class DatabaseError(ForensicsPlatformException):
    """Database operation failures"""
    pass

class ExternalToolError(ForensicsPlatformException):
    """External tool execution failures"""
    pass
```

### 6.2 Error Handling Pattern

```python
def operation_with_error_handling():
    """Example of proper error handling"""
    try:
        # Validate inputs
        if not valid_input:
            raise ValidationError("Invalid input: ...")
        
        # Check permissions
        if not has_permission:
            raise PermissionError("Insufficient privileges")
        
        # Perform operation
        result = do_operation()
        
        # Log success
        logger.info("Operation completed successfully")
        
        return Result.ok(result)
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return Result.fail(str(e), "ValidationError")
        
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        return Result.fail(str(e), "PermissionError")
        
    except Exception as e:
        logger.exception("Unexpected error")
        return Result.fail(f"Unexpected error: {e}", "InternalError")
```

---

## 7. CONFIGURATION SCHEMA

```yaml
# default_config.yaml

application:
  name: "Forensics Platform"
  version: "1.0.0"
  
directories:
  data_dir: "~/.local/share/forensics-platform"
  log_dir: "${data_dir}/logs"
  case_dir: "${data_dir}/cases"
  temp_dir: "${data_dir}/temp"

database:
  path: "${data_dir}/forensics.db"
  backup_enabled: true
  backup_interval_hours: 24

sanitization:
  simulation_mode: true  # SAFETY: Default to simulation
  require_confirmation: true
  confirmation_count: 3
  default_method: "zero_fill"
  
carving:
  chunk_size_mb: 1
  max_file_size_mb: 100
  default_confidence_threshold: 50
  parallel_validation: true
  
forensics:
  calculate_hashes: true
  hash_algorithm: "sha256"
  verify_evidence_on_open: true
  
logging:
  level: "INFO"
  max_size_mb: 100
  backup_count: 5
  enable_audit: true
  
gui:
  theme: "dark"
  remember_window_size: true
  confirm_destructive_operations: true
  
external_tools:
  sleuthkit_path: "/usr/bin"  # Auto-detect if empty
  required_tools:
    - mmls
    - fsstat
    - fls
    - icat
    - tsk_recover
```

---

## 8. PERFORMANCE TARGETS

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Hash 1GB file | <30 seconds | SHA-256 calculation |
| Scan 1GB image | <10 minutes | Signature scanning |
| Validate 1000 files | <5 minutes | Structure validation |
| Database query | <100ms | Typical queries |
| GUI response | <16ms | Frame rate (60fps) |
| Operation start | <1 second | From user action to start |

---

## 9. MEMORY TARGETS

| Component | Target | Notes |
|-----------|--------|-------|
| Base application | <100MB | GUI + core |
| Per image open | <50MB | Image reader overhead |
| Carving buffer | <10MB | Sliding window |
| Database cache | <50MB | SQLite cache |
| Total typical | <500MB | During normal operation |
| Maximum | <2GB | During intensive carving |

---

## 10. PLATFORM-SPECIFIC CONSIDERATIONS

### 10.1 Linux (Primary Platform)

**Device Access:**
- Requires root/sudo for block device access
- Use `/dev/` paths
- Read from `/sys/block/` for device info
- Use `lsblk`, `blkid` for device enumeration

**Filesystem:**
- XDG Base Directory specification
- Config: `~/.config/forensics-platform/`
- Data: `~/.local/share/forensics-platform/`
- Cache: `~/.cache/forensics-platform/`

### 10.2 Windows (Future)

**Device Access:**
- Requires Administrator privileges
- Use `\\.\PhysicalDriveN` paths
- Use WMI for device info

**Filesystem:**
- Config: `%APPDATA%\ForensicsPlatform\`
- Data: `%LOCALAPPDATA%\ForensicsPlatform\`

---

## 11. SECURITY CONSIDERATIONS

### 11.1 Input Validation

```python
def validate_device_path(path: str) -> bool:
    """Validate device path to prevent injection"""
    # Only allow /dev/sdX or /dev/nvmeXnY patterns
    import re
    pattern = r'^/dev/(sd[a-z]|nvme\d+n\d+)$'
    return re.match(pattern, path) is not None

def validate_case_number(case_number: str) -> bool:
    """Validate case number format"""
    pattern = r'^CASE-\d{4}-\d{3,}$'
    return re.match(pattern, case_number) is not None
```

### 11.2 SQL Injection Prevention

```python
# GOOD: Parameterized query
cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))

# BAD: String concatenation
cursor.execute(f"SELECT * FROM cases WHERE id = {case_id}")
```

### 11.3 Command Injection Prevention

```python
# GOOD: List arguments
subprocess.run(['mmls', image_path], capture_output=True)

# BAD: Shell execution
subprocess.run(f'mmls {image_path}', shell=True)
```

---

## 12. TESTING STRATEGY

### 12.1 Unit Testing

```python
def test_sha256_calculation():
    """Test SHA-256 hash calculation"""
    test_file = Path("tests/fixtures/test.bin")
    expected_hash = "abc123..."
    
    result = calculate_sha256(test_file)
    
    assert result == expected_hash

def test_signature_detection():
    """Test JPEG signature detection"""
    jpeg_data = bytes.fromhex("FFD8FFE0")
    
    scanner = SignatureScanner()
    result = scanner.scan_data(jpeg_data)
    
    assert result.detected_type == "JPEG"
```

### 12.2 Integration Testing

```python
def test_case_evidence_workflow():
    """Test complete case/evidence workflow"""
    # Create case
    case_info = CaseInfo(...)
    case_result = case_manager.create_case(case_info)
    assert case_result.success
    
    # Register evidence
    evidence_info = EvidenceInfo(case_id=case_result.data.id, ...)
    evidence_result = evidence_manager.register_evidence(evidence_info)
    assert evidence_result.success
    
    # Verify evidence
    verify_result = evidence_manager.verify_evidence_integrity(evidence_result.data.id)
    assert verify_result.success
    assert verify_result.data == True
```

---

## 13. DEPLOYMENT

### 13.1 Installation Methods

**Development:**
```bash
python -m venv venv
source venv/bin/activate
pip install -e .
forensics-platform
```

**User Installation (Future):**
```bash
pip install forensics-platform
forensics-platform
```

**PyInstaller Bundle (Future):**
```bash
pyinstaller --onefile --windowed forensics_platform/__main__.py
```

---

## 14. SUMMARY

This technology stack provides:

✓ **Rapid Development:** Python ecosystem
✓ **Professional UI:** Qt framework
✓ **Data Integrity:** SQLite + SQLAlchemy
✓ **Extensibility:** Modular architecture
✓ **Safety:** Multiple validation layers
✓ **Performance:** Native extensions where needed
✓ **Maintainability:** Clear APIs and patterns
✓ **Documentation:** Type hints and docstrings
✓ **Testing:** Comprehensive test strategy

The platform is designed for academic/research use while maintaining professional standards for forensic tools.

---

**END OF TECHNOLOGY STACK DOCUMENT**
