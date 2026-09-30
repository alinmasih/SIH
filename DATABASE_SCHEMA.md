# Database Schema & Entity Relationship Design

**Project:** Integrated Secure Data Sanitization & Digital Forensics Platform  
**Version:** 1.0  
**Date:** 2026-09-08  
**Purpose:** Complete database design with relationships, constraints, and queries

---

## 1. ENTITY RELATIONSHIP DIAGRAM

```
                    ┌─────────────────┐
                    │     CASES       │
                    │─────────────────│
                    │ PK  id          │
                    │     case_number │
                    │     title       │
                    │     investigator│
                    │     description │
                    │     created_at  │
                    │     updated_at  │
                    │     status      │
                    └────────┬────────┘
                             │
                             │ 1
                             │
                ┌────────────┴────────────┐
                │                         │
             N  │                      N  │
        ┌───────▼────────┐       ┌───────▼──────────┐
        │    EVIDENCE    │       │   OPERATIONS     │
        │────────────────│       │──────────────────│
        │ PK  id         │       │ PK  id           │
        │ FK  case_id    │       │ FK  case_id      │
        │     evidence_# │       │     operation_#  │
        │     source_type│       │     target       │
        │     device_*   │       │     start_time   │
        │     image_path │       │     end_time     │
        │     sha256     │       │     status       │
        │     notes      │       │     tool_version │
        └────────────────┘       └───────┬──────────┘
                                         │
                                         │ 1
                                         │
                            ┌────────────┴────────────┐
                            │                         │
                         N  │                      N  │
                ┌───────────▼──────────┐  ┌──────────▼─────────────┐
                │  RECOVERED_FILES     │  │ SANITIZATION_OPS       │
                │──────────────────────│  │────────────────────────│
                │ PK  id               │  │ PK  id                 │
                │ FK  operation_id     │  │ FK  operation_id (UQ)  │
                │     filename         │  │     device             │
                │     detected_type    │  │     device_type        │
                │     size             │  │     sanitization_method│
                │     offset           │  │     verification_result│
                │     validation_status│  │     verification_details│
                │     confidence_score │  └────────────────────────┘
                │     sha256           │
                └──────────────────────┘


        ┌───────────────────┐              ┌─────────────────┐
        │   AUDIT_EVENTS    │              │    REPORTS      │
        │───────────────────│              │─────────────────│
        │ PK  id            │              │ PK  id          │
        │ FK  case_id       │──────────────│ FK  case_id     │
        │ FK  operation_id  │              │ FK  operation_id│
        │     timestamp     │              │     report_type │
        │     user          │              │     file_path   │
        │     event_type    │              │     generated_at│
        │     event_data    │              │     report_hash │
        │     previous_hash │              └─────────────────┘
        │     event_hash    │
        └───────────────────┘
```

---

## 2. TABLE DEFINITIONS

### 2.1 CASES Table

**Purpose:** Central case management for forensic investigations

```sql
CREATE TABLE cases (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Case Identification
    case_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    investigator TEXT NOT NULL,
    
    -- Case Details
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Status
    status TEXT CHECK(status IN ('active', 'closed', 'archived')) DEFAULT 'active' NOT NULL,
    
    -- Constraints
    CONSTRAINT chk_case_number_format CHECK(
        case_number GLOB 'CASE-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]*'
    ),
    CONSTRAINT chk_title_length CHECK(length(title) BETWEEN 5 AND 200),
    CONSTRAINT chk_investigator_length CHECK(length(investigator) BETWEEN 2 AND 100)
);

-- Indexes
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_investigator ON cases(investigator);
CREATE INDEX idx_cases_created_at ON cases(created_at);

-- Triggers
CREATE TRIGGER trg_cases_updated_at
AFTER UPDATE ON cases
FOR EACH ROW
BEGIN
    UPDATE cases SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

**Field Descriptions:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | INTEGER | Primary key | AUTO INCREMENT |
| case_number | TEXT | Unique case identifier | Format: CASE-YYYY-NNN |
| title | TEXT | Case title/name | 5-200 characters |
| investigator | TEXT | Lead investigator name | 2-100 characters |
| description | TEXT | Case description | Optional, unlimited |
| created_at | TIMESTAMP | Case creation time | Auto-set |
| updated_at | TIMESTAMP | Last modification time | Auto-update trigger |
| status | TEXT | Case status | active/closed/archived |

---

### 2.2 EVIDENCE Table

**Purpose:** Track forensic evidence items associated with cases

```sql
CREATE TABLE evidence (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign Key
    case_id INTEGER NOT NULL,
    
    -- Evidence Identification
    evidence_number TEXT NOT NULL,
    
    -- Source Information
    source_type TEXT CHECK(source_type IN (
        'physical_device',
        'disk_image',
        'logical_files',
        'network_capture',
        'memory_dump'
    )) NOT NULL,
    
    -- Device Information (if applicable)
    device_model TEXT,
    device_serial TEXT,
    capacity INTEGER CHECK(capacity > 0),
    
    -- Paths
    source_path TEXT,
    image_path TEXT,
    
    -- Acquisition Metadata
    acquisition_time TIMESTAMP,
    acquisition_method TEXT,
    acquisition_tool TEXT,
    
    -- Integrity
    sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
    md5 TEXT CHECK(md5 IS NULL OR length(md5) = 32),
    
    -- Additional Information
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    UNIQUE(case_id, evidence_number)
);

