"""
Unit tests for Reporting and Export Engine (Phase 7).

Tests:
- TemplateEngine syntax (variables, filters, loops, conditionals, CSS inlining)
- PDFGenerator (HTML to PDF, pypdf watermarking and metadata)
- ReportGenerator (Forensic, Sanitization, Case Summary, Audit reports)
- Multi-format exports (HTML, PDF, JSON, CSV)
- SHA-256 seal calculation & tamper-detection verification
- Database persistence and audit logging
"""

from datetime import datetime
from pathlib import Path
import json
import os
import tempfile
import pytest

from forensics_platform.audit.audit_logger import AuditLogger
from forensics_platform.database.models import (
    AuditEvent,
    Case,
    Evidence,
    Operation,
    RecoveredFile,
    Report,
    SanitizationOperation,
)
from forensics_platform.database.session import DatabaseManager
from forensics_platform.reporting.pdf_generator import PDFGenerator
from forensics_platform.reporting.report_generator import (
    ReportFormat,
    ReportGenerator,
    ReportType,
    calculate_file_sha256,
)
from forensics_platform.reporting.template_engine import (
    TemplateEngine,
    format_bytes,
    format_datetime,
    format_hash,
    render_pill,
)


# =============================================================================
# 1. Template Engine Tests
# =============================================================================

def test_template_engine_helpers():
    """Test format helpers (bytes, datetime, hash, pill)."""
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1048576) == "1.00 MB"
    assert format_bytes(None) == "N/A"

    dt = datetime(2026, 9, 8, 12, 0, 0)
    assert "2026-09-08" in format_datetime(dt)
    assert format_datetime(None) == "N/A"

    h = "a" * 64
    assert format_hash(h, length=10) == "aaaaaaaaaa..."
    assert format_hash(None) == "N/A"

    assert "pill-success" in render_pill("valid")
    assert "pill-danger" in render_pill("fail")
    assert "pill-warning" in render_pill("partial")


def test_template_engine_interpolation_and_filters():
    """Test variable interpolation, nested property lookup, and filters."""
    te = TemplateEngine()
    tpl = "Case: {{ case.number }} | Size: {{ size|bytes }} | Status: {{ status|pill }} | Name: {{ name|upper }}"
    ctx = {
        "case": {"number": "CASE-101"},
        "size": 2048,
        "status": "valid",
        "name": "john",
    }
    res = te.render_string(tpl, ctx)
    assert "CASE-101" in res
    assert "2.00 KB" in res
    assert "pill-success" in res
    assert "JOHN" in res


def test_template_engine_conditionals():
    """Test if / elif / else branches with operators."""
    te = TemplateEngine()
    tpl = "{% if val == 'alpha' %}A{% elif val == 'beta' %}B{% else %}Other{% endif %}"
    assert te.render_string(tpl, {"val": "alpha"}) == "A"
    assert te.render_string(tpl, {"val": "beta"}) == "B"
    assert te.render_string(tpl, {"val": "gamma"}) == "Other"

    # Numeric comparisons
    num_tpl = "{% if score >= 80 %}HIGH{% else %}LOW{% endif %}"
    assert te.render_string(num_tpl, {"score": 90}) == "HIGH"
    assert te.render_string(num_tpl, {"score": 50}) == "LOW"


def test_template_engine_loops():
    """Test for loop iteration and loop counter metadata."""
    te = TemplateEngine()
    tpl = "{% for item in items %}[{{ loop.index }}: {{ item }}]{% endfor %}"
    ctx = {"items": ["first", "second", "third"]}
    res = te.render_string(tpl, ctx)
    assert "[1: first][2: second][3: third]" == res


def test_template_engine_inlines_css():
    """Test that default template rendering embeds report.css."""
    te = TemplateEngine()
    css = te.get_inline_css()
    assert len(css) > 100
    assert "--primary" in css


# =============================================================================
# 2. PDF Generator Tests
# =============================================================================

