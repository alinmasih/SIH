"""
SQLAlchemy ORM models for the forensics platform database.

Defines all database tables and relationships:
- Cases, Evidence, Operations
- RecoveredFiles, SanitizationOperations
- AuditEvents, Reports
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, CheckConstraint, UniqueConstraint, Index,
    create_engine, event
)
from sqlalchemy.orm import (
    DeclarativeBase, relationship, Session, mapped_column, Mapped
)


def utc_now() -> datetime:
    """Return current UTC datetime for database column defaults."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class Case(Base):
    """
    Forensic case model.

    Represents a forensic investigation case containing evidence,
    operations, and reports.
    """
    __tablename__ = 'cases'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    investigator: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default='active', nullable=False
    )

    # Relationships
    evidence = relationship('Evidence', back_populates='case', cascade='all, delete-orphan')
    operations = relationship('Operation', back_populates='case')
    reports = relationship('Report', back_populates='case', cascade='all, delete-orphan')
    audit_events = relationship('AuditEvent', back_populates='case')

    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed', 'archived')", name='chk_case_status'),
        CheckConstraint("length(title) >= 3", name='chk_case_title_length'),
    )

    def __repr__(self):
        return f"<Case(id={self.id}, case_number='{self.case_number}', title='{self.title}')>"


class Evidence(Base):
    """
    Forensic evidence model.

    Represents a piece of evidence (disk image, physical device, etc.)
    associated with a case.
    """
    __tablename__ = 'evidence'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False
    )
    evidence_number: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    device_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    device_serial: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acquisition_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acquisition_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    acquisition_tool: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    md5: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    # Relationships
    case = relationship('Case', back_populates='evidence')
    audit_events = relationship('AuditEvent', back_populates='evidence')

    __table_args__ = (
        UniqueConstraint('case_id', 'evidence_number', name='uq_case_evidence'),
        CheckConstraint(
            "source_type IN ('physical_device', 'disk_image', 'logical_files', "
            "'network_capture', 'memory_dump')",
            name='chk_evidence_source_type'
        ),
        CheckConstraint("length(sha256) = 64", name='chk_evidence_sha256_length'),
        Index('idx_evidence_case', 'case_id'),
        Index('idx_evidence_sha256', 'sha256'),
    )

    def __repr__(self):
        return f"<Evidence(id={self.id}, evidence_number='{self.evidence_number}', type='{self.source_type}')>"


class Operation(Base):
    """
    Operation model.

    Represents any operation performed (forensic analysis, carving, sanitization).
    """
    __tablename__ = 'operations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('cases.id', ondelete='SET NULL'), nullable=True
    )
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)
    tool_version: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_versions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    bytes_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    case = relationship('Case', back_populates='operations')
    recovered_files = relationship(
        'RecoveredFile', back_populates='operation', cascade='all, delete-orphan'
    )
    sanitization = relationship(
        'SanitizationOperation', back_populates='operation',
        uselist=False, cascade='all, delete-orphan'
    )
    audit_events = relationship('AuditEvent', back_populates='operation')
    reports = relationship('Report', back_populates='operation')

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('forensic_analysis', 'filesystem_analysis', "
            "'file_carving', 'deleted_file_recovery', 'drive_sanitization', "
            "'file_deletion', 'hash_calculation', 'evidence_verification')",
            name='chk_operation_type'
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name='chk_operation_status'
        ),
        Index('idx_operations_case', 'case_id'),
        Index('idx_operations_type', 'operation_type'),
        Index('idx_operations_status', 'status'),
        Index('idx_operations_start_time', 'start_time'),
    )

    def __repr__(self):
        return f"<Operation(id={self.id}, type='{self.operation_type}', status='{self.status}')>"


class RecoveredFile(Base):
    """
    Recovered file model.

    Represents a file recovered through forensic operations (carving, recovery).
    """
    __tablename__ = 'recovered_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('operations.id', ondelete='CASCADE'), nullable=False
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_type: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extension: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    offset: Mapped[int] = mapped_column(Integer, nullable=False)
    recovery_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    validation_status: Mapped[str] = mapped_column(
        String(20), default='unknown', nullable=False
    )
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    md5: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    file_metadata: Mapped[Optional[str]] = mapped_column('metadata', Text, nullable=True)  # JSON
    is_fragmented: Mapped[bool] = mapped_column(Boolean, default=False)
    fragment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fragment_map: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    file_created_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    file_modified_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    file_accessed_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    operation = relationship('Operation', back_populates='recovered_files')

    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('valid', 'partial', 'invalid', 'unknown')",
            name='chk_recovered_validation'
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)",
            name='chk_recovered_confidence'
        ),
        CheckConstraint("size >= 0", name='chk_recovered_size'),
        CheckConstraint("offset >= 0", name='chk_recovered_offset'),
        Index('idx_recovered_files_operation', 'operation_id'),
        Index('idx_recovered_files_type', 'detected_type'),
        Index('idx_recovered_files_validation', 'validation_status'),
        Index('idx_recovered_files_confidence', 'confidence_score'),
    )

    def __repr__(self):
        return (
            f"<RecoveredFile(id={self.id}, filename='{self.filename}', "
            f"type='{self.detected_type}', confidence={self.confidence_score})>"
        )


