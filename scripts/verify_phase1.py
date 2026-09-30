#!/usr/bin/env python3
"""
Test runner and verification script for Phase 1.

Tests all foundation components:
- Configuration system
- Hashing utilities
- Database models
- Audit logging
- Core functionality
"""

import sys
import tempfile
from pathlib import Path

print("=" * 80)
print("FORENSICS PLATFORM - PHASE 1 VERIFICATION")
print("=" * 80)
print()

# Test 1: Import all core modules
print("[1/8] Testing module imports...")
try:
    from forensics_platform import __version__
    from forensics_platform.core import Config, ConfigManager, ApplicationController
    from forensics_platform.utils import calculate_sha256, hash_string
    from forensics_platform.database import Case, Evidence, DatabaseManager
    from forensics_platform.audit import AuditLogger
    print("✓ All modules imported successfully")
    print(f"  Version: {__version__}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Configuration system
print("\n[2/8] Testing configuration system...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        manager = ConfigManager(config_path)
        assert manager.config.app_name == "Forensics Platform"
        assert manager.config.simulation_mode == True  # Safety default
        print("✓ Configuration system working")
        print(f"  Simulation mode (safety): {manager.config.simulation_mode}")
except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    sys.exit(1)

# Test 3: Hashing utilities
print("\n[3/8] Testing hashing utilities...")
try:
    test_data = b"Hello, Forensics!"
    hash_value = hash_string("test", "sha256")
    assert len(hash_value) == 64
    print("✓ Hashing utilities working")
    print(f"  SHA-256 output length: {len(hash_value)} chars")
except Exception as e:
    print(f"✗ Hashing test failed: {e}")
    sys.exit(1)

# Test 4: Database initialization
print("\n[4/8] Testing database initialization...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.initialize()
        assert db_manager.is_initialized == True
        assert db_path.exists()
        print("✓ Database initialization working")
        print(f"  Database file created: {db_path.name}")
        db_manager.close()
except Exception as e:
    print(f"✗ Database test failed: {e}")
    sys.exit(1)

# Test 5: Database models
print("\n[5/8] Testing database models...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.initialize()

        with db_manager.session() as session:
            case = Case(
                case_number="CASE-2026-TEST",
                title="Verification Test",
                investigator="System"
            )
            session.add(case)
            session.commit()
            assert case.id is not None
            case_id = case.id

        print("✓ Database models working")
        print(f"  Created test case with ID: {case_id}")
        db_manager.close()
except Exception as e:
    print(f"✗ Database model test failed: {e}")
    sys.exit(1)

# Test 6: Audit logging
print("\n[6/8] Testing audit logging...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.initialize()

        audit_logger = AuditLogger(db_manager.get_session)
        event_id = audit_logger.log_event(
            event_type="test_event",
            event_data={"test": "data"}
        )

        assert event_id is not None
        print("✓ Audit logging working")
        print(f"  Created audit event with ID: {event_id}")
        db_manager.close()
except Exception as e:
    print(f"✗ Audit logging test failed: {e}")
    sys.exit(1)

# Test 7: Audit chain integrity
print("\n[7/8] Testing audit chain integrity...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.initialize()

        audit_logger = AuditLogger(db_manager.get_session)

        # Log multiple events
        for i in range(5):
            audit_logger.log_event(
                event_type=f"test_event_{i}",
                event_data={"index": i}
            )

        # Verify chain integrity
        result = audit_logger.verify_integrity()
        assert result["valid"] == True
        assert result["total_events"] >= 5  # Plus genesis event

        print("✓ Audit chain integrity verified")
        print(f"  Total events: {result['total_events']}")
        print(f"  Chain valid: {result['valid']}")
        db_manager.close()
except Exception as e:
    print(f"✗ Audit integrity test failed: {e}")
    sys.exit(1)

# Test 8: Application controller
print("\n[8/8] Testing application controller...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Initialize controller
        controller = ApplicationController(config_path)

        assert controller.is_simulation_mode == True  # Safety check
        assert controller.version is not None

        status = controller.get_system_status()
        assert status["database_initialized"] == True

        print("✓ Application controller working")
        print(f"  Version: {controller.version}")
        print(f"  Simulation mode: {controller.is_simulation_mode}")
        print(f"  Database initialized: {status['database_initialized']}")

        controller.shutdown()
except Exception as e:
    print(f"✗ Application controller test failed: {e}")
    sys.exit(1)

# All tests passed!
print("\n" + "=" * 80)
print("✓ ALL PHASE 1 TESTS PASSED!")
print("=" * 80)
print()
print("Foundation components verified:")
print("  ✓ Module imports")
print("  ✓ Configuration system")
print("  ✓ Hashing utilities")
print("  ✓ Database initialization")
print("  ✓ Database models (ORM)")
print("  ✓ Audit logging")
print("  ✓ Audit chain integrity")
print("  ✓ Application controller")
print()
print("Phase 1 is COMPLETE and ready for Phase 2!")
print()