def test_pdf_generator_basic(tmp_path):
    """Test converting simple HTML to PDF."""
    pdf_gen = PDFGenerator()
    out_pdf = tmp_path / "simple_test.pdf"
    html = "<html><body><h1>Forensic Document</h1><p>Certified content.</p></body></html>"

    res = pdf_gen.html_to_pdf(html, out_pdf)
    assert res.exists()
    assert res.stat().st_size > 1000


def test_pdf_generator_watermark_and_metadata(tmp_path):
    """Test watermarked PDF creation and metadata embedding."""
    pdf_gen = PDFGenerator()
    out_pdf = tmp_path / "watermarked.pdf"
    html = "<html><body><h1>Confidential Audit</h1><p>Restricted access evidence.</p></body></html>"

    pdf_gen.html_to_pdf(
        html_content=html,
        output_path=out_pdf,
        watermark="TOP SECRET",
        metadata={
            "title": "Evidence Audit",
            "author": "Forensic Officer",
            "subject": "Case 101",
        },
    )

    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 2000

    # Inspect with pypdf
    import pypdf
    reader = pypdf.PdfReader(str(out_pdf))
    assert len(reader.pages) == 1
    assert reader.metadata.title == "Evidence Audit"
    assert reader.metadata.author == "Forensic Officer"


def test_pdf_generator_add_watermark_in_place(tmp_path):
    """Test add_watermark utility on an existing PDF."""
    pdf_gen = PDFGenerator()
    raw_pdf = tmp_path / "plain.pdf"
    pdf_gen.html_to_pdf("<html><body>Plain text</body></html>", raw_pdf)
    initial_size = raw_pdf.stat().st_size

    pdf_gen.add_watermark(raw_pdf, "WATERMARK TEST")
    assert raw_pdf.exists()
    assert raw_pdf.stat().st_size >= initial_size


# =============================================================================
# 3. Report Generator Integration Tests
# =============================================================================