-- Indexes
CREATE INDEX idx_evidence_case ON evidence(case_id);
CREATE INDEX idx_evidence_type ON evidence(source_type);
CREATE INDEX idx_evidence_sha256 ON evidence(sha256);
CREATE INDEX idx_evidence_created_at ON evidence(created_at);
```

**Field Descriptions:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | INTEGER | Primary key | AUTO INCREMENT |
| case_id | INTEGER | Parent case | FK to cases(id) |
| evidence_number | TEXT | Evidence identifier | Unique per case |
| source_type | TEXT | Type of evidence | Enumerated values |
| device_model | TEXT | Device model (if hardware) | Optional |
| device_serial | TEXT | Device serial number | Optional |
| capacity | INTEGER | Storage capacity (bytes) | Must be positive |
| source_path | TEXT | Original source location | Optional |
| image_path | TEXT | Forensic image path | Optional |
| acquisition_time | TIMESTAMP | When evidence was acquired | Optional |
| acquisition_method | TEXT | How evidence was acquired | Optional |
| acquisition_tool | TEXT | Tool used for acquisition | Optional |
| sha256 | TEXT | SHA-256 hash | Required, 64 hex chars |
| md5 | TEXT | MD5 hash (legacy) | Optional, 32 hex chars |
| notes | TEXT | Additional notes | Optional |
| created_at | TIMESTAMP | Record creation time | Auto-set |

---

### 2.3 OPERATIONS Table

**Purpose:** Track all operations performed (forensic analysis, sanitization, etc.)

```sql
CREATE TABLE operations (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign Key (nullable for standalone operations)
    case_id INTEGER,
    
    -- Operation Identification
    operation_type TEXT CHECK(operation_type IN (
        'forensic_analysis',
        'filesystem_analysis',
        'file_carving',
        'deleted_file_recovery',
        'drive_sanitization',
        'file_deletion',
        'hash_calculation',
        'evidence_verification'
    )) NOT NULL,
    
    -- Target Information
    target TEXT NOT NULL,
    target_type TEXT CHECK(target_type IN (
        'disk_image',
        'physical_device',
        'directory',
        'file'
    )),
    
    -- Timing
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        CAST((julianday(end_time) - julianday(start_time)) * 86400 AS INTEGER)
    ) VIRTUAL,
    
    -- Status
    status TEXT CHECK(status IN (
        'pending',
        'running',
        'completed',
        'failed',
        'cancelled'
    )) DEFAULT 'pending' NOT NULL,
    
    -- Tool Information
    tool_version TEXT NOT NULL,
    tool_versions TEXT,  -- JSON: all tool versions used
    
    -- Parameters and Results
    parameters TEXT,  -- JSON: operation parameters
    result TEXT,      -- JSON: operation results
    
    -- Statistics
    bytes_processed INTEGER DEFAULT 0,
    items_processed INTEGER DEFAULT 0,
    items_found INTEGER DEFAULT 0,
    
    -- Error Handling
    error_message TEXT,
    error_traceback TEXT,
    
    -- Constraints
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
    CHECK(end_time IS NULL OR end_time >= start_time)
);

