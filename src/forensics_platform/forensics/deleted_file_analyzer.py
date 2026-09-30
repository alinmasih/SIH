"""
Deleted File Recovery Analyzer.

Specializes in discovering and recovering deleted files from unallocated filesystem
records, extracting bitstreams, computing cryptographic hashes, and recording
recovered evidence in the database.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Union

from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper
from forensics_platform.forensics.filesystem_analyzer import FilesystemAnalyzer
from forensics_platform.database.session import DatabaseManager
from forensics_platform.database.models import Operation, RecoveredFile
from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.utils.hashing import calculate_sha256, calculate_md5
from forensics_platform.utils.logging import get_logger

if TYPE_CHECKING:
    from forensics_platform.core.config import Config


logger = get_logger(__name__)


def guess_file_type(filename: str) -> str:
    """Infer file type categorization from extension."""
    ext = Path(filename).suffix.lower().lstrip(".")
    type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip",
        "tar": "application/x-tar",
        "gz": "application/gzip",
        "txt": "text/plain",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "sqlite": "application/x-sqlite3",
        "db": "application/x-sqlite3",
    }
    return type_map.get(ext, "application/octet-stream")


class DeletedFileAnalyzer:
    """
    Coordinates detection, extraction, and cryptographic verification
    of deleted files from forensic storage images.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        audit_logger: AuditLogger,
        config: Config,
        tsk_wrapper: Optional[SleuthKitWrapper] = None
    ):
        self.db = db_manager
        self.audit = audit_logger
        self.config = config
        self.tsk = tsk_wrapper or SleuthKitWrapper()
        self.fs_analyzer = FilesystemAnalyzer(self.tsk)

    def scan_deleted_files(
        self,
        image_path: Union[str, Path],
        offset_sectors: int = 0,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scan a partition for deleted files.

        Args:
            image_path: Disk image path
            offset_sectors: Partition offset in sectors
            recursive: Whether to scan subdirectories

        Returns:
            List of deleted file metadata dictionaries
        """
        all_files = self.fs_analyzer.list_files(
            image_path,
            offset_sectors=offset_sectors,
            deleted_only=True,
            recursive=recursive
        )
        # Filter strictly for deleted files (not directories)
        deleted_files = [f for f in all_files if f.get("is_deleted") and not f.get("is_directory")]
        return deleted_files

    def recover_file(
        self,
        image_path: Union[str, Path],
        offset_sectors: int,
        inode: Union[int, str],
        filename: str,
        output_dir: Union[str, Path],
        case_id: Optional[int] = None,
        operation_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a single deleted file by inode, hash it, and record in DB.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition starting sector
            inode: Inode number
            filename: Target file name
            output_dir: Directory where recovered file should be written
            case_id: Optional case to associate with
            operation_id: Optional operation ID to associate with

        Returns:
            Dictionary with recovered file details or None if failed
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        # Clean filename of unsafe characters
        safe_name = os.path.basename(filename).replace("/", "_").replace("\\", "_")
        target_file = out_dir / safe_name

        # Avoid overwriting
        counter = 1
        base_stem = target_file.stem
        base_suffix = target_file.suffix
        while target_file.exists():
            target_file = out_dir / f"{base_stem}_{counter}{base_suffix}"
            counter += 1

        success = self.tsk.extract_file_by_inode(
            image_path=image_path,
            offset_sectors=offset_sectors,
            inode=inode,
            output_path=target_file
        )

        if not success or not target_file.exists():
            logger.error(f"Failed to extract deleted inode {inode} from {image_path}")
            return None

        file_size = target_file.stat().st_size
        sha256_hash = calculate_sha256(target_file)
        md5_hash = calculate_md5(target_file)
        detected_type = guess_file_type(safe_name)

        # Database transaction
        with self.db.session() as session:
            # Ensure an active operation exists
            op_id = operation_id
            if not op_id:
                op = Operation(
                    case_id=case_id,
                    operation_type="deleted_file_recovery",
                    target=str(image_path),
                    target_type="disk_image",
                    start_time=datetime.now(timezone.utc),
                    status="completed",
                    tool_version=self.tsk.get_version(),
                )
                session.add(op)
                session.commit()
                op_id = op.id

            recovered_rec = RecoveredFile(
                operation_id=op_id,
                path=str(target_file),
                filename=safe_name,
                detected_type=detected_type,
                extension=target_file.suffix.lstrip("."),
                size=file_size,
                offset=offset_sectors * 512,
                recovery_method="tsk_icat",
                validation_status="valid" if file_size > 0 else "unknown",
                confidence_score=90 if file_size > 0 else 30,
                sha256=sha256_hash,
                md5=md5_hash,
                is_fragmented=False,
                created_at=datetime.now(timezone.utc),
            )
            session.add(recovered_rec)
            session.commit()

            rec_id = recovered_rec.id
            result_dict = {
                "id": rec_id,
                "operation_id": op_id,
                "path": str(target_file),
                "filename": safe_name,
                "size": file_size,
                "detected_type": detected_type,
                "sha256": sha256_hash,
                "md5": md5_hash,
                "inode": str(inode),
                "recovered_at": recovered_rec.created_at.isoformat(),
            }

        self.audit.log_event(
            event_type="file_recovered",
            event_data=result_dict,
            event_category="forensic_operation",
            case_id=case_id,
            operation_id=op_id,
        )

        return result_dict

    def recover_all_deleted(
        self,
        image_path: Union[str, Path],
        offset_sectors: int,
        output_dir: Union[str, Path],
        case_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Recover all deleted files discovered on a partition.

        Args:
            image_path: Path to disk image
            offset_sectors: Partition starting sector
            output_dir: Output folder
            case_id: Optional associated case ID

        Returns:
            List of recovered file dictionaries
        """
        # First try bulk recovery via tsk_recover
        recovered_paths = self.tsk.recover_deleted_files(
            image_path=image_path,
            offset_sectors=offset_sectors,
            output_dir=output_dir
        )

        results = []
        with self.db.session() as session:
            op = Operation(
                case_id=case_id,
                operation_type="bulk_deleted_recovery",
                target=str(image_path),
                target_type="disk_image",
                start_time=datetime.now(timezone.utc),
                status="completed",
                tool_version=self.tsk.get_version(),
            )
            session.add(op)
            session.commit()
            op_id = op.id

            for p in recovered_paths:
                file_size = p.stat().st_size
                sha256_hash = calculate_sha256(p)
                md5_hash = calculate_md5(p)
                safe_name = p.name
                det_type = guess_file_type(safe_name)

                rec = RecoveredFile(
                    operation_id=op_id,
                    path=str(p),
                    filename=safe_name,
                    detected_type=det_type,
                    extension=p.suffix.lstrip("."),
                    size=file_size,
                    offset=offset_sectors * 512,
                    recovery_method="tsk_recover",
                    validation_status="valid" if file_size > 0 else "unknown",
                    confidence_score=85,
                    sha256=sha256_hash,
                    md5=md5_hash,
                    is_fragmented=False,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(rec)
                session.commit()

                results.append({
                    "id": rec.id,
                    "operation_id": op_id,
                    "path": str(p),
                    "filename": safe_name,
                    "size": file_size,
                    "sha256": sha256_hash,
                })

        self.audit.log_event(
            event_type="bulk_recovery_completed",
            event_data={
                "total_recovered": len(results),
                "image_path": str(image_path),
                "offset_sectors": offset_sectors,
                "output_dir": str(output_dir),
            },
            event_category="forensic_operation",
            case_id=case_id,
            operation_id=op_id,
        )

        return results