@pytest.fixture
def test_setup(tmp_path):
    """Setup in-memory/temp database, audit logger, and report generator."""
    db_path = tmp_path / "test_reporting.db"
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()

    audit_logger = AuditLogger(db_manager.get_session)
    reports_dir = tmp_path / "reports"
    generator = ReportGenerator(
        db_manager=db_manager,
        audit_logger=audit_logger,
        reports_dir=reports_dir,
    )

    # Populate sample Case, Evidence, Operation, Recovered Files, Sanitization
    session = db_manager.get_session()
    try:
        case = Case(
            case_number="CASE-2026-001",
            title="Digital Evidence Extraction",
            investigator="Detective Miller",
            status="active",
            description="Investigation into suspect storage media.",
        )
        session.add(case)
        session.commit()

        evidence = Evidence(
            case_id=case.id,
            evidence_number="EVD-001",
            source_type="disk_image",
            device_model="Samsung Flash Drive 64GB",
            capacity=64000000,
            image_path="/tmp/fake_usb.raw",
            sha256="1111222233334444555566667777888899990000111122223333444455556666",
            md5="11112222333344445555666677778888",
        )
        session.add(evidence)
        session.commit()

        operation = Operation(
            case_id=case.id,
            operation_type="file_carving",
            target="/tmp/fake_usb.raw",
            tool_version="CarvingEngine v1.0",
            status="completed",
            start_time=datetime(2026, 9, 8, 10, 0, 0),
            end_time=datetime(2026, 9, 8, 10, 5, 0),
        )
        session.add(operation)
        session.commit()

        # Add Recovered Files
        rf1 = RecoveredFile(
            operation_id=operation.id,
            path=str(tmp_path / "carved_1.jpg"),
            filename="carved_1.jpg",
            detected_type="jpeg",
            mime_type="image/jpeg",
            extension=".jpg",
            size=102400,
            offset=512,
            recovery_method="carving",
            validation_status="valid",
            confidence_score=95,
            sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        rf2 = RecoveredFile(
            operation_id=operation.id,
            path=str(tmp_path / "carved_2.pdf"),
            filename="carved_2.pdf",
            detected_type="pdf",
            mime_type="application/pdf",
            extension=".pdf",
            size=204800,
            offset=2048,
            recovery_method="carving",
            validation_status="valid",
            confidence_score=88,
            sha256="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        session.add_all([rf1, rf2])
        session.commit()

        # Add Sanitization Operation
        sanit_op = Operation(
            case_id=case.id,
            operation_type="drive_sanitization",
            target="/dev/sdb",
            tool_version="SanitizationManager v1.0",
            status="completed",
            start_time=datetime(2026, 9, 8, 11, 0, 0),
            end_time=datetime(2026, 9, 8, 11, 15, 0),
        )
        session.add(sanit_op)
        session.commit()

        sanit_details = SanitizationOperation(
            operation_id=sanit_op.id,
            device="/dev/sdb",
            device_type="usb",
            device_model="SanDisk Ultra",
            device_serial="SD123456789",
            capacity=64000000,
            sanitization_method="Clear (Single-pass Zero)",
            sanitization_standard="NIST SP 800-88 Rev 1",
            pass_count=1,
            pattern_used="0x00",
            verification_method="Statistical LBA Sampling (1,000 sectors)",
            verification_result="pass",
            verification_sample_count=1000,
            verification_failed_samples=0,
            user_confirmation_count=2,
        )
        session.add(sanit_details)
        session.commit()

        case_id = case.id
        carve_op_id = operation.id
        sanit_op_id = sanit_op.id

    finally:
        session.close()

    return {
        "db_manager": db_manager,
        "audit_logger": audit_logger,
        "generator": generator,
        "case_id": case_id,
        "carve_op_id": carve_op_id,
        "sanit_op_id": sanit_op_id,
    }


def test_generate_forensic_report_html_and_pdf(test_setup):
    """Test forensic report generation in HTML and PDF formats."""
    gen: ReportGenerator = test_setup["generator"]
    case_id = test_setup["case_id"]
    op_id = test_setup["carve_op_id"]

    # HTML
    rep_html = gen.generate_forensic_report(
        case_id=case_id,
        operation_id=op_id,
        format="html",
        generated_by="Tester",
    )
    assert rep_html.id is not None
    assert rep_html.report_format == "html"
    assert rep_html.report_type == ReportType.FORENSIC_RECOVERY
    assert len(rep_html.report_hash) == 64
    assert Path(rep_html.file_path).exists()
    content = Path(rep_html.file_path).read_text(encoding="utf-8")
    assert "DIGITAL FORENSICS INVESTIGATION REPORT" in content
    assert "carved_1.jpg" in content
    assert "carved_2.pdf" in content

    # PDF
    rep_pdf = gen.generate_forensic_report(
        case_id=case_id,
        operation_id=op_id,
        format="pdf",
        watermark="EVIDENCE DRAFT",
    )
    assert rep_pdf.id is not None
    assert rep_pdf.report_format == "pdf"
    assert Path(rep_pdf.file_path).exists()
    assert rep_pdf.file_size > 2000


def test_generate_forensic_report_json_and_csv(test_setup):
    """Test forensic report generation in JSON and CSV formats."""
    gen: ReportGenerator = test_setup["generator"]
    case_id = test_setup["case_id"]

    # JSON
    rep_json = gen.generate_forensic_report(case_id=case_id, format="json")
    assert rep_json.report_format == "json"
    data = json.loads(Path(rep_json.file_path).read_text(encoding="utf-8"))
    assert data["report_type"] == ReportType.FORENSIC_RECOVERY
    assert len(data["recovered_files"]) == 2
    assert data["statistics"]["total_files"] == 2

    # CSV
    rep_csv = gen.generate_forensic_report(case_id=case_id, format="csv")
    assert rep_csv.report_format == "csv"
    csv_text = Path(rep_csv.file_path).read_text(encoding="utf-8")
    assert "File ID,Filename,Detected Type" in csv_text
    assert "carved_1.jpg" in csv_text


def test_generate_sanitization_certificate(test_setup):
    """Test NIST SP 800-88 Sanitization Certificate generation in HTML and PDF."""
    gen: ReportGenerator = test_setup["generator"]
    sanit_op_id = test_setup["sanit_op_id"]

    # HTML
    rep_sanit = gen.generate_sanitization_report(
        operation_id=sanit_op_id,
        format="html",
        generated_by="Sanitization Specialist",
    )
    assert rep_sanit.report_type == ReportType.SANITIZATION
    assert rep_sanit.report_format == "html"
    content = Path(rep_sanit.file_path).read_text(encoding="utf-8")
    assert "CERTIFICATE OF MEDIA SANITIZATION" in content
    assert "NIST SP 800-88 REV 1" in content
    assert "SANITIZATION VERIFIED & CERTIFIED (PASS)" in content
    assert "SanDisk Ultra" in content
    assert "/dev/sdb" in content

    # PDF
    rep_sanit_pdf = gen.generate_sanitization_report(
        operation_id=sanit_op_id,
        format="pdf",
        watermark="OFFICIAL CERTIFICATE",
    )
    assert rep_sanit_pdf.report_format == "pdf"
    assert Path(rep_sanit_pdf.file_path).exists()


def test_generate_case_summary_and_audit_report(test_setup):
    """Test case summary dossier and audit trail ledger generation."""
    gen: ReportGenerator = test_setup["generator"]
    case_id = test_setup["case_id"]

    # Case Summary
    rep_summary = gen.generate_case_summary(case_id=case_id, format="html")
    assert rep_summary.report_type == ReportType.CASE_SUMMARY
    assert "FORENSIC CASE SUMMARY REPORT" in Path(rep_summary.file_path).read_text(encoding="utf-8")

    # Audit Trail
    rep_audit = gen.generate_audit_report(case_id=case_id, format="html")
    assert rep_audit.report_type == ReportType.AUDIT_TRAIL
    assert "AUDIT TRAIL & CHAIN OF CUSTODY REPORT" in Path(rep_audit.file_path).read_text(encoding="utf-8")


def test_cryptographic_integrity_and_tamper_detection(test_setup):
    """Test verifying report SHA-256 seal and detecting file tampering."""
    gen: ReportGenerator = test_setup["generator"]
    case_id = test_setup["case_id"]

    # Generate a report
    rep = gen.generate_case_summary(case_id=case_id, format="html")
    report_id = rep.id

    # 1. Verification on untouched file
    is_valid, curr_hash, stored_hash = gen.verify_report_integrity(report_id)
    assert is_valid is True
    assert curr_hash == stored_hash
    assert curr_hash == rep.report_hash

    # 2. Tamper with file
    p = Path(rep.file_path)
    p.write_text(p.read_text(encoding="utf-8") + "<!-- MALICIOUS INJECTION -->", encoding="utf-8")

    # 3. Verification must fail
    is_valid_after, new_hash, original_hash = gen.verify_report_integrity(report_id)
    assert is_valid_after is False
    assert new_hash != original_hash
    assert original_hash == rep.report_hash


def test_list_and_delete_reports(test_setup):
    """Test listing reports, querying metadata, and deletion."""
    gen: ReportGenerator = test_setup["generator"]
    case_id = test_setup["case_id"]

    r1 = gen.generate_case_summary(case_id=case_id, format="html")
    r2 = gen.generate_audit_report(case_id=case_id, format="json")

    reports = gen.list_reports(case_id=case_id)
    assert len(reports) >= 2
    r_ids = [r["id"] for r in reports]
    assert r1.id in r_ids
    assert r2.id in r_ids

    # Delete r1
    success = gen.delete_report(r1.id)
    assert success is True
    assert not Path(r1.file_path).exists()
    assert gen.get_report(r1.id) is None
