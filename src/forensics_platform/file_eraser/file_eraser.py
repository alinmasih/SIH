"""
File Eraser module - high-level file and directory deletion coordinator.

Provides recursive directory walking, system directory protection, audit logging,
and database operation tracking.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union

if TYPE_CHECKING:
    from forensics_platform.core.config import Config

from forensics_platform.database.models import Operation
from forensics_platform.database.session import DatabaseManager
from forensics_platform.file_eraser.shredder import FileShredder, ShredMethod
from forensics_platform.utils.hashing import calculate_sha256

logger = logging.getLogger(__name__)

SYSTEM_PROTECTED_PATHS: Set[str] = {
    "/",
    "/bin",
    "/sbin",
    "/etc",
    "/usr",
    "/lib",
    "/lib64",
    "/boot",
    "/sys",
    "/proc",
    "/dev",
    "/run",
    "/var",
}


class FileEraser:
    """Manages secure file and directory destruction with safety interlocks."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        audit_logger: Optional[Any] = None,
        config: Optional["Config"] = None,
    ):
        self.db = db_manager
        self.audit = audit_logger
        if config is None:
            from forensics_platform.core.config import Config
            config = Config()
        self.config = config
        self.shredder = FileShredder()

    @staticmethod
    def is_protected(path: Union[str, Path]) -> bool:
        """Check if path or any of its parents is a protected system directory."""
        resolved = Path(path).resolve()
        resolved_str = str(resolved)
        if resolved_str in SYSTEM_PROTECTED_PATHS:
            return True
        for parent in resolved.parents:
            p_str = str(parent)
            if p_str in SYSTEM_PROTECTED_PATHS and p_str != "/":
                return True
        return False

    def erase_file(
        self,
        file_path: Union[str, Path],
        method: ShredMethod = ShredMethod.ZERO,
        case_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Erase a single file with safety check, shredding, and audit logging.

        Args:
            file_path: Target file path.
            method: ShredMethod algorithm.
            case_id: Optional active Case ID.

        Returns:
            Dict describing outcome.
        """
        p = Path(file_path).resolve()
        if self.is_protected(p):
            return {"path": str(p), "success": False, "error": "Protected system path"}

        if not p.exists() or not p.is_file():
            return {"path": str(p), "success": False, "error": "File does not exist or is not a regular file"}

        size = p.stat().st_size
        sha_before = calculate_sha256(p)

        # Shred file
        success = self.shredder.shred_file(p, method=method, wipe_metadata=True)

        if success and self.audit:
            self.audit.log_event(
                event_type="file_deleted",
                event_data={
                    "path": str(p),
                    "size_bytes": size,
                    "sha256_before": sha_before,
                    "method": method.value,
                },
                case_id=case_id,
            )

        return {
            "path": str(p),
            "size": size,
            "sha256_before": sha_before,
            "method": method.value,
            "success": success,
        }

    def erase_batch(
        self,
        paths: List[Union[str, Path]],
        method: ShredMethod = ShredMethod.ZERO,
        case_id: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Securely erase multiple files or directories.

        Args:
            paths: List of file and directory paths.
            method: ShredMethod algorithm.
            case_id: Optional active Case ID.
            progress_callback: Optional callback reporting dict.
            cancel_token: Optional callback returning True if cancelled.

        Returns:
            Summary dict with total files erased and errors.
        """
        # Collect all individual files
        files_to_delete: List[Path] = []
        dirs_to_clean: List[Path] = []

        for p_in in paths:
            p = Path(p_in).resolve()
            if not p.exists() or self.is_protected(p):
                continue
            if p.is_file():
                files_to_delete.append(p)
            elif p.is_dir():
                for root, _, files in os.walk(p, topdown=False):
                    for f in files:
                        files_to_delete.append(Path(root) / f)
                    dirs_to_clean.append(Path(root))

        total_files = len(files_to_delete)
        deleted_count = 0
        total_bytes = 0
        errors: List[str] = []

        op_id = None
        if self.db:
            try:
                with self.db.session() as session:
                    op = Operation(
                        case_id=case_id,
                        operation_type="file_deletion",
                        target=f"Batch Deletion ({total_files} files)",
                        target_type="logical_files",
                        start_time=datetime.now(timezone.utc),
                        status="running",
                        tool_version="FileEraser 1.0",
                        parameters=json.dumps({"method": method.value, "file_count": total_files}),
                    )
                    session.add(op)
                    session.commit()
                    op_id = op.id
            except Exception as e:
                logger.error(f"Failed to record file deletion operation in DB: {e}")

        for idx, file_p in enumerate(files_to_delete, start=1):
            if cancel_token and cancel_token():
                errors.append("Batch erasure cancelled by user request.")
                break

            res = self.erase_file(file_p, method=method, case_id=case_id)
            if res.get("success"):
                deleted_count += 1
                total_bytes += res.get("size", 0)
            else:
                errors.append(f"{file_p}: {res.get('error', 'Deletion failed')}")

            if progress_callback:
                progress_callback({
                    "current": idx,
                    "total": total_files,
                    "percent": round((idx / total_files) * 100, 1) if total_files > 0 else 0,
                    "current_file": str(file_p),
                    "deleted_count": deleted_count,
                    "total_bytes": total_bytes,
                })

        # Remove now-empty directory structures
        for d in dirs_to_clean:
            try:
                if d.exists() and not self.is_protected(d):
                    d.rmdir()
            except OSError:
                pass

        if self.db and op_id:
            try:
                with self.db.session() as session:
                    op = session.get(Operation, op_id)
                    if op:
                        op.status = "completed"
                        op.end_time = datetime.now(timezone.utc)
                        op.items_processed = deleted_count
                        op.bytes_processed = total_bytes
                        op.result = json.dumps({"deleted": deleted_count, "errors": len(errors)})
                        session.commit()
            except Exception as e:
                logger.error(f"Failed to close file deletion operation: {e}")

        return {
            "total_requested": total_files,
            "deleted_count": deleted_count,
            "total_bytes": total_bytes,
            "errors": errors,
        }

    def erase_directory(
        self,
        directory_path: Union[str, Path],
        method: ShredMethod = ShredMethod.ZERO,
        case_id: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Securely erase an entire directory structure and all its contents."""
        return self.erase_batch(
            paths=[directory_path],
            method=method,
            case_id=case_id,
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )
