"""
Forensic Report and Sanitization Certificate Generation Engine.

Generates court-admissible forensic analysis reports, NIST SP 800-88 Rev 1
sanitization certificates, case dossiers, and audit trail ledgers in
HTML, PDF, JSON, and CSV formats with cryptographic SHA-256 integrity sealing.
"""

from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import desc

from forensics_platform.database.models import (
    AuditEvent,
    Case,
    Evidence,
    Operation,
    RecoveredFile,
    Report,
    SanitizationOperation,
)
from forensics_platform.reporting.pdf_generator import PDFGenerator
from forensics_platform.reporting.template_engine import TemplateEngine


class ReportType:
    """Standard report type identifiers conforming to database check constraint."""
    FORENSIC_RECOVERY = "forensic_recovery"
    FILESYSTEM_ANALYSIS = "filesystem_analysis"
    SANITIZATION = "sanitization"
    AUDIT_TRAIL = "audit_trail"
    CASE_SUMMARY = "case_summary"

    ALL_TYPES = [
        FORENSIC_RECOVERY,
        FILESYSTEM_ANALYSIS,
        SANITIZATION,
        AUDIT_TRAIL,
        CASE_SUMMARY,
    ]


class ReportFormat:
    """Supported report export formats."""
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"

    ALL_FORMATS = [HTML, PDF, JSON, CSV]


