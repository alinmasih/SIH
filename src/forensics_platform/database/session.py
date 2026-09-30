"""
Database session management for the forensics platform.

Handles database initialization, session creation, and connection management.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from forensics_platform.database.models import Base
from forensics_platform.utils.hashing import hash_string


class DatabaseManager:
    """
    Database connection and session management.

    Handles database initialization, session creation, and cleanup.
    """

    def __init__(self, database_path: Path):
        """
        Initialize database manager.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.engine = None
        self._Session = None
        self._initialized = False

    def initialize(self):
        """
        Initialize the database connection and create tables.

        Creates the database file and all tables if they don't exist.
        """
        # Create database directory
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        db_url = f"sqlite:///{self.database_path}"
        self.engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True
        )

        # Enable foreign keys for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        # Create all tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self._Session = sessionmaker(bind=self.engine)

        self._initialized = True

        # Create genesis audit event if this is a new database
        self._create_genesis_event()

    def _create_genesis_event(self):
        """Create the genesis audit event if the audit_events table is empty."""
        with self.session() as session:
            from forensics_platform.database.models import AuditEvent

            existing_count = session.query(AuditEvent).count()
            if existing_count == 0:
                from forensics_platform.audit.hash_chain import calculate_event_hash

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                timestamp_str = now.isoformat()
                genesis_data = json.dumps({
                    "action": "database_initialized",
                    "timestamp": timestamp_str,
                    "version": "1.0.0"
                }, sort_keys=True)

                # Genesis event has no previous hash
                event_hash = calculate_event_hash(
                    timestamp=timestamp_str,
                    user="SYSTEM",
                    event_type="database_initialized",
                    event_data=genesis_data,
                    previous_hash=None,
                )

                genesis_event = AuditEvent(
                    timestamp=now,
                    user="SYSTEM",
                    user_role="system",
                    event_type="database_initialized",
                    event_category="system",
                    event_data=genesis_data,
                    previous_hash=None,
                    event_hash=event_hash,
                )
                session.add(genesis_event)
                session.commit()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Create a database session context manager.

        Usage:
            with db_manager.session() as session:
                case = session.query(Case).first()

        Yields:
            SQLAlchemy Session

        Raises:
            RuntimeError: If database not initialized
        """
        if not self._initialized or self._Session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """
        Get a new database session.

        Caller is responsible for committing/closing the session.

        Returns:
            SQLAlchemy Session

        Raises:
            RuntimeError: If database not initialized
        """
        if not self._initialized or self._Session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self._Session()

    def close(self):
        """Close the database connection"""
        if self.engine:
            self.engine.dispose()

    def backup(self, backup_path: Path):
        """
        Create a backup of the database.

        Args:
            backup_path: Path for backup file
        """
        import shutil

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.database_path, backup_path)

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        from forensics_platform.core.config import get_config
        config = get_config()
        _db_manager = DatabaseManager(config.database_path)
        _db_manager.initialize()
    return _db_manager


def get_session() -> Session:
    """Get a new database session from global manager"""
    return get_database_manager().get_session()