-- Indexes
CREATE INDEX idx_operations_case ON operations(case_id);
CREATE INDEX idx_operations_type ON operations(operation_type);
CREATE INDEX idx_operations_status ON operations(status);
CREATE INDEX idx_operations_start_time ON operations(start_time);
CREATE INDEX idx_operations_target ON operations(target);
```

**Field Descriptions:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | INTEGER | Primary key | AUTO INCREMENT |
| case_id | INTEGER | Associated case | FK, nullable |
| operation_type | TEXT | Type of operation | Enumerated values |
| target | TEXT | What is being operated on | Required |
| target_type | TEXT | Type of target | Enumerated values |
| start_time | TIMESTAMP | Operation start | Auto-set |
| end_time | TIMESTAMP | Operation completion | Optional |
| duration_seconds | INTEGER | Calculated duration | Virtual column |
| status | TEXT | Current status | Enumerated values |
| tool_version | TEXT | Platform version | Required |
| tool_versions | TEXT | All tool versions (JSON) | Optional |
| parameters | TEXT | Operation config (JSON) | Optional |
| result | TEXT | Operation results (JSON) | Optional |
| bytes_processed | INTEGER | Bytes processed | Default 0 |
| items_processed | INTEGER | Items processed | Default 0 |
| items_found | INTEGER | Items found/recovered | Default 0 |
| error_message | TEXT | Error description | Optional |
| error_traceback | TEXT | Full error trace | Optional |

---

### 2.4 RECOVERED_FILES Table

**Purpose:** Catalog files recovered through forensic operations

```sql
CREATE TABLE recovered_files (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign Key
    operation_id INTEGER NOT NULL,
    
    -- File Location
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    
    -- File Identification
    detected_type TEXT NOT NULL,
    mime_type TEXT,
    extension TEXT,
    
    -- File Properties
    size INTEGER NOT NULL CHECK(size >= 0),
    offset INTEGER NOT NULL CHECK(offset >= 0),
    
    -- Recovery Information
    recovery_method TEXT CHECK(recovery_method IN (
        'filesystem_metadata',
        'signature_carving',
        'fragment_reconstruction',
        'unallocated_space'
    )),
    
    -- Validation
    validation_status TEXT CHECK(validation_status IN (
        'valid',
        'partial',
        'invalid',
        'unknown'
    )) DEFAULT 'unknown' NOT NULL,
    
    -- Confidence Scoring
    confidence_score INTEGER CHECK(
        confidence_score IS NULL OR 
        (confidence_score >= 0 AND confidence_score <= 100)
    ),
    confidence_details TEXT,  -- JSON: detailed scoring breakdown
    
    -- Integrity
    sha256 TEXT CHECK(sha256 IS NULL OR length(sha256) = 64),
    md5 TEXT CHECK(md5 IS NULL OR length(md5) = 32),
    
    -- Metadata
    metadata TEXT,  -- JSON: file-specific metadata (EXIF, timestamps, etc.)
    
    -- Fragmentation
    is_fragmented BOOLEAN DEFAULT 0,
    fragment_count INTEGER,
    fragment_map TEXT,  -- JSON: fragment locations
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- File Timestamps (recovered from filesystem/metadata)
    file_created_time TIMESTAMP,
    file_modified_time TIMESTAMP,
    file_accessed_time TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_recovered_files_operation ON recovered_files(operation_id);
CREATE INDEX idx_recovered_files_type ON recovered_files(detected_type);
CREATE INDEX idx_recovered_files_validation ON recovered_files(validation_status);
CREATE INDEX idx_recovered_files_confidence ON recovered_files(confidence_score);
CREATE INDEX idx_recovered_files_sha256 ON recovered_files(sha256);
CREATE INDEX idx_recovered_files_size ON recovered_files(size);
CREATE INDEX idx_recovered_files_filename ON recovered_files(filename);

-- Full-text search index for filenames
CREATE VIRTUAL TABLE recovered_files_fts USING fts5(
    filename,
    detected_type,
    content=recovered_files,
    content_rowid=id
);
```

---

### 2.5 SANITIZATION_OPERATIONS Table

**Purpose:** Extended details for drive/file sanitization operations

```sql
CREATE TABLE sanitization_operations (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign Key (one-to-one with operations)
    operation_id INTEGER NOT NULL UNIQUE,
    
    -- Device Information
    device TEXT NOT NULL,
    device_type TEXT CHECK(device_type IN (
        'hdd',
        'ssd',
        'nvme',
        'usb',
        'sd_card',
        'other'
    )) NOT NULL,
    device_model TEXT,
    device_serial TEXT,
    capacity INTEGER CHECK(capacity > 0),
    
    -- Device Capabilities
    supports_secure_erase BOOLEAN,
    supports_crypto_erase BOOLEAN,
    supports_trim BOOLEAN,
    
    -- Sanitization Method
    sanitization_method TEXT NOT NULL,
    sanitization_standard TEXT,
    pass_count INTEGER,
    pattern_used TEXT,
    
    -- Verification
    verification_method TEXT NOT NULL,
    verification_result TEXT CHECK(verification_result IN (
        'pass',
        'fail',
        'partial',
        'skipped'
    )) NOT NULL,
    verification_details TEXT,  -- JSON
    
    -- Sampling (for verification)
    verification_sample_count INTEGER,
    verification_sample_size INTEGER,
    verification_failed_samples INTEGER DEFAULT 0,
    
    -- Before/After Hashes (for verification)
    pre_sanitization_hash TEXT,
    post_sanitization_hash TEXT,
    
    -- Safety Information
    was_system_disk BOOLEAN DEFAULT 0,
    was_mounted BOOLEAN DEFAULT 0,
    user_confirmation_count INTEGER DEFAULT 0,
    
    -- Constraints
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_sanitization_ops_operation ON sanitization_operations(operation_id);
CREATE INDEX idx_sanitization_ops_device_type ON sanitization_operations(device_type);
CREATE INDEX idx_sanitization_ops_method ON sanitization_operations(sanitization_method);
CREATE INDEX idx_sanitization_ops_result ON sanitization_operations(verification_result);
```

---

### 2.6 AUDIT_EVENTS Table

**Purpose:** Tamper-evident audit log with hash chaining

```sql
CREATE TABLE audit_events (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Timestamp
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Actor
    user TEXT NOT NULL,
    user_role TEXT,
    
    -- Event Classification
    event_type TEXT NOT NULL,
    event_category TEXT CHECK(event_category IN (
        'case_management',
        'evidence_management',
        'forensic_operation',
        'sanitization_operation',
        'system',
        'security',
        'configuration'
    )),
    
    -- Context
    case_id INTEGER,
    operation_id INTEGER,
    evidence_id INTEGER,
    
    -- Event Data
    event_data TEXT NOT NULL,  -- JSON
    
    -- Hash Chain
    previous_hash TEXT,
    event_hash TEXT NOT NULL CHECK(length(event_hash) = 64),
    
    -- System Information
    hostname TEXT,
    ip_address TEXT,
    
    -- Constraints
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE SET NULL,
    FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_events_user ON audit_events(user);
CREATE INDEX idx_audit_events_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_case ON audit_events(case_id);
CREATE INDEX idx_audit_events_operation ON audit_events(operation_id);

-- Trigger to ensure hash chain integrity
CREATE TRIGGER trg_audit_events_before_insert
BEFORE INSERT ON audit_events
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit hash chain broken')
    WHERE NEW.previous_hash IS NOT NULL
    AND NEW.previous_hash != (
        SELECT event_hash FROM audit_events 
        ORDER BY id DESC LIMIT 1
    );
END;
```

---

### 2.7 REPORTS Table

**Purpose:** Track generated reports

```sql
CREATE TABLE reports (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign Keys
    case_id INTEGER NOT NULL,
    operation_id INTEGER,
    
    -- Report Information
    report_type TEXT CHECK(report_type IN (
        'forensic_recovery',
        'filesystem_analysis',
        'sanitization',
        'audit_trail',
        'case_summary'
    )) NOT NULL,
    report_format TEXT CHECK(report_format IN (
        'html',
        'pdf',
        'json',
        'csv'
    )) NOT NULL,
    
    -- File Information
    file_path TEXT NOT NULL,
    file_size INTEGER,
    
    -- Generation Information
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    generated_by TEXT NOT NULL,
    
    -- Integrity
    report_hash TEXT NOT NULL CHECK(length(report_hash) = 64),
    
    -- Template Information
    template_name TEXT,
    template_version TEXT,
    
    -- Constraints
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_reports_case ON reports(case_id);
CREATE INDEX idx_reports_operation ON reports(operation_id);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_generated_at ON reports(generated_at);
```

---

## 3. COMMON QUERIES

### 3.1 Case Management Queries

```sql
-- Get case summary with counts
SELECT 
    c.*,
    COUNT(DISTINCT e.id) as evidence_count,
    COUNT(DISTINCT o.id) as operation_count,
    COUNT(DISTINCT r.id) as report_count
FROM cases c
LEFT JOIN evidence e ON c.id = e.case_id
LEFT JOIN operations o ON c.id = o.case_id
LEFT JOIN reports r ON c.id = r.case_id
WHERE c.id = ?
GROUP BY c.id;

-- Get active cases
SELECT * FROM cases 
WHERE status = 'active' 
ORDER BY created_at DESC;

-- Search cases
SELECT * FROM cases
WHERE title LIKE '%' || ? || '%'
   OR case_number LIKE '%' || ? || '%'
   OR investigator LIKE '%' || ? || '%'
ORDER BY created_at DESC;
```

### 3.2 Evidence Queries

```sql
-- Get all evidence for a case
SELECT * FROM evidence
WHERE case_id = ?
ORDER BY evidence_number;

-- Verify evidence integrity
SELECT 
    id,
    evidence_number,
    sha256,
    CASE 
        WHEN sha256 = ? THEN 'VERIFIED'
        ELSE 'INTEGRITY FAILURE'
    END as integrity_status
FROM evidence
WHERE id = ?;

-- Find evidence by hash
SELECT e.*, c.case_number, c.title
FROM evidence e
JOIN cases c ON e.case_id = c.id
WHERE e.sha256 = ?;
```

### 3.3 Operation Queries

```sql
-- Get operations for a case
SELECT 
    o.*,
    CASE 
        WHEN o.status = 'running' THEN 'In Progress'
        WHEN o.status = 'completed' THEN 'Completed'
        ELSE o.status
    END as status_display
FROM operations o
WHERE o.case_id = ?
ORDER BY o.start_time DESC;

-- Get operation statistics
SELECT 
    operation_type,
    COUNT(*) as total_operations,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    AVG(duration_seconds) as avg_duration_seconds
FROM operations
WHERE case_id = ?
GROUP BY operation_type;

-- Get running operations
SELECT * FROM operations
WHERE status = 'running'
ORDER BY start_time;
```

### 3.4 Recovery Queries

```sql
-- Get recovered files for an operation
SELECT * FROM recovered_files
WHERE operation_id = ?
ORDER BY confidence_score DESC, filename;

-- Get high-confidence recoveries
SELECT * FROM recovered_files
WHERE operation_id = ?
  AND confidence_score >= 70
  AND validation_status = 'valid'
ORDER BY size DESC;

-- File type distribution
SELECT 
    detected_type,
    COUNT(*) as file_count,
    SUM(size) as total_size_bytes,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN validation_status = 'valid' THEN 1 ELSE 0 END) as valid_count
FROM recovered_files
WHERE operation_id = ?
GROUP BY detected_type
ORDER BY file_count DESC;

-- Search recovered files
SELECT * FROM recovered_files_fts
WHERE filename MATCH ?
   OR detected_type MATCH ?;
```

### 3.5 Sanitization Queries

```sql
-- Get sanitization details
SELECT 
    o.id,
    o.target,
    o.start_time,
    o.end_time,
    o.status,
    s.device_type,
    s.sanitization_method,
    s.verification_result
FROM operations o
JOIN sanitization_operations s ON o.id = s.operation_id
WHERE o.case_id = ?
ORDER BY o.start_time DESC;

-- Sanitization success rate
SELECT 
    device_type,
    COUNT(*) as total,
    SUM(CASE WHEN verification_result = 'pass' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN verification_result = 'fail' THEN 1 ELSE 0 END) as failed
FROM sanitization_operations s
JOIN operations o ON s.operation_id = o.id
WHERE o.status = 'completed'
GROUP BY device_type;
```

### 3.6 Audit Queries

```sql
-- Get audit trail for a case
SELECT * FROM audit_events
WHERE case_id = ?
ORDER BY timestamp DESC;

-- Verify audit chain integrity
WITH RECURSIVE chain AS (
    SELECT 
        id,
        timestamp,
        event_hash,
        previous_hash,
        1 as position
    FROM audit_events
    WHERE id = 1
    
    UNION ALL
    
    SELECT 
        ae.id,
        ae.timestamp,
        ae.event_hash,
        ae.previous_hash,
        chain.position + 1
    FROM audit_events ae
    JOIN chain ON ae.previous_hash = chain.event_hash
)
SELECT 
    COUNT(*) as verified_events,
    MAX(position) as chain_length
FROM chain;

-- Get recent activity
SELECT 
    ae.timestamp,
    ae.user,
    ae.event_type,
    c.case_number,
    o.operation_type
FROM audit_events ae
LEFT JOIN cases c ON ae.case_id = c.id
LEFT JOIN operations o ON ae.operation_id = o.id
ORDER BY ae.timestamp DESC
LIMIT 50;
```

---

## 4. VIEWS

### 4.1 Case Overview View

```sql
CREATE VIEW v_case_overview AS
SELECT 
    c.id,
    c.case_number,
    c.title,
    c.investigator,
    c.status,
    c.created_at,
    c.updated_at,
    COUNT(DISTINCT e.id) as evidence_count,
    COUNT(DISTINCT o.id) as operation_count,
    SUM(CASE WHEN o.status = 'running' THEN 1 ELSE 0 END) as running_operations,
    COUNT(DISTINCT rf.id) as recovered_file_count,
    COUNT(DISTINCT r.id) as report_count
FROM cases c
LEFT JOIN evidence e ON c.id = e.case_id
LEFT JOIN operations o ON c.id = o.case_id
LEFT JOIN recovered_files rf ON o.id = rf.operation_id
LEFT JOIN reports r ON c.id = r.case_id
GROUP BY c.id;
```

### 4.2 Recovery Summary View

```sql
CREATE VIEW v_recovery_summary AS
SELECT 
    o.id as operation_id,
    o.case_id,
    o.target,
    o.start_time,
    o.end_time,
    o.status,
    COUNT(rf.id) as total_files,
    SUM(CASE WHEN rf.validation_status = 'valid' THEN 1 ELSE 0 END) as valid_files,
    SUM(CASE WHEN rf.confidence_score >= 70 THEN 1 ELSE 0 END) as high_confidence_files,
    SUM(rf.size) as total_size_bytes,
    AVG(rf.confidence_score) as avg_confidence
FROM operations o
LEFT JOIN recovered_files rf ON o.id = rf.operation_id
WHERE o.operation_type IN ('file_carving', 'deleted_file_recovery')
GROUP BY o.id;
```

---

## 5. SQLALCHEMY MODELS

```python
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Case(Base):
    __tablename__ = 'cases'
    
    id = Column(Integer, primary_key=True)
    case_number = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    investigator = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = Column(String(20), default='active', nullable=False)
    
    # Relationships
    evidence = relationship('Evidence', back_populates='case', cascade='all, delete-orphan')
    operations = relationship('Operation', back_populates='case')
    reports = relationship('Report', back_populates='case', cascade='all, delete-orphan')
    audit_events = relationship('AuditEvent', back_populates='case')
    
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed', 'archived')"),
    )

class Evidence(Base):
    __tablename__ = 'evidence'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    evidence_number = Column(String(50), nullable=False)
    source_type = Column(String(50), nullable=False)
    device_model = Column(String(200))
    device_serial = Column(String(200))
    capacity = Column(Integer)
    source_path = Column(Text)
    image_path = Column(Text)
    acquisition_time = Column(DateTime)
    sha256 = Column(String(64), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    case = relationship('Case', back_populates='evidence')
    
    __table_args__ = (
        UniqueConstraint('case_id', 'evidence_number'),
        CheckConstraint("source_type IN ('physical_device', 'disk_image', 'logical_files', 'network_capture')"),
        CheckConstraint("length(sha256) = 64"),
    )

class Operation(Base):
    __tablename__ = 'operations'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id', ondelete='SET NULL'))
    operation_type = Column(String(50), nullable=False)
    target = Column(Text, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), default='pending', nullable=False)
    tool_version = Column(String(50), nullable=False)
    tool_versions = Column(Text)
    parameters = Column(Text)
    result = Column(Text)
    error_message = Column(Text)
    
    # Relationships
    case = relationship('Case', back_populates='operations')
    recovered_files = relationship('RecoveredFile', back_populates='operation', cascade='all, delete-orphan')
    sanitization = relationship('SanitizationOperation', back_populates='operation', uselist=False, cascade='all, delete-orphan')
    audit_events = relationship('AuditEvent', back_populates='operation')

# ... (additional models follow similar pattern)
```

---

## 6. DATABASE INITIALIZATION

```python
import sqlite3

def initialize_database(db_path: str):
    """Initialize the database with all tables and indexes"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create all tables (execute all CREATE TABLE statements)
    # ... (all SQL from sections above)
    
    # Insert genesis audit event
    cursor.execute("""
        INSERT INTO audit_events (
            user, event_type, event_category, event_data, 
            previous_hash, event_hash
        ) VALUES (
            'SYSTEM',
            'database_initialized',
            'system',
            '{"action": "database_created"}',
            NULL,
            ? -- SHA256 of initialization event
        )
    """, (calculate_genesis_hash(),))
    
    conn.commit()
    conn.close()
```

---

**END OF DATABASE SCHEMA DOCUMENT**