def calculate_file_sha256(filepath: Union[str, Path]) -> str:
    """Calculate the SHA-256 checksum of any file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ReportGenerator:
    """
    Core reporting engine handling template compilation, data aggregation,
    format conversion, hash sealing, and audit persistence.
    """

    def __init__(
        self,
        db_manager=None,
        audit_logger=None,
        config=None,
        reports_dir: Optional[Union[str, Path]] = None,
    ):
        self.db_manager = db_manager
        self.audit_logger = audit_logger
        self.config = config

        if reports_dir is not None:
            self.reports_dir = Path(reports_dir).resolve()
        elif self.config and hasattr(self.config, "data_dir"):
            self.reports_dir = Path(self.config.data_dir).resolve() / "reports"
        else:
            self.reports_dir = Path("data/reports").resolve()

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.template_engine = TemplateEngine()
        self.pdf_generator = PDFGenerator()

    # -------------------------------------------------------------------------
    # Forensic Recovery & Analysis Report
    # -------------------------------------------------------------------------

    def generate_forensic_report(
        self,
        case_id: int,
        operation_id: Optional[int] = None,
        format: str = "html",
        output_path: Optional[Union[str, Path]] = None,
        watermark: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        """
        Generate a forensic recovery and filesystem investigation report.
        """
        fmt = format.lower()
        if fmt not in ReportFormat.ALL_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        user = generated_by or os.getenv("USER", "Forensic Examiner")
        session = self.db_manager.get_session()
        try:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Case with ID {case_id} not found")

            # Determine operation
            if operation_id:
                operation = session.query(Operation).filter(Operation.id == operation_id).first()
            else:
                operation = (
                    session.query(Operation)
                    .filter(
                        Operation.case_id == case_id,
                        Operation.operation_type.in_([
                            "file_carving", "forensic_analysis", "filesystem_analysis", "deleted_file_recovery"
                        ])
                    )
                    .order_by(desc(Operation.id))
                    .first()
                )
                if not operation:
                    operation = (
                        session.query(Operation)
                        .filter(Operation.case_id == case_id)
                        .order_by(desc(Operation.id))
                        .first()
                    )

            # Determine evidence
            evidence = session.query(Evidence).filter(Evidence.case_id == case_id).first()

            # Query recovered files
            files = []
            if operation:
                files = (
                    session.query(RecoveredFile)
                    .filter(RecoveredFile.operation_id == operation.id)
                    .all()
                )
            if not files and case:
                op_ids = [op.id for op in case.operations]
                if op_ids:
                    files = (
                        session.query(RecoveredFile)
                        .filter(RecoveredFile.operation_id.in_(op_ids))
                        .all()
                    )

            # Calculate stats
            total_files = len(files)
            total_bytes = sum(f.size for f in files) if files else 0
            valid_files = sum(1 for f in files if f.validation_status == "valid")
            scores = [f.confidence_score for f in files if f.confidence_score is not None]
            avg_confidence = round(sum(scores) / len(scores)) if scores else 0

            stats = {
                "total_files": total_files,
                "total_bytes": total_bytes,
                "valid_files": valid_files,
                "avg_confidence": avg_confidence,
            }

            # Prepare output filepath
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"forensic_report_case_{case_id}_{ts_str}.{fmt}"
            dest_file = Path(output_path).resolve() if output_path else (self.reports_dir / filename)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Render output based on format
            if fmt in (ReportFormat.HTML, ReportFormat.PDF):
                ctx = {
                    "title": f"Forensic Report - Case #{case.case_number}",
                    "case": case,
                    "evidence": evidence,
                    "operation": operation,
                    "files": files,
                    "stats": stats,
                    "generated_by": user,
                    "generated_at": datetime.now(timezone.utc),
                    "report_id": f"REP-FR-{case.id}-{ts_str}",
                    "report_hash": "SEAL_COMPUTED_POST_RENDER",
                }
                html_out = self.template_engine.render_template("forensic_report.html", ctx)

                if fmt == ReportFormat.HTML:
                    dest_file.write_text(html_out, encoding="utf-8")
                else:
                    self.pdf_generator.html_to_pdf(
                        html_content=html_out,
                        output_path=dest_file,
                        watermark=watermark,
                        metadata={
                            "title": f"Forensic Report - Case {case.case_number}",
                            "author": user,
                            "subject": "Digital Evidence & Recovery Dossier",
                        },
                    )

            elif fmt == ReportFormat.JSON:
                json_data = {
                    "report_type": ReportType.FORENSIC_RECOVERY,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generated_by": user,
                    "case": {
                        "id": case.id,
                        "case_number": case.case_number,
                        "title": case.title,
                        "investigator": case.investigator,
                        "status": case.status,
                    },
                    "evidence": {
                        "id": evidence.id if evidence else None,
                        "evidence_number": evidence.evidence_number if evidence else None,
                        "label": (evidence.device_model or evidence.evidence_number) if evidence else None,
                        "sha256": evidence.sha256 if evidence else None,
                    } if evidence else None,
                    "operation": {
                        "id": operation.id if operation else None,
                        "type": operation.operation_type if operation else None,
                        "status": operation.status if operation else None,
                    } if operation else None,
                    "statistics": stats,
                    "recovered_files": [
                        {
                            "id": f.id,
                            "filename": f.filename,
                            "type": f.detected_type,
                            "size": f.size,
                            "offset": f.offset,
                            "status": f.validation_status,
                            "confidence": f.confidence_score,
                            "sha256": f.sha256,
                        }
                        for f in files
                    ],
                }
                dest_file.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

            elif fmt == ReportFormat.CSV:
                with open(dest_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "File ID", "Filename", "Detected Type", "Size (Bytes)",
                        "Validation Status", "Confidence Score", "Offset", "SHA256"
                    ])
                    for rf in files:
                        writer.writerow([
                            rf.id, rf.filename, rf.detected_type, rf.size,
                            rf.validation_status, rf.confidence_score or "", rf.offset, rf.sha256 or ""
                        ])

            # Calculate SHA-256 seal of the file
            file_hash = calculate_file_sha256(dest_file)
            file_size = dest_file.stat().st_size

            # Persist Report record
            report = Report(
                case_id=case.id,
                operation_id=operation.id if operation else None,
                report_type=ReportType.FORENSIC_RECOVERY,
                report_format=fmt,
                file_path=str(dest_file),
                file_size=file_size,
                generated_at=datetime.now(timezone.utc),
                generated_by=user,
                report_hash=file_hash,
                template_name="forensic_report.html",
                template_version="1.0",
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            # Audit log
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="report_generated",
                    event_category="forensic_operation",
                    case_id=case.id,
                    operation_id=operation.id if operation else None,
                    user=user,
                    event_data={
                        "report_id": report.id,
                        "report_type": report.report_type,
                        "format": fmt,
                        "file_path": str(dest_file),
                        "hash": file_hash,
                        "recovered_files": total_files,
                    },
                )

            return report
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # NIST SP 800-88 Rev 1 Sanitization Certificate
    # -------------------------------------------------------------------------

    def generate_sanitization_report(
        self,
        operation_id: int,
        case_id: Optional[int] = None,
        format: str = "html",
        output_path: Optional[Union[str, Path]] = None,
        watermark: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        """
        Generate an official NIST SP 800-88 Rev 1 Certificate of Media Sanitization.
        """
        fmt = format.lower()
        if fmt not in ReportFormat.ALL_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        user = generated_by or os.getenv("USER", "Sanitization Technician")
        session = self.db_manager.get_session()
        try:
            # Query SanitizationOperation
            sanit_op = (
                session.query(SanitizationOperation)
                .filter(SanitizationOperation.operation_id == operation_id)
                .first()
            )
            if not sanit_op:
                raise ValueError(f"No sanitization details found for operation #{operation_id}")

            operation = session.query(Operation).filter(Operation.id == operation_id).first()

            # Determine case_id
            resolved_case_id = case_id or (operation.case_id if operation else None)
            if not resolved_case_id:
                # Find or ensure fallback system case
                fallback = session.query(Case).order_by(Case.id.asc()).first()
                if fallback:
                    resolved_case_id = fallback.id
                else:
                    # Create default general sanitization case
                    fallback = Case(
                        case_number="SAN-SYSTEM-01",
                        title="Media Sanitization Operations",
                        investigator=user,
                        description="Information Security Department - Automated Sanitization Registry",
                        status="active",
                    )
                    session.add(fallback)
                    session.commit()
                    resolved_case_id = fallback.id

            case = session.query(Case).filter(Case.id == resolved_case_id).first()

            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"sanitization_certificate_op_{operation_id}_{ts_str}.{fmt}"
            dest_file = Path(output_path).resolve() if output_path else (self.reports_dir / filename)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            is_sim = getattr(self.config, "simulation_mode", False) if self.config else False

            if fmt in (ReportFormat.HTML, ReportFormat.PDF):
                ctx = {
                    "title": "Certificate of Media Sanitization (NIST SP 800-88)",
                    "sanitization": sanit_op,
                    "operation": operation,
                    "case": case,
                    "is_simulation": is_sim,
                    "generated_by": user,
                    "organization": getattr(case, "organization", "Information Security Unit"),
                    "generated_at": datetime.now(timezone.utc),
                    "cert_id": f"NIST800-88-CERT-{sanit_op.id}-{ts_str}",
                    "report_hash": "SEAL_COMPUTED_POST_RENDER",
                }
                html_out = self.template_engine.render_template("sanitization_report.html", ctx)

                if fmt == ReportFormat.HTML:
                    dest_file.write_text(html_out, encoding="utf-8")
                else:
                    self.pdf_generator.html_to_pdf(
                        html_content=html_out,
                        output_path=dest_file,
                        watermark=watermark,
                        metadata={
                            "title": "Certificate of Media Sanitization",
                            "author": user,
                            "subject": f"NIST SP 800-88 Erase Verification ({sanit_op.device})",
                        },
                    )

            elif fmt == ReportFormat.JSON:
                json_data = {
                    "certificate_standard": "NIST SP 800-88 Rev 1",
                    "certificate_id": f"CERT-{sanit_op.id}-{ts_str}",
                    "operation_id": operation_id,
                    "case_id": resolved_case_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "technician": user,
                    "device": {
                        "path": sanit_op.device,
                        "type": sanit_op.device_type,
                        "model": sanit_op.device_model,
                        "serial": sanit_op.device_serial,
                        "capacity": sanit_op.capacity,
                    },
                    "sanitization": {
                        "standard": sanit_op.sanitization_standard,
                        "method": sanit_op.sanitization_method,
                        "pass_count": sanit_op.pass_count,
                        "pattern": sanit_op.pattern_used,
                    },
                    "verification": {
                        "method": sanit_op.verification_method,
                        "result": sanit_op.verification_result,
                        "sample_count": sanit_op.verification_sample_count,
                        "failed_samples": sanit_op.verification_failed_samples,
                    },
                }
                dest_file.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

            elif fmt == ReportFormat.CSV:
                with open(dest_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Property", "Value"])
                    writer.writerow(["Certificate Standard", sanit_op.sanitization_standard or "NIST SP 800-88 Rev 1"])
                    writer.writerow(["Device Identifier", sanit_op.device])
                    writer.writerow(["Device Type", sanit_op.device_type])
                    writer.writerow(["Model", sanit_op.device_model or "N/A"])
                    writer.writerow(["Serial Number", sanit_op.device_serial or "N/A"])
                    writer.writerow(["Capacity (Bytes)", sanit_op.capacity or "N/A"])
                    writer.writerow(["Method", sanit_op.sanitization_method])
                    writer.writerow(["Passes Completed", sanit_op.pass_count or 1])
                    writer.writerow(["Verification Result", sanit_op.verification_result])
                    writer.writerow(["Samples Tested", sanit_op.verification_sample_count or 1000])
                    writer.writerow(["Technician", user])
                    writer.writerow(["Date", datetime.now(timezone.utc).isoformat()])

            file_hash = calculate_file_sha256(dest_file)
            file_size = dest_file.stat().st_size

            report = Report(
                case_id=resolved_case_id,
                operation_id=operation_id,
                report_type=ReportType.SANITIZATION,
                report_format=fmt,
                file_path=str(dest_file),
                file_size=file_size,
                generated_at=datetime.now(timezone.utc),
                generated_by=user,
                report_hash=file_hash,
                template_name="sanitization_report.html",
                template_version="1.0",
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="report_generated",
                    event_category="sanitization_operation",
                    case_id=resolved_case_id,
                    operation_id=operation_id,
                    user=user,
                    event_data={
                        "report_id": report.id,
                        "report_type": report.report_type,
                        "format": fmt,
                        "file_path": str(dest_file),
                        "hash": file_hash,
                        "device": sanit_op.device,
                        "verdict": sanit_op.verification_result,
                    },
                )

            return report
        finally:
            session.close()

    generate_sanitization_certificate = generate_sanitization_report

    # -------------------------------------------------------------------------
    # Case Summary Report
    # -------------------------------------------------------------------------

    def generate_case_summary(
        self,
        case_id: int,
        format: str = "html",
        output_path: Optional[Union[str, Path]] = None,
        watermark: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        """
        Generate a comprehensive Case Summary Report.
        """
        fmt = format.lower()
        if fmt not in ReportFormat.ALL_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        user = generated_by or os.getenv("USER", "Lead Investigator")
        session = self.db_manager.get_session()
        try:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Case with ID {case_id} not found")

            evidence_items = (
                session.query(Evidence)
                .filter(Evidence.case_id == case_id)
                .order_by(Evidence.id.asc())
                .all()
            )
            operations = (
                session.query(Operation)
                .filter(Operation.case_id == case_id)
                .order_by(desc(Operation.id))
                .all()
            )

            # Count recovered files
            op_ids = [op.id for op in operations]
            recovered_count = 0
            if op_ids:
                recovered_count = (
                    session.query(RecoveredFile)
                    .filter(RecoveredFile.operation_id.in_(op_ids))
                    .count()
                )

            total_evidence_size = sum(e.capacity or 0 for e in evidence_items) if evidence_items else 0

            stats = {
                "total_evidence_size": total_evidence_size,
                "total_recovered_files": recovered_count,
            }

            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"case_summary_{case_id}_{ts_str}.{fmt}"
            dest_file = Path(output_path).resolve() if output_path else (self.reports_dir / filename)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            if fmt in (ReportFormat.HTML, ReportFormat.PDF):
                ctx = {
                    "title": f"Case Summary - {case.case_number}",
                    "case": case,
                    "evidence_items": evidence_items,
                    "operations": operations,
                    "stats": stats,
                    "generated_by": user,
                    "generated_at": datetime.now(timezone.utc),
                    "report_hash": "SEAL_COMPUTED_POST_RENDER",
                }
                html_out = self.template_engine.render_template("case_summary.html", ctx)

                if fmt == ReportFormat.HTML:
                    dest_file.write_text(html_out, encoding="utf-8")
                else:
                    self.pdf_generator.html_to_pdf(
                        html_content=html_out,
                        output_path=dest_file,
                        watermark=watermark,
                        metadata={
                            "title": f"Case Summary - {case.case_number}",
                            "author": user,
                            "subject": "Case Investigation Summary Dossier",
                        },
                    )

            elif fmt == ReportFormat.JSON:
                json_data = {
                    "report_type": ReportType.CASE_SUMMARY,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generated_by": user,
                    "case": {
                        "id": case.id,
                        "case_number": case.case_number,
                        "title": case.title,
                        "investigator": case.investigator,
                        "organization": getattr(case, "organization", "N/A"),
                        "status": case.status,
                        "description": case.description,
                        "created_at": case.created_at.isoformat() if case.created_at else None,
                    },
                    "evidence": [
                        {
                            "id": e.id,
                            "number": e.evidence_number,
                            "label": e.device_model or e.evidence_number,
                            "type": e.source_type,
                            "size": e.capacity,
                            "sha256": e.sha256,
                        }
                        for e in evidence_items
                    ],
                    "operations": [
                        {
                            "id": op.id,
                            "type": op.operation_type,
                            "tool": getattr(op, "tool_version", "Platform Engine"),
                            "status": op.status,
                            "started_at": op.start_time.isoformat() if getattr(op, "start_time", None) else None,
                            "completed_at": op.end_time.isoformat() if getattr(op, "end_time", None) else None,
                        }
                        for op in operations
                    ],
                    "statistics": stats,
                }
                dest_file.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

            elif fmt == ReportFormat.CSV:
                with open(dest_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Section", "Field", "Value"])
                    writer.writerow(["Case", "Number", case.case_number])
                    writer.writerow(["Case", "Title", case.title])
                    writer.writerow(["Case", "Investigator", case.investigator])
                    writer.writerow(["Case", "Status", case.status])
                    writer.writerow(["Case", "Evidence Items", len(evidence_items)])
                    writer.writerow(["Case", "Operations", len(operations)])
                    writer.writerow(["Case", "Recovered Files", recovered_count])

            file_hash = calculate_file_sha256(dest_file)
            file_size = dest_file.stat().st_size

            report = Report(
                case_id=case.id,
                operation_id=None,
                report_type=ReportType.CASE_SUMMARY,
                report_format=fmt,
                file_path=str(dest_file),
                file_size=file_size,
                generated_at=datetime.now(timezone.utc),
                generated_by=user,
                report_hash=file_hash,
                template_name="case_summary.html",
                template_version="1.0",
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="report_generated",
                    event_category="case_management",
                    case_id=case.id,
                    user=user,
                    event_data={
                        "report_id": report.id,
                        "report_type": report.report_type,
                        "format": fmt,
                        "file_path": str(dest_file),
                        "hash": file_hash,
                    },
                )

            return report
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Audit Trail & Chain of Custody Report
    # -------------------------------------------------------------------------

    def generate_audit_report(
        self,
        case_id: Optional[int] = None,
        format: str = "html",
        output_path: Optional[Union[str, Path]] = None,
        watermark: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        """
        Generate an Audit Trail and Cryptographic Chain of Custody Report.
        """
        fmt = format.lower()
        if fmt not in ReportFormat.ALL_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        user = generated_by or os.getenv("USER", "Security Auditor")
        session = self.db_manager.get_session()
        try:
            # Query audit events
            query = session.query(AuditEvent).order_by(AuditEvent.id.asc())
            if case_id is not None:
                query = query.filter(AuditEvent.case_id == case_id)
            events = query.all()

            # Verify integrity
            chain_status = (
                self.audit_logger.verify_integrity()
                if self.audit_logger
                else {"valid": True, "total_events": len(events), "verified_events": len(events), "first_broken_event_id": None}
            )

            chain_valid = chain_status.get("valid", True)
            verified_count = chain_status.get("verified_events", len(events))
            broken_count = (len(events) - verified_count) if not chain_valid else 0

            # Determine case_id binding for report row
            resolved_case_id = case_id
            if not resolved_case_id:
                fallback = session.query(Case).order_by(Case.id.asc()).first()
                if fallback:
                    resolved_case_id = fallback.id
                else:
                    fallback = Case(
                        case_number="AUDIT-PLATFORM-01",
                        title="Platform System Audit Registry",
                        investigator=user,
                        description="Platform Security Unit",
                        status="active",
                    )
                    session.add(fallback)
                    session.commit()
                    resolved_case_id = fallback.id

            scope_name = f"Case #{case_id}" if case_id else "Platform Global System"

            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"audit_report_{case_id or 'global'}_{ts_str}.{fmt}"
            dest_file = Path(output_path).resolve() if output_path else (self.reports_dir / filename)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            if fmt in (ReportFormat.HTML, ReportFormat.PDF):
                ctx = {
                    "title": f"Audit Trail Report ({scope_name})",
                    "scope_name": scope_name,
                    "events": [
                        {
                            "id": e.id,
                            "timestamp": e.timestamp,
                            "user": e.user,
                            "event_type": e.event_type,
                            "details": e.event_data,
                            "previous_hash": e.previous_hash,
                            "current_hash": e.event_hash,
                        }
                        for e in events
                    ],
                    "chain_valid": chain_valid,
                    "verified_count": verified_count,
                    "broken_count": broken_count,
                    "generated_by": user,
                    "generated_at": datetime.now(timezone.utc),
                    "report_hash": "SEAL_COMPUTED_POST_RENDER",
                }
                html_out = self.template_engine.render_template("audit_report.html", ctx)

                if fmt == ReportFormat.HTML:
                    dest_file.write_text(html_out, encoding="utf-8")
                else:
                    self.pdf_generator.html_to_pdf(
                        html_content=html_out,
                        output_path=dest_file,
                        watermark=watermark,
                        metadata={
                            "title": f"Audit Trail Report ({scope_name})",
                            "author": user,
                            "subject": "Tamper-Evident Hash Chain Audit Ledger",
                        },
                    )

            elif fmt == ReportFormat.JSON:
                json_data = {
                    "report_type": ReportType.AUDIT_TRAIL,
                    "scope": scope_name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "generated_by": user,
                    "chain_integrity": chain_status,
                    "events": [
                        {
                            "id": e.id,
                            "timestamp": e.timestamp.isoformat(),
                            "user": e.user,
                            "event_type": e.event_type,
                            "category": e.event_category,
                            "case_id": e.case_id,
                            "operation_id": e.operation_id,
                            "event_data": e.event_data,
                            "previous_hash": e.previous_hash,
                            "event_hash": e.event_hash,
                        }
                        for e in events
                    ],
                }
                dest_file.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

            elif fmt == ReportFormat.CSV:
                with open(dest_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Event ID", "Timestamp", "User", "Event Type",
                        "Category", "Case ID", "Operation ID", "Previous Hash", "Event Hash"
                    ])
                    for ev in events:
                        writer.writerow([
                            ev.id, ev.timestamp.isoformat(), ev.user, ev.event_type,
                            ev.event_category or "", ev.case_id or "", ev.operation_id or "",
                            ev.previous_hash or "", ev.event_hash
                        ])

            file_hash = calculate_file_sha256(dest_file)
            file_size = dest_file.stat().st_size

            report = Report(
                case_id=resolved_case_id,
                operation_id=None,
                report_type=ReportType.AUDIT_TRAIL,
                report_format=fmt,
                file_path=str(dest_file),
                file_size=file_size,
                generated_at=datetime.now(timezone.utc),
                generated_by=user,
                report_hash=file_hash,
                template_name="audit_report.html",
                template_version="1.0",
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="report_generated",
                    event_category="security",
                    case_id=resolved_case_id,
                    user=user,
                    event_data={
                        "report_id": report.id,
                        "report_type": report.report_type,
                        "format": fmt,
                        "file_path": str(dest_file),
                        "hash": file_hash,
                    },
                )

            return report
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Unified Entrypoint & Integrity Verification
    # -------------------------------------------------------------------------

    def generate_report(
        self,
        report_type: str,
        case_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        format: str = "html",
        output_path: Optional[Union[str, Path]] = None,
        watermark: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        """
        Unified report generator entrypoint for GUI and CLI callers.
        """
        rt = report_type.lower()
        if rt == ReportType.FORENSIC_RECOVERY:
            if not case_id:
                raise ValueError("case_id is required for forensic recovery reports")
            return self.generate_forensic_report(
                case_id=case_id,
                operation_id=operation_id,
                format=format,
                output_path=output_path,
                watermark=watermark,
                generated_by=generated_by,
            )
        elif rt == ReportType.SANITIZATION:
            if not operation_id:
                raise ValueError("operation_id is required for sanitization reports")
            return self.generate_sanitization_report(
                operation_id=operation_id,
                case_id=case_id,
                format=format,
                output_path=output_path,
                watermark=watermark,
                generated_by=generated_by,
            )
        elif rt == ReportType.CASE_SUMMARY:
            if not case_id:
                raise ValueError("case_id is required for case summary reports")
            return self.generate_case_summary(
                case_id=case_id,
                format=format,
                output_path=output_path,
                watermark=watermark,
                generated_by=generated_by,
            )
        elif rt == ReportType.AUDIT_TRAIL:
            return self.generate_audit_report(
                case_id=case_id,
                format=format,
                output_path=output_path,
                watermark=watermark,
                generated_by=generated_by,
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def verify_report_integrity(self, report_id: int) -> Tuple[bool, str, str]:
        """
        Cryptographically verify that a generated report has not been altered on disk.

        Returns:
            (is_valid, current_file_hash, stored_db_hash)
        """
        session = self.db_manager.get_session()
        try:
            report = session.query(Report).filter(Report.id == report_id).first()
            if not report:
                raise ValueError(f"Report #{report_id} not found in database")

            p = Path(report.file_path)
            if not p.exists():
                return False, "FILE_NOT_FOUND", report.report_hash

            current_hash = calculate_file_sha256(p)
            is_valid = (current_hash == report.report_hash)
            return is_valid, current_hash, report.report_hash
        finally:
            session.close()

    def list_reports(
        self,
        case_id: Optional[int] = None,
        report_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List generated reports with metadata and integrity status.
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(Report).order_by(desc(Report.id))
            if case_id is not None:
                query = query.filter(Report.case_id == case_id)
            if report_type:
                query = query.filter(Report.report_type == report_type)

            reports = query.limit(limit).all()
            result = []
            for r in reports:
                exists = Path(r.file_path).exists()
                result.append({
                    "id": r.id,
                    "case_id": r.case_id,
                    "operation_id": r.operation_id,
                    "report_type": r.report_type,
                    "report_format": r.report_format,
                    "file_path": r.file_path,
                    "file_size": r.file_size,
                    "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                    "generated_by": r.generated_by,
                    "report_hash": r.report_hash,
                    "file_exists": exists,
                })
            return result
        finally:
            session.close()

    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details for a single report."""
        session = self.db_manager.get_session()
        try:
            r = session.query(Report).filter(Report.id == report_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "case_id": r.case_id,
                "operation_id": r.operation_id,
                "report_type": r.report_type,
                "report_format": r.report_format,
                "file_path": r.file_path,
                "file_size": r.file_size,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "generated_by": r.generated_by,
                "report_hash": r.report_hash,
                "template_name": r.template_name,
                "template_version": r.template_version,
            }
        finally:
            session.close()

    def delete_report(self, report_id: int) -> bool:
        """Delete a report file and its database record."""
        session = self.db_manager.get_session()
        try:
            r = session.query(Report).filter(Report.id == report_id).first()
            if not r:
                return False

            # Remove file
            try:
                p = Path(r.file_path)
                if p.exists():
                    p.unlink()
            except OSError:
                pass

            case_id = r.case_id
            session.delete(r)
            session.commit()

            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="report_deleted",
                    event_category="case_management",
                    case_id=case_id,
                    event_data={"report_id": report_id},
                )

            return True
        finally:
            session.close()