class SanitizationOperation(Base):
    """
    Sanitization operation details model.

    Extended information for drive/file sanitization operations.
    One-to-one relationship with Operation.
    """
    __tablename__ = 'sanitization_operations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('operations.id', ondelete='CASCADE'),
        nullable=False, unique=True
    )
    device: Mapped[str] = mapped_column(String(200), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)
    device_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    device_serial: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_secure_erase: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    supports_crypto_erase: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    supports_trim: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    sanitization_method: Mapped[str] = mapped_column(String(100), nullable=False)
    sanitization_standard: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pass_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pattern_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_method: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_result: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    verification_sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verification_failed_samples: Mapped[int] = mapped_column(Integer, default=0)
    was_system_disk: Mapped[bool] = mapped_column(Boolean, default=False)
    was_mounted: Mapped[bool] = mapped_column(Boolean, default=False)
    user_confirmation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    operation = relationship('Operation', back_populates='sanitization')

    __table_args__ = (
        CheckConstraint(
            "device_type IN ('hdd', 'ssd', 'nvme', 'usb', 'sd_card', 'other')",
            name='chk_sanitization_device_type'
        ),
        CheckConstraint(
            "verification_result IN ('pass', 'fail', 'partial', 'skipped')",
            name='chk_sanitization_verification'
        ),
        Index('idx_sanitization_operation', 'operation_id'),
    )

    def __repr__(self):
        return (
            f"<SanitizationOperation(id={self.id}, device='{self.device}', "
            f"method='{self.sanitization_method}', result='{self.verification_result}')>"
        )


class AuditEvent(Base):
    """
    Audit event model.

    Tamper-evident audit logging with hash chaining.
    Each event stores the hash of the previous event to form a chain.
    """
    __tablename__ = 'audit_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    user: Mapped[str] = mapped_column(String(100), nullable=False)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    case_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('cases.id', ondelete='SET NULL'), nullable=True
    )
    operation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('operations.id', ondelete='SET NULL'), nullable=True
    )
    evidence_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('evidence.id', ondelete='SET NULL'), nullable=True
    )
    event_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    case = relationship('Case', back_populates='audit_events')
    operation = relationship('Operation', back_populates='audit_events')
    evidence = relationship('Evidence', back_populates='audit_events')

    __table_args__ = (
        CheckConstraint("length(event_hash) = 64", name='chk_audit_hash_length'),
        CheckConstraint(
            "event_category IS NULL OR event_category IN ('case_management', "
            "'evidence_management', 'forensic_operation', 'sanitization_operation', "
            "'system', 'security', 'configuration')",
            name='chk_audit_category'
        ),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user'),
        Index('idx_audit_type', 'event_type'),
        Index('idx_audit_case', 'case_id'),
    )

    def __repr__(self):
        return f"<AuditEvent(id={self.id}, type='{self.event_type}', user='{self.user}')>"


class Report(Base):
    """
    Report model.

    Tracks generated reports (forensic recovery, sanitization, etc.).
    """
    __tablename__ = 'reports'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False
    )
    operation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('operations.id', ondelete='SET NULL'), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    report_format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    generated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    template_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    case = relationship('Case', back_populates='reports')
    operation = relationship('Operation', back_populates='reports')

    __table_args__ = (
        CheckConstraint(
            "report_type IN ('forensic_recovery', 'filesystem_analysis', "
            "'sanitization', 'audit_trail', 'case_summary')",
            name='chk_report_type'
        ),
        CheckConstraint(
            "report_format IN ('html', 'pdf', 'json', 'csv')",
            name='chk_report_format'
        ),
        CheckConstraint("length(report_hash) = 64", name='chk_report_hash_length'),
        Index('idx_reports_case', 'case_id'),
        Index('idx_reports_type', 'report_type'),
    )

    def __repr__(self):
        return f"<Report(id={self.id}, type='{self.report_type}', format='{self.report_format}')>"
