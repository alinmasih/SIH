"""
Carving Engine module - end-to-end file carving pipeline.

Coordinates signature scanning, format validation, confidence scoring,
disk extraction, database persistence, and audit logging.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from forensics_platform.carving.confidence_engine import ConfidenceEngine, ConfidenceScore
from forensics_platform.carving.signature_database import FileSignature, SignatureDatabase
from forensics_platform.carving.signature_scanner import ScanCandidate, SignatureScanner
from forensics_platform.carving.validators import BaseValidator, ValidationResult, ValidatorRegistry
from forensics_platform.database.models import Operation, RecoveredFile
from forensics_platform.database.session import DatabaseManager
from forensics_platform.utils.hashing import calculate_md5, calculate_sha256

logger = logging.getLogger(__name__)


class CarvingEngine:
    """
    High-performance, non-destructive file carving engine.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        audit_logger: Optional[Any] = None,
        signature_db: Optional[SignatureDatabase] = None,
    ):
        """
        Initialize carving engine.

        Args:
            db_manager: Optional DatabaseManager for persistence.
            audit_logger: Optional AuditLogger for chained event logging.
            signature_db: Optional SignatureDatabase.
        """
        self.db = db_manager
        self.audit = audit_logger
        self.sig_db = signature_db or SignatureDatabase()
        self.scanner = SignatureScanner()
        self.validators = ValidatorRegistry()
        self.confidence_engine = ConfidenceEngine()

    def carve_image(
        self,
        image_path: Union[str, Path],
        target_types: Optional[List[str]] = None,
        min_confidence: int = 50,
        output_dir: Optional[Union[str, Path]] = None,
        case_id: Optional[int] = None,
        evidence_id: Optional[int] = None,
        sector_aligned: bool = True,
        sector_size: int = 512,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan image, validate candidates, calculate confidence, and carve files.

        Args:
            image_path: Path to disk image or media.
            target_types: List of file types to target (e.g. ['jpeg', 'png', 'pdf', 'zip']).
            min_confidence: Minimum score (0-100) required to save carved file.
            output_dir: Directory to save carved files (defaults to image_dir/carved).
            case_id: Optional Case ID for database correlation.
            evidence_id: Optional Evidence ID.
            sector_aligned: Optimize search to sector boundaries.
            sector_size: Bytes per sector (default 512).
            progress_callback: Optional callback reporting dict with progress info.
            cancel_token: Optional callback returning True if cancellation requested.

        Returns:
            List of dictionaries describing successfully carved files.
        """
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Target image does not exist: {img_path}")

        file_size = img_path.stat().st_size

        # Resolve target signatures
        all_sigs = self.sig_db.list_signatures()
        if target_types:
            clean_targets = [t.lower().strip() for t in target_types]
            active_sigs = [s for s in all_sigs if s.file_type in clean_targets]
        else:
            active_sigs = all_sigs

        if not active_sigs:
            logger.warning("No active signatures match requested target types.")
            return []

        self.scanner.set_signatures(active_sigs)

        # Output directory setup
        if output_dir is None:
            out_path = img_path.parent / "carved"
        else:
            out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Audit logging start
        if self.audit:
            self.audit.log_event(
                event_type="carving_started",
                event_data={
                    "image_path": str(img_path),
                    "file_size": file_size,
                    "target_types": [s.file_type for s in active_sigs],
                    "min_confidence": min_confidence,
                    "sector_aligned": sector_aligned,
                },
                case_id=case_id,
                evidence_id=evidence_id,
            )

        # Database Operation tracking
        op_id = None
        if self.db:
            try:
                with self.db.session() as session:
                    op = Operation(
                        case_id=case_id,
                        operation_type="file_carving",
                        target=str(img_path),
                        target_type="disk_image",
                        start_time=datetime.now(timezone.utc),
                        status="running",
                        tool_version="CarvingEngine 1.0",
                        parameters=json.dumps({
                            "target_types": [s.file_type for s in active_sigs],
                            "min_confidence": min_confidence,
                            "sector_aligned": sector_aligned,
                        }),
                    )
                    session.add(op)
                    session.commit()
                    op_id = op.id
            except Exception as e:
                logger.error(f"Failed to record carving operation in database: {e}")

        carved_results: List[Dict[str, Any]] = []
        candidates_found = 0
        bytes_scanned = 0

        try:
            with open(img_path, "rb") as f:
                def on_scanner_progress(processed: int, total: int):
                    nonlocal bytes_scanned
                    bytes_scanned = processed
                    if progress_callback:
                        progress_callback({
                            "status": "scanning",
                            "bytes_scanned": processed,
                            "total_bytes": total,
                            "percent": round((processed / total) * 100, 1) if total > 0 else 0,
                            "candidates_found": candidates_found,
                            "files_carved": len(carved_results),
                        })

                # Stream and identify candidates
                for candidate in self.scanner.scan_file(
                    file_path=img_path,
                    chunk_size=2 * 1024 * 1024,
                    sector_aligned=sector_aligned,
                    sector_size=sector_size,
                    progress_callback=on_scanner_progress,
                ):
                    if cancel_token and cancel_token():
                        logger.info("Carving cancelled by user request.")
                        break

                    candidates_found += 1
                    sig = candidate.signature

                    # Seek to candidate start and read window
                    f.seek(candidate.start_offset)
                    read_limit = min(sig.max_size, file_size - candidate.start_offset)
                    candidate_data = f.read(read_limit)

                    if not candidate_data:
                        continue

                    # Validate format
                    validator = self.validators.get_validator(sig.validator)
                    validation: ValidationResult = validator.validate(candidate_data)

                    estimated_size = validation.estimated_size
                    if estimated_size <= 0:
                        estimated_size = min(len(candidate_data), sig.max_size)

                    carved_bytes = candidate_data[:estimated_size]

                    # Score confidence
                    confidence: ConfidenceScore = self.confidence_engine.evaluate(
                        signature=sig,
                        validation=validation,
                        data=carved_bytes,
                    )

                    # Filter by confidence threshold
                    if confidence.total < min_confidence:
                        continue

                    # Determine filename and extension
                    ext = sig.extensions[0] if sig.extensions else sig.file_type
                    carved_name = f"carved_{sig.file_type}_{candidate.start_offset:08x}.{ext}"
                    carved_file_path = out_path / carved_name

                    # Save carved bytes to file
                    with open(carved_file_path, "wb") as out_f:
                        out_f.write(carved_bytes)

                    # Calculate hashes
                    sha256 = calculate_sha256(carved_file_path)
                    md5 = calculate_md5(carved_file_path)

                    # Persist record in database
                    rec_id = None
                    if self.db and op_id:
                        try:
                            with self.db.session() as session:
                                val_status = "valid" if validation.is_valid else "partial"
                                rec = RecoveredFile(
                                    operation_id=op_id,
                                    path=str(carved_file_path),
                                    filename=carved_name,
                                    detected_type=sig.file_type,
                                    mime_type=sig.mime_type,
                                    extension=ext,
                                    size=len(carved_bytes),
                                    offset=candidate.start_offset,
                                    recovery_method="signature_carving",
                                    validation_status=val_status,
                                    confidence_score=confidence.total,
                                    confidence_details=json.dumps(confidence.factors),
                                    sha256=sha256,
                                    md5=md5,
                                    file_metadata=json.dumps(validation.details),
                                    created_at=datetime.now(timezone.utc),
                                )
                                session.add(rec)
                                session.commit()
                                rec_id = rec.id
                        except Exception as e:
                            logger.error(f"Failed to record carved file in DB: {e}")

                    # Log audit event
                    if self.audit:
                        self.audit.log_event(
                            event_type="file_carved",
                            event_data={
                                "filename": carved_name,
                                "path": str(carved_file_path),
                                "file_type": sig.file_type,
                                "offset": candidate.start_offset,
                                "size": len(carved_bytes),
                                "confidence_score": confidence.total,
                                "confidence_level": confidence.classification,
                                "sha256": sha256,
                            },
                            case_id=case_id,
                            evidence_id=evidence_id,
                        )

                    result_info = {
                        "id": rec_id,
                        "filename": carved_name,
                        "path": str(carved_file_path),
                        "file_type": sig.file_type,
                        "offset": candidate.start_offset,
                        "size": len(carved_bytes),
                        "confidence_score": confidence.total,
                        "confidence_classification": confidence.classification,
                        "sha256": sha256,
                        "md5": md5,
                        "details": validation.details,
                    }
                    carved_results.append(result_info)

                    if progress_callback:
                        progress_callback({
                            "status": "carving",
                            "bytes_scanned": bytes_scanned,
                            "total_bytes": file_size,
                            "percent": round((bytes_scanned / file_size) * 100, 1) if file_size > 0 else 0,
                            "candidates_found": candidates_found,
                            "files_carved": len(carved_results),
                            "latest_carved": result_info,
                        })

        finally:
            # Complete DB operation
            if self.db and op_id:
                try:
                    with self.db.session() as session:
                        op = session.get(Operation, op_id)
                        if op:
                            op.status = "completed"
                            op.end_time = datetime.now(timezone.utc)
                            op.result = json.dumps({"carved_count": len(carved_results)})
                            op.items_found = len(carved_results)
                            session.commit()
                except Exception as e:
                    logger.error(f"Failed to close operation record: {e}")

            # Complete audit logging
            if self.audit:
                self.audit.log_event(
                    event_type="carving_completed",
                    event_data={
                        "image_path": str(img_path),
                        "candidates_found": candidates_found,
                        "files_carved": len(carved_results),
                    },
                    case_id=case_id,
                    evidence_id=evidence_id,
                )

        return carved_results
